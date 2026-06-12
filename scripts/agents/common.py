"""エージェント共通の基盤ユーティリティ。

- Claudeクライアントの生成 (ANTHROPIC_API_KEY / CLAUDE_MODEL)
- JST・各ディレクトリのパス
- 投稿スロット定数 POST_SLOTS と scheduled_at 生成
- ドラフトJSONの load/save と新旧スキーマの正規化
- プロンプト・learnings の読み込み
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import anthropic

JST = timezone(timedelta(hours=9))

ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = ROOT / "scripts"
PROMPTS_DIR = ROOT / "prompts"
DRAFTS_DIR = ROOT / "drafts"
RESEARCH_DIR = ROOT / "research"
INSIGHTS_DIR = ROOT / "insights"

# 1日4投稿の枠 (JST)。ここを変えれば投稿時刻が変わる。
POST_SLOTS = ["07:00", "12:00", "19:00", "21:00"]

# 5ツリー型 = メイン1 + 返信4 = 5投稿
REPLIES_PER_POST = 4

DEFAULT_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")


# レート上限(429)に当たったとき、SDKが retry-after に従って自動リトライする回数。
# 無料/低ティア(例: 30,000 input tokens/分)でも通るよう多めにする。
MAX_RETRIES = int(os.environ.get("ANTHROPIC_MAX_RETRIES", "8"))

# 各エージェント(リサーチ→作成→校正)の間に空ける秒数。
# 1分あたりの入力トークン上限をまたいで処理を分散させ、429を避ける。
STAGE_PACING_SECONDS = int(os.environ.get("STAGE_PACING_SECONDS", "30"))


def get_client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY が設定されていません")
    return anthropic.Anthropic(api_key=api_key, max_retries=MAX_RETRIES)


def collect_text(message) -> str:
    """messages.create のレスポンスから text ブロックだけを連結する。"""
    parts = []
    for block in message.content:
        if getattr(block, "type", "") == "text":
            parts.append(block.text)
    return "".join(parts)


def load_prompt(name: str) -> str:
    path = PROMPTS_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"prompt not found: {path}")
    return path.read_text(encoding="utf-8")


def load_learnings() -> str:
    """計測フィードバック (prompts/learnings.md)。無ければ空文字。"""
    path = PROMPTS_DIR / "learnings.md"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def slot_scheduled_at(date_str: str, slot: str) -> str:
    """'2026-06-12' と '07:00' から ISO8601(+09:00) を作る。"""
    hour, minute = (int(x) for x in slot.split(":"))
    y, m, d = (int(x) for x in date_str.split("-"))
    dt = datetime(y, m, d, hour, minute, tzinfo=JST)
    return dt.isoformat(timespec="seconds")


def empty_post(date_str: str, slot: str) -> dict:
    return {
        "slot": slot,
        "scheduled_at": slot_scheduled_at(date_str, slot),
        "theme": "",
        "main": "",
        "replies": [],
        "posted": False,
        "post_ids": [],
        "posted_at": None,
    }


def load_draft(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_draft(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_draft(data: dict, date_str: str | None = None) -> dict:
    """新スキーマ(posts[])に正規化する。

    旧スキーマ(トップレベル main/replies/posted)も読めるよう、
    1投稿だけの posts[] に変換する。
    """
    if "posts" in data and isinstance(data["posts"], list):
        return data

    date_value = data.get("date") or date_str or ""
    scheduled = data.get("scheduled_at") or (
        slot_scheduled_at(date_value, POST_SLOTS[0]) if date_value else ""
    )
    slot = scheduled[11:16] if len(scheduled) >= 16 else POST_SLOTS[0]
    return {
        "date": date_value,
        "posts": [
            {
                "slot": slot,
                "scheduled_at": scheduled,
                "theme": data.get("theme", ""),
                "main": data.get("main", ""),
                "replies": data.get("replies", []),
                "posted": data.get("posted", False),
                "post_ids": data.get("post_ids", []),
                "posted_at": data.get("posted_at"),
            }
        ],
    }
