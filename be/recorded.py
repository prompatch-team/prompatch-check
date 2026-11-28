"""API 키 없이 서버를 돌리는 "저장된 응답" 모드 (PROMPATCH_AI_MODE=recorded).

- 조건 뽑기(/api/extract): samples/의 지어낸 예시 가이드 4개만 알아보고, contracts/의 조건 목록 예시를 그대로 돌려줘요.
  AI를 부르지 않아요. 모르는 가이드는 422로 거절해요(받은 글을 되돌려 보내지 않아요).
- 셀 수 없는 조건 판단(/api/judge)은 AI 없이 코드로 센 결과만 돌려줘요.
- ai/ 코드가 없는 저장소(AI PR 전)에서는 늘 이 모드예요. ai/가 있어도 PROMPATCH_AI_MODE=recorded면 이 모드예요.
- 지어낸 예시만 써요. 실제 가이드를 AI에 넣은 응답은 여기에 두지 않아요.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV = "PROMPATCH_AI_MODE"
# (지어낸 가이드, 그 가이드의 조건 목록 예시)
EXAMPLES = (
    ("guide-sample.md", "conditions.example.json"),
    ("guide-sample-2.md", "conditions.example-2.json"),
    ("guide-04.md", "conditions.example-3.json"),
    ("guide-05.md", "conditions.example-4.json"),
)
UNKNOWN = "API 키 없이 도는 모드라서 저장된 예시 가이드(samples/의 지어낸 가이드 4개)만 읽을 수 있어요."


def active(ai_ready: bool) -> bool:
    """저장된 응답 모드인지. ai/ 코드가 없거나 PROMPATCH_AI_MODE=recorded면 그래요."""
    return not ai_ready or os.environ.get(ENV, "").strip().lower() == "recorded"


def squash(text: str) -> str:
    """줄바꿈 모양과 줄 끝 공백, 앞뒤 빈 줄만 맞춰요 (fe/api.js의 예시 모드와 같은 규칙)."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    return "\n".join(line.rstrip(" \t") for line in lines).strip()


def conditions(guide: str) -> dict | None:
    """예시 가이드면 그 조건 목록, 아니면 None."""
    want = squash(guide)
    for guide_file, doc_file in EXAMPLES:
        if squash((ROOT / "samples" / guide_file).read_text(encoding="utf-8")) == want:
            return json.loads((ROOT / "contracts" / doc_file).read_text(encoding="utf-8"))
    return None


def load_env(path: Path = ROOT / ".env") -> None:
    """.env의 KEY=VALUE를 환경 변수로 읽어요. 이미 있는 값은 건드리지 않고, 아무것도 출력하지 않아요.
    ponytail: ai/extract.py의 load_env와 같은 6줄이에요. ai/가 없는 저장소에서도 서버가 .env를 읽어야 해서 따로 둬요."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        key, sep, value = line.strip().partition("=")
        if sep and key and not key.startswith("#"):
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))
