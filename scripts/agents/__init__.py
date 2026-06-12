"""Threads投稿PDCAのエージェント群。

各タスク = 1エージェント:
  research     リサーチ (P: Web検索でネタ出し)
  writer       投稿文作成 (D: 5ツリー×4枠生成)
  proofreader  校正 (D: 誤字/AIっぽさ/記号チェック)
  analytics    計測 (C+A: インサイト取得→learnings更新)

管理エージェント: scripts/pdca_manager.py (P→D) と scripts/measure.py (C→A)。
共通基盤: scripts/agents/common.py。
"""
