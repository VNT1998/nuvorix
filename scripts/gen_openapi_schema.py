"""OpenAPI Contract Generator Script.

Exports the live OpenAPI JSON specification from the FastAPI control plane application.
Used for contract testing, client SDK generation, and preventing schema drift.
"""

import json
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from apps.api.app.main import app  # noqa: E402


def export_openapi_schema(output_path: str = "docs/openapi.json") -> None:
    schema = app.openapi()
    target_file = Path(output_path)
    target_file.parent.mkdir(parents=True, exist_ok=True)

    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)

    sys.stdout.write(
        f"Exported OpenAPI schema ({len(schema.get('paths', {}))} endpoints) to {output_path}\n"
    )


if __name__ == "__main__":
    export_openapi_schema()
