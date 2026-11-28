"""조건 뽑기 정확도 재기 (개발용). 실행은 저장소 맨 위 폴더에서:

  python -m ai.eval                         저장된 응답을 지금 코드로 다시 채점해요. AI를 부르지 않아요.
  python -m ai.eval --max-calls 12          가이드마다 실제로 불러서 채점해요. 호출 상한은 코드가 세요 (--repeat로 가이드마다 몇 번).

- 실제 가이드·정답지·저장된 응답은 .env의 PROMPATCH_PRIVATE_DATA 폴더에서만 읽어요. 폴더 구조는 ai/README.md에 있어요.
- 화면에는 숫자만 써요 (가이드 글, 키워드, AI가 쓴 글은 안 써요). 실제로 부른 응답은 그 폴더의 results/에만 저장해요.
- 정답지에 없는 조건 = 채점표의 어느 항목에도 쓰이지 않은 조건이에요 (원고 밖 조건은 빼요).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

from . import client
from . import extract as ex

ENV = "PROMPATCH_PRIVATE_DATA"
NO_DATA = "비공개 자료가 없어요. .env의 PROMPATCH_PRIVATE_DATA에 폴더를 적어 주세요 (폴더 구조는 ai/README.md)."
LIMIT = 60                     # --max-calls를 크게 줘도 이 수를 넘지 않아요


# ── 비공개 폴더 ──────────────────────────────────────────────────────────

def private_dir() -> Path | None:
    ex.load_env()
    value = os.environ.get(ENV, "").strip()
    path = Path(value) if value else None
    return path if path and (path / "answer-keys" / "scoring.json").is_file() else None


def load_spec(base: Path) -> dict:
    return json.loads((base / "answer-keys" / "scoring.json").read_text(encoding="utf-8"))


def guide_text(base: Path, spec: dict, name: str) -> str:
    return (base / "guides" / spec["guides"][name]["file"]).read_text(encoding="utf-8").replace("\r\n", "\n")


# ── 채점 ─────────────────────────────────────────────────────────────────

def spec_items(spec: dict, name: str) -> list[dict]:
    """가이드의 채점 항목. 같은 플랫폼 양식이면 공통 항목(template_items)에 가이드별 값을 채워 써요."""
    g = spec["guides"][name]
    if "items" in g:
        return g["items"]
    out = []
    for item in spec["template_items"]:
        item = json.loads(json.dumps(item))
        params = item.get("params", {})
        if params.get("keywords_set") == "$keywords":
            params["keywords_set"] = g["keywords"]
        if "$extra_outside" in item.get("anchors", []):
            item["anchors"] = [a for a in item["anchors"] if a != "$extra_outside"] + g.get("extra_outside", [])
        out.append(item)
    return out


def quotes(c: dict) -> list[dict]:
    return [c["guide_quote"], *c.get("extra_quotes", [])]


def anchor_lines(guide: str, anchors: list[str]) -> list[tuple[int, int]]:
    return [(s, e) for s, e, t in ex._guide_lines(guide) if any(a in t for a in anchors)]


def touches(c: dict, spans: list[tuple[int, int]]) -> bool:
    return any(q["start"] < e and s < q["end"] for q in quotes(c) for s, e in spans)


def params_ok(c: dict, want: dict) -> bool:
    p = c["params"]
    for k, v in want.items():
        if k == "keywords_set" and set(p.get("keywords") or []) != set(v):
            return False
        if k == "keywords_count" and len(p.get("keywords") or []) != v:
            return False
        if k not in ("keywords_set", "keywords_count") and p.get(k) != v:
            return False
    return True


def score(guide: str, doc: dict, items: list[dict], heads: list[str]) -> dict:
    """항목마다 맞음/틀림과, 정답지에 없는 조건(원고 밖 칸에서 뽑은 것 포함)."""
    conds, used, verdicts = doc["conditions"], set(), {}
    for it in items:
        cls, ok = it["class"], False
        spans = anchor_lines(guide, it.get("anchors", []))
        near = [c for c in conds if spans and touches(c, spans)]
        if cls == "must":
            if "each_text" in it:
                hit = [c for c in conds if c["type"] == it["type"]]
                has = lambda c, t: t in (c["params"].get("phrase") or "") or any(t in q["text"] for q in quotes(c))
                ok = all(any(has(c, t) for c in hit) for t in it["each_text"])
                used.update(id(c) for t in it["each_text"] for c in hit if has(c, t))
            else:
                hit = [c for c in conds if c["type"] == it["type"] and c["countable"] and params_ok(c, it.get("params", {}))]
                ok = bool(hit)
                used.update(id(c) for c in hit)
        elif cls == "absent":
            bad = [c for c in conds if c["type"] == it["type"] and (
                "keywords_any" not in it or (set(c["params"].get("keywords") or []) & set(it["keywords_any"])
                                             and c["params"].get("pick") in ("each", "both")))]
            ok = not bad
        elif cls == "hold":
            ok = bool(near) and not [c for c in near if c["countable"]] and any(c["type"] != "outside_draft" for c in near)
            used.update(id(c) for c in near)
        elif cls == "outside":
            ok = not [c for c in near if c["type"] != "outside_draft"]
            used.update(id(c) for c in near if c["type"] == "outside_draft")
        elif cls == "either":
            ok = not [c for c in near if c["countable"]]
            used.update(id(c) for c in near)
        elif cls == "any_condition":
            hit = [c for c in near if c["type"] != "outside_draft"]
            ok = bool(hit)
            used.update(id(c) for c in hit)
        elif cls == "any_noncountable":
            hit = [c for c in conds if not c["countable"] and (c in near or any(w in c["label"] for w in it.get("label_any", [])))]
            ok = bool(hit)
            used.update(id(c) for c in hit)
        elif cls == "flag":
            hit = [c for c in conds if all(w in c["label"] for w in it["label_has"])]
            ok = bool(hit)
            used.update(id(c) for c in hit)
        verdicts[it["id"]] = ok
    lines = ex._guide_lines(guide)
    head = next((s for s, _, t in lines if any(" ".join(t.split()).startswith(h) for h in heads)), None)
    extra = [c for c in conds if id(c) not in used and c["type"] != "outside_draft"]
    in_outside = [c for c in extra if head is not None and any(q["start"] >= head for q in quotes(c))]
    return {"verdicts": verdicts, "extra": len(extra), "extra_in_outside": len(in_outside),
            "extra_kinds": sorted(c["type"] + ("" if c["countable"] else "(셀 수 없음)") for c in extra),
            "extra_list": extra, "conditions": len(conds),
            "signature": sorted({(c["type"], c["countable"], c["guide_quote"]["start"]) for c in conds})}   # 번끼리 겹침을 볼 때


def score_response(base: Path, spec: dict, name: str, response: dict) -> dict:
    guide = guide_text(base, spec, name)
    heads = spec["outside_heads"].get(spec["guides"][name].get("form"), [])
    doc, _ = ex.build(guide, response)
    return score(guide, doc, spec_items(spec, name), heads)


def table(base: Path, spec: dict, runs: dict[str, list[dict]]) -> list[str]:
    """가이드별 숫자 표 (글은 없어요)."""
    lines = ["| 가이드 | 항목 | 맞음(합) | 정확도 | 정답지에 없는 조건(합) | 조건 수(번마다) |", "| --- | --- | --- | --- | --- | --- |"]
    right = total = extra = 0
    kinds: Counter = Counter()
    for name, results in runs.items():
        n = len(spec_items(spec, name)) * len(results)
        r = sum(sum(x["verdicts"].values()) for x in results)
        e = sum(x["extra"] for x in results)
        lines.append(f"| {name} | {len(spec_items(spec, name))} | {r}/{n} | {r / n:.0%} | {e} | {', '.join(str(x['conditions']) for x in results)} |")
        right, total, extra = right + r, total + n, extra + e
        kinds.update(k for x in results for k in x["extra_kinds"])
    if total:
        lines.append(f"| 합계 | | {right}/{total} | {right / total:.0%} | {extra} | |")
        lines.append("\n정답지에 없는 조건의 종류: " + (", ".join(f"{k} {v}" for k, v in sorted(kinds.items())) or "없음"))
    return lines


# ── 저장된 응답 다시 채점 ────────────────────────────────────────────────

def rescore(base: Path, spec: dict) -> int:
    """responses/<묶음>/<가이드>-<…>.json을 지금 코드로 다시 채점해요. AI를 부르지 않아요."""
    sets = sorted(d for d in (base / "responses").iterdir() if d.is_dir()) if (base / "responses").is_dir() else []
    if not sets:
        print("저장된 응답이 없어요 (responses/<묶음>/<가이드>-<번>.json).")
        return 0
    every: dict[str, list[dict]] = {}
    for d in sets:
        runs: dict[str, list[dict]] = {}
        for f in sorted(d.glob("*.json")):
            name = f.stem.split("-")[0]
            raw = json.loads(f.read_text(encoding="utf-8"))
            if name in spec["guides"] and "response" in raw:
                runs.setdefault(name, []).append(score_response(base, spec, name, raw["response"]))
        if runs:
            print(f"## {d.name} (응답 {sum(map(len, runs.values()))}개)\n")
            print("\n".join(table(base, spec, runs)) + "\n")
            for name, rs in runs.items():
                every.setdefault(name, []).extend(rs)
    if len(sets) > 1 and every:
        print(f"## 모두 합쳐서 (응답 {sum(map(len, every.values()))}개)\n")
        print("\n".join(table(base, spec, every)))
    return 0


# ── 상한 있는 실제 호출 ──────────────────────────────────────────────────

def live(base: Path, spec: dict, max_calls: int, repeat: int) -> int:
    cap = min(max_calls, LIMIT)
    names = list(spec["guides"])
    plan = [(name, i) for i in range(1, repeat + 1) for name in names][:cap]
    print(f"계획: 가이드 {len(names)}개 × {repeat}번 → {len(plan)}번 (상한 {cap}번), 모델 {ex.model_name()}, effort {ex.EFFORT}")
    client.RETRIES = 0                       # 자동 다시 시도도 호출이라 꺼요
    out = base / "results" / f"eval-{time.strftime('%Y%m%d-%H%M%S')}"
    out.mkdir(parents=True, exist_ok=True)
    runs: dict[str, list[dict]] = {}
    calls, secs = 0, []
    for name, i in plan:
        if calls >= cap:                     # 실패한 호출도 1번으로 세요
            break
        calls += 1
        started = time.perf_counter()
        try:
            data, usage = client.call(ex.build_request(guide_text(base, spec, name)))
        except client.AIError as e:
            print(f"  {name} {i}번째: 실패 {e.code} (호출 {calls})")
            continue
        sec = round(time.perf_counter() - started, 1)
        secs.append(sec)
        (out / f"{name}-{i}.json").write_text(json.dumps({"usage": usage, "seconds": sec, "response": data}, ensure_ascii=False),
                                              encoding="utf-8")
        runs.setdefault(name, []).append(score_response(base, spec, name, data))
        print(f"  {name} {i}번째: {sec}초 (호출 {calls})", flush=True)
    print("\n" + "\n".join(table(base, spec, runs)))
    if secs:
        secs.sort()
        print(f"\n걸린 시간 가운데 {secs[len(secs) // 2]}초, 가장 긴 {secs[-1]}초")
    print(f"호출 {calls}번 (상한 {cap}번). 응답은 비공개 폴더의 results/{out.name}에만 저장했어요.")
    return 0


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(prog="python -m ai.eval", description="조건 뽑기 정확도 재기")
    p.add_argument("--max-calls", type=int, help=f"실제로 부를 때의 호출 상한 (최대 {LIMIT}). 없으면 저장된 응답만 다시 채점해요")
    p.add_argument("--repeat", type=int, default=1, help="가이드마다 몇 번 부를지 (기본 1)")
    args = p.parse_args(argv)
    base = private_dir()
    if base is None:
        print(NO_DATA)
        return 0
    spec = load_spec(base)
    if args.max_calls:
        return live(base, spec, args.max_calls, max(1, args.repeat))
    return rescore(base, spec)


if __name__ == "__main__":
    sys.exit(main())
