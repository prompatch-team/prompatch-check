"""개발용 명령: python -m ai <가이드 파일> [--call] [--out 결과.json] [--compare 기준.json]

- 캐시(ai/cache/)에 같은 가이드의 결과가 있으면 그걸 써요. API를 부르지 않아요.
- 캐시가 없으면 멈추고 알려 줘요. --call을 붙였을 때만 AI API를 한 번 불러요.
- 조건 목록은 화면(또는 --out 파일)에, 버린 목록은 그 아래에 따로 보여 줘요.
- --compare를 주면 조건 목록 대신 기준 조건 목록과 비교한 표를 보여 줘요.
- --quiet를 주거나 가이드가 holdout 폴더에 있으면 개수만 보여 줘요. 조건, 인용, 버린 문장은 보여 주지 않아요.
"""
import argparse
import json
import sys
from pathlib import Path

from . import compare as cmp
from . import extract as ex

parser = argparse.ArgumentParser(prog="python -m ai", description="가이드 원문에서 조건 목록을 뽑아요")
parser.add_argument("guide", type=Path, help="가이드 글 파일 (지어낸 예시는 samples/, 실제 가이드는 private/)")
parser.add_argument("--call", action="store_true", help="캐시가 없으면 AI API를 한 번 불러요")
parser.add_argument("--out", type=Path, help="조건 목록 JSON을 저장할 파일")
parser.add_argument("--compare", type=Path, help="비교할 기준 조건 목록 JSON (예: contracts/conditions.example.json)")
parser.add_argument("--quiet", action="store_true", help="개수만 보여 줘요 (holdout 폴더의 가이드는 늘 이렇게 해요)")
args = parser.parse_args()

for stream in (sys.stdout, sys.stderr):
    stream.reconfigure(encoding="utf-8")
ex.load_env()
guide = args.guide.read_text(encoding="utf-8")

cache_dir = ex.cache_dir_for(args.guide)       # samples/private/ 아래의 가이드는 ai/cache/private/에
if ex.cached(cache_dir, guide) is None and not args.call:
    sys.exit(f"캐시가 없어요. AI API를 1번 불러야 해요 (모델: {ex.model_name()}). 부르려면 --call을 붙여 주세요.")
try:
    doc, dropped = ex.extract(guide, cache_dir=cache_dir, guide_id=args.guide.stem)
except ex.ExtractError as why:
    sys.exit(f"조건을 뽑지 못했어요: {why}")

if args.quiet or "holdout" in args.guide.resolve().parts:
    # holdout은 열어 보지 않는 샘플이에요. 내용은 화면에도 파일에도 내보내지 않고 개수만 알려 줘요.
    if args.out or args.compare:
        sys.exit("holdout 가이드(또는 --quiet)에는 --out, --compare를 쓸 수 없어요. 개수만 보여 줘요.")
    review_count = sum(bool(c["params"].get("needs_review")) for c in doc["conditions"])
    print(f"조건 {len(doc['conditions'])}개, 버린 조건 {len(dropped)}개, 숫자 확인 필요 {review_count}개 (내용은 보여 주지 않아요)")
    sys.exit(0)

text = json.dumps(doc, ensure_ascii=False, indent=2)
if args.out:
    args.out.write_text(text + "\n", encoding="utf-8")
    print(f"조건 {len(doc['conditions'])}개를 {args.out}에 저장했어요.")
elif not args.compare:
    print(text)
if args.compare:
    rows = cmp.compare(doc, json.loads(args.compare.read_text(encoding="utf-8")))
    print(cmp.table(rows))
    print("\n" + ", ".join(f"{k} {v}" for k, v in cmp.summary(rows).items()))
review = [c for c in doc["conditions"] if c["params"].get("needs_review")]
print(f"\n숫자 확인이 필요한 조건(needs_review) {len(review)}개", file=sys.stderr)
for c in review:
    print(f"  - {c['id']} | {c['type']} | {c['label']}", file=sys.stderr)
print(f"\n버린 조건 {len(dropped)}개", file=sys.stderr)
for d in dropped:
    print(f"  - {d['reason']} | {d['type']} | {d['label']} | {d['quote']}", file=sys.stderr)
