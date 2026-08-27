import json
import sys
from pathlib import Path

from application.api.main import app


def main() -> None:
    output_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("openapi.json")
    output_path.write_text(json.dumps(app.openapi(), indent=2) + "\n")
    print(f"wrote {output_path}")


if __name__ == "__main__":
    main()
