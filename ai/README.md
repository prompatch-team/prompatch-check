# ai: 가이드에서 조건 뽑기 (훈)

광고주 가이드 원문을 받아 `contracts/conditions.schema.json`(0.3) 형식의 조건 목록을 내보내요.

- **입력**: 가이드 원문 문자열 (예시: `samples/guide-sample.md`)
- **출력**: 조건 목록 JSON (예시: `contracts/conditions.example.json`)과 버린 목록
- **연결 ①** owner예요. 서버(`be/server.py`)는 `ai/`가 있으면 이 코드를 함수로 불러요 (`/api/extract`, `/api/judge`).

## 실행

1. 설치: `pip install -r ai/requirements.txt` / 테스트 (API 안 부름, 가짜 AI 응답): `python -m unittest ai.test_extract ai.test_judge ai.test_security`
2. 예시 가이드로 단독 실행 (`.env`의 `ANTHROPIC_API_KEY`, AI 1번): `python -m ai samples/guide-sample.md --call --compare contracts/conditions.example.json`
3. 서버에 붙여 쓰기: `python -m uvicorn be.server:app --port 8000` (키 없이 돌리려면 `.env`에 `PROMPATCH_AI_MODE=recorded`)

## 하는 일

| 파일 | 하는 일 |
| --- | --- |
| `extract.py` | 가이드 → 조건 목록. 레뷰·강남맛집·리뷰플레이스의 고정 칸은 코드가 먼저 읽고(`source: "rule"`), AI에는 그 칸을 가린 사본만 보내요 |
| `prompt.py` | AI 지침과 응답 형식(JSON 스키마) |
| `judge.py` | 셀 수 없는 조건 판단. 화면 설정에서 켰을 때만 불러요. 근거 문장이 원고에 없으면 판단 보류로 바꿔요 |
| `client.py` | AI API를 부르는 유일한 곳. 시간 제한, 1번 다시 시도, 실패 이유 코드, 토큰으로 계산한 비용 |
| `compare.py`, `__main__.py` | 개발용 명령. 결과는 `ai/cache/`에 저장해서 같은 가이드면 다시 부르지 않아요 (`ai/.gitignore`로 올리지 않아요) |
| `IO.md` | 주고받는 값과 누가 쓰는지 |

## 코드가 확인하는 것 (AI 결과를 그대로 믿지 않아요)

- 조건마다 인용(`guide_quote`)이 가이드 원문에 그대로 있어야 해요. 없으면 버리고, 버린 이유를 버린 목록에 코드로 남겨요.
- 키워드·금지어·문구·주소도 가이드 원문에 있어야 해요. 기준 숫자를 인용에서 확인하지 못하면 `needs_review`를 붙여요.
- 셀 수 있는 조건이 이미 나온 가이드 줄에서 AI가 덧붙인 셀 수 없는 조건은 버려요 (저장된 응답 48개로 쟀을 때 잃은 정답지 항목 0개).
- 셀 수 있는 것도 개수는 세지 않아요. 기준값만 뽑고 세는 건 BE가 해요.

## 여기에 적어 주세요

- 쓰는 언어와 라이브러리: 파이썬 3, `anthropic` SDK. 형식 확인 시험에만 `jsonschema` (없으면 그 시험만 건너뛰어요).
- 쓰는 모델과 프롬프트 위치: 기본 `claude-haiku-5-5`, `.env`의 `PROMPATCH_MODEL`로 바꿔요. 생각(thinking)은 끄고 effort는 medium. 프롬프트는 `prompt.py`.
- 정확도: 실제 가이드 6개를 같은 설정으로 여러 번 부른 평균 약 90% (한 번마다 89~92%, 원문은 저장소 밖). 한 번 부르는 데 약 1.1원 (토큰으로 계산).
