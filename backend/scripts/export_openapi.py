"""Write the OpenAPI schema (used to generate the frontend's TypeScript types).

python -m scripts.export_openapi ../frontend/openapi.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from app.main import app


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    text = json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n"
    if target:
        target.write_text(text)
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
