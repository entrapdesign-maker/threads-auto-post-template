"""計測エントリ (PDCA の C→A の統括)。

analytics エージェントを呼び、Threads Insights を取得して傾向を集計し、
prompts/learnings.md を自動更新する。

GitHub Actions の measure.yml から毎晩呼ばれる。
手動実行も可: `python scripts/measure.py`

環境変数:
  ANTHROPIC_API_KEY     (必須)
  THREADS_ACCESS_TOKEN  (必須, threads_manage_insights 権限つき)
  MEASURE_DAYS          (任意, 既定 14 = 直近何日分を集計するか)
"""

from __future__ import annotations

import os
import sys

from agents import analytics, common


def main() -> int:
    try:
        client = common.get_client()
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    days = int(os.environ.get("MEASURE_DAYS", "14"))
    try:
        measured = analytics.collect(days=days)
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    analytics.update_learnings(client, measured)
    print("done: 計測とフィードバック反映が完了しました")
    return 0


if __name__ == "__main__":
    sys.exit(main())
