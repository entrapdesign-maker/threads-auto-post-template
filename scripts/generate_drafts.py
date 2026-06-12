"""[後方互換ラッパ] 旧 generate_drafts は pdca_manager に統合されました。

旧構成 (1日1投稿) から PDCAマルチエージェント構成 (1日4投稿×5ツリー) へ移行したため、
このスクリプトは新しい管理エージェント scripts/pdca_manager.py を呼び出すだけのラッパです。

直接の生成ロジックは:
  - scripts/pdca_manager.py        (P→D: research→writer→proofreader)
  - scripts/agents/research.py     (リサーチ)
  - scripts/agents/writer.py       (投稿文作成)
  - scripts/agents/proofreader.py  (校正)

環境変数 DAYS / CLAUDE_MODEL / ANTHROPIC_API_KEY は pdca_manager がそのまま使います。
"""

from __future__ import annotations

import sys

from pdca_manager import main

if __name__ == "__main__":
    print("note: generate_drafts は pdca_manager に統合されています。pdca_manager を実行します。")
    sys.exit(main())
