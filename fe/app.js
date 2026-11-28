// 화면. 처음에는 "가이드", "원고" 두 칸과 "점검하기" 하나만 보여요. 누르면 조건 뽑기 → 점검을 한 번에 하고,
// 결과는 원고 위에 빨간 표시와 여백 메모를 단 "교정지"로 보여 줘요.
//
// - 원고를 읽어 오는 부분은 reader.js, 결과를 그리는 부분은 results.js예요. 이 파일은 상태와 흐름만 맡아요.
// - 붙여 넣은 글은 글자(textContent, value)로만 화면에 써요. 서식(HTML)으로 넣지 않고, 사진을 불러오지 않아요.
// - 서버와 만나는 곳은 api.js뿐이에요. 이 파일에는 요청을 보내는 코드가 없어요.
// - 글을 대신 쓰거나 고쳐 주지 않아요. 무엇이 빠졌고 어디인지까지만 보여 줘요.
'use strict';

const $ = id => document.getElementById(id);
const clone = v => JSON.parse(JSON.stringify(v));

// 대가성 문구 예시: 고정 문구예요. AI가 만들지 않아요.
const DISCLOSURE_EXAMPLE = '본 포스팅은 업체로부터 제품 또는 서비스를 제공받아 작성했습니다.';
const MAX_GUIDE = 20000, MAX_DRAFT = 60000;          // be/server.py의 한도와 같아요. 보내기 전에 먼저 알려 줘요
const FORMS = { reviewplace: '리뷰플레이스', revu: '레뷰', gangnam: '강남맛집', reviewnote: '리뷰노트' };
// "바꾸기"에서 고를 수 있는 형식. 일반 가이드는 고정 칸을 읽지 않고 AI와 문장 규칙으로만 읽어요
const FORM_CHOICES = [['revu', '레뷰'], ['gangnam', '강남맛집'], ['reviewplace', '리뷰플레이스'], ['reviewnote', '리뷰노트'], ['general', '일반']];
const shownForm = form => (form && FORMS[form] ? form : null);
const TYPE = {
  title_keyword: '제목 키워드', keyword_count: '본문 키워드', length: '글자 수', photo_count: '사진 수',
  video_count: '동영상', link: '링크', map: '지도', hashtag: '해시태그', exact_phrase: '정확한 표기',
  banned_terms: '금지어', required_phrase: '필수 문구', disclosure: '대가성 문구',
  outside_draft: '원고 밖에서 확인', judgment: '직접 확인',
};
const UNIT = { keyword_count: '회', length: '자', photo_count: '장', video_count: '개', link: '개' };
const fresh = () => ({ title: '', photo: null, video: null, map: null, tags: '' });

const S = {
  view: 'input',                    // input(처음 화면) → busy(점검 중) → result(교정지)
  guide: '', draft: '', base: null, pasted: null, scenario: null,
  doc: null, original: null, dropped: [], form: null, picking: false, removed: [], request: null, readGuide: null,
  // 나눠 보여 주기: 코드가 읽은 결과를 먼저 보여 주고, 가이드의 나머지(AI가 읽는 조건)는 도착하면 이어 붙여요
  aiState: 'idle', aiMsg: '',                      // idle → reading → done | failed
  edits: {}, gone: new Set(), formPick: null,       // 고친 조건 값, 뺀 조건(조건 표시로 기억), "바꾸기"로 고른 형식
  res: null, error: null, busy: '',
  // 설정: 기본값으로 바로 써요. AI로 살펴보기는 켰을 때만 원고 글이 AI 서비스로 가요.
  ai: false, captions: true,
  tips: true, tipsOpen: false,      // 도움이 될 팁: 보기(설정에서 끌 수 있어요), 펼쳐 둠(펼쳤을 때만 원고에 표시)
  extra: fresh(),                   // 결과 화면의 "점검에 필요한 것"에서 받은 값
  judging: false, judgeMsg: '', judged: null, last: null, changed: null,
  selected: null,
};

// ── 공통 ─────────────────────────────────────────────────────────────────

// AI에게 물을 조건: 셀 수 없는 조건 중 원고로 판단할 수 있는 것 (ai/judge.py의 qualitative와 같아요)
const qualitative = doc => doc.conditions.filter(c => !c.countable && c.type !== 'outside_draft'
  && c.type !== 'photo_count' && !(c.params || {}).unverified);
function statuses(result) {
  const m = {};
  for (const r of result.results) m[keyOf('condition', r)] = r.status;
  for (const p of result.principles) m[keyOf('principle', p)] = p.status;
  return m;
}
function markChanged(skip = new Set()) {
  const now = statuses(S.res.result);
  S.changed = S.last ? new Set(Object.keys(now).filter(k => !skip.has(k) && k in S.last && S.last[k] !== now[k])) : null;
}

function render() {
  const mode = $('mode');
  mode.hidden = !Api.mock;
  mode.textContent = '예시 모드: 지어낸 예시로만 해 볼 수 있어요';
  const view = { input: viewInput, busy: viewBusy, result: viewResult }[S.view];
  $('main').replaceChildren(...tidy(view()));
  document.body.dataset.view = S.view;
  if (S.view === 'result') requestAnimationFrame(alignNotes);
}

function show(view, focusId) {
  S.view = view;
  render();
  const target = focusId && $(focusId);
  if (target) target.focus({ preventScroll: true });
  // 처음 화면의 칸 오류는 그 칸으로, 나머지(점검 중, 결과)는 맨 위로 가요. 머리의 이름이 보이게요
  if (target && view === 'input' && focusId !== 'page-title') target.scrollIntoView({ block: 'center' });
  else window.scrollTo(0, 0);
}

async function copyText(text, btn, done) {
  let ok = true;
  try { await navigator.clipboard.writeText(text); }
  catch {
    const ta = h('textarea', { class: 'offscreen' });
    ta.value = text;
    document.body.append(ta);
    ta.select();
    ok = document.execCommand('copy');
    ta.remove();
  }
  const old = btn.textContent;
  btn.textContent = ok ? done : '복사하지 못했어요';
  setTimeout(() => { btn.textContent = old; }, 1800);
}

// ── 처음 화면: 가이드, 원고, 점검하기 ─────────────────────────────────────

// 원고 칸 아래 한 줄: 무엇을 읽었는지
function readLine() {
  if (!S.draft.trim()) return '';
  if (S.base && S.draft !== S.pasted) return '붙여 넣은 글을 고쳐서 글자만으로 점검해요. 사진·링크·지도까지 세려면 에디터에서 다시 붙여 넣어 주세요.';
  if (!S.base) return '직접 쓴 글로 점검해요. 사진 수가 필요하면 결과 화면에서 물어볼게요.';
  const b = S.base;
  if (b.input_mode === 'text') return '글자만 읽었어요. 사진 수가 필요하면 결과 화면에서 물어볼게요.';
  const banner = b.banner_count ? ` (체험단 배너 ${b.banner_count}개는 사진에서 뺐어요${b.banner_top ? ', 맨 위 배너는 대가성 표시로 봐요' : ''})` : '';
  return `서식째 읽었어요. 사진 ${b.photo_count}장${banner}, 동영상 ${b.video_count}개, 지도 ${b.has_map ? '있음' : '없음'}.`;
}

function fieldError(id) {
  return S.error && S.error.where === id ? S.error.text : '';
}

function viewInput() {
  const guide = h('textarea', { id: 'guide', class: 'paper-input', spellcheck: 'false', 'aria-describedby': 'guide-help guide-err',
    'aria-invalid': fieldError('guide') ? 'true' : null,
    placeholder: '캠페인 페이지의 가이드를 처음부터 끝까지 복사해서 붙여 넣으세요.' });
  guide.value = S.guide;
  guide.addEventListener('input', () => { S.guide = guide.value; S.formPick = null; });     // 새 가이드는 형식을 다시 알아봐요

  const draft = h('textarea', { id: 'draft', class: 'paper-input', spellcheck: 'false', 'aria-describedby': 'draft-help draft-read draft-err',
    'aria-invalid': fieldError('draft') ? 'true' : null,
    placeholder: '네이버 블로그 에디터에서 본문을 모두 선택(Ctrl+A)해 복사(Ctrl+C)한 뒤, 여기에 붙여 넣으세요(Ctrl+V).' });
  draft.value = S.draft;
  const read = h('p', { class: 'read-line', id: 'draft-read', role: 'status', text: readLine() });
  const draftErr = h('p', { class: 'field-err', id: 'draft-err', role: 'alert', text: fieldError('draft') });
  draft.addEventListener('paste', e => {
    e.preventDefault();                                 // 붙여 넣은 서식을 화면에 넣지 않고 분석만 해요
    const got = Reader.fromPaste(e.clipboardData.getData('text/html'), e.clipboardData.getData('text/plain'));
    if (got.error) { draftErr.textContent = got.error; return; }
    Object.assign(S, { base: got.request, scenario: null, draft: got.request.draft_text, pasted: got.request.draft_text });
    if (got.request.title) { S.extra.title = got.request.title; title.value = got.request.title; }   // 보기 화면 복사는 제목을 찾아 채워요
    draft.value = S.draft;                               // 읽은 본문 글자만 칸에 보여 줘요
    draftErr.textContent = '';
    read.textContent = readLine();
  });
  draft.addEventListener('input', () => { S.draft = draft.value; read.textContent = readLine(); });
  // 제목 한 줄 (필수 아님). 글쓰기 화면 복사에는 제목이 오지 않아서 따로 받아요. 결과 화면의 "블로그 글 제목"과 같은 값이에요
  const title = h('input', { type: 'text', id: 'post-title', class: 'title-input', autocomplete: 'off', 'aria-describedby': 'post-title-help',
    placeholder: '블로그 글 제목 (없어도 돼요)' });
  title.value = S.extra.title;
  title.addEventListener('input', () => { S.extra.title = title.value; });
  const titleField = h('div', { class: 'title-field' },
    h('label', { class: 'title-label', for: 'post-title', text: '제목' }), title,
    h('p', { class: 'hint', id: 'post-title-help', text: '글쓰기 화면에서 복사하면 제목이 따라오지 않아요. 적어 주시면 제목 조건도 함께 볼게요.' }));

  const captions = h('input', { type: 'checkbox', id: 'opt-captions' });
  captions.checked = S.captions;
  captions.addEventListener('change', () => { S.captions = captions.checked; });
  const tips = h('input', { type: 'checkbox', id: 'opt-tips' });
  tips.checked = S.tips;
  tips.addEventListener('change', () => { S.tips = tips.checked; });
  const useAi = h('input', { type: 'checkbox', id: 'use-ai', disabled: Api.mock });
  useAi.checked = S.ai;
  useAi.addEventListener('change', () => { S.ai = useAi.checked; });

  const sheet = (id, title, help, input, ...after) => h('section', { class: 'sheet input-sheet', 'aria-labelledby': `${id}-label` },
    h('label', { class: 'sheet-label', id: `${id}-label`, for: id, text: title }),
    h('p', { class: 'sheet-help', id: `${id}-help`, text: help }),
    input, after);

  return [
    h('div', { class: 'intro' },
      h('h1', { id: 'page-title', tabindex: '-1', text: '내기 전에, 가이드와 원고를 맞춰 봐요' }),
      h('p', { class: 'lead', text: '두 칸에 붙여 넣으면, 빠진 조건과 그 자리를 원고 위에 짚어 드릴게요. 글은 대신 쓰지 않아요.' })),
    S.error && S.error.where === 'top' ? h('p', { class: 'form-error', id: 'form-error', role: 'alert', tabindex: '-1', text: S.error.text }) : null,
    h('div', { class: 'desk' },
      sheet('guide', '가이드', '캠페인 페이지에 있는 가이드 글이에요', guide,
        h('p', { class: 'field-err', id: 'guide-err', role: 'alert', text: fieldError('guide') })),
      sheet('draft', '원고', '블로그 에디터에서 쓴 글이에요. 서식째 붙여 넣으면 사진 수도 세어 드려요', [titleField, draft], read, draftErr)),
    h('div', { class: 'go' },
      button('점검하기', 'primary', () => start(), { id: 'check' }),
      h('details', { class: 'settings', id: 'settings' },
        h('summary', { text: '점검 설정' }),
        h('label', { class: 'opt', for: 'opt-captions' }, captions, h('span', { text: '사진 설명(캡션)도 글자 수에 넣기' })),
        h('label', { class: 'opt', for: 'opt-tips' }, tips, h('span', { text: '도움이 될 팁 보기 (키워드를 넣을 자리, 띄어쓰기 안내). 점검 결과와 고칠 곳 개수에는 넣지 않아요.' })),
        h('label', { class: 'opt', for: 'use-ai' }, useAi, h('span', {},
          '셀 수 없는 조건도 AI로 살펴보기. 켜면 원고 글이 AI 서비스(Anthropic)로 전송돼요. 결과는 참고용이에요.',
          Api.mock ? h('em', { text: ' 예시 모드에서는 쓸 수 없어요.' }) : null)))),
    Api.mock && h('details', { class: 'samples', id: 'samples' },
      h('summary', { text: '예시로 해 보기' }),
      h('div', { class: 'sample-list' }, Api.scenarios.map(s => button(s.name, 'quiet', () => {
        Object.assign(S, { guide: s.guide, base: clone(s.request), draft: s.request.draft_text, pasted: s.request.draft_text,
          scenario: s.id, error: null, formPick: null });
        S.extra.title = s.request.title || '';           // 예시의 제목을 제목 칸에 보여 줘요
        render();
        $('check').focus();
      }, { 'data-sample': s.id })))),
  ];
}

// ── 점검 중 ──────────────────────────────────────────────────────────────

function viewBusy() {
  // 코드가 읽는 단계라 금방 끝나요. 가이드의 나머지는 결과 화면에서 읽어요
  return h('section', { class: 'busy', id: 'busy', role: 'status', 'aria-live': 'polite' },
    h('h1', { id: 'busy-title', tabindex: '-1', text: '원고를 살펴보고 있어요' }),
    h('ol', { class: 'busy-steps' }, h('li', { class: 'now', text: '가이드 조건을 읽고 원고를 세고 있어요' })));
}

function fail(text, where = 'top') {
  S.error = { text, where };
  show('input', where === 'top' ? 'form-error' : where);
}

function draftRequest() {
  if (S.base && S.draft === S.pasted) return clone(S.base);
  return Reader.fromPaste('', S.draft);                 // 손으로 쓰거나 고친 글: 글자만으로 읽어요
}

async function start() {
  S.error = null;
  const guide = S.guide.replace(/\r\n?/g, '\n');
  if (!guide.trim()) return fail('가이드를 붙여 넣어 주세요.', 'guide');
  if (guide.length > MAX_GUIDE) return fail(`가이드가 너무 길어요. ${MAX_GUIDE.toLocaleString()}자까지 점검할 수 있어요.`, 'guide');
  if (!S.draft.trim()) return fail('원고를 붙여 넣어 주세요.', 'draft');
  if (Array.from(S.draft).length > MAX_DRAFT) return fail(`원고가 너무 길어요. ${MAX_DRAFT.toLocaleString()}자까지 점검할 수 있어요.`, 'draft');
  const base = draftRequest();
  if (base.error) return fail(base.error, 'draft');
  if (S.doc && S.readGuide === guide) {
    // 가이드가 그대로면(원고만 고쳐서 다시 점검) 조건을 다시 뽑지 않아요. AI를 다시 부르지 않고,
    // 결과 화면에서 적은 값(제목, 사진 수, 자율 키워드, 고친 조건)과 뺀 조건도 그대로 둬요
    S.request = base.request || base;
    await check();
    if (S.aiState === 'failed') readRest();           // 지난번에 나머지를 못 읽었으면 다시 읽어요
    return;
  }
  S.busy = 'check';
  show('busy', 'busy-title');
  const t0 = performance.now();                         // 걸린 시간: 누른 때부터 (숫자만 서버 기록으로)
  let got;
  try {
    got = await Api.extract(guide, { ai: false, form: S.formPick || null });     // 1단계: 코드가 고정 칸에서 읽은 조건만
  } catch (why) {
    return fail(`${why.message}`);
  }
  if (!got) return fail('예시 모드에서는 예시 가이드만 점검할 수 있어요. 아래 "예시로 해 보기"를 눌러 주세요.');
  Object.assign(S, { doc: got.doc, original: clone(got.doc), dropped: got.dropped, form: shownForm(got.form), picking: false,
    scenario: got.scenario || S.scenario, removed: [], extra: fresh(), last: null, changed: null, judged: null,
    request: base.request || base, readGuide: guide, aiState: 'reading', aiMsg: '', edits: {}, gone: new Set(), tipsOpen: false });
  await check();
  readRest({ t0, first: Math.round(performance.now() - t0) });   // 2단계: 가이드의 나머지는 AI가 읽고, 오면 이어 붙여요
}

// 가이드의 나머지 조건(AI가 읽는 것)을 받아 조건 목록을 바꾸고 다시 점검해요. 코드 결과는 그동안 그대로 보여요.
async function readRest(clock = null) {
  const guide = S.readGuide;
  S.aiState = 'reading';
  S.aiMsg = '';
  if (S.view === 'result') render();
  let got;
  try {
    got = await Api.extract(guide, { ai: true, form: S.formPick || null });
  } catch (why) {
    if (S.readGuide !== guide) return;                  // 그새 다른 가이드로 점검했으면 버려요
    S.aiState = 'failed';
    S.aiMsg = why.message;
    if (S.view === 'result') render();
    if (clock) Api.timing({ first_ms: clock.first, full_ms: null, ai: 'failed' });
    return;
  }
  if (S.readGuide !== guide) return;
  if (got) {
    Object.assign(S, { dropped: got.dropped, form: shownForm(got.form), original: clone(got.doc), doc: withEdits(got.doc) });
  }
  S.aiState = 'done';
  if (!S.doc.conditions.length) S.aiMsg = '가이드에서 지킬 조건을 찾지 못했어요. 체험단 캠페인의 가이드 글이 맞는지 확인해 주세요.';
  await check({ quiet: true });
  if (clock) Api.timing({ first_ms: clock.first, full_ms: Math.round(performance.now() - clock.t0), ai: 'done' });
}

// 다시 받은 조건 목록에 블로거가 고친 값과 뺀 조건을 그대로 다시 적용해요
function withEdits(doc) {
  const out = clone(doc);
  out.conditions = out.conditions.filter(c => !(S.gone || new Set()).has(sig(c)));
  for (const c of out.conditions) {
    const edit = (S.edits || {})[sig(c)];
    if (edit) { Object.assign(c.params, edit); delete c.params.needs_review; }
  }
  return out;
}
const sig = c => `${c.type}|${c.guide_quote.start}|${c.guide_quote.end}`;

// 조건 빼기: 다시 점검하거나 가이드의 나머지를 읽어 와도 빠진 채로 남아요
function removeCondition(c) {
  const at = S.doc.conditions.findIndex(x => x.id === c.id);
  if (at < 0) return;
  S.removed.push(...S.doc.conditions.splice(at, 1));
  S.gone.add(sig(c));
}

// 결과 화면에서 받은 값(제목, 사진 수 등)을 원고 요청에 더해요
function finalRequest() {
  const e = S.extra, req = clone(S.request);
  // 제목은 블로거가 적은 것이 먼저예요 (처음 화면의 제목 칸 = 결과 화면의 "블로그 글 제목". 붙여 넣은 글에서 찾은 제목은 그 칸에 미리 채워요).
  // 사진 수 같은 다른 값은 받은 원고에 없을 때만 채워요
  if (e.title.trim()) req.title = e.title.trim();
  if (!req.title || !String(req.title).trim()) req.title = null;      // 제목을 모르면 null. 빈 글자("")로 보내지 않아요
  for (const [key, field] of [['photo', 'photo_count'], ['video', 'video_count'], ['map', 'has_map']]) {
    if (e[key] !== null && req[field] == null) { req[field] = e[key]; req.counts_source = 'user'; }
  }
  const tags = e.tags.split(/[,\s]+/).filter(Boolean).map(t => t.startsWith('#') ? t : '#' + t);
  req.hashtags = [...new Set([...req.hashtags, ...tags])];
  if (!S.captions) req.count_captions = false;
  return req;
}

// quiet: 결과 화면을 그대로 두고 다시 점검해요 (AI가 나머지를 읽어 왔을 때, 조건을 고쳤을 때)
async function check({ quiet = false } = {}) {
  if (!quiet) {
    S.busy = 'check';
    show('busy', 'busy-title');
  }
  S.checking = true;                                    // 다시 점검하는 중 (화면을 다시 그리기 전까지)
  try {
    S.res = await Api.check(S.doc, finalRequest(), S.scenario);
  } catch (why) {
    S.checking = false;
    if (quiet) { S.aiMsg = why.message; render(); return; }
    return fail(why.message);
  }
  S.checking = false;
  S.judging = false;
  if (quiet) render(); else { S.selected = null; show('result', 'summary'); }   // 코드로 센 결과를 먼저 보여 줘요
  if (S.aiState === 'done') runJudge();                 // 셀 수 없는 조건 판단은 조건을 다 읽은 뒤에
}

// 정적 결과를 보여 준 뒤에 불러요. 셀 수 없는 조건만 AI로 판단해 결과를 이어 붙여요.
// 다시 점검할 때 조건과 원고가 그대로면 AI를 다시 부르지 않고 지난 판단을 써요.
async function runJudge() {
  const mine = S.res;
  const asked = qualitative(mine.doc);
  S.judgeMsg = '';
  if (!S.ai || Api.mock || !asked.length) { markChanged(); S.last = statuses(mine.result); render(); return; }
  const key = JSON.stringify([mine.doc, mine.request]);
  if (S.judged && S.judged.key === key) {
    mine.result = clone(S.judged.result);
    markChanged();
    S.last = statuses(mine.result);
    render();
    return;
  }
  markChanged(new Set(asked.map(c => `condition:${c.id}`)));
  S.judging = true;
  render();
  try {
    const result = await Api.judge(mine.doc, mine.request);
    if (S.res !== mine) return;                         // 그새 다시 점검했으면 버려요
    mine.result = result;
    S.judged = { key, result: clone(result) };
    markChanged();
    S.last = statuses(result);
  } catch (why) {
    if (S.res !== mine) return;
    S.judgeMsg = why.message;                           // 코드로 센 결과는 그대로 둬요
    S.last = statuses(mine.result);
  } finally {
    if (S.res === mine) { S.judging = false; render(); }
  }
}

// ── 결과: 교정지 ─────────────────────────────────────────────────────────

function feedback(kind, id, label, status) {
  const box = h('div', { class: 'fb', hidden: true });
  const agree = h('input', { type: 'checkbox', id: `agree-${kind}-${id}` });
  const send = button('보내기', 'quiet', async () => {
    // 동의한 경우에만, 해당 조건과 판정만 보내요. 원고 글과 note는 넣지 않아요.
    try {
      const got = await Api.feedback({ kind, id, label, status });
      box.replaceChildren(h('p', { class: 'hint', 'data-sent': id,
        text: got.saved ? '받았어요. 고마워요.' : '받았어요. 예시 모드라서 저장하지는 않아요.' }));
    } catch (why) {
      box.append(h('p', { class: 'field-err', text: why.message }));
    }
  }, { disabled: true, 'data-send': id });
  agree.addEventListener('change', () => { send.disabled = !agree.checked; });
  box.append(h('label', { class: 'opt', for: `agree-${kind}-${id}` }, agree,
    h('span', { text: '이 조건 이름과 판정 결과를 보내는 데 동의해요. 원고 글은 보내지 않아요.' })), send);
  return [button('판정이 틀렸어요', 'link', () => { box.hidden = !box.hidden; }, { 'data-wrong': id }), box];
}

function card(kind, r, opts = {}) {
  const id = kind === 'condition' ? r.condition_id : r.rule_id;
  const key = keyOf(kind, r);
  const cond = kind === 'condition' ? S.doc.conditions.find(c => c.id === r.condition_id) : null;
  return noteCard(kind, r, { ...opts, changed: !!(S.changed && S.changed.has(key)), onPick: () => pick(key),
    foot: feedback(kind, id, r.label, r.status), edit: cond ? editor(cond) : null, edited: !!(cond && S.edits[sig(cond)]) });
}

// 조건 고치기 (가볍게): 그 조건의 값(횟수·장수·글자 수, 키워드·태그)만 고치거나 조건을 지워요.
// 고친 값은 조건 표시(sig)로 기억해서, 원고를 다시 점검하거나 가이드의 나머지를 읽어 와도 남아요.
const EDIT_NUMBERS = { min: { keyword_count: '횟수', photo_count: '장수', video_count: '개수', length: '글자 수', link: '개수' },
  max: { photo_count: '최대 장수' } };
const EDIT_LISTS = { keywords: '키워드 (쉼표로 나눠요)', tags: '태그 (쉼표로 나눠요)' };

function editor(c) {
  const p = c.params;
  const fields = [];
  if (c.countable && !p.unverified) {
    for (const [key, names] of Object.entries(EDIT_NUMBERS)) {
      if (Number.isInteger(p[key]) && names[c.type]) fields.push([key, names[c.type], 'number']);
    }
    for (const [key, name] of Object.entries(EDIT_LISTS)) {
      if (Array.isArray(p[key]) && (p[key].length || p.free)) fields.push([key, name, 'list']);
    }
  }
  const err = h('p', { class: 'field-err', role: 'alert' });
  const inputs = fields.map(([key, name, kind]) => {
    const id = `edit-${c.id}-${key}`;
    const input = h('input', { id, type: kind === 'number' ? 'number' : 'text', min: kind === 'number' ? 0 : null,
      inputmode: kind === 'number' ? 'numeric' : null, autocomplete: 'off' });
    input.value = kind === 'list' ? p[key].join(', ') : p[key];
    return [key, kind, input, h('div', { class: 'need' }, h('label', { for: id, text: name }), input)];
  });
  const save = () => {
    const patch = {};
    for (const [key, kind, input] of inputs) {
      if (kind === 'number') {
        const n = Number(input.value);
        if (input.value.trim() === '' || !Number.isInteger(n) || n < 0) { err.textContent = '0 이상의 숫자로 적어 주세요.'; return; }
        patch[key] = n;
      } else {
        const items = input.value.split(',').map(s => s.trim()).filter(Boolean).map(s => key === 'tags' && !s.startsWith('#') ? '#' + s : s);
        if (!items.length && !p.free) { err.textContent = '하나 이상 적어 주세요.'; return; }
        patch[key] = items;
      }
    }
    if (Number.isInteger(patch.max) && Number.isInteger(patch.min) && patch.max < patch.min) { err.textContent = '최대는 기준보다 작을 수 없어요.'; return; }
    Object.assign(p, patch);
    delete p.needs_review;
    S.edits[sig(c)] = { ...(S.edits[sig(c)] || {}), ...patch };
    check({ quiet: true });
  };
  const box = h('div', { class: 'edit-box', id: `edit-${c.id}`, hidden: true },
    inputs.map(x => x[3]),
    err,
    h('div', { class: 'edit-actions' },
      inputs.length ? button('고친 값으로 다시 점검', 'quiet', save, { 'data-save': c.id }) : null,
      button('이 조건 지우기', 'link', () => { removeCondition(c); check({ quiet: true }); }, { 'data-delete': c.id })));
  const toggle = button('고치기', 'link', () => {
    box.hidden = !box.hidden;
    toggle.setAttribute('aria-expanded', String(!box.hidden));
    if (!box.hidden && inputs[0]) inputs[0][2].focus();
    requestAnimationFrame(alignNotes);
  }, { 'data-edit': c.id, 'aria-expanded': 'false', 'aria-controls': `edit-${c.id}` });
  return [toggle, box];
}

function allItems() {
  const { result, doc } = S.res;
  const outside = new Set(doc.conditions.filter(c => c.type === 'outside_draft').map(c => c.id));
  // 지금 조건에 있는 것만 (예시 모드의 미리 계산한 결과에는 지운 조건이 남아 있을 수 있어요)
  const now = new Set(S.doc.conditions.map(c => c.id));
  const results = result.results.filter(r => now.has(r.condition_id));
  return {
    inside: [...results.filter(r => !outside.has(r.condition_id)).map(r => ['condition', r]),
      ...result.principles.map(p => ['principle', p])],
    outside: results.filter(r => outside.has(r.condition_id)),
  };
}

// 도움이 될 팁: 설정에서 껐으면 없고, 지금 조건에서 나온 것만 보여 줘요. 판정(allItems, fixNotes)에는 넣지 않아요
function shownTips() {
  if (!S.tips) return [];
  const now = new Set(S.doc.conditions.map(c => c.id));
  return (S.res.result.tips || []).filter(t => !t.condition_id || now.has(t.condition_id));
}
const openTips = () => (S.tipsOpen ? shownTips() : []);      // 펼쳐 둔 동안만 원고에 표시해요

// 원고 종이만 다시 그려요 (항목을 골랐을 때, 팁을 펼치거나 접었을 때)
function redrawSheet() {
  const picked = S.selected && allItems().inside.find(([kind, r]) => keyOf(kind, r) === S.selected);
  const sheet = $('manuscript');
  if (sheet) sheet.replaceWith(proofSheet(S.res.request, fixNotes(), picked && picked[1], openTips()));
  requestAnimationFrame(alignNotes);
}

function pick(key) {
  S.selected = key;
  redrawSheet();
  markPicked(key);
}

// 고칠 곳 메모: 원고 전체에 대한 것(위치 없음)을 먼저, 그다음 원고에 나오는 차례대로 번호를 매겨요
function fixNotes() {
  const firstAt = r => {
    const s = r.draft_spans[0];
    return s ? (s.field === 'title' ? -1 : s.start) : -2;
  };
  let n = 0;
  return allItems().inside.filter(([, r]) => r.status === 'missing')
    .sort((a, b) => firstAt(a[1]) - firstAt(b[1]))
    .map(([kind, r]) => ({ kind, r, n: r.draft_spans.length ? ++n : null }));
}

// "점검에 필요한 것": 결과를 더 정확히 하려고 꼭 필요할 때만 묻는 칸
function needs() {
  const { request, result } = S.res;
  const doc = S.doc;                                  // 지금 조건 (고친 값이 바로 보이게)
  const byId = Object.fromEntries(result.results.map(r => [r.condition_id, r]));
  const has = type => doc.conditions.some(c => c.type === type && c.countable);
  const out = [];
  const titleConds = doc.conditions.some(c => c.countable && (c.type === 'title_keyword'
    || ['title', 'title_and_body'].includes((c.params || {}).scope)));
  if (request.title == null && titleConds) {
    out.push(['need-title', '블로그 글 제목', h('input', { type: 'text', id: 'need-title', value: S.extra.title, autocomplete: 'off' }),
      '제목을 알려 주시면 제목 조건도 볼게요.']);
  }
  const counts = [['photo', 'photo_count', '사진 수', '장'], ['video', 'video_count', '동영상 수', '개']];
  for (const [key, field, name, unit] of counts) {
    if (request[field] == null && has(field)) {
      out.push([`need-${key}`, name, h('span', { class: 'with-unit' },
        h('input', { type: 'number', id: `need-${key}`, min: 0, inputmode: 'numeric', value: S.extra[key] ?? '' }), h('span', { text: unit })),
      '글만 붙여 넣어서 셀 수 없었어요.']);
    }
  }
  if (request.has_map == null && has('map')) {
    const sel = h('select', { id: 'need-map' }, [['', '모름'], ['true', '있음'], ['false', '없음']].map(([v, t]) => h('option', { value: v, text: t })));
    sel.value = S.extra.map === null ? '' : String(S.extra.map);
    out.push(['need-map', '지도', sel, '글만 붙여 넣어서 알 수 없었어요.']);
  }
  for (const c of doc.conditions.filter(c => c.params && c.params.free === true)) {
    out.push([`need-free-${c.id}`, '자율 키워드', h('input', { type: 'text', id: `need-free-${c.id}`, value: (c.params.keywords || []).join(', '),
      autocomplete: 'off' }), '강남맛집 가이드는 지정 키워드 말고 직접 고른 키워드도 3번 이상 써야 해요. 고른 키워드를 적어 주세요.']);
  }
  for (const c of doc.conditions.filter(c => c.params && c.params.needs_review === true && Number.isInteger(c.params.min))) {
    out.push([`need-min-${c.id}`, `기준 숫자: ${c.label}`, h('span', { class: 'with-unit' },
      h('input', { type: 'number', id: `need-min-${c.id}`, min: 0, inputmode: 'numeric', value: c.params.min }), h('span', { text: UNIT[c.type] || '' })),
    '가이드에서 이 숫자를 확인하지 못했어요. 가이드와 맞는지 봐 주세요.']);
  }
  if (doc.conditions.some(c => c.type === 'hashtag' && byId[c.id] && byId[c.id].status === 'missing')) {
    out.push(['need-tags', '에디터 태그 칸의 태그', h('input', { type: 'text', id: 'need-tags', value: S.extra.tags, placeholder: '#태그1, #태그2', autocomplete: 'off' }),
      '태그 칸에 넣은 태그는 복사할 때 따라오지 않아요. 넣었다면 적어 주세요.']);
  }
  if (!out.length) return null;
  const err = h('p', { class: 'field-err', id: 'needs-err', role: 'alert' });
  const apply = () => {
    const num = id => { const el = $(id); if (!el || el.value.trim() === '') return null; const n = Number(el.value); return Number.isInteger(n) && n >= 0 ? n : NaN; };
    const vals = { photo: num('need-photo'), video: num('need-video') };
    if (Object.values(vals).some(Number.isNaN)) { err.textContent = '사진·동영상 수는 0 이상의 숫자로 적어 주세요.'; return; }
    if ($('need-title')) S.extra.title = $('need-title').value;
    if ($('need-photo')) S.extra.photo = vals.photo;
    if ($('need-video')) S.extra.video = vals.video;
    if ($('need-map')) S.extra.map = $('need-map').value === '' ? null : $('need-map').value === 'true';
    if ($('need-tags')) S.extra.tags = $('need-tags').value;
    for (const c of S.doc.conditions) {
      const free = $(`need-free-${c.id}`), min = $(`need-min-${c.id}`);
      if (free) {
        c.params.keywords = free.value.split(',').map(s => s.trim()).filter(Boolean);
        S.edits[sig(c)] = { ...(S.edits[sig(c)] || {}), keywords: c.params.keywords };
      }
      if (min && min.value.trim() !== '') {
        const n = Number(min.value);
        if (!Number.isInteger(n) || n < 0) { err.textContent = '기준 숫자는 0 이상의 숫자로 적어 주세요.'; return; }
        c.params.min = n;
        delete c.params.needs_review;                    // 숫자를 확인했으면 표시를 지워요
        S.edits[sig(c)] = { ...(S.edits[sig(c)] || {}), min: n };
      }
    }
    check();
  };
  return h('section', { class: 'needs', id: 'needs', 'aria-labelledby': 'needs-title' },
    h('h2', { id: 'needs-title', text: '점검에 필요한 것' }),
    h('div', { class: 'needs-fields' }, out.map(([id, name, input, help]) => h('div', { class: 'need' },
      h('label', { for: id, text: name }), input, h('p', { class: 'hint', text: help })))),
    err,
    button('적은 값으로 다시 점검하기', 'quiet', apply, { id: 'recheck' }));
}

function conditionsList() {
  const d = S.doc;                                       // 지금 조건 (예시 모드의 결과는 처음 조건으로 미리 계산한 값이라 S.res.doc과 다를 수 있어요)
  const formName = S.form ? FORMS[S.form] : '일반';
  return h('details', { class: 'fold', id: 'conds-list' },
    h('summary', { text: `가이드에서 읽은 조건 ${d.conditions.length}개` }),
    h('p', { class: 'hint', text: formName ? `${formName} 가이드로 읽었어요. 조건이 아닌 줄이 있으면 빼고 다시 점검할 수 있어요.`
      : '조건이 아닌 줄이 있으면 빼고 다시 점검할 수 있어요.' }),
    h('ol', { class: 'conds' }, d.conditions.map(c => h('li', { class: 'cond', 'data-id': c.id },
      h('span', { class: 'kind', text: c.params.unverified ? '확인 못 한 조건' : TYPE[c.type] || c.type }),
      h('strong', { text: c.params.unverified ? `${c.label}. ${c.params.question}` : c.label }),
      c.guide_quote.text ? h('q', { class: 'quote', text: c.guide_quote.text }) : null,
      (c.extra_quotes || []).map(x => h('q', { class: 'quote quote-more', text: x.text })),
      button('이 조건 빼고 다시 점검', 'link', () => {
        removeCondition(c);
        check();
      }, { 'data-remove': c.id })))),
    S.removed.length ? h('p', { class: 'undo' }, `뺀 조건 ${S.removed.length}개. `,
      button('되돌리고 다시 점검', 'link', () => {
        const order = S.original.conditions.map(c => c.id);
        for (const c of S.removed) S.gone.delete(sig(c));
        S.doc.conditions.push(...S.removed.splice(0));
        S.doc.conditions.sort((a, b) => order.indexOf(a.id) - order.indexOf(b.id));
        check();
      }, { id: 'undo' })) : null);
}

function viewResult() {
  const { exact, doc, request } = S.res;
  const { inside, outside } = allItems();
  const notes = fixNotes();
  const look = inside.filter(([, r]) => r.status === 'hold').sort((a, b) => (a[0] === 'principle') - (b[0] === 'principle'));
  const kept = inside.filter(([, r]) => r.status === 'kept');
  const picked = S.selected && inside.find(([kind, r]) => keyOf(kind, r) === S.selected);
  const asked = qualitative(doc).length;
  const formName = S.form ? FORMS[S.form] : '일반';
  const pickForm = h('select', { id: 'form-pick', 'aria-label': '가이드 형식' },
    FORM_CHOICES.map(([value, text]) => h('option', { value, text: `${text} 가이드` })));
  pickForm.value = S.form || 'general';
  const copyBtn = button('문구 복사', 'quiet', () => copyText(DISCLOSURE_EXAMPLE, copyBtn, '복사했어요'), { id: 'copy-disclosure' });

  return [
    h('div', { class: 'result-head' },
      h('h1', { id: 'summary', tabindex: '-1', text: notes.length ? `고칠 곳 ${notes.length}개` : '고칠 곳이 없어요' }),
      h('p', { class: 'summary-more', id: 'summary-more', text: `직접 확인할 것 ${look.length}개, 지킨 것 ${kept.length}개.` }),
      // 가이드 형식은 가이드의 칸 이름으로 알아봐요. 묻지 않고, 못 알아보면 일반 가이드로 점검해요
      h('p', { class: 'form-line', id: 'form-line' }, `${formName} 가이드로 읽었어요 · `,
        button('바꾸기', 'link', () => { S.picking = !S.picking; render(); }, { id: 'change-form', 'aria-expanded': String(S.picking) })),
      S.picking ? h('div', { class: 'form-pick' }, pickForm,
        button('이 형식으로 다시 읽기', 'quiet', () => {
          S.formPick = pickForm.value;
          S.readGuide = null;                            // 같은 가이드라도 고른 형식으로 다시 읽어요
          start();
        }, { id: 'reread' })) : null),
    !exact && h('p', { class: 'banner', id: 'mock-banner', text:
      '예시 모드라서, 이 결과는 예시 원고와 처음 조건으로 미리 계산해 둔 값이에요. 붙여 넣은 원고나 고친 값은 서버를 붙인 뒤에 반영돼요.' }),
    S.aiState === 'reading' && h('p', { class: 'banner reading', id: 'ai-status', role: 'status',
      text: '가이드의 나머지 조건을 읽고 있어요. 지금 보이는 것은 코드가 읽은 조건의 결과예요.' }),
    S.aiState === 'failed' && h('div', { class: 'banner', id: 'ai-failed', role: 'alert' },
      h('p', { text: `나머지 조건은 읽지 못했어요. ${S.aiMsg} 코드가 읽은 결과는 그대로예요.` }),
      button('다시 시도', 'quiet', () => readRest(), { id: 'retry-ai' })),
    S.aiState === 'done' && S.aiMsg && h('p', { class: 'banner', id: 'ai-msg', role: 'status', text: S.aiMsg }),
    S.judging && h('p', { class: 'banner', id: 'judge-status', role: 'status',
      text: `셀 수 없는 조건 ${asked}개는 AI가 살펴보는 중이에요. 지금 보이는 결과는 코드로 센 결과예요.` }),
    S.judgeMsg && h('p', { class: 'banner', id: 'judge-msg', role: 'status', text: `${S.judgeMsg} 코드로 센 결과는 그대로예요.` }),
    needs(),
    h('div', { class: 'proof' },
      proofSheet(request, notes, picked && picked[1], openTips()),
      h('aside', { class: 'margin', 'aria-label': '고칠 곳 메모' },
        notes.length
          ? h('ol', { class: 'notes', id: 'notes' }, notes.map(({ kind, r, n }) => card(kind, r, { n })))
          : h('p', { class: 'clean', id: 'notes-empty', text: '빠진 조건을 찾지 못했어요. 아래 직접 확인할 것만 한 번 봐 주세요.' }))),
    h('div', { class: 'lists' },
      look.length ? h('section', { class: 'list', 'aria-labelledby': 'look-title' },
        h('h2', { id: 'look-title', text: `직접 확인할 것 ${look.length}개` }),
        h('p', { class: 'hint', text: '사진 내용처럼 세어 볼 수 없는 조건이에요. 원고를 보며 직접 확인해 주세요.' }),
        h('ol', { class: 'rows', id: 'look' }, look.map(([kind, r]) => card(kind, r, { cls: 'row' })))) : null,
      kept.length ? h('details', { class: 'fold', id: 'kept-list' },
        h('summary', { text: `지킨 것 ${kept.length}개` }),
        h('ol', { class: 'rows', id: 'kept' }, kept.map(([kind, r]) => card(kind, r, { cls: 'row' })))) : null,
      outside.length ? h('details', { class: 'fold', id: 'outside-list' },
        h('summary', { text: `원고 밖에서 확인할 것 ${outside.length}개` }),
        h('p', { class: 'hint', text: '등록 기간처럼 원고만 봐서는 알 수 없는 조건이에요. 위 개수에는 넣지 않았어요.' }),
        h('ul', { class: 'rows', id: 'outside' }, outside.map(r => h('li', { class: 'row plain' },
          h('strong', { class: 'label', text: r.label }), h('span', { class: 'line', text: r.note }))))) : null,
      // 도움이 될 팁: 점검 결과보다 한 단계 가볍게, 접어 둬요. 펼치고 접을 때 원고의 표시만 바꿔요
      tipsBlock(shownTips(), S.tipsOpen, open => { if (S.tipsOpen !== open) { S.tipsOpen = open; redrawSheet(); } }),
      conditionsList(),
      h('details', { class: 'fold', id: 'disclosure' },
        h('summary', { text: '대가성 문구 예시' }),
        h('p', { class: 'example-text', id: 'disclosure-example', text: DISCLOSURE_EXAMPLE }),
        h('p', { class: 'hint', text: '정해진 예시 문구예요. 가이드가 문구를 따로 정했다면 가이드 문구를 쓰세요.' }),
        copyBtn),
      keywordLinks(doc)),
    h('div', { class: 'go end' },
      button('원고 고치고 다시 점검하기', 'primary', () => { S.error = null; show('input', 'draft'); }, { id: 'edit' }),
      button('새로 점검하기', 'quiet', () => {
        Object.assign(S, { guide: '', draft: '', base: null, pasted: null, scenario: null, doc: null, res: null, error: null, readGuide: null,
          aiState: 'idle', aiMsg: '', edits: {}, gone: new Set(), formPick: null,
          extra: fresh(), last: null, changed: null, judged: null, selected: null, tipsOpen: false });
        show('input', 'page-title');
      }, { id: 'reset' })),
  ];
}

window.addEventListener('resize', () => { if (S.view === 'result') alignNotes(); });
if (document.fonts) document.fonts.ready.then(() => { if (S.view === 'result') alignNotes(); });
document.addEventListener('toggle', e => { if (e.target.closest && e.target.closest('#notes')) alignNotes(); }, true);

render();

// 자체 시험과 화면 확인용 (평소에는 불러오지 않아요)
if (/^#(selftest|selftest-server|shot-\d)$/.test(location.hash)) document.body.append(h('script', { src: 'selftest.js' }));
