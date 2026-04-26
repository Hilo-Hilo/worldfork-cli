from __future__ import annotations


def multiverse_label(parent_label: str | None, sibling_index: int | None) -> str:
    if not parent_label:
        return "M1"
    if sibling_index is None or sibling_index < 1:
        raise ValueError("sibling_index must be >= 1 for child multiverses")
    return f"{parent_label}.{sibling_index}"


def tick_label(ui_multiverse_label: str, tick_index: int) -> str:
    if tick_index < 0:
        raise ValueError("tick_index must be >= 0")
    return f"{ui_multiverse_label}:T{tick_index}"


def next_child_label(parent_label: str, existing_child_count: int) -> str:
    return multiverse_label(parent_label, existing_child_count + 1)
