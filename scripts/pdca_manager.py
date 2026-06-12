"""PDCA管理エージェント (P→D の統括)。

research(P) → writer(D) → proofreader(D) を順に回し、
当日分の drafts/YYYY-MM-DD.json を 4枠×5ツリー で書き出す。

GitHub Actions の pdca-generate.yml から毎朝呼ばれる。
手動実行も可: `DAYS=1 python scripts/pdca_manager.py`

環境変数:
  ANTHROPIC_API_KEY  (必須)
  CLAUDE_MODEL       (任意, 既定 claude-sonnet-4-6)
  DAYS               (任意, 既定 1 = 当日のみ生成)
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta

from agents import common, proofreader, research, writer


def generate_for_date(client, date_str: str) -> bool:
    out_path = common.DRAFTS_DIR / f"{date_str}.json"
    if out_path.exists():
        print(f"skip: {out_path.name} は既に存在します")
        return False

    print(f"=== generate {date_str} ===")
    # P: リサーチ
    ideas = research.run(client, date_str)["ideas"]
    # D: 作成
    drafts_by_slot = writer.run(client, ideas)
    # D: 校正
    drafts_by_slot = proofreader.run(client, drafts_by_slot)

    posts = []
    idea_by_slot = {i["slot"]: i for i in ideas}
    for slot in common.POST_SLOTS:
        post = common.empty_post(date_str, slot)
        post["theme"] = idea_by_slot.get(slot, {}).get("theme", "")
        written = drafts_by_slot.get(slot, {})
        post["main"] = written.get("main", "")
        post["replies"] = written.get("replies", [])
        posts.append(post)

    common.save_draft(out_path, {"date": date_str, "posts": posts})
    filled = sum(1 for p in posts if p["main"])
    print(f"saved: {out_path.name} ({filled}/{len(posts)} 枠生成)")
    return True


def main() -> int:
    try:
        client = common.get_client()
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    days = int(os.environ.get("DAYS", "1"))
    today = datetime.now(common.JST).date()
    created = 0
    for offset in range(days):
        date_str = (today + timedelta(days=offset)).isoformat()
        if generate_for_date(client, date_str):
            created += 1

    print(f"done: {created} 日分のドラフトを生成しました")
    return 0


if __name__ == "__main__":
    # `python scripts/pdca_manager.py` で実行すると scripts/ が sys.path[0] に入り、
    # `agents` パッケージがそのまま import できる。
    sys.exit(main())
