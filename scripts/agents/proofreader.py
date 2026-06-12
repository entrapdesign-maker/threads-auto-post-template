"""校正エージェント (PDCA の D)。

writer が作った各投稿(メイン+返信)を1件ずつ点検し、
誤字脱字・AIっぽい言い回し・不要な記号や装飾・文字数オーバーを直す。
内容や主張は変えず、整える/削るだけ。
"""

from __future__ import annotations

import json
import re

from . import common

_SYSTEM = """あなたはThreads投稿の校正担当です。受け取った投稿群を、意味を変えずに整えます。

直すもの:
- 誤字脱字・不自然な助詞・二重表現
- AIっぽい定型句 (「〜と言えるでしょう」「いかがでしたか」「〜することが重要です」「まとめると」など)
- 不要な記号・装飾・過剰な絵文字 (絵文字は0〜1個まで)・ハッシュタグ
- メイン/各返信が120文字を超える場合は、主張を保ったまま削る

守るもの:
- 主張・体験・固有の言い回しは残す。無難に薄めない。
- ツリーの本数(メイン+返信)は増減させない。

出力は受け取ったものと同じJSON構造のみ。前置きや講評は書かない。
{"posts": [{"slot": "07:00", "main": "...", "replies": ["...","...","...","..."]}, ...]}"""


def _extract_json(text: str) -> dict | None:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def run(client, posts_by_slot: dict[str, dict]) -> dict[str, dict]:
    payload = {
        "posts": [
            {"slot": slot, "main": v.get("main", ""), "replies": v.get("replies", [])}
            for slot, v in posts_by_slot.items()
        ]
    }
    user_prompt = (
        "次の投稿群を校正し、同じJSON構造で返してください。\n\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )

    try:
        msg = client.messages.create(
            model=common.DEFAULT_MODEL,
            max_tokens=4000,
            system=_SYSTEM,
            messages=[{"role": "user", "content": user_prompt}],
        )
        data = _extract_json(common.collect_text(msg))
    except Exception as e:
        print(f"proofreader: 校正に失敗。原文をそのまま使います: {e}")
        return posts_by_slot

    if not data or "posts" not in data:
        print("proofreader: 構造化出力を取得できず、原文をそのまま使います")
        return posts_by_slot

    result = dict(posts_by_slot)
    for item in data["posts"]:
        slot = item.get("slot")
        if slot in result and item.get("main"):
            result[slot] = {
                "main": item.get("main", "").strip(),
                "replies": [r.strip() for r in item.get("replies", []) if r.strip()],
            }
    print(f"proofreader: {len(data['posts'])} スロット分を校正")
    return result
