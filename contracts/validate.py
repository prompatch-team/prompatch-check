"""연결 형식 확인: 내가 만든 JSON이 약속한 형식에 맞는지 봐요.

사용법
    pip install jsonschema
    python contracts/validate.py conditions  내파일.json
    python contracts/validate.py check-request 내파일.json
    python contracts/validate.py check-result  내파일.json
파일을 안 주면 예시 파일(*.example.json)을 확인해요.
"""
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

HERE = Path(__file__).parent
KINDS = ("conditions", "check-request", "check-result")


def check(kind: str, path: Path) -> int:
    schema = json.loads((HERE / f"{kind}.schema.json").read_text(encoding="utf-8"))
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(data), key=lambda e: list(e.path))
    if not errors:
        print(f"OK  {kind}: {path}")
        return 0
    print(f"형식이 달라요  {kind}: {path}")
    for e in errors:
        where = "/".join(str(p) for p in e.path) or "(맨 위)"
        print(f"  - {where}: {e.message}")
    return 1


def main() -> int:
    if len(sys.argv) >= 2:
        kind = sys.argv[1]
        if kind not in KINDS:
            print(f"종류는 {', '.join(KINDS)} 중 하나예요")
            return 2
        path = Path(sys.argv[2]) if len(sys.argv) >= 3 else HERE / f"{kind}.example.json"
        return check(kind, path)
    return max(check(k, HERE / f"{k}.example.json") for k in KINDS)


if __name__ == "__main__":
    sys.exit(main())
