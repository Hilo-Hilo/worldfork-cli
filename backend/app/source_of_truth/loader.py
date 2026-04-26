from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.source_of_truth.validator import validate_source_of_truth_dir


class SourceOfTruthLoader:
    def __init__(self, root: Path | None = None):
        self.root = (root or get_settings().source_of_truth_dir).resolve()

    def validate(self) -> None:
        validate_source_of_truth_dir(self.root)

    def load_json(self, name: str) -> Any:
        self.validate()
        return json.loads((self.root / name).read_text())

    def load_template(self, name: str) -> str:
        self.validate()
        return (self.root / "report_templates" / name).read_text()
