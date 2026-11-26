# be: 원고에서 세고 결과 돌려주기 (감자)

조건 목록과 원고를 받아 조건마다 지킴·빠짐·판단 보류를 정하고 `contracts/check-result.schema.json` 형식으로 돌려줘요. 배포와 전체 흐름(US5) owner예요.

- **입력**: 점검 요청 (`contracts/check-request.example.json`) + 조건 목록 (`contracts/conditions.example.json`)
- **출력**: 점검 결과 (`contracts/check-result.example.json`)
- AI 자리는 처음에 `conditions.example.json`으로 대신해요. 연결 ①이 되면 훈의 결과로 바꿔요.

## 세는 규칙 (초안, 정답지와 같아야 해요)

- 키워드: 원고 전체에서 정확히 같은 문자열 개수. 겹치지 않게 앞에서부터 세요.
- 글자 수: `[사진]`, `[지도]` 줄을 뺀 본문. 공백·줄바꿈 제외와 포함을 둘 다 세고, 조건의 `count_spaces`로 골라요.
- 사진 수: 요청의 `photo_count`. 없으면 `hold`.
- 대가성 문구: 원고 첫 3줄 안에 문구가 있으면 지킴.
- 지도: 요청의 `has_map`. 없으면 `hold`.
- `countable: false` 조건: 1주차에는 모두 `hold`.

## 혼자 개발하는 법

1. 예시 조건 목록과 `samples/draft-sample.md`로 세요.
2. 결과를 `python contracts/validate.py check-result 결과.json`으로 확인해요.
3. 숫자가 `criteria/sample-answer-key.md`와 같은지 테스트로 고정해요.

## 여기에 적어 주세요

- 쓰는 언어와 프레임워크: Python 3.13 (세기는 표준 라이브러리만, API는 11/28~29에 정함)
- 실행 방법과 API 주소:
  - 점검 돌리기: `py be/run_check.py contracts/check-request.example.json contracts/conditions.example.json be/out.json`
  - 테스트: `py -m unittest discover -s be/tests -v`
  - 형식 확인: `py contracts/validate.py check-result be/out.json`
  - API 주소: 아직 없음
- 배포 위치: 아직 없음

## 파일

- `counter.py`: 조건 종류별로 세는 코드. `check(요청, 조건 목록)`이 점검 결과를 돌려줘요.
- `run_check.py`: 명령창에서 JSON 파일로 점검을 돌려요.
- `tests/test_counter.py`: 정답지 숫자와 같은지 고정하는 테스트예요.

## 정답지와 맞춘 세는 방법

- 글자 수 공백 포함: `[사진]`, `[지도]` 줄을 뺀 본문을 줄바꿈으로 잇고 앞뒤 빈 줄을 뺀 길이예요. 예시 원고에서 564자로 정답지 메모와 같아요.
- 대가성 문구: 원고의 첫 3줄(빈 줄 포함)에서 문구를 정확히 같은 문자열로 찾아요.
- `countable: false`인 사진 조건(`subject`가 있는 것)은 "사진 내용은 확인할 수 없어요"로 보류해요.
