"""Small signed piece-square residual model with dependency-free inference."""

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path

import chess

from chesslab.config import json_object, reject_unknown_fields
from chesslab.engine.evaluation.material import PIECE_VALUES
from chesslab.games import Player
from chesslab.games.chess import ChessState

FEATURE_SCHEMA = "signed-piece-square-tempo-v1"
FEATURE_COUNT = 385


def piece_feature(square: chess.Square, piece: chess.Piece) -> tuple[int, int]:
    """Return shared piece-square index and White-perspective sign."""
    relative = square if piece.color else chess.square_mirror(square)
    return (piece.piece_type - 1) * 64 + relative, 1 if piece.color else -1


def board_features(state: ChessState) -> tuple[float, ...]:
    """Encode the same features used by sparse runtime evaluation."""
    features = [0.0] * FEATURE_COUNT
    for square, piece in state.piece_map().items():
        index, sign = piece_feature(square, piece)
        features[index] += sign
    features[-1] = 1.0 if state.current_player == 0 else -1.0
    return tuple(features)


@dataclass(frozen=True, slots=True)
class LinearEvaluator:
    """A frozen material-prior correction, bounded well below terminal utility."""

    coefficients: tuple[float, ...]
    clip_cp: int = 2000

    def __post_init__(self) -> None:
        if len(self.coefficients) != FEATURE_COUNT or any(
            type(w) not in (int, float) or not math.isfinite(w)
            for w in self.coefficients
        ):
            raise ValueError("model requires 385 finite numeric coefficients")
        if type(self.clip_cp) is not int or not 0 < self.clip_cp <= 10000:
            raise ValueError("clip_cp must be a positive integer at most 10000")

    def evaluate(self, state: ChessState, perspective: Player) -> int:
        """Return clipped cp from the requested stable player's perspective."""
        if perspective not in (0, 1):
            raise ValueError("perspective must be White (0) or Black (1)")
        value = self.coefficients[-1] * (1 if state.current_player == 0 else -1)
        for square, piece in state.piece_map().items():
            index, sign = piece_feature(square, piece)
            value += sign * (PIECE_VALUES[piece.piece_type] + self.coefficients[index])
        score = round(max(-self.clip_cp, min(self.clip_cp, value)))
        return score if perspective == 0 else -score

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "feature_schema": FEATURE_SCHEMA,
            "coefficients": list(self.coefficients),
            "clip_cp": self.clip_cp,
            "prior": "material-v1",
            "perspective": "white",
        }

    @classmethod
    def from_dict(cls, value: object) -> "LinearEvaluator":
        data = json_object(value, "linear model")
        reject_unknown_fields(
            data,
            {
                "schema_version",
                "feature_schema",
                "coefficients",
                "clip_cp",
                "prior",
                "perspective",
            },
            "linear model",
        )
        if (
            type(data.get("schema_version")) is not int
            or data["schema_version"] != 1
            or data.get("feature_schema") != FEATURE_SCHEMA
            or data.get("prior") != "material-v1"
            or data.get("perspective") != "white"
        ):
            raise ValueError("unsupported model schema/prior/perspective")
        raw = data.get("coefficients")
        if not isinstance(raw, list) or any(type(w) not in (int, float) for w in raw):
            raise ValueError("coefficients must be a numeric array")
        clip = data.get("clip_cp")
        if type(clip) is not int:
            raise ValueError("clip_cp must be an integer")
        return cls(tuple(float(w) for w in raw), clip)

    @classmethod
    def load(cls, path: Path, sha256: str) -> "LinearEvaluator":
        payload = path.read_bytes()
        if hashlib.sha256(payload).hexdigest() != sha256:
            raise ValueError("linear model SHA-256 mismatch")
        return cls.from_dict(json.loads(payload))
