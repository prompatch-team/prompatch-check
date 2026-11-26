# 연결 형식 (contracts)

영역 사이에 주고받는 JSON의 약속이에요. **조건 목록(연결 ①)은 0.2로 확정**했어요. 점검 요청과 결과(연결 ②)는 아직 **초안(0.1-draft)**이에요.

| 연결 | 누가 → 누구 | 파일 | 버전 | owner |
| --- | --- | --- | --- | --- |
| ① 조건 목록 | AI → BE | `conditions.schema.json`, `conditions.example.json`, `conditions.example-2.json`, `-3.json`, `-4.json` | 0.2 | 훈 |
| ② 점검 요청 | FE → BE | `check-request.schema.json`, `check-request.example.json` | 0.1-draft | 리릭 |
| ② 점검 결과 | BE → FE | `check-result.schema.json`, `check-result.example.json` | 0.1-draft | 리릭 |

예시 파일은 `samples/`의 지어낸 가이드·원고로 만들었어요.

- `*.example.json`: `samples/guide-sample.md` + `samples/draft-sample.md`. 숫자는 `criteria/sample-answer-key.md`와 같아요.
- `conditions.example-2.json`: `samples/guide-sample-2.md`(리뷰플레이스 형식)의 조건 목록이에요. 종류 14가지 중 대부분이 들어 있어요.
- `conditions.example-3.json`: `samples/guide-04.md`의 조건 목록이에요. 링크 조건이 가이드 두 곳에서 나와서 `extra_quotes`가 들어 있어요.
- `conditions.example-4.json`: `samples/guide-05.md`의 조건 목록이에요. 코드가 직접 읽은 조건(`source: "rule"`)과 확인하지 못한 조건(`params.unverified`)이 들어 있어요.
- 예시 2~4는 **형식 예시**예요. 정답지가 아니에요.

## 조건 목록 (연결 ①) 0.2

`version`은 `"0.2"`여야 해요. 다른 값이면 형식 오류예요.

0.1-draft에서 바뀐 것:

- 조건 종류가 6가지에서 14가지로 늘었어요.
- `keyword_count`의 `keyword`(하나)가 `keywords`(목록)로 바뀌고 `pick`, `scope`가 생겼어요.
- 맨 위에 `platform`, `campaign_type`이 생겼어요.
- 조건에 `extra_quotes`, `source`, `params.needs_review`, `params.unverified`를 넣을 수 있어요. 모두 없어도 돼요.

### 맨 위

| 필드 | 뜻 |
| --- | --- |
| `version` | `"0.2"` |
| `guide_id` | 가이드 이름. 없어도 돼요 |
| `platform` | 가이드 형식. 리뷰플레이스 형식이면 `"reviewplace"`, 아니면 `null` |
| `campaign_type` | `"체험"`, `"기자단"`, 모르면 `null` |
| `conditions` | 조건 목록 |

### 조건 하나

조건마다 `id`, `type`, `label`, `countable`, `params`, `guide_quote`(가이드 원문과 글자 위치)가 있어요.

- `guide_quote.text`는 가이드 원문에 그대로 있어야 해요. 없으면 그 조건은 버려요.
- 글자 위치(`start`, `end`)는 코드 포인트로 세요. 이모지 1개가 1글자예요. 파이썬은 문자열 위치 그대로, JS는 `Array.from(글)`으로 나눈 뒤의 위치예요. `end`는 포함하지 않아요.
- `extra_quotes`: 같은 조건을 가이드의 두 곳이 말하면(구매 링크 줄과 리뷰어 미션의 "링크 삽입") 조건은 하나로 두고 나머지 원문을 여기에 넣어요. `guide_quote`와 같은 모양의 목록이에요.
- `source`: `"rule"`이면 코드가 리뷰플레이스 고정 칸에서 직접 읽어 만든 조건이에요. `"ai"`이거나 없으면 AI가 뽑고 코드가 확인한 조건이에요.

| type | 뜻 | params 예 | 판정 |
| --- | --- | --- | --- |
| `title_keyword` | 제목 키워드 | `{"keywords": ["녹차스틱", "바다숲녹차"], "pick": "any"}` | 코드 |
| `keyword_count` | 본문 키워드 N회 | `{"keywords": [...], "min": 4, "pick": "any", "scope": "body"}` | 코드 |
| `length` | 본문 글자 수 | `{"min": 1000, "count_spaces": false}` (`count_spaces: null` = 가이드가 안 정함) | 코드 |
| `photo_count` | 사진 수 | `{"min": 15}`. 특정 내용의 사진("책상 위 제품 사진 1장")은 `{"min": 1, "subject": "..."}`이고 `countable: false` | 코드 |
| `video_count` | 동영상 수 | `{"min": 1}` | 코드 |
| `link` | 링크 | `{"min": 1, "url": null}` | 코드 |
| `map` | 지도 | `{"position": "bottom"}` (`null` = 위치 무관) | 코드 |
| `hashtag` | 해시태그 | `{"tags": ["#바다숲녹차"], "pick": "each"}` (`pick`이 없으면 `each`) | 코드 |
| `exact_phrase` | 정확한 표기 | `{"allowed": "바다숲 녹차", "forbidden": ["바다숲 녹차 스틱"], "scope": "title"}` | 코드 |
| `banned_terms` | 금지어 | `{"terms": ["효능", "효과"], "category": null, "scope": "title_and_body"}` (`category`만 있으면 `countable: false`) | 코드 / AI |
| `required_phrase` | 필수 문구 | `{"phrase": "*제품이 아닌 원료에 관한 내용입니다", "scope": "body", "after": "원료 특징 문장"}` | 코드 |
| `disclosure` | 대가성 문구 | `{"phrase": null, "position": "top"}` (`phrase`가 `null`일 수 있어요) | 코드 |
| `outside_draft` | 원고 밖 조건 | `{"what": "기간"}` | 표시만 |
| `judgment` | 셀 수 없는 조건 | `{"question": "다른 브랜드와 비교하는 내용이 없는가"}` | `hold` |

- `pick`: `any` = 목록 중 하나라도 기준을 넘으면 지킴, `each` = 모두 넘어야 지킴. `title_keyword`, `keyword_count`, `hashtag`에 써요.
- `scope`: `title`, `body`, `title_and_body`
- "키워드 중 1개를 선택하여 제목 및 #태그에 넣어주세요" 같은 가이드는 조건 두 개로 뽑아요: `title_keyword` 하나와 `hashtag`(`pick: any`) 하나. 둘 다 같은 `guide_quote`를 써요 (`conditions.example-2.json`의 c1, c2).
- `params.needs_review`: `true`이면 기준 숫자를 코드가 인용 문구에서 확인하지 못했다는 뜻이에요 (예: 가이드에 "다섯 번"처럼 한글로 적혀 있음). 어느 type에나 붙을 수 있어요. 조건은 버리지 않고 남겨요.
- `params.unverified`: `true`이면 AI가 낸 조건을 코드가 확인하지 못해 버렸고, 그 자리에 "가이드의 이 부분을 직접 봐 주세요" 안내로 남긴 조건이에요. `type`은 `judgment`예요. `guide_quote`는 코드가 가이드에서 찾은 줄이고, 못 찾았으면 빈 글자(`start` = `end` = 0)예요.

`countable: false`인 조건은 판단하지 않고 `hold`로 돌려줘요.

## 점검 요청과 결과 (연결 ②) 0.1-draft

- 요청: `guide_text`, `draft_text`, `photo_count`(블로거가 입력한 사진 수), `has_map`
- 결과: `summary`(지킴·빠짐·판단 보류 개수)와 조건마다 `status`, `expected`, `actual`, `unit`, `note`, `draft_spans`(원고 안 위치)

상태는 `kept`(지킴), `missing`(빠짐), `hold`(판단 보류) 셋뿐이에요.

## 형식을 바꿀 때

1. owner가 스키마와 예시를 같이 고치고 `version`을 올려요.
2. `python contracts/validate.py`로 예시가 통과하는지 확인해요.
3. PR 제목에 `[연결 ①]` 또는 `[연결 ②]`를 붙이고, 영향받는 사람을 리뷰어로 넣어요.

## 확인하기

```bash
pip install jsonschema
python contracts/validate.py                       # 예시 전부
python contracts/validate.py conditions            # 조건 목록 예시만
python contracts/validate.py conditions out.json   # 내가 만든 파일
```
