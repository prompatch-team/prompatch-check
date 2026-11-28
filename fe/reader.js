// 원고를 읽어 오는 부분. 붙여 넣은 서식(HTML)과 글을 점검 요청(contracts/check-request 0.4)으로 바꿔요.
//
// - 화면(DOM)과 서버를 몰라요. 받은 글자만 다뤄요. 그래서 나중에 크롬 확장으로 옮길 때 이 파일과 analyze.js만
//   가져가면 돼요 (확장의 콘텐츠 스크립트가 에디터 본문을 읽어 Reader.fromPaste에 넘기면 돼요).
// - 실제 분석은 analyze.js(tools/paste-test.html과 같은 코드)가 해요. 서식은 DOMParser로 분석만 하고 화면에 넣지 않아요.
'use strict';

const Reader = {
  // 클립보드의 서식과 글 → { request } 또는 { error: 블로거에게 보여 줄 이유 }
  fromPaste(html, plainRaw) {
    const plain = zw(plainRaw || '').replace(/\r\n?/g, '\n').trim();
    let r = html && html.trim() ? analyze(html) : null;
    if (r && !r.draft) r = null;
    if (!r && !plain) return { error: '클립보드에 글이 없어요. 에디터에서 다시 복사해 주세요.' };
    const request = r ? toRequest(r) : toTextRequest(plain);
    // 스마트에디터 서식이면 본문(draft_text)에 보기 화면 머리(제목·프로파일·작성자 줄)가 없어요.
    // 그래서 글 개수와 제목은 함께 온 글자(text/plain)에서 찾아요. 글자가 없으면 본문에서 찾아요.
    const scan = r && r.seText && plain ? plain : request.draft_text;
    if (Reader.countPosts(scan) > 1) return { error: Reader.MANY_POSTS };
    if (!request.title) request.title = Reader.guessTitle(scan);
    return { request };
  },

  // 10단계: 보기 화면에서 복사한 글 (be/engine.py의 guess_title, count_posts와 같은 규칙)
  MANY_POSTS: '글이 여러 개 들어왔어요. 블로그 화면에서 점검할 글 하나만 열고 복사해 붙여 넣어 주세요.',
  AUTHOR_DATE: /^.{1,40}\s・\s(\d{4}\.\s?\d{1,2}\.\s?\d{1,2}\..*|\d+\s*(초|분|시간|일)\s*전|방금\s*전|어제.*)$/,
  keys(text) { return (text || '').split('\n').map(l => zw(l).split(/\s+/).filter(Boolean).join(' ')); },

  // 모바일 보기 화면 (2026-11-27): 머리 줄이 "프로필"이고, 작성자 이름 줄과 날짜 줄이 따로 와요
  PROFILE: new Set(['프로파일', '프로필']),
  DATE_ONLY: /^(\d{4}\.\s?\d{1,2}\.\s?\d{1,2}\.(\s*\d{1,2}:\d{2})?|\d+\s*(초|분|시간|일)\s*전|방금\s*전|어제.*)$/,
  HEADER_LINES: 5,

  // 제목: [출처] 줄이 있으면 거기서, 없으면 머리 줄(글 맨 위 몇 줄 안의 "프로파일"/"프로필") 바로 위 줄. 없으면 null
  guessTitle(text) {
    const keys = Reader.keys(text);
    // "|작성자"가 있는 [출처] 줄만 (본문의 "[출처] 네이버 지식백과" 같은 인용 줄은 아니에요)
    const source = [...keys].reverse().find(k => k.startsWith('[출처]') && k.includes('|작성자'));
    if (source) return source.slice('[출처]'.length, source.lastIndexOf('|작성자')).trim() || null;
    const filled = keys.map((k, i) => [k, i]).filter(([k]) => k).slice(0, Reader.HEADER_LINES);
    const head = filled.find(([k]) => Reader.PROFILE.has(k));
    if (!head) return null;
    const above = keys.slice(0, head[1]).filter(Boolean);
    return above.length ? above[above.length - 1] : null;
  },

  // 글 개수: 머리 줄 바로 다음(빈 줄 건너뜀)에 작성자 ・ 날짜 줄이 오거나, 작성자 이름 줄과 날짜 줄이 따로 오는 곳의 수
  countPosts(text) {
    const keys = Reader.keys(text).filter(Boolean);
    return keys.filter((k, i) => Reader.PROFILE.has(k) && i + 1 < keys.length && (Reader.AUTHOR_DATE.test(keys[i + 1])
      || (i + 2 < keys.length && keys[i + 1].length <= 20 && Reader.DATE_ONLY.test(keys[i + 2])))).length;
  },

  // 글자 수 미리 보기: [사진] 같은 자리 표시 줄만 빼고 세요. 본문에 직접 쓴 해시태그 줄과 주소 줄은 세요 (2026-11-27 기준).
  // 보기 화면 줄 빼기와 사진 설명 설정은 서버(엔진)만 해서, 미리 보기와 결과가 조금 다를 수 있어요.
  counts(draftText) {
    const marks = new Set(Object.values(MARK));
    return counts(draftText.split('\n').filter(l => !marks.has(l.trim())).join('\n'));
  },
};
