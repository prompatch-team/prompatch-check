"""서버 기록 자리 (9단계). 지금은 표준 출력에 JSON 한 줄씩 써요. 본격적인 기록은 나중에 해요.

- 남기는 것: 숫자, 정해진 이유 코드, 개수. 예: 점검 시간, AI 호출 시간, 토큰 수, 캐시 읽기 토큰, 오류 이유 코드,
  조건 수(정적/정성), "조건 0개" 같은 이상 징후.
- 남기지 않는 것: 가이드·원고 글, 사진, 개인 정보. 값이 글자면 영문·숫자·코드 기호만 통과하고,
  한글이나 긴 글은 "?"로 바꿔 버려요. 실수로 글을 넘겨도 기록에 남지 않게요.
- 출력 위치는 _write 한 곳에서만 정해요. 파일이나 모니터링 서비스(예: Grafana Cloud)로 보내려면 _write만 바꾸면 돼요.
"""
from __future__ import annotations

import json
import re
import sys
import time

SAFE = re.compile(r"[A-Za-z0-9_.:/\-]{0,80}")      # 이유 코드, 주소 경로, 오류 종류 이름만 통과


def _clean(value, nested: bool = False):
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return value if SAFE.fullmatch(value) else "?"
    if isinstance(value, dict) and not nested:          # 이유 코드별 개수 같은 한 겹짜리 표만
        return {(k if isinstance(k, str) and SAFE.fullmatch(k) else "?"): _clean(v, True) for k, v in value.items()}
    return "?"


def _write(line: str) -> None:
    """출력 위치. 지금은 표준 출력이에요."""
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


def log_event(name: str, **fields) -> None:
    record = {"event": _clean(name), "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    record.update({k: _clean(v) for k, v in fields.items() if SAFE.fullmatch(k)})
    _write(json.dumps(record, ensure_ascii=False, sort_keys=True))


def ms(started: float) -> int:
    """time.perf_counter()로 잰 시작 시각부터 지금까지 밀리초."""
    return round((time.perf_counter() - started) * 1000)
