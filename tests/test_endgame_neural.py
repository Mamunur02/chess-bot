"""Optional PyTorch checks for the opponent-dependence value model."""

import chess
import pytest

torch = pytest.importorskip("torch", reason="optional PyTorch neural environment")

import chesslab.endgames.neural as neural  # noqa: E402


def test_network_shape_bounds_reproducibility_and_global_rng_restoration() -> None:
    torch.manual_seed(721)
    rng_before = torch.random.get_rng_state().clone()
    first = neural.ValueNetwork(101)
    assert torch.equal(torch.random.get_rng_state(), rng_before)
    repeated = neural.ValueNetwork(101)
    distinct = neural.ValueNetwork(202)
    assert torch.equal(torch.random.get_rng_state(), rng_before)

    for left, right in zip(first.parameters(), repeated.parameters(), strict=True):
        torch.testing.assert_close(left, right, rtol=0, atol=0)
    assert any(
        not torch.equal(left, right)
        for left, right in zip(first.parameters(), distinct.parameters(), strict=True)
    )
    output = first(torch.zeros((4, 775), dtype=torch.float32))
    assert output.shape == (4, 1)
    assert bool(torch.all(output >= -1))
    assert bool(torch.all(output <= 1))
    assert [
        module.in_features
        for module in first.layers
        if isinstance(module, torch.nn.Linear)
    ] == [
        775,
        128,
        128,
    ]
    assert [
        module.out_features
        for module in first.layers
        if isinstance(module, torch.nn.Linear)
    ] == [
        128,
        128,
        1,
    ]


def test_named_torch_seeds_are_stable_and_separate() -> None:
    assert neural.derive_torch_seed(101, "initialization") == neural.derive_torch_seed(
        101, "initialization"
    )
    assert 0 <= neural.derive_torch_seed(101, "initialization") < 2**63
    assert neural.derive_torch_seed(101, "initialization") != neural.derive_torch_seed(
        101, "replay"
    )


def test_batch_predictor_uses_full_history_and_counts_work() -> None:
    model = neural.ValueNetwork(303)
    predictor = neural.BatchPredictor(model)
    board = chess.Board()
    board.push_uci("g1f3")
    second = chess.Board()
    positions = ((board, chess.WHITE), (second, chess.BLACK))

    values = predictor.predict(positions)
    assert len(values) == 2
    assert all(type(value) is float for value in values)
    assert predictor.boards_evaluated == 2
    assert predictor.batch_calls == 1
    assert predictor.predict(()) == ()
    assert predictor.boards_evaluated == 2
    assert predictor.batch_calls == 1

    protocol_values = predictor((board, second), chess.WHITE)
    assert len(protocol_values) == 2
    assert predictor.boards_evaluated == 4
    assert predictor.batch_calls == 2


def test_protocol_rl_loss_is_half_mean_squared_error_and_detaches_targets() -> None:
    predictions = torch.tensor([1.0, -1.0], requires_grad=True)
    targets = torch.tensor([0.0, 0.0], requires_grad=True)
    loss = neural.value_loss(predictions, targets)
    torch.testing.assert_close(loss, torch.tensor(0.5))
    loss.backward()
    assert predictions.grad is not None
    assert targets.grad is None


def test_rl_update_changes_finite_online_parameters_and_syncs_at_250() -> None:
    online = neural.ValueNetwork(404)
    trainer = neural.RLValueTrainer(online)
    assert not trainer.target.training
    assert all(not parameter.requires_grad for parameter in trainer.target.parameters())
    initial_target = {
        name: value.detach().clone()
        for name, value in trainer.target.state_dict().items()
    }
    features = torch.zeros((4, 775), dtype=torch.float32)
    targets = (1.0, -1.0, 0.5, 0.0)

    first_update = trainer.update_batch(features, targets)
    assert first_update.update_number == 1
    assert not first_update.target_updated
    assert first_update.loss > 0
    assert torch.isfinite(torch.tensor(first_update.gradient_norm_before_clipping))
    assert any(
        not torch.equal(value, initial_target[name])
        for name, value in online.state_dict().items()
    )
    assert all(
        torch.equal(value, initial_target[name])
        for name, value in trainer.target.state_dict().items()
    )
    target_values = trainer.target_values(features)
    assert not target_values.requires_grad
    assert all(parameter.grad is None for parameter in trainer.target.parameters())

    for _ in range(2, 250):
        trainer.update_batch(features, targets)
    final_update = trainer.update_batch(features, targets)
    assert final_update.update_number == 250
    assert final_update.target_updated
    for online_value, target_value in zip(
        trainer.online.state_dict().values(),
        trainer.target.state_dict().values(),
        strict=True,
    ):
        torch.testing.assert_close(online_value, target_value, rtol=0, atol=0)
    assert all(not parameter.requires_grad for parameter in trainer.target.parameters())


def test_early_stopping_patience_and_actual_best_checkpoint_are_separate() -> None:
    state = neural._EarlyStoppingState(min_delta=0.1, patience=2)
    assert not state.observe(1.0, 1, {"weight": torch.tensor([1.0])})
    assert not state.observe(0.95, 2, {"weight": torch.tensor([2.0])})
    assert state.observe(0.94, 3, {"weight": torch.tensor([3.0])})
    assert state.best_epoch == 3
    assert state.best_validation_mse == 0.94
    assert state.best_state_dict is not None
    torch.testing.assert_close(state.best_state_dict["weight"], torch.tensor([3.0]))


def test_pretraining_uses_explicit_shuffle_and_returns_best_state() -> None:
    model = neural.ValueNetwork(505)
    training = torch.zeros((8, 775), dtype=torch.float32)
    labels = torch.tensor([0.0, 0.0, 0.0, 0.0, 1.0, -1.0, 1.0, -1.0])
    validation = torch.zeros((4, 775), dtype=torch.float32)
    validation_labels = torch.zeros(4, dtype=torch.float32)
    rng_before = torch.random.get_rng_state().clone()
    result = neural.pretrain(
        model,
        training,
        labels,
        validation,
        validation_labels,
        seed=101,
        config=neural.PretrainingConfig(batch_size=4, max_epochs=3),
    )
    assert torch.equal(torch.random.get_rng_state(), rng_before)
    assert len(result.epochs) == 3
    assert result.stop_reason == "max_epochs"
    assert 1 <= result.best_epoch <= 3
    assert result.best_validation_mse >= 0
    assert result.best_state_dict
    assert not model.training
    for name, parameter in model.state_dict().items():
        torch.testing.assert_close(parameter, result.best_state_dict[name])


def test_nonfinite_gradient_is_reported_before_rl_update() -> None:
    model = neural.ValueNetwork(9001)
    trainer = neural.RLValueTrainer(model)
    parameter = next(model.parameters())
    parameter.register_hook(lambda gradient: gradient * float("nan"))
    with pytest.raises(ValueError, match="finite"):
        trainer.update_batch(torch.zeros((1, 775)), [1.0])
    assert trainer.updates == 0


def test_nonfinite_validation_is_not_hidden_by_checkpoint_restore() -> None:
    model = neural.ValueNetwork(9001)
    with pytest.raises(ValueError, match="finite"):
        neural.pretrain(
            model,
            torch.zeros((1, 775)),
            [0.0],
            torch.full((1, 775), float("nan")),
            [0.0],
            seed=9001,
            config=neural.PretrainingConfig(max_epochs=1),
        )
