"""
Threadsの投稿ドラフトをClaude APIで生成し、drafts/YYYY-MM-DD.jsonに書き出す。

呼び出し: 週1回 cron + 手動 workflow_dispatch

入力:
  - prompts/system.md  (キャラクター・ルールのシステムプロンプト)
  - prompts/user.md    (本日のテーマ・ニュース等の差し込み)
  - 環境変数: ANTHROPIC_API_KEY, DAYS

出力:
  drafts/YYYY-MM-DD.json
  {
    "date": "YYYY-MM-DD",
    "scheduled_at": "YYYY-MM-DDTHH:MM:00+09:00",
    "main": "...",
    "replies": ["...", "..."],
    "posted": false,
    "post_ids": []
  }
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import anthropic

JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent
DRAFTS_DIR = ROOT / "drafts"
PROMPTS_DIR = ROOT / "prompts"

# 投稿時間 (JST) — 必要に応じて prompts/schedule.json で上書き
DEFAULT_POST_HOUR = 8
DEFAULT_POST_MINUTE = 0


def load_prompt(name: str) -> str:
    path = PROMPTS_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"prompt not found: {path}")
    return path.read_text(encoding="utf-8")


def parse_response(text: str) -> dict:
    """
    モデル出力から main / replies を抽出する。
    期待フォーマット:
      MAIN:
      <本文>

      REPLY1:
      <続き1>

      REPLY2:
      <続き2>
    """
    sections: dict[str, list[str]] = {}
    current = None
    for line in text.splitlines():
        m = re.match(r"^(MAIN|REPLY\d+)\s*:\s*$", line.strip())
        if m:
            current = m.group(1)
            sections[current] = []
            continue
        if current is not None:
            sections[current].append(line)

    def join(key: str) -> str:
        return "\n".join(sections.get(key, [])).strip()

    main = join("MAIN")
    replies = []
    for i in range(1, 10):
        body = join(f"REPLY{i}")
        if body:
            replies.append(body)

    if not main:
        # フォールバック: 全文を main にする
        main = text.strip()

    return {"main": main, "replies": replies}


def generate_one(client: anthropic.Anthropic, system_prompt: str, user_prompt: str, target_date: str) -> dict:
    user_filled = user_prompt.replace("{{DATE}}", target_date)
    msg = client.messages.create(
        model=os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6"),
        max_tokens=1500,
        system=system_prompt,
        messages=[{"role": "user", "content": user_filled}],
    )
    text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    return parse_response(text)


def main() -> int:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY が設定されていません", file=sys.stderr)
        return 1

    days = int(os.environ.get("DAYS", "7"))
    DRAFTS_DIR.mkdir(exist_ok=True)

    system_prompt = load_prompt("system.md")
    user_prompt = load_prompt("user.md")

    client = anthropic.Anthropic(api_key=api_key)
    today = datetime.now(JST).date()
    created = 0

    for offset in range(days):
        target = today + timedelta(days=offset)
        date_str = target.isoformat()
        out_path = DRAFTS_DIR / f"{date_str}.json"
        if out_path.exists():
            print(f"skip: {out_path.name} already exists")
            continue

        print(f"generating: {date_str}")
        result = generate_one(client, system_prompt, user_prompt, date_str)

        scheduled_dt = datetime(
            target.year, target.month, target.day,
            DEFAULT_POST_HOUR, DEFAULT_POST_MINUTE, tzinfo=JST,
        )
        payload = {
            "date": date_str,
            "scheduled_at": scheduled_dt.isoformat(timespec="seconds"),
            "main": result["main"],
            "replies": result["replies"],
            "posted": False,
            "post_ids": [],
        }
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        created += 1

    print(f"done: created {created} draft(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
