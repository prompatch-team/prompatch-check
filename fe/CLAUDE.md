# fe 폴더 (FE 영역, 담당 리릭)

- 이 폴더 안에서만 파일을 만들고 고쳐요. 서버 코드는 만들지 않아요.
- 서버가 없을 때는 `contracts/check-result.example.json`을 불러와 화면을 그려요.
- 보낼 요청은 `contracts/check-request.schema.json`에 맞춰요.
- 상태 표시는 지킴(`kept`), 빠짐(`missing`), 판단 보류(`hold`) 세 가지예요.
- 원고 위치 표시는 `draft_spans`의 글자 위치를 써요.
