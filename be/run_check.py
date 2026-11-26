"""명령창에서 점검을 돌려 결과 JSON을 만들어요.

사용법 (저장소 맨 위 폴더에서):
    py be/run_check.py contracts/check-request.example.json contracts/conditions.example.json be/out.json
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from counter import check  # noqa: E402


def main():
    if len(sys.argv) != 4:
        print("사용법: py be/run_check.py <점검요청.json> <조건목록.json> <결과.json>")
        sys.exit(1)
    req_path, cond_path, out_path = sys.argv[1:]
    request = json.loads(Path(req_path).read_text(encoding="utf-8"))
    conditions = json.loads(Path(cond_path).read_text(encoding="utf-8"))
    result = check(request, conditions)
    Path(out_path).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    s = result["summary"]
    print(f"지킴 {s['kept']} · 빠짐 {s['missing']} · 판단 보류 {s['hold']} → {out_path}")


if __name__ == "__main__":
    main()
