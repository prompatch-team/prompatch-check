"""명령줄에서 한 번 돌려 보기: python -m be <조건 목록.json> <점검 요청.json>

점검 결과 JSON만 내보내요. 받은 원고 글은 내보내지 않아요.
"""
import json
import sys
from pathlib import Path

from .engine import check

if len(sys.argv) != 3:
    sys.exit("사용법: python -m be <조건 목록.json> <점검 요청.json>")
conditions, request = (json.loads(Path(p).read_text(encoding="utf-8")) for p in sys.argv[1:])
sys.stdout.reconfigure(encoding="utf-8")
json.dump(check(conditions, request), sys.stdout, ensure_ascii=False, indent=2)
