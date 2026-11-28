// 화면 자체 시험. index.html#selftest 로 열면 지어낸 예시로 흐름을 끝까지 눌러 보고 결과를 화면 아래에 적어요.
// index.html#shot-2 … #shot-7 은 그 화면까지만 가요 (캡처할 때). 평소에는 불러오지 않아요 (app.js 맨 아래).
'use strict';

(async () => {
  const checks = [];
  const ok = (name, pass) => checks.push([name, !!pass]);
  const wait = () => new Promise(r => setTimeout(r, 0));
  const settle = async () => { for (let i = 0; i < 6; i++) await wait(); };
  const q = sel => document.querySelector(sel);
  const all = sel => [...document.querySelectorAll(sel)];
  const type = (el, v) => { el.value = v; el.dispatchEvent(new Event('input', { bubbles: true })); };
  const paste = (el, html, plain) => {
    const dt = new DataTransfer();
    if (html) dt.setData('text/html', html);
    if (plain) dt.setData('text/plain', plain);
    el.dispatchEvent(new ClipboardEvent('paste', { clipboardData: dt, bubbles: true, cancelable: true }));
  };
  const sample = async id => { q(`[data-sample="${id}"]`).click(); await wait(); };
  // 가이드의 나머지(AI 몫)까지 다 읽을 때까지 기다려요 (예시 모드는 60ms쯤 걸리는 것처럼 흉내 내요)
  const ready = async () => { for (let i = 0; i < 300 && (S.view !== 'result' || S.aiState === 'reading' || S.checking); i++) await new Promise(r => setTimeout(r, 10)); };
  const run = async id => {
    if (id && S.view !== 'input') { $('edit').click(); await wait(); }
    if (id) await sample(id);
    $('check').click();
    await settle();
    await ready();
  };
  const key = k => q(`[data-key="${k}"]`);
  const A = 'https://example.invalid/';
  const HTML = `<div class="se-component se-text"><p>업체에서 제품을 받아 쓴 글이에요 🍵</p><p>둘째 줄 <a href="${A}a">링크</a></p></div>`
    + `<script>window.__pasted_script_ran = 1</script><p onclick="window.__pasted_script_ran = 1">굵은 <b style="background:url(${A}bg.png)">글</b></p>`
    + `<div class="se-component se-image"><img src="${A}1.jpg" onerror="window.__pasted_script_ran = 1" onload="window.__pasted_script_ran = 1"></div>`
    + `<div class="se-component se-image"><img src="${A}2.jpg"></div><iframe src="${A}frame"></iframe><a href="javascript:window.__pasted_script_ran = 1">누르지 마세요</a>`
    + `<div class="se-component se-sticker"><img src="${A}s.png"></div><div class="se-component se-text"><p>#본문태그</p></div>`;

  // ── 캡처용: 그 화면까지만 가요 ──
  const shot = /^#shot-(\d)$/.exec(location.hash);
  if (shot) {
    const n = Number(shot[1]);
    if (n === 1) { await run('sample-1'); $('tips').open = true; }      // 도움이 될 팁을 펼친 결과 화면
    if (n === 2) await sample('sample-2');
    if (n === 3) await run('sample-2');
    if (n === 4) { await run('sample-3'); q('#notes .pick').click(); }
    if (n === 5) { await sample('sample-2'); S.busy = 'extract'; show('busy', 'busy-title'); }
    if (n === 6) { $('check').click(); await settle(); }
    if (n === 7) await run('sample-4');
    if (n === 8) {                 // 모두 지킨 결과 (캡처용: 예시 2의 결과에서 빠짐을 지킴으로 바꿔 그려요)
      await run('sample-2');
      for (const r of [...S.res.result.results, ...S.res.result.principles]) if (r.status === 'missing') r.status = 'kept';
      render();
    }
    if (n === 9) { await sample('sample-2'); fail('서버에 닿지 못했어요. 인터넷 연결을 확인하고 다시 해 주세요.'); }   // 서버 오류 (캡처용)
    return;
  }

  // ── 서버에서 열었을 때: 진짜 서버를 불러 끝까지 가요 (be/test_server.py가 가짜 AI로 서버를 띄워서 돌려요) ──
  if (location.hash === '#selftest-server') {
    const until = async test => { for (let i = 0; i < 400 && !test(); i++) await new Promise(r => setTimeout(r, 25)); return test(); };
    const two = MOCK.scenarios.find(s => s.id === 'sample-2');
    ok('서버 모드에서는 예시 모드 안내와 예시 버튼이 없고, AI 설정을 켤 수 있음', !Api.mock && $('mode').hidden && !q('[data-sample]') && !$('use-ai').disabled);
    type($('guide'), two.guide);
    Object.assign(S, { base: JSON.parse(JSON.stringify(two.request)), draft: two.request.draft_text, pasted: two.request.draft_text });
    $('settings').open = true;
    $('opt-captions').click();
    $('check').click();
    ok('누르면 점검 중 화면이 먼저 나옴', S.view === 'busy' && !!$('busy'));
    ok('코드 결과를 먼저 보이고, 가이드의 나머지까지 읽으면 교정지가 채워짐 (조건 14개)',
      await until(() => S.view === 'result' && S.aiState === 'done' && !S.checking) && !$('mock-banner')
      && all('#conds-list .cond').length === 14);
    ok('서버가 알아본 가이드 형식을 작게 보여 줌', $('form-line').textContent.startsWith('리뷰플레이스 가이드로 읽었어요'));
    ok('첫 결과·전체 결과까지 걸린 시간을 숫자로 서버에 남김', await until(() =>
      performance.getEntriesByType('resource').some(e => e.name.endsWith('/api/timing'))));
    ok('설정에서 사진 설명을 끄면 점검 요청에 그대로 실림', S.res.request.count_captions === false);
    // 기준 숫자를 확인하지 못한 조건이 있다고 치고 (가짜 AI 결과에는 없어요) "점검에 필요한 것"에서 고쳐 봐요
    const review = S.doc.conditions.find(c => c.type === 'photo_count' && c.countable);
    review.params.needs_review = true;
    render();
    type($(`need-min-${review.id}`), String(review.params.min + 1));
    $('recheck').click();
    const row = id => key(`condition:${id}`);
    ok('확인한 기준 숫자가 결과에 반영됨', await until(() => S.view === 'result' && row(review.id) && row(review.id).classList.contains('missing'))
      && row(review.id).querySelector('.numbers').textContent.includes(`기준 ${review.params.min}`));
    ok('확인한 숫자는 다시 묻지 않음', !$(`need-min-${review.id}`));
    q('[data-remove="c14"]').click();
    ok('뺀 조건은 결과에 없음', await until(() => S.view === 'result' && !S.doc.conditions.some(c => c.id === 'c14')) && !$('outside-list'));
    $('kept-list').open = true;
    row('c3').querySelector('.pick').click();
    // 본문 글 4번 + 본문 해시태그(#바다숲녹차) 1번 (2026-11-27부터 해시태그 안도 세요)
    ok('강조 위치가 원고와 맞음', all('#ms-body mark.on').map(m => m.textContent).join() === Array(5).fill('바다숲녹차').join());
    row('c3').querySelector('.more').open = true;
    q('[data-wrong="c3"]').click();
    $('agree-condition-c3').click();
    q('[data-send="c3"]').click();
    ok('"판정이 틀렸어요"를 서버가 받음', await until(() => q('[data-sent="c3"]')) && q('[data-sent="c3"]').textContent.includes('고마워요'));
    // 셀 수 없는 조건은 켰을 때만 AI로. 코드 결과를 먼저 보여 준 뒤 이어 붙여요
    const quote = S.doc.conditions[0].guide_quote;
    S.doc.conditions.push({ id: 'c99', type: 'judgment', label: '비교 내용 없음', countable: false,
      params: { question: '다른 브랜드와 비교하는 내용이 없는가' }, guide_quote: { ...quote } });
    S.ai = true;
    check();
    ok('코드 결과를 먼저 보여 주고 AI 결과가 오면 이어 붙임', await until(() => S.view === 'result' && !S.judging && row('c99'))
      && row('c99').querySelector('.note').textContent.startsWith('AI 판단(참고용)') && !!row('c99').querySelector('.tag'));
    const judgeCalls = () => performance.getEntriesByType('resource').filter(e => e.name.endsWith('/api/judge')).length;
    const before = judgeCalls();
    check();
    ok('조건과 원고가 그대로면 AI를 다시 부르지 않음', await until(() => S.view === 'result' && !S.judging)
      && judgeCalls() === before && row('c99').querySelector('.note').textContent.startsWith('AI 판단'));
    ok('다시 점검하면 달라진 결과 없음 표시가 없음', !q('.tag.changed'));
    $('edit').click();
    type($('guide'), '가'.repeat(20001));
    $('check').click();
    ok('너무 긴 가이드는 보내기 전에 이유를 알려 줌', S.view === 'input' && $('guide-err').textContent.includes('너무 길어요'));
    type($('guide'), '오늘 점심은 국수를 먹었어요.');
    $('check').click();
    // 서버가 AI를 부르기 전에 거절하거나(위쪽 안내), 조건이 하나도 없으면(가이드 칸 옆 안내) 이유를 말해 줘요
    const why = () => ($('guide-err') && $('guide-err').textContent) || ($('form-error') && $('form-error').textContent) || '';
    ok('가이드가 아닌 글이면 사람이 알아들을 말로 알려 줌', await until(() => S.view === 'input' && why())
      && /가이드 글이 맞는지|가이드를 살펴볼 수 없어요/.test(why()));
    // 원고만 고쳐 다시 점검: 진짜 버튼으로. 가이드가 그대로면 조건을 다시 뽑지 않고, 결과 화면에서 적은 제목도 남아요
    const extracts = () => performance.getEntriesByType('resource').filter(e => e.name.endsWith('/api/extract')).length;
    type($('guide'), two.guide);
    const untitled = JSON.parse(JSON.stringify(two.request));
    untitled.title = null;
    Object.assign(S, { base: untitled, draft: untitled.draft_text, pasted: untitled.draft_text, ai: false });
    render();
    $('check').click();
    await until(() => S.view === 'result');
    type($('need-title'), '바다숲녹차 후기');
    $('recheck').click();
    ok('결과 화면에서 적은 제목이 점검 요청에 실림', await until(() => S.view === 'result' && S.res.request.title === '바다숲녹차 후기'));
    const calls = extracts();
    $('edit').click();
    type($('draft'), $('draft').value + '\n덧붙인 문장이에요.');
    $('check').click();
    ok('원고만 고쳐 다시 점검하면 조건을 다시 뽑지 않고 적은 제목도 남음', await until(() => S.view === 'result' && S.res.request.draft_text.includes('덧붙인'))
      && extracts() === calls && S.res.request.title === '바다숲녹차 후기');
    const local = location.origin;
    ok('우리 서버 말고는 요청이 없음', performance.getEntriesByType('resource').every(e => e.name.startsWith(local)));
    const pass = checks.filter(c => c[1]).length;
    document.body.append(h('section', { id: 'selftest-report' },
      h('h2', { id: 'selftest', class: pass === checks.length ? 'ok' : 'bad', text: `서버 자체 시험 ${pass}/${checks.length} 통과` }),
      h('ol', {}, checks.map(([name, good]) => h('li', { 'data-pass': String(good), text: `${good ? '통과' : '실패'}: ${name}` })))));
    return;
  }

  const logs = [];
  const realLog = console.log;
  try {
  console.log = (...args) => logs.push(args);
  const stray = () => /(^|[^가-힣\w])(false|null|undefined|NaN)([^가-힣\w]|$)/.test($('main').textContent);

  // ── 1. 처음 화면: 두 칸과 버튼 하나 ──
  ok('처음 화면에는 가이드·원고 두 칸과 점검하기 버튼 하나만 보임',
    all('main textarea').length === 2 && all('main .primary').length === 1 && $('check').textContent === '점검하기'
    && all('main input[type="number"], main select').length === 0);
  // 2026-11-27: 글쓰기 화면 복사에는 제목이 오지 않아서 원고 칸 위에 제목 한 줄 (필수 아님)
  ok('원고 칸 위에 제목 한 줄 입력칸이 있고 비워도 됨',
    all('main input[type="text"]').map(i => i.id).join() === 'post-title' && !$('post-title').required
    && !!($('post-title').compareDocumentPosition($('draft')) & Node.DOCUMENT_POSITION_FOLLOWING));
  ok('설정은 접혀 있고 기본값으로 바로 쓸 수 있음 (사진 설명 넣기 켬, AI 끔)',
    !$('settings').open && $('opt-captions').checked && !$('use-ai').checked);
  ok('예시 모드에서는 AI 설정을 켤 수 없음', $('use-ai').disabled);
  ok('주소(URL) 입력칸이 없음', !q('input[type="url"]'));
  $('check').click();
  await settle();
  ok('빈 칸으로 누르면 무엇이 빠졌는지 칸 옆에 알려 줌', S.view === 'input' && $('guide-err').textContent === '가이드를 붙여 넣어 주세요.'
    && $('guide').getAttribute('aria-invalid') === 'true');
  type($('guide'), '가'.repeat(20001));
  $('check').click();
  await settle();
  ok('너무 긴 가이드는 보내기 전에 알려 줌', $('guide-err').textContent.includes('너무 길어요'));
  type($('guide'), '예시가 아닌 가이드');
  type($('draft'), '그냥 쓴 원고예요.');
  $('check').click();
  await settle();
  ok('예시가 아닌 가이드는 예시 모드 안내가 나옴', S.view === 'input' && $('form-error').textContent.includes('예시 가이드만'));

  // ── 2. 원고 붙여 넣기 ──
  paste($('draft'), HTML, '업체에서 제품을 받아 쓴 글이에요 🍵');
  ok('서식째 붙여 넣으면 무엇을 읽었는지 한 줄로 알려 줌 (사진 2장, 스티커 제외)',
    S.base.input_mode === 'html' && S.base.photo_count === 2 && $('draft-read').textContent.includes('사진 2장'));
  ok('붙여 넣은 서식이 화면에 들어가지 않음 (img·iframe·video 0개, 칸에는 글자만)',
    !q('img, iframe, video') && !$('draft').value.includes('<') && $('draft').value.includes('업체에서 제품을 받아'));
  ok('붙여 넣은 서식의 스크립트와 이벤트 속성이 실행되지 않음',
    window.__pasted_script_ran === undefined && !q('[onclick], [onerror], [onload], script:not([src])')
    && !all('a').some(a => (a.getAttribute('href') || '').startsWith('javascript:')));
  ok('javascript: 주소는 링크로 세지 않음', !S.base.links.some(l => l.url.startsWith('javascript:')));
  type($('draft'), $('draft').value + ' 덧붙임');
  ok('붙여 넣은 뒤 글을 고치면 글자만으로 점검하고, 다시 붙여 넣으라고 알려 줌', $('draft-read').textContent.includes('다시 붙여 넣어'));
  const VIEW = ['일상 기록', '솔바람 녹차 후기 | 녹차추천', '', '프로파일', '가나다 ・ 2026. 1. 2. 10:00', 'URL 복사  이웃추가',
    '본문 기타 기능', '', '녹차를 마셨어요.', '[출처] 솔바람 녹차 후기 | 녹차추천|작성자 가나다'].join('\n');
  const before = S.base;
  paste($('draft'), '', VIEW + '\n\n다음 글\n프로파일\n가나다 ・ 2026. 1. 3. 10:00\n본문');
  ok('글이 여러 개 들어오면 점검하지 않고 알려 줌', S.base === before && $('draft-err').textContent === Reader.MANY_POSTS);
  paste($('draft'), '', VIEW);
  ok('보기 화면에서 복사한 글은 [출처] 줄에서 제목을 찾음', S.base.title === '솔바람 녹차 후기 | 녹차추천' && $('draft-err').textContent === '');
  {
    // 모바일 보기 화면 (2026-11-27): 머리 줄 "프로필", 작성자 이름 줄과 날짜 줄이 따로 와요 (지어낸 글)
    const mobile = ['[서울 종로] 솔바람 찻집 후기', '', '프로필', '가나다', '2026. 11. 9. 21:40', '', '본문이에요.'].join('\n');
    ok('모바일 보기 화면 글도 제목과 글 개수를 알아봄',
      Reader.guessTitle(mobile) === '[서울 종로] 솔바람 찻집 후기' && Reader.countPosts(mobile) === 1 && Reader.countPosts(mobile + '\n' + mobile) === 2);
  }
  const banner = `<div class="se-component se-image"><img class="se-image-resource" src="//www.revu.net/campaign/img.php?p=1"></div>`
    + `<img class="img" src="//blogpfthumb-phinf.pstatic.net/x.jpg"><p>본문이에요</p>`
    + `<div class="se-component se-imageGroup"><img class="se-image-resource" src="${A}g1.jpg"><img class="se-image-resource" src="${A}g2.jpg"></div>`
    + `<div class="se-component se-image"><img class="se-image-resource" src="${A}3.jpg"></div><div class="se-component se-oglink"><img src="${A}thumb.jpg"></div>`;
  paste($('draft'), banner, '본문이에요');
  ok('사진 수에서 캠페인 배너·프로필 사진·링크 카드 썸네일은 빼고, 묶음 안의 사진은 하나씩 셈', S.base.photo_count === 3);
  ok('원고 읽기(Reader)와 결과 그리기(results.js)가 따로 있음', typeof Reader.fromPaste === 'function' && typeof proofSheet === 'function');

  // ── 글자 수 기준 (2026-11-27): 스마트에디터 글 블록만 세요. 같은 글을 글자로 붙여 넣은 be/test_engine.py의 SE_TEXT_PASTE와 같은 수 ──
  const T = t => `<div class="se-component se-text"><div class="se-module se-module-text"><p class="se-text-paragraph"><span>${t}</span></p></div></div>`;
  const SE_HTML = `<div class="blog-head"><p>일상 기록</p><p>솔바람 녹차 후기</p><p>프로파일</p></div>`
    + T('솔바람 녹차를 한 달 마셨어요.')
    + `<div class="se-component se-image"><img class="se-image-resource" src="${A}1.jpg">`
    + `<div class="se-module se-module-text se-caption"><p class="se-text-paragraph"><span>아침에 우린 녹차</span></p></div></div>`
    + T(`${A}item`)
    + `<div class="se-component se-oglink"><a href="${A}item"><strong class="se-oglink-title">솔바람 녹차 30포</strong>`
    + `<p class="se-oglink-summary">녹차 전문</p><p class="se-oglink-url">example.invalid</p></a></div>`
    + `<div class="se-component se-imageGroup"><img class="se-image-resource" src="${A}2.jpg"><button>Previous image</button><button>Next image</button></div>`
    + T('향이 좋았어요.') + T('#녹차 #아침차')
    + `<div class="post-tags"><span>태그</span><a>#녹차</a><a>#태그칸만</a></div>`;
  const se = analyze(SE_HTML), seReq = toRequest(se);
  ok('스마트에디터 서식: 글 블록 글자만 세요 (머리·꼬리·태그 칸·링크 카드·단추 빠짐, 본문 해시태그·주소·사진 설명 들어감)',
    JSON.stringify(Reader.counts(se.draft)) === JSON.stringify({ spaces: 70, noSpaces: 62 })        // 줄바꿈은 안 세요 (11/28)
    && !se.draft.includes('프로파일') && !se.draft.includes('30포') && !se.draft.includes('Previous') && !se.draft.includes('태그칸만'));
  ok('사진 설명 자리를 captions로 알려 줌', seReq.captions.length === 1
    && Array.from(seReq.draft_text).slice(seReq.captions[0].start, seReq.captions[0].end).join('') === '아침에 우린 녹차');
  ok('맨 아래 태그 칸의 태그도 해시태그로는 찾음', seReq.hashtags.includes('#태그칸만') && seReq.photo_count === 2);
  const head = '일상 기록\n솔바람 녹차 후기\n\n프로파일\n 가나다 ・ 2026. 1. 2. 10:00\n솔바람 녹차를 한 달 마셨어요.';
  const one = Reader.fromPaste(SE_HTML, head);
  ok('스마트에디터 서식: 제목을 함께 온 글자에서 찾음', one.request && one.request.title === '솔바람 녹차 후기');
  ok('스마트에디터 서식: 글이 여러 개면 함께 온 글자로 알아봄', Reader.fromPaste(SE_HTML, head + '\n' + head).error === Reader.MANY_POSTS);

  // ── 3. 예시 2로 점검: 교정지 ──
  await sample('sample-2');
  ok('예시를 고르면 두 칸이 채워짐', $('guide').value.length > 0 && $('draft').value === S.base.draft_text);
  $('check').click();
  ok('누르면 점검 중 화면이 나옴', S.view === 'busy' && $('busy').getAttribute('aria-live') === 'polite');
  await settle();
  ok('코드가 읽은 결과를 먼저 보여 주고 나머지는 읽는 중이라고 알려 줌',
    S.view === 'result' && S.aiState === 'reading' && $('ai-status').textContent.includes('가이드의 나머지 조건을 읽고 있어요')
    && S.doc.conditions.every(c => c.source === 'rule') && !$('mock-banner'));
  const firstCount = S.doc.conditions.length;
  await ready();
  ok('AI 결과가 오면 이어 붙이고 읽는 중 안내가 사라짐', S.aiState === 'done' && !$('ai-status') && S.doc.conditions.length > firstCount);
  ok('교정지가 보이고 예시 그대로라 안내가 없음', S.view === 'result' && !$('mock-banner'));
  ok('가이드 형식은 묻지 않고 작게 보여 줌 ("리뷰플레이스 가이드로 읽었어요 · 바꾸기")',
    $('form-line').textContent === '리뷰플레이스 가이드로 읽었어요 · 바꾸기' && !$('form-pick'));
  ok('결과 화면에 false, null 같은 글자가 새어 나오지 않음', !stray());
  const fix = S.res.result.results.filter(r => r.status === 'missing' && r.condition_id !== 'c14').length
    + S.res.result.principles.filter(p => p.status === 'missing').length;
  ok('맨 위 한 줄 요약이 고칠 곳 수와 같음', $('summary').textContent === `고칠 곳 ${fix}개` && all('#notes .note-card').length === fix);
  {
    // 제목 칸에 적은 제목이 점검 요청에 실려요. 비우면 받은 원고의 제목(없으면 null)
    const kept = S.extra.title, base = S.request.title;
    S.extra.title = '적은 제목';
    const typed = finalRequest().title;
    S.extra.title = '';
    const blank = finalRequest().title;
    S.extra.title = kept;
    ok('제목 칸에 적은 제목이 요청에 실리고, 비우면 받은 원고의 제목', typed === '적은 제목' && blank === (base || null));
  }
  ok('고칠 곳 메모에 번호가 있으면 원고에도 같은 번호가 붙음',
    all('#notes .note-card[data-n]').every(c => !!q(`#manuscript sup.n[data-n="${c.dataset.n}"]`)));
  ok('원고의 고칠 곳은 빨간 표시로 보임 (키워드 과다 3곳)', all('#ms-body mark.m-miss').length === 3);
  ok('통과한 항목은 접혀 있음', $('kept-list') && !$('kept-list').open && all('#kept .row').length === S.res.result.results.filter(r => r.status === 'kept').length
    + S.res.result.principles.filter(p => p.status === 'kept').length);
  ok('원고 밖 조건은 따로 접어 두고 개수에서 뺌', $('outside-list') && !$('outside-list').open
    && q('#outside-list summary').textContent === '원고 밖에서 확인할 것 1개' && !key('condition:c14'));
  const lookNotes = all('#look .row .note').map(n => n.textContent);
  ok('직접 확인할 것마다 "이 조건은 직접 확인해 주세요"가 있음', lookNotes.length >= 2 && lookNotes.filter(t => t.includes('직접 확인해 주세요')).length >= 2);
  ok('네이버·공정위 점검은 표시와 근거가 있음', all('[data-key^="principle:"] .tag').some(t => t.textContent === '네이버·공정위')
    && all('[data-key^="principle:"] .basis').length === 5);
  ok('기준 숫자를 확인하지 못한 조건은 "점검에 필요한 것"에서만 물어봄', !!$('needs') && !!$('need-min-c12') && !$('need-title'));
  ok('화면 글자에 개발 용어가 없음', !/\b(hold|missing|kept|countable)\b|정적 분석/.test($('main').textContent));
  $('kept-list').open = true;
  key('condition:c3').querySelector('.pick').click();
  const marks = all('#ms-body mark.on').map(m => m.textContent);
  ok('항목을 누르면 원고에서 그 자리가 강조됨 (이모지 뒤에서도 글자가 맞음)',
    marks.length === 5 && marks.every(t => t === '바다숲녹차') && key('condition:c3').classList.contains('on'));
  key('condition:c1').querySelector('.pick').click();
  ok('제목 위치는 제목 줄에서 강조됨', all('#ms-title mark.on').length === 1 && all('#ms-body mark.on').length === 0);
  ok('사진 자리는 글자로만 표시됨', all('#ms-body .media').some(m => m.textContent === '[사진]') && !q('img'));
  const kwLinks = all('#keyword-links a[data-keyword]');
  ok('키워드를 누르면 네이버 검색을 새 탭으로 여는 링크만 있음 (접혀 있음)', !$('keyword-links').open && kwLinks.length > 0
    && kwLinks.every(a => a.target === '_blank' && a.rel === 'noopener noreferrer' && a.href === NAVER_SEARCH + encodeURIComponent(a.dataset.keyword)));
  ok('데이터랩 검색어트렌드 링크도 새 탭으로 열림', $('datalab-link') && $('datalab-link').target === '_blank'
    && $('datalab-link').rel === 'noopener noreferrer');

  key('condition:c3').querySelector('.more').open = true;
  q('[data-wrong="c3"]').click();
  const send = q('[data-send="c3"]');
  ok('"판정이 틀렸어요"는 동의하기 전에는 보낼 수 없음', send.disabled && logs.length === 0);
  $('agree-condition-c3').click();
  send.click();
  await settle();
  const sent = logs[0] && logs[0][1];
  ok('동의하면 조건 이름과 판정만 남김 (원고 글과 note 없음)',
    logs.length === 1 && Object.keys(sent).join() === 'consent,kind,id,label,status' && sent.status === 'kept'
    && sent.consent === true && !JSON.stringify(sent).includes('마셔') && !!q('[data-sent="c3"]'));
  ok('원고를 내려받거나 통째로 복사하는 버튼이 배포 화면에 없음',
    !q('[download]') && !all('button, a').some(b => /내려받|다운로드|JSON/.test(b.textContent)));
  ok('대가성 문구 예시(고정 문구)와 복사 버튼', $('disclosure-example').textContent === DISCLOSURE_EXAMPLE && !!$('copy-disclosure'));
  ok('하단 고지', q('.notice').textContent === '점검 결과는 참고용이며 노출·법규 준수를 보장하지 않아요.');
  ok('아래 안내문은 두 줄 이내이고 자세한 것은 개인정보 안내로', all('.foot p').length <= 2 && !!q('.foot a[href="privacy.html"]'));
  const words = document.body.textContent.replace(q('.notice').textContent, '');
  ok('보장하는 말이 화면에 없음', !/상위\s?노출|노출 보장|준수 보장|보장해|보장돼/.test(words));
  ok('누를 수 있는 것은 모두 키보드로 닿음 (버튼·링크·입력칸·접는 칸 머리)',
    all('main [data-key] .pick, main summary, main button, main a').every(el => el.tabIndex >= 0));

  // ── 4. 기준 숫자를 고쳐 다시 점검 (예시 모드: 미리 계산한 값이라 안내가 나와야 함) ──
  type($('need-min-c12'), '16');
  $('recheck').click();
  await settle();
  ok('값을 고쳐 다시 점검하면, 예시 모드라 반영되지 않았다고 알려 줌', S.view === 'result' && !!$('mock-banner')
    && !S.doc.conditions.find(c => c.id === 'c12').params.needs_review);

  // ── 5. 다른 예시들 ──
  $('reset').click();
  await settle();
  ok('새로 점검하면 두 칸이 비고 처음 화면으로', S.view === 'input' && $('guide').value === '' && $('draft').value === '');
  await run('sample-1');
  ok('예시 1 (글만 붙여 넣은 원고): 안내 없이 고칠 곳 4개, 숫자를 이미 넣었으면 더 묻지 않음',
    !$('mock-banner') && $('summary').textContent === '고칠 곳 4개' && !$('needs'));
  ok('예시 1: 형식을 못 알아보면 묻지 않고 일반 가이드로 점검함', $('form-line').textContent.startsWith('일반 가이드로 읽었어요')
    && !$('form-pick') && !q('select'));

  // ── 도움이 될 팁 (2026-11-28): 판정과 고칠 곳 개수를 바꾸지 않아요. 접어 두고, 펼쳤을 때만 원고에 차분한 색으로 ──
  {
    const tipN = S.res.result.tips.length;
    const verdict = () => [$('summary').textContent, $('summary-more').textContent, all('#notes .note-card').length,
      all('#manuscript mark.m-miss').length, all('#manuscript sup.n').length].join('|');
    const before = verdict();
    ok('도움이 될 팁은 결과 아래에 접혀 있고 "팁 N개"만 보임', tipN === 1 && !!$('tips') && !$('tips').open
      && q('#tips > summary').textContent === `도움이 될 팁 ${tipN}개` && !q('#manuscript mark.m-tip') && !S.tipsOpen
      && !!($('look').compareDocumentPosition($('tips')) & Node.DOCUMENT_POSITION_FOLLOWING));
    ok('팁은 고칠 곳 메모·직접 확인·지킨 것 목록에 들어가지 않음', !q('#notes [data-tip], #look [data-tip], #kept [data-tip]')
      && all('#tips .tip').length === tipN && !all('[data-key]').some(li => li.textContent.includes('넣을 자리 추천')));
    $('tips').open = true;
    await settle();
    ok('팁을 펼치면 원고에 차분한 색 표시가 생기고, 고칠 곳 개수와 빨간 표시는 그대로', S.tipsOpen && all('#manuscript mark.m-tip').length > 0
      && verdict() === before && !q('#manuscript mark.m-tip.m-miss'));
    ok('팁 표시는 빨강이 아님 (팁 색 면, 밑줄·번호 없음)', (() => {
      const style = getComputedStyle(q('#manuscript mark.m-tip'));
      const fix = getComputedStyle(document.documentElement).getPropertyValue('--c-fix').trim();
      const probe = h('span', { style: `color: ${fix}` });
      document.body.append(probe);
      const red = getComputedStyle(probe).color;
      probe.remove();
      return style.backgroundColor !== red && style.backgroundColor !== 'rgba(0, 0, 0, 0)' && !style.textDecorationLine.includes('underline');
    })());
    ok('팁의 틀은 빈칸(○○)이 있는 짧은 조각이고, 복사·판정 단추가 없음', all('#tips .tip-frames li').length >= 2
      && all('#tips .tip-frames li').every(li => li.textContent.includes('○○') && !/[.!?]|[다요]$/.test(li.textContent))
      && !q('#tips [data-wrong], #tips [data-edit], #tips .quiet') && !all('#tips button').some(b => b.textContent.includes('복사')));
    ok('팁 글은 권하는 말 ("더 자연스러워요")이고 "고쳐야" 같은 말이 없음', q('#tips .tip .note').textContent.includes('더 자연스러워요')
      && !/고쳐야 해요|빠졌어요|필요해요\./.test(q('#tips .tip-list').textContent));
    render();                                             // 가이드의 나머지가 도착할 때처럼 화면을 다시 그려도
    await settle();
    ok('화면을 다시 그려도 펼친 팁과 원고 표시가 남음', $('tips').open && all('#manuscript mark.m-tip').length > 0 && verdict() === before);
    q('#notes .pick').click();
    ok('팁을 펼친 채 고칠 곳을 골라도 팁 표시가 남음', all('#manuscript mark.m-tip').length > 0 && !!q('#notes .note-card.on'));
    $('tips').open = false;
    await settle();
    ok('팁을 접으면 원고의 팁 표시가 사라짐', !S.tipsOpen && !q('#manuscript mark.m-tip') && verdict() === before);
    $('edit').click();
    await settle();
    $('settings').open = true;
    ok('설정에 "도움이 될 팁 보기"가 있고 기본은 켬', $('opt-tips').checked && S.tips);
    $('opt-tips').click();
    await run();
    ok('설정에서 팁을 끄면 팁 묶음이 없고 점검 결과는 그대로', !S.tips && !$('tips') && !q('#manuscript mark.m-tip') && verdict() === before);
    S.tips = true;
    render();
    ok('다시 켜면 팁이 돌아옴', !!$('tips') && verdict() === before);
  }
  $('change-form').click();
  ok('"바꾸기"를 누르면 형식을 고를 수 있음', !!$('form-pick') && $('form-pick').value === 'general');
  $('form-pick').value = 'gangnam';
  $('reread').click();
  await settle();
  await ready();
  ok('고른 형식으로 다시 읽고 결과 위에 적음', S.formPick === 'gangnam' && $('form-line').textContent.startsWith('강남맛집 가이드로 읽었어요'));
  $('kept-list') && ($('kept-list').open = true);
  q('#notes .pick') && q('#notes .pick').click();
  ok('고칠 곳 메모를 누르면 그 메모가 표시됨', !!q('#notes .note-card.on'));
  $('edit').click();
  await settle();
  ok('원고 고쳐서 다시 점검: 처음 화면으로 돌아가고 두 칸은 그대로', S.view === 'input' && $('guide').value.length > 0 && $('draft').value.length > 0);
  await run('sample-3');
  ok('예시 3: 같은 조건을 말하는 가이드 원문 두 곳이 조건 목록에 모두 보임',
    all('#conds-list .cond').filter(li => li.querySelector('.kind').textContent === '링크').length === 1
    && all('#conds-list .cond[data-id="c8"] .quote').length === 2);
  await run('sample-4');
  const lost = all('#conds-list .cond').filter(li => li.querySelector('.kind').textContent === '확인 못 한 조건');
  ok('예시 4: 확인하지 못한 조건이 조건 목록에 안내로 보임', lost.length === 1
    && lost[0].querySelector('strong').textContent === '조건 하나를 확인하지 못했어요. 가이드의 이 부분을 직접 봐 주세요');
  const lostItem = all('#look .row').find(li => li.textContent.includes('조건 하나를 확인하지 못했어요'));
  ok('확인하지 못한 조건은 직접 확인할 것으로 세어짐', !!lostItem && lostItem.querySelector('.note').textContent.includes('가이드의 이 부분을 직접 보고'));
  ok('예시 4: 해시태그가 빠졌으면 태그 칸 태그를 물어봄', !!$('need-tags'));
  lost[0].querySelector('[data-remove]').click();
  await settle();
  ok('조건이 아니면 빼고 다시 점검할 수 있음', S.view === 'result' && !all('#conds-list .kind').some(k => k.textContent === '확인 못 한 조건') && !!$('undo'));

  // ── 조건 고치기 (가볍게): 값만 고치고, 지우고, 다시 점검해도 남아요 ──
  $('reset').click();
  await settle();
  await run('sample-2');
  const c3 = () => S.doc.conditions.find(c => c.id === 'c3');
  $('kept-list').open = true;
  q('[data-edit="c3"]').click();
  ok('고치기를 누르면 그 조건의 값(횟수, 키워드)만 고치는 칸이 열림', !$('edit-c3').hidden && !!$('edit-c3-min')
    && !!$('edit-c3-keywords') && all('#edit-c3 input').length === 2);
  type($('edit-c3-min'), '-1');
  q('[data-save="c3"]').click();
  ok('잘못된 값은 받지 않음', c3().params.min === 4 && $('edit-c3').querySelector('.field-err').textContent !== '');
  type($('edit-c3-min'), '6');
  q('[data-save="c3"]').click();
  await settle();
  ok('고친 값으로 다시 점검하고 "고쳤어요"가 붙음', c3().params.min === 6
    && [...key('condition:c3').querySelectorAll('.tag')].some(t => t.textContent === '고쳤어요'));
  $('edit').click();
  await settle();
  type($('draft'), $('draft').value + '\n덧붙인 문장이에요.');
  await run();
  ok('원고를 고쳐 다시 점검해도 고친 값이 남음', c3() && c3().params.min === 6);
  q('[data-delete="c3"]').click();
  await settle();
  ok('조건을 지울 수 있음', !c3() && !key('condition:c3'));
  $('edit').click();
  await settle();
  await run();
  ok('지운 조건은 다시 점검해도 빠진 채로 남음', !c3());
  $('reset').click();
  await settle();
  await sample('sample-3');
  $('check').click();
  await settle();
  const early = S.doc.conditions.find(c => c.countable && Number.isInteger(c.params.min) && c.source === 'rule');
  const earlySig = sig(early);
  q(`[data-edit="${early.id}"]`).click();
  type($(`edit-${early.id}-min`), '99');
  q(`[data-save="${early.id}"]`).click();
  await ready();
  const later = S.doc.conditions.find(c => sig(c) === earlySig);
  ok('코드가 읽은 조건을 먼저 고쳐도 가이드의 나머지가 온 뒤 고친 값이 남음', S.aiState === 'done' && later && later.params.min === 99);

  // ── 나머지 조건을 읽지 못하면: 코드 결과는 그대로, "다시 시도" ──
  const realExtract = Api.extract;
  Api.extract = async (g, o) => { if (o && o.ai) throw new Error('시간이 너무 오래 걸려서 멈췄어요. 다시 시도해 주세요.'); return realExtract(g, o); };
  $('reset').click();
  await settle();
  await run('sample-2');
  ok('나머지 조건을 읽지 못하면 코드 결과는 그대로 두고 "다시 시도"가 나옴', S.view === 'result' && S.aiState === 'failed'
    && $('ai-failed').textContent.includes('나머지 조건은 읽지 못했어요') && !!$('retry-ai') && all('#notes .note-card').length > 0);
  Api.extract = realExtract;
  $('retry-ai').click();
  await ready();
  ok('다시 시도하면 나머지 조건을 이어 붙임', S.aiState === 'done' && !$('ai-failed') && S.doc.conditions.some(c => c.source !== 'rule'));

  const local = location.protocol === 'file:' ? 'file:' : location.origin;
  ok('밖으로 나간 요청이 없음', performance.getEntriesByType('resource').every(e => e.name.startsWith(local)));
  } catch (why) {
    ok(`시험이 중간에 멈춤: ${why.message} (${checks.length}번째 확인 뒤) ${String(why.stack).split(/\n/).slice(1, 3).join(' ')}`, false);
  }

  console.log = realLog;
  const pass = checks.filter(c => c[1]).length;
  document.body.append(h('section', { id: 'selftest-report' },
    h('h2', { id: 'selftest', class: pass === checks.length ? 'ok' : 'bad', text: `자체 시험 ${pass}/${checks.length} 통과` }),
    h('ol', {}, checks.map(([name, good]) => h('li', { 'data-pass': String(good), text: `${good ? '통과' : '실패'}: ${name}` })))));
})();
