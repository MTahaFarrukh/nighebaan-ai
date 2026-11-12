"""Export public OpenAPI contracts without requiring a running API server."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.main import app

path = Path(__file__).resolve().parents[2] / "frontend/openapi.json"
path.write_text(json.dumps(app.openapi(), indent=2), encoding="utf-8")
