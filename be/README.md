# be: 원고에서 세고 결과 돌려주기 (감자)

조건 목록과 원고를 받아 조건마다 지킴·빠짐·판단 보류를 정하고 `contracts/check-result.schema.json`(0.4) 형식으로 돌려줘요. 배포와 전체 흐름(US5) owner예요.

- **입력**: 점검 요청 (`contracts/check-request.example.json`) + 조건 목록 (`contracts/conditions.example.json`)
- **출력**: 점검 결과 (`contracts/check-result.example.json`)

## 실행 (API 키 없이)

1. 설치: `pip install -r be/requirements.txt` / 테스트: 저장소 맨 위에서 `python -m unittest` (모든 영역 테스트를 한 번에 돌려요)
2. 엔진만 한 번: `python -m be contracts/conditions.example.json contracts/check-request.example.json`
3. 서버: `python -m uvicorn be.server:app --port 8000` (`ai/` 코드가 없거나 `.env`에 `PROMPATCH_AI_MODE=recorded`면 `samples/`의 예시 가이드 4개만 읽는 저장된 응답 모드예요)

## 파일

| 파일 | 하는 일 |
| --- | --- |
| `engine.py` | 규칙 엔진. `check(조건 목록, 점검 요청)` → 점검 결과. 조건 14가지, 원칙 점검 p1~p7, 도움이 될 팁 |
| `phrases.py` | 문구 목록 (대가성 표현, 모호한 표현, 조사, 팁의 짧은 틀). **우리 기준**이라 여기만 고치면 돼요 |
| `server.py` | 서버. 조건 뽑기(`/api/extract`)와 점검(`/api/check`)을 이어 줘요 |
| `recorded.py` | API 키 없이 도는 저장된 응답 모드. 지어낸 예시 가이드면 `contracts/`의 조건 목록 예시를 돌려줘요 |
| `events.py` | 서버 기록. 숫자와 정해진 코드만 남기고 받은 글은 남기지 않아요 |
| `__main__.py` | 명령줄에서 엔진 한 번 돌리기 |
| `test_engine.py`, `test_recorded.py` | 엔진·서버 시험. API를 부르지 않아요. fastapi가 없으면 서버 시험만 건너뛰어요 |
| `counter.py`, `run_check.py`, `tests/` | 감자님 PR #14. 형식 0.1 기준이고 지금도 그대로 돌아요(테스트 9개). 엔진과 같은 일을 해서, 지울지는 감자님이 정해 주세요 |

## 감자님 PR #14에서 이어받은 것

- 기준 숫자(`min`)가 없으면 1 같은 값을 지어내지 않고 판단 보류: `engine.py`의 `NEEDS_MIN`, `NO_MIN` (`counter.py`의 "기준 횟수가 없어서 판단하지 않아요")
- 띄어쓰기가 다르면 키워드로 세지 않는다는 시험: `test_engine.py`의 `FromCounter`
- 키워드를 겹치지 않게 앞에서부터 찾는 방식은 같아요 (`engine.find_all`)

## 서버

| 주소 | 받는 것 | 돌려주는 것 |
| --- | --- | --- |
| `POST /api/extract` | `{"guide", "ai", "form"}` | `{"conditions", "dropped", "form"}` (`contracts/README.md`의 "조건 뽑기 주소") |
| `POST /api/check` | `{"conditions", "request"}` | 점검 결과. AI를 부르지 않아요 |
| `POST /api/judge` | `{"conditions", "request"}` | 점검 결과. 셀 수 없는 조건만 AI가 채워요 (저장된 응답 모드에서는 `/api/check`와 같아요) |
| `POST /api/feedback` | `{"consent": true, "kind", "id", "label", "status"}` | 동의했을 때만 조건 이름과 판정을 `be/data/`에 저장 |
| `POST /api/timing` | `{"first_ms", "full_ms", "ai"}` | 화면이 잰 시간(숫자만) |
| `GET /api/health` | - | `{"ok": true}` |

- 서버가 밖으로 보내는 요청은 AI API 하나뿐이에요. 네이버나 체험단 플랫폼에 접속하지 않아요.
- 받은 가이드·원고 글은 파일, DB, 로그에 남기지 않아요. 오류가 나면 오류 종류와 주소만 남겨요.
- 한도: 가이드 20,000자, 원고 60,000자, 요청 본문 400KB, 조건 80개. AI를 부르는 주소는 IP 하나가 10분에 10번, 서버 전체가 하루 500번 (`.env`로 바꿔요, `.env.example`).
- IP별 한도는 `X-Forwarded-For`를 그대로 믿지 않아요. 프록시 뒤에 두면 `PROMPATCH_PROXY_HOPS`에 믿는 프록시 수를 적어요.

## 세는 규칙

형식과 공통 규칙(글자 위치, 글자 수, 키워드, 링크)은 `contracts/README.md`를 따라요. 아래는 엔진에서 정한 것이에요.

| type | 판정 |
| --- | --- |
| `title_keyword` | 제목에 키워드가 있는지. 제목을 모르면(`null`) 판단 보류 |
| `keyword_count` | 정확히 같은 문자열을 겹치지 않게 앞에서부터 세요. 본문 해시태그 안의 것도 세고 `note`에 나눠 적어요. `any`는 가장 많이 쓴 키워드 기준 |
| `length` | `[사진]` `[동영상]` `[지도]` 줄을 뺀 본문 글 블록. 가이드가 공백 기준을 안 정했으면 공백 포함으로 판정 |
| `photo_count`, `video_count` | 요청의 숫자. `null`이면 판단 보류. 사진 수만은 원고의 "대표사진" 줄 수로도 셀 수 있어요 |
| `map` | "하단"은 지도 뒤에 글 문단이 없을 때. 위치를 모르면 판단 보류 |
| `link` | 요청의 `links`와 본문에 적힌 주소. 같은 주소는 1개로 |
| `hashtag` | 요청의 `hashtags`에 있는지. `pick`이 없으면 `each` |
| `exact_phrase` | 금지 표기가 있으면 빠짐. 허용 표기는 없어도 지킴 |
| `banned_terms` | 금지어가 든 곳은 전부 빠짐 |
| `required_phrase` | 문구가 없으면 빠짐. 있는데 `after`가 있으면 판단 보류 |
| `disclosure` | 제목 또는 본문 첫 문단에 있으면 지킴. 맨 위 체험단 배너도 대가성 표시로 봐요 |
| `outside_draft`, `judgment`, `countable: false` | 판단 보류. `note`에 "이 조건은 직접 확인해 주세요" |

- **본문 첫 문단** = 첫 글 줄부터 첫 빈 줄(또는 사진·동영상·지도 줄) 전까지.
- **편집 화면 줄·보기 화면 줄·숨은 문자·자모가 나뉜 한글**: 세지 않거나 합쳐서 세요. 위치(`draft_spans`)는 받은 `draft_text` 그대로예요.
- **원칙 점검**: p1~p7은 `contracts/README.md`의 표대로예요. 숫자 기준(2배, 3개, 30자)은 `engine.py` 맨 위에 있고 `note`에 "우리 기준"이라고 적어요.
- **글자 수가 `counter.py`와 달라요**: 공백 포함은 엔진이 줄바꿈을 세지 않아서 예시 원고에서 550자, `counter.py`는 564자예요. 형식 0.4 기준은 엔진 쪽이에요.
