# be 폴더 (BE 영역, 담당 감자)

- 이 폴더 안에서만 파일을 만들고 고쳐요. `ai/`, `fe/` 코드는 만들지 않아요.
- 세는 일은 전부 코드로 해요. LLM을 부르지 않아요.
- 응답은 `contracts/check-result.schema.json`에 맞아야 해요. 숫자는 `criteria/sample-answer-key.md`와 같아야 해요.
- 위치(`draft_spans`)는 요청의 `draft_text` 기준 글자 위치예요.
- 키와 주소는 `.env`에서 읽어요.
