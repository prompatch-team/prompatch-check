// 이 파일은 손으로 고치지 않아요. tools/paste-test.html의 분석 코드를 그대로 옮긴 거예요.
// 고칠 때는 paste-test.html을 고친 뒤 python fe/make_analyze.py 를 돌려요.
'use strict';

// <<분석 코드 시작>> 여기부터 <<분석 코드 끝>>까지는 fe/analyze.js와 같아야 해요.
// 고치면 python fe/make_analyze.py 로 fe 쪽을 다시 만들어요. python -m unittest fe.test_fe 가 다르면 알려 줘요.
// ── 임시 힌트 ────────────────────────────────────────────────────────────
// class 이름을 낱말로 쪼갠 뒤(se-placesMap → se, places, map) 아래 낱말이 있으면 그 종류로 봐요.
// 실제 에디터 구조를 확인하기 전의 추측이에요. "구조만 복사" 결과를 보고 여기만 고쳐요.
const HINT = {
  video:   ['video', 'movie', 'vod'],
  map:     ['map', 'places', 'place', 'location'],
  oglink:  ['oglink', 'linkpreview'],
  sticker: ['sticker', 'emoticon'],
};
const isDocTitle  = w => w.includes('title') && w.includes('document');   // se-documentTitle
const isComponent = w => w.includes('component');                         // se-component
// ─────────────────────────────────────────────────────────────────────────

const VERSION = '0.4';
const KIND = { photo: '사진', video: '동영상', map: '지도·장소', oglink: '링크 카드', sticker: '스티커',
  banner: '캠페인 배너', profile: '프로필 사진', other: '본문 사진 블록 밖의 그림' };
// 사진 수에서 빼는 그림 (10단계, 실제 붙여넣기에서 찾은 것). 주소는 읽기만 하고 불러오지 않아요.
// 체험단 플랫폼이 본문 맨 위에 넣게 하는 배너 (주소, 경로 앞부분). 걸러서 사진 수에서 빼고 "배너"로 따로 세요.
// 레뷰 revu.net. 강남맛집은 사이트 주소의 /_sp/ 그림, 리뷰노트는 reviewnote.cloud의 /gongjeong/ 그림 (2026-11-27 확인)
const BANNERS = [
  { host: 'revu.net' },
  { host: 'xn--939au0g4vj8sq.net', path: '/_sp/' },
  { host: 'reviewnote.cloud', path: '/gongjeong/' },
];
const pathOf = src => ((/^(?:https?:)?\/\/[^\/?#]+(\/[^?#]*)?/i.exec(src) || [])[1] || '/');
const isBanner = src => {
  const host = hostOf(src), path = pathOf(src).toLowerCase();
  return BANNERS.some(b => (host === b.host || host.endsWith('.' + b.host)) && (!b.path || path.startsWith(b.path)));
};
// 배너가 "글 맨 위"인지: 첫 사진 블록이나 첫 3블록(se-component) 안. 맨 위 배너는 대가성 표시로 봐요 (우리 기준)
const TOP_BLOCKS = 3;
const PROFILE = /blogpfthumb|profile/i;               // 보기 화면의 블로거 프로필 사진
const hostOf = src => ((/^(?:https?:)?\/\/([^\/?#:]+)/i.exec(src) || [])[1] || '').toLowerCase();
const MARK = { photo: '[사진]', video: '[동영상]', map: '[지도]' };
// button: 슬라이드의 "Previous image / Next image" 같은 단추 글자는 본문이 아니에요
const SKIP = new Set(['script', 'style', 'noscript', 'template', 'head', 'meta', 'link', 'title', 'svg', 'button']);
// 글자 수 기준 (2026-11-27): "네이버 블로그 본문 글 블록에 쓴 글자". 스마트에디터 글 블록(se-module-text)이 있는 서식이면
// 글 블록 안의 글자만 본문(draft)에 넣어요. 보기 화면 머리·꼬리, 맨 아래 태그 칸, 링크 카드·동영상·지도 안 글은 빠져요.
// 사진 설명(se-caption)은 글 블록이라 넣고, 자리를 captions로 따로 알려요 (빼는 것은 서버 설정 PROMPATCH_COUNT_CAPTIONS=0).
// se-module-text, se-oglink는 실제 붙여넣기에서 확인했어요. se-caption은 2026-11-27 글쓰기 화면 복사 시험(samples/editor/)에서 확인했어요.
const SE_TEXT = 'se-module-text', SE_CAPTION = 'se-caption';
// 글쓰기 화면에서 복사하면 빈 칸의 안내 글자("사진 설명을 입력하세요." 등)가 se-placeholder로 따라와요. 글이 아니라서 읽지 않아요.
// 글쓰기 화면의 링크는 a 태그가 아니라 span.se-link[data-href]이고, 링크 카드 안에는 주소 글자(se-oglink-url)만 있어요.
// (셋 다 2026-11-27 글쓰기 화면 복사 시험 samples/editor/editor-test.html에서 확인)
const SE_PLACEHOLDER = 'se-placeholder', SE_LINK = 'se-link', SE_OGLINK_URL = 'se-oglink-url';
const EMBED = new Set(['video', 'iframe', 'embed', 'object']);
const BLOCK = new Set(('address article aside blockquote dd details div dl dt fieldset figcaption figure footer form ' +
  'h1 h2 h3 h4 h5 h6 header hr li main nav ol p pre section summary table td th tr ul').split(' '));

// 글자 수와 위치는 파이썬과 같게 코드 포인트로 세요 (이모지 1개 = 1글자)
const cp = s => Array.from(s).length;
// 보이지 않는 글자(에디터가 빈 줄에 넣는 것)를 지우고 공백을 하나로 묶어요
const zw = s => s.replace(/[​⁠﻿]/g, '');
const clean = s => zw(s).replace(/\s+/g, ' ');
const classWords = el => (el.getAttribute('class') || '')
  .split(/[\s_-]+|(?<=[a-z0-9])(?=[A-Z])/).filter(Boolean).map(w => w.toLowerCase());
const sel = el => [el.localName, ...(el.getAttribute('class') || '').split(/\s+/).filter(Boolean)].join('.');
const hashtagsIn = s => [...new Set(s.match(/(?<![\p{L}\p{N}_&\/#])#[\p{L}\p{N}_]+/gu) || [])];
// 공백 포함 = 문단 안의 글자와 띄어쓰기만 (2026-11-28 카티 결정). 줄바꿈·빈 줄·줄 앞뒤 공백은 세지 않아요
const counts = s => ({ spaces: s.split('\n').reduce((n, l) => n + cp(l.trim()), 0), noSpaces: cp(s.replace(/\s/g, '')) });

function specialKind(el) {
  const w = classWords(el);
  return Object.keys(HINT).find(k => w.some(x => HINT[k].includes(x))) || null;
}
function embedKind(el) {
  const hint = (classWords(el).join(' ') + ' ' + (el.getAttribute('src') || '')).toLowerCase();
  return hint.includes('map') ? 'map' : 'video';
}

// 붙여 넣은 HTML을 화면에 넣지 않고 DOMParser 문서 안에서만 읽어요. 이 문서는 사진을 불러오지 않아요.
function analyze(html) {
  const doc = new DOMParser().parseFromString(html, 'text/html');
  const body = doc.body;
  const lines = [];                 // { text, media, links }
  let cur = '', curLinks = [];
  const open = [];                  // 지금 열려 있는 a 태그
  const links = [], imgs = [], units = [], excluded = [], titles = [];
  // 네이버 글의 본문 사진에는 se-image-resource가 붙어요. 이 class가 있는 글이면 이것만 사진으로 세요
  // (프로필 사진, 링크 카드 썸네일 같은 그 밖의 그림은 빼요). 콜라주·슬라이드도 안의 사진마다 하나씩 세요.
  const resourceOnly = !!body.querySelector('img.se-image-resource');
  const seText = !!body.querySelector('.' + SE_TEXT);
  let inText = 0, inCaption = 0;
  const outside = [];               // 글 블록 밖 글자 (해시태그만 찾아요. 맨 아래 태그 칸의 태그도 해시태그 조건에는 써요)
  const banners = [];               // 걸러 낸 배너 그림 (맨 위인지 보려고 요소를 기억해요)
  const imgKind = el => {
    const src = el.getAttribute('src') || '';
    if (isBanner(src)) return 'banner';
    if (PROFILE.test(src) || PROFILE.test(el.getAttribute('class') || '')) return 'profile';
    if (resourceOnly && !classWords(el).includes('resource')) return 'other';
    return 'photo';
  };

  const push = (text, media = null) => {
    lines.push({ text, media, links: curLinks, caption: !media && inCaption > 0 }); cur = ''; curLinks = [];
  };
  const flush = () => { if (cur.trim()) push(cur.trimEnd()); else { cur = ''; } };
  const addText = raw => {
    if (seText && inText === 0) { outside.push(raw); return; }
    let t = clean(raw);
    if (cur === '' || cur.endsWith(' ')) t = t.trimStart();
    if (!t) return;
    if (t.trim()) for (const l of open) if (l.col === null) {
      l.col = cur.length + (t.length - t.trimStart().length);
      curLinks.push(l);
    }
    cur += t;
  };
  const compLabel = el => {
    let top = el;
    for (let p = el; p && p !== body; p = p.parentElement) {
      if (isComponent(classWords(p))) return sel(p);
      top = p;
    }
    return sel(top);
  };

  function walk(node, special, buf) {
    for (const child of node.childNodes) {
      if (child.nodeType === 3) { special ? buf.push(child.nodeValue) : addText(child.nodeValue); continue; }
      if (child.nodeType !== 1) continue;
      const name = child.localName;
      if (SKIP.has(name)) continue;
      const own = (child.getAttribute('class') || '').split(/\s+/);
      if (own.includes(SE_PLACEHOLDER)) continue;
      if (name === 'br') { if (!special) push(cur.trimEnd()); continue; }
      if (name === 'img') {
        const kind = special || imgKind(child);
        imgs.push({ kind, comp: compLabel(child) });
        if (kind === 'banner') banners.push(child);
        if (kind === 'photo') { flush(); push(MARK.photo, 'photo'); }
        continue;
      }
      let link = null;
      const href = name === 'a' ? child.getAttribute('href') : own.includes(SE_LINK) ? child.getAttribute('data-href') : null;
      if (href != null) {
        const url = href.trim();
        if (url && !/^(#|javascript:)/i.test(url)) {
          link = { url, where: special || 'body', col: null, start: null };
          links.push(link);
        }
      }
      if (special) { walk(child, special, buf); continue; }

      // 바깥쪽에서 처음 만난 동영상·지도·링크 카드·스티커 묶음을 하나로 세요
      const kind = specialKind(child) || (EMBED.has(name) ? embedKind(child) : null);
      if (kind) {
        units.push({ kind, label: sel(child) });
        if (MARK[kind]) { flush(); push(MARK[kind], kind); }
        const inner = [], before = links.length;
        walk(child, kind, inner);
        // 글쓰기 화면의 링크 카드: a 태그가 없으면 카드 안 주소 글자로 링크 하나를 세요 (보기 화면 카드에는 a 태그가 있어요)
        const urlEl = kind === 'oglink' && links.length === before ? child.querySelector('.' + SE_OGLINK_URL) : null;
        const shown = urlEl ? clean(urlEl.textContent).trim() : '';
        if (shown) links.push({ url: /^https?:\/\//i.test(shown) ? shown : 'https://' + shown, where: 'oglink', col: null, start: null });
        const text = clean(inner.join(' ')).trim();
        if (text) excluded.push({ kind, text });
        continue;
      }
      if (isDocTitle(classWords(child))) {
        const text = clean(child.textContent).trim();
        if (text) titles.push({ text, how: 'class에 documentTitle (본문에서 뺌)', strong: true });
        continue;
      }
      if (/^h[1-3]$/.test(name)) {
        const text = clean(child.textContent).trim();
        if (text) titles.push({ text, how: name + ' 태그', strong: false });
      }

      const block = BLOCK.has(name);
      let mark = 0;
      if (block) { flush(); mark = lines.length; }
      const textBlock = own.includes(SE_TEXT), caption = own.includes(SE_CAPTION);
      inText += textBlock; inCaption += caption;
      if (link) open.push(link);
      walk(child, null, null);
      if (link) open.pop();
      if (block) {
        if (cur.trim()) push(cur.trimEnd());
        else {
          cur = '';
          // 빈 문단(빈 줄)을 살려요: 빈 p, 또는 보이지 않는 글자만 든 요소.
          // 글 블록이 있는 서식에서는 글 블록 안만 (사진 블록의 "AI 활용 설정" 같은 편집 화면 문단은 빈 줄이 아니에요).
          // 비어 있는 사진 설명 칸도 빈 줄이 아니에요 (글쓰기 화면에서는 사진마다 빈 설명 칸이 따라와요)
          if (lines.length === mark && (!seText || (inText > 0 && inCaption === 0)) && (name === 'p' || /[​ ]/.test(child.textContent))) push('');
        }
      }
      inText -= textBlock; inCaption -= caption;
    }
  }
  walk(body, null, null);
  flush();

  // 빈 줄 정리: 맨 앞·맨 뒤는 지우고, 이어진 빈 줄은 하나로
  const kept = [];
  for (const ln of lines) {
    if (ln.text === '' && (kept.length === 0 || kept[kept.length - 1].text === '')) continue;
    kept.push(ln);
  }
  while (kept.length && kept[kept.length - 1].text === '') kept.pop();

  // 위치 계산 (코드 포인트)
  const media = [], captions = [];
  let off = 0;
  for (const ln of kept) {
    if (ln.media) media.push({ kind: ln.media, start: off });
    if (ln.caption && ln.text) captions.push({ start: off, end: off + cp(ln.text) });
    for (const l of ln.links) l.start = off + cp(ln.text.slice(0, l.col));
    off += cp(ln.text) + 1;
  }
  const draft = kept.map(l => l.text).join('\n');
  const bodyOnly = kept.filter(l => !l.media).map(l => l.text).join('\n');
  const firstLine = kept.find(l => !l.media && l.text);
  if (firstLine) titles.push({ text: firstLine.text, how: '본문 첫 줄 (참고)', strong: false });

  // 최상위 요소: 감싸는 요소가 하나뿐이면 안으로 들어가요
  let root = body;
  const path = [];
  const els = n => [...n.children].filter(c => !SKIP.has(c.localName));
  const ownText = n => [...n.childNodes].some(c => c.nodeType === 3 && clean(c.nodeValue).trim());
  while (els(root).length === 1 && !ownText(root) && els(els(root)[0]).length) { root = els(root)[0]; path.push(sel(root)); }
  const top = new Map();
  for (const c of els(root)) top.set(sel(c), (top.get(sel(c)) || 0) + 1);

  // 맨 위 배너: 배너가 든 블록(가장 바깥 se-component)이 첫 3블록 안이거나 첫 사진 블록이면.
  // 블록 구조가 없는 서식이면 글의 첫 그림 자리에 배너가 있을 때만.
  const outer = el => { let c = null; for (let p = el; p && p !== body; p = p.parentElement) if (isComponent(classWords(p))) c = p; return c; };
  const blocks = [...body.querySelectorAll('*')].filter(el => isComponent(classWords(el)) && outer(el) === el);
  const firstPhoto = blocks.find(b => [...b.querySelectorAll('img')].some(i => imgKind(i) === 'photo' || imgKind(i) === 'banner'));
  const bannerTop = banners.some(img => {
    const block = outer(img);
    if (!block) return body.querySelector('img') === img;
    const at = blocks.indexOf(block);
    return at >= 0 && (at < TOP_BLOCKS || block === firstPhoto);
  });

  return {
    draft, bodyOnly, media, captions, links, imgs, units, excluded, titles, seText,
    title: (titles.find(t => t.strong) || {}).text || null,
    photoCount: imgs.filter(i => i.kind === 'photo').length,
    bannerCount: banners.length, bannerTop,
    videoCount: units.filter(u => u.kind === 'video').length,
    hasMap: units.some(u => u.kind === 'map'),
    hashtags: hashtagsIn(bodyOnly + '\n' + outside.join('\n')),
    // 아래 태그 칸: 글 블록 밖의 해시태그 (강남맛집 키워드 횟수에 써요, 2026-11-28)
    // ponytail: 글 블록 밖 해시태그를 모두 태그 칸으로 봐요. 태그 칸이 아닌 블록 밖 해시태그가 보이면 태그 칸 class로 좁히기
    tagArea: hashtagsIn(outside.join('\n')),
    top: [...top], path,
    dump: structure(doc),
  };
}

// "구조만": 태그 이름과 class 이름만 남겨요. 글, 주소, 다른 속성은 넣지 않아요.
function structure(doc) {
  const ser = (el, depth) => {
    const hasText = [...el.childNodes].some(n => n.nodeType === 3 && clean(n.nodeValue).trim());
    const out = [];
    let prev = null, n = 0;
    const emit = () => {
      if (prev === null) return;
      const ls = prev.split('\n');
      if (n > 1) ls[0] += '  ×' + n;
      out.push(...ls);
    };
    for (const k of el.children) {
      const s = ser(k, depth + 1);
      if (s === prev) n++; else { emit(); prev = s; n = 1; }
    }
    emit();
    return '  '.repeat(depth) + sel(el) + (hasText ? ' [글]' : '') + (out.length ? '\n' + out.join('\n') : '');
  };
  const count = t => doc.body.querySelectorAll(t).length;
  return [
    '# paste-test 구조만: 태그와 class 이름뿐이에요. [글] = 글자가 든 자리, ×N = 같은 모양이 N번 이어짐',
    `# img ${count('img')} / video ${count('video')} / iframe ${count('iframe')} / a ${count('a')}`,
    ...[...doc.body.children].length ? [ser(doc.body, 0)] : ['(요소 없음)'],
  ].join('\n');
}

// contracts/check-request (0.4) 모양. 이 JSON이 점검 요청 형식의 기준이에요.
// counts_source: 이 도구는 숫자를 고치는 칸이 없어서 html이면 항상 parsed(자동으로 센 값)예요.
function toRequest(r) {
  return {
    version: VERSION, input_mode: 'html', counts_source: 'parsed', title: r.title, draft_text: r.draft,
    photo_count: r.photoCount, video_count: r.videoCount, has_map: r.hasMap,
    links: r.links.filter(l => l.where === 'body' || l.where === 'oglink').map(l => ({ url: l.url, start: l.start })),
    hashtags: r.hashtags, tag_area: r.tagArea, media: r.media, captions: r.captions,
    banner_count: r.bannerCount, banner_top: r.bannerTop,
  };
}
function toTextRequest(plain) {
  return {
    version: VERSION, input_mode: 'text', counts_source: 'user', title: null, draft_text: plain,
    photo_count: null, video_count: null, has_map: null,
    links: [], hashtags: hashtagsIn(plain), tag_area: [], media: [], captions: [],   // 글만이면 태그 칸은 엔진이 글에서 찾아요
    banner_count: null, banner_top: null,                // 글만 붙여 넣으면 그림을 못 봐요
  };
}
// <<분석 코드 끝>>
