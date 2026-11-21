"""Print the OpenAPI schema (the frontend type contract) as stable JSON."""

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("APP_ENV", "test")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402

print(json.dumps(app.openapi(), indent=2, sort_keys=True))
