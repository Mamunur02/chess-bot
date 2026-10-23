"""Optional PyTorch value model and protocol-v1 training utilities.

This module is intentionally not imported by :mod:`chesslab.endgames` so the
standard package remains usable without PyTorch. Neural experiments use the
CPU-compatible PyTorch API and receive their random seeds explicitly.
"""

from __future__ import annotations

import copy
import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Literal

import chess
import torch  # type: ignore[import-not-found]
from torch import Tensor, nn

from chesslab.endgames.encoding import INPUT_SIZE, encode_board
from chesslab.endgames.identity import derive_seed

HIDDEN_WIDTH = 128
RL_LEARNING_RATE = 0.0001
RL_GRADIENT_NORM_LIMIT = 5.0
TARGET_UPDATE_INTERVAL = 250
PRETRAIN_LEARNING_RATE = 0.001
PRETRAIN_BATCH_SIZE = 256
PRETRAIN_MAX_EPOCHS = 30
PRETRAIN_PATIENCE = 5
PRETRAIN_MIN_DELTA = 0.0001


def derive_torch_seed(root_seed: int, stream_name: str) -> int:
    """Derive an explicit non-negative 63-bit seed for ``torch.Generator``.

    The stable identity helper hashes the documented UTF-8 serialization
    ``protocol-v1|seed|<root_seed>|<stream_name>``. PyTorch generators accept
    signed 64-bit seeds, so this function keeps the low 63 bits of that digest.
    Named streams remain independent and never use Python's ``hash()``.
    """

    return derive_seed(root_seed, stream_name) & ((1 << 63) - 1)


class ValueNetwork(nn.Module):  # type: ignore[misc]
    """The prespecified 775-128-128-1 ReLU MLP with a tanh value output."""

    def __init__(self, root_seed: int) -> None:
        super().__init__()
        if not isinstance(root_seed, int) or isinstance(root_seed, bool):
            raise TypeError("root_seed must be an integer")
        # Linear construction runs its default initializer, so keep those
        # temporary global draws inside fork_rng; all retained weights below
        # use the explicitly seeded local generator.
        with torch.random.fork_rng(devices=[]):
            self.layers = nn.Sequential(
                nn.Linear(INPUT_SIZE, HIDDEN_WIDTH),
                nn.ReLU(),
                nn.Linear(HIDDEN_WIDTH, HIDDEN_WIDTH),
                nn.ReLU(),
                nn.Linear(HIDDEN_WIDTH, 1),
                nn.Tanh(),
            )
        generator = torch.Generator(device="cpu")
        generator.manual_seed(derive_torch_seed(root_seed, "initialization"))
        for layer in self.layers:
            if isinstance(layer, nn.Linear):
                nn.init.kaiming_uniform_(
                    layer.weight,
                    a=math.sqrt(5),
                    generator=generator,
                )
                bound = 1 / math.sqrt(layer.in_features)
                nn.init.uniform_(
                    layer.bias,
                    -bound,
                    bound,
                    generator=generator,
                )

    def forward(self, features: Tensor) -> Tensor:
        """Return one bounded value for each encoded position."""

        if features.shape[-1] != INPUT_SIZE:
            raise ValueError(f"expected {INPUT_SIZE} input features")
        return self.layers(features)


class BatchPredictor:
    """Evaluate full-history board encodings in one no-gradient batch."""

    def __init__(self, model: ValueNetwork) -> None:
        self.model = model
        self.boards_evaluated = 0
        self.batch_calls = 0

    def predict(
        self,
        positions: Sequence[tuple[chess.Board, chess.Color]],
    ) -> tuple[float, ...]:
        """Return detached Python floats for ``(board, learner colour)`` pairs."""

        if not positions:
            return ()
        device = next(self.model.parameters()).device
        encoded = [encode_board(board, learner) for board, learner in positions]
        features = torch.tensor(encoded, dtype=torch.float32, device=device)
        with torch.no_grad():
            values = self.model(features).reshape(-1).detach().cpu().tolist()
        self.boards_evaluated += len(positions)
        self.batch_calls += 1
        return tuple(float(value) for value in values)

    def __call__(
        self,
        boards: Sequence[chess.Board],
        learner: chess.Color,
    ) -> tuple[float, ...]:
        """Implement the target predictor protocol for one learner colour."""

        return self.predict(tuple((board, learner) for board in boards))


def value_loss(predictions: Tensor, targets: Tensor | Sequence[float]) -> Tensor:
    """Return the protocol's batch mean of ``0.5 * (prediction-target)^2``."""

    target_values = torch.as_tensor(
        targets,
        dtype=predictions.dtype,
        device=predictions.device,
    ).detach()
    prediction_values = predictions.reshape(-1)
    target_values = target_values.reshape(-1)
    if prediction_values.numel() != target_values.numel():
        raise ValueError("prediction and target batch sizes must match")
    return 0.5 * torch.mean(torch.square(prediction_values - target_values))


def _require_finite_gradients(parameters: Sequence[nn.Parameter]) -> None:
    """Raise before an optimizer step if any parameter gradient is invalid."""

    for parameter in parameters:
        if parameter.grad is not None and not torch.isfinite(parameter.grad).all():
            raise ValueError("gradient is not finite")


def _require_finite_parameters(parameters: Sequence[nn.Parameter]) -> None:
    """Raise when an optimizer step has produced invalid model parameters."""

    if any(not torch.isfinite(parameter).all() for parameter in parameters):
        raise ValueError("model parameter is not finite")


@dataclass(frozen=True, slots=True)
class UpdateResult:
    """Metrics from one completed online optimizer update."""

    loss: float
    gradient_norm_before_clipping: float
    update_number: int
    target_updated: bool


class RLValueTrainer:
    """Online value updates with a frozen target copied every 250 updates."""

    def __init__(
        self,
        online: ValueNetwork,
        *,
        learning_rate: float = RL_LEARNING_RATE,
        gradient_norm_limit: float = RL_GRADIENT_NORM_LIMIT,
        target_update_interval: int = TARGET_UPDATE_INTERVAL,
    ) -> None:
        if learning_rate <= 0 or gradient_norm_limit <= 0:
            raise ValueError("learning rate and gradient norm limit must be positive")
        if target_update_interval <= 0:
            raise ValueError("target update interval must be positive")
        self.online = online
        self.target = copy.deepcopy(online)
        self.target.eval()
        self.target.requires_grad_(False)
        self.optimizer = torch.optim.Adam(self.online.parameters(), lr=learning_rate)
        self.gradient_norm_limit = gradient_norm_limit
        self.target_update_interval = target_update_interval
        self.updates = 0

    def target_values(self, features: Tensor) -> Tensor:
        """Evaluate the frozen target and return detached one-dimensional values."""

        device = next(self.target.parameters()).device
        with torch.no_grad():
            return self.target(features.to(device)).reshape(-1).detach()

    def update_batch(
        self,
        features: Tensor,
        targets: Tensor | Sequence[float],
    ) -> UpdateResult:
        """Apply one Adam update, clipping global gradient norm at five."""

        device = next(self.online.parameters()).device
        batch = features.to(device=device, dtype=torch.float32)
        self.optimizer.zero_grad(set_to_none=True)
        loss = value_loss(self.online(batch), targets)
        if not torch.isfinite(loss):
            raise ValueError("loss is not finite")
        loss.backward()
        parameters = tuple(self.online.parameters())
        _require_finite_gradients(parameters)
        norm = torch.nn.utils.clip_grad_norm_(
            parameters,
            max_norm=self.gradient_norm_limit,
        )
        if not torch.isfinite(norm):
            self.optimizer.zero_grad(set_to_none=True)
            raise ValueError("gradient norm is not finite")
        self.optimizer.step()
        _require_finite_parameters(parameters)
        self.updates += 1
        target_updated = self.updates % self.target_update_interval == 0
        if target_updated:
            self.target.load_state_dict(self.online.state_dict())
            self.target.eval()
            self.target.requires_grad_(False)
        return UpdateResult(
            loss=float(loss.detach().cpu().item()),
            gradient_norm_before_clipping=float(norm.detach().cpu().item()),
            update_number=self.updates,
            target_updated=target_updated,
        )


@dataclass(frozen=True, slots=True)
class PretrainingConfig:
    """Prespecified supervised optimizer settings, overrideable for unit tests."""

    learning_rate: float = PRETRAIN_LEARNING_RATE
    batch_size: int = PRETRAIN_BATCH_SIZE
    max_epochs: int = PRETRAIN_MAX_EPOCHS
    patience: int = PRETRAIN_PATIENCE
    min_delta: float = PRETRAIN_MIN_DELTA

    def __post_init__(self) -> None:
        if self.learning_rate <= 0 or self.batch_size <= 0:
            raise ValueError("learning rate and batch size must be positive")
        if not 1 <= self.max_epochs <= PRETRAIN_MAX_EPOCHS:
            raise ValueError("max_epochs must be between 1 and 30")
        if self.patience <= 0 or self.min_delta < 0:
            raise ValueError("patience must be positive and min_delta non-negative")


@dataclass(frozen=True, slots=True)
class EpochRecord:
    """Mean training and validation MSE for one completed epoch."""

    epoch: int
    training_mse: float
    validation_mse: float


@dataclass(frozen=True, slots=True)
class PretrainingResult:
    """Epoch history and the earliest checkpoint with minimum validation MSE."""

    epochs: tuple[EpochRecord, ...]
    best_epoch: int
    best_validation_mse: float
    stop_reason: Literal["early_stopping", "max_epochs"]
    best_state_dict: dict[str, Tensor]


class _EarlyStoppingState:
    """Track actual best checkpoint separately from min-delta patience."""

    def __init__(self, min_delta: float, patience: int) -> None:
        self.min_delta = min_delta
        self.patience = patience
        self.best_validation_mse = math.inf
        self.best_epoch = 0
        self.best_state_dict: dict[str, Tensor] | None = None
        self.early_stop_reference = math.inf
        self.bad_epochs = 0

    def observe(
        self,
        validation_mse: float,
        epoch: int,
        state_dict: dict[str, Tensor],
    ) -> bool:
        """Record the actual earliest best and report whether patience expired."""

        if validation_mse < self.best_validation_mse:
            self.best_validation_mse = validation_mse
            self.best_epoch = epoch
            self.best_state_dict = {
                name: value.detach().cpu().clone() for name, value in state_dict.items()
            }
        if validation_mse < self.early_stop_reference - self.min_delta:
            self.early_stop_reference = validation_mse
            self.bad_epochs = 0
        else:
            self.bad_epochs += 1
        return self.bad_epochs >= self.patience


def _matrix(values: Tensor | Sequence[Sequence[float]], device: torch.device) -> Tensor:
    tensor = torch.as_tensor(values, dtype=torch.float32, device=device)
    if tensor.ndim != 2 or tensor.shape[1] != INPUT_SIZE:
        raise ValueError(f"features must have shape [n, {INPUT_SIZE}]")
    return tensor


def _labels(values: Tensor | Sequence[float], device: torch.device) -> Tensor:
    tensor = torch.as_tensor(values, dtype=torch.float32, device=device).reshape(-1)
    if not torch.isfinite(tensor).all():
        raise ValueError("labels must be finite")
    if torch.any(torch.abs(tensor) > 1):
        raise ValueError("value labels must lie in [-1, 1]")
    return tensor


def pretrain(
    model: ValueNetwork,
    training_features: Tensor | Sequence[Sequence[float]],
    training_labels: Tensor | Sequence[float],
    validation_features: Tensor | Sequence[Sequence[float]],
    validation_labels: Tensor | Sequence[float],
    *,
    seed: int,
    config: PretrainingConfig = PretrainingConfig(),
    deadline_check: Callable[[], bool] | None = None,
    progress_callback: Callable[[EpochRecord], None] | None = None,
) -> PretrainingResult:
    """Train with protocol MSE/Adam settings and restore the earliest best model.

    The explicit CPU shuffle generator is derived from the named
    ``pretraining-shuffle`` stream and is separate from model initialization.
    The routine accepts already encoded examples so dataset access and label
    policy remain with the caller.

    Optional cooperative deadlines raise TimeoutError between bounded operations;
    an in-flight tensor operation cannot be preempted. Completed epochs are sent
    to the callback for caller-owned persistence. Callback exceptions propagate.
    Interrupted training does not restore a checkpoint or return a success result.
    """

    def check_deadline() -> None:
        if deadline_check is not None and deadline_check():
            raise TimeoutError("pretraining deadline exceeded")

    check_deadline()
    device = next(model.parameters()).device
    train_x = _matrix(training_features, device)
    train_y = _labels(training_labels, device)
    validation_x = _matrix(validation_features, device)
    validation_y = _labels(validation_labels, device)
    if len(train_x) == 0 or len(validation_x) == 0:
        raise ValueError("training and validation data must be non-empty")
    if len(train_x) != len(train_y) or len(validation_x) != len(validation_y):
        raise ValueError("feature and label counts must match")

    shuffle_generator = torch.Generator(device="cpu")
    shuffle_generator.manual_seed(derive_torch_seed(seed, "pretraining-shuffle"))
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
    stopping = _EarlyStoppingState(config.min_delta, config.patience)
    records: list[EpochRecord] = []
    stop_reason: Literal["early_stopping", "max_epochs"] = "max_epochs"

    for epoch in range(1, config.max_epochs + 1):
        check_deadline()
        model.train()
        permutation = torch.randperm(len(train_x), generator=shuffle_generator)
        training_sum = 0.0
        for start in range(0, len(train_x), config.batch_size):
            check_deadline()
            indices = permutation[start : start + config.batch_size].to(device)
            batch_x = train_x[indices]
            batch_y = train_y[indices]
            optimizer.zero_grad(set_to_none=True)
            loss = torch.mean(torch.square(model(batch_x).reshape(-1) - batch_y))
            if not torch.isfinite(loss):
                raise ValueError("pretraining loss is not finite")
            loss.backward()
            parameters = tuple(model.parameters())
            _require_finite_gradients(parameters)
            optimizer.step()
            _require_finite_parameters(parameters)
            training_sum += float(loss.detach().cpu().item()) * len(indices)

        check_deadline()
        model.eval()
        with torch.no_grad():
            validation_mse = float(
                torch.mean(torch.square(model(validation_x).reshape(-1) - validation_y))
                .detach()
                .cpu()
                .item()
            )
        if not math.isfinite(validation_mse):
            raise ValueError("validation MSE is not finite")
        record = EpochRecord(
            epoch=epoch,
            training_mse=training_sum / len(train_x),
            validation_mse=validation_mse,
        )
        records.append(record)
        should_stop = stopping.observe(
            validation_mse,
            epoch,
            model.state_dict(),
        )
        if progress_callback is not None:
            progress_callback(record)
        check_deadline()
        if should_stop:
            stop_reason = "early_stopping"
            break

    if stopping.best_state_dict is None:
        raise RuntimeError("pretraining produced no validation checkpoint")
    model.load_state_dict(stopping.best_state_dict)
    model.eval()
    return PretrainingResult(
        epochs=tuple(records),
        best_epoch=stopping.best_epoch,
        best_validation_mse=stopping.best_validation_mse,
        stop_reason=stop_reason,
        best_state_dict=stopping.best_state_dict,
    )
