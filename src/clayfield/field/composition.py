"""Deterministic composition of normalized source fields."""

from __future__ import annotations

import numpy as np

from clayfield.field.model import FieldMetadata, NormalizedField


_OPERATIONS = {"add", "subtract", "multiply", "minimum", "maximum", "blend"}
_RANGE_POLICIES = {"clip", "normalize"}


def compose_fields(
    primary: NormalizedField,
    secondary: NormalizedField,
    *,
    operation: str = "blend",
    amount: float = 1.0,
    mask: NormalizedField | None = None,
    range_policy: str = "clip",
) -> NormalizedField:
    """Combine two equal-sized fields using an explicit range policy.

    ``amount`` controls how much of the operation result replaces the primary
    field. A mask scales that replacement per sample. This keeps composition
    predictable for both bounded operations and additive displacement.
    """
    if primary.shape != secondary.shape:
        raise ValueError("Fields must have the same shape for composition")
    if mask is not None and mask.shape != primary.shape:
        raise ValueError("Mask must have the same shape as composed fields")
    if operation not in _OPERATIONS:
        raise ValueError(f"Unsupported field composition operation: {operation}")
    if range_policy not in _RANGE_POLICIES:
        raise ValueError("Field range policy must be clip or normalize")
    if not np.isfinite(amount) or not 0.0 <= amount <= 1.0:
        raise ValueError("Composition amount must be between 0 and 1")

    first = primary.values
    second = secondary.values
    if operation == "add":
        operation_result = first + second
    elif operation == "subtract":
        operation_result = first - second
    elif operation == "multiply":
        operation_result = first * second
    elif operation == "minimum":
        operation_result = np.minimum(first, second)
    elif operation == "maximum":
        operation_result = np.maximum(first, second)
    else:
        operation_result = second

    effective_amount = amount
    if mask is not None:
        effective_amount = effective_amount * mask.values
    result = first + (operation_result - first) * effective_amount
    if range_policy == "normalize":
        minimum, maximum = float(result.min()), float(result.max())
        result = (result - minimum) / (maximum - minimum) if maximum > minimum else np.zeros_like(result)
    else:
        result = np.clip(result, 0.0, 1.0)
    metadata = FieldMetadata(
        source_type="composite",
        algorithm=f"compose_{operation}",
        algorithm_version="1",
        tileable=primary.metadata.tileable and secondary.metadata.tileable and (mask is None or mask.metadata.tileable),
    )
    return NormalizedField(np.asarray(result, dtype=np.float32), metadata)
