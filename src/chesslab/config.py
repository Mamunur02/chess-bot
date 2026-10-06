"""Small strict JSON validators shared by the two experiment commands."""

from collections.abc import Mapping


def json_object(value: object, label: str) -> Mapping[str, object]:
    """Require an object with string keys."""
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValueError(f"{label} must be a JSON object")
    return value


def reject_unknown_fields(
    data: Mapping[str, object],
    allowed: set[str],
    label: str,
) -> None:
    """Reject misspelled or unsupported configuration fields."""
    unknown = set(data) - allowed
    if unknown:
        raise ValueError(f"unknown {label} fields: {', '.join(sorted(unknown))}")


def nonempty_string(value: object, label: str) -> str:
    """Require a nonblank string without altering its contents."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value
