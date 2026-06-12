"""投稿文作成エージェント (PDCA の D)。

リサーチの4テーマ + prompts/system.md の文体ルール + learnings をもとに、
4枠ぶんの「5ツリー型」(メイン1 + 返信4) を1回の生成でまとめて作る。

出力フォーマット(モデルに厳守させる):
  === SLOT 07:00 ===
  MAIN:
  <本文>
  REPLY1:
  <本文>
  ... REPLY4 まで
  === SLOT 12:00 ===
  ...
"""

from __future__ import annotations

import re

from . import common

_FORMAT_RULE = """## 出力フォーマット (厳守)
各スロットを以下の形式で、4スロットすべて出力する。前置き・解説・コードブロックは書かない。

=== SLOT {slot} ===
MAIN:
<メイン投稿: 120文字以内, 最初の1行でフック, 主張は1つ>
REPLY1:
<ツリー1本目: 120文字以内, 1投稿1論点>
REPLY2:
<ツリー2本目>
REPLY3:
<ツリー3本目>
REPLY4:
<ツリー4本目: 最後はゆるい問いかけや一言でしめる>"""


def _build_user_prompt(ideas: list[dict]) -> str:
    learnings = common.load_learnings()
    lines = ["以下の4テーマで、それぞれ5ツリー型(メイン+返信4)の投稿を作成してください。", ""]
    for idea in ideas:
        lines.append(f"### SLOT {idea['slot']}")
        lines.append(f"- テーマ: {idea.get('theme','')}")
        if idea.get("angle"):
            lines.append(f"- 核になる主張: {idea['angle']}")
        if idea.get("evidence"):
            lines.append(f"- 参考/根拠: {idea['evidence']}")
        lines.append("")
    if learnings:
        lines += [
            "## これまでの計測から分かった『伸びる投稿』の傾向 (必ず反映する)",
            learnings,
            "",
        ]
    lines.append(_FORMAT_RULE)
    return "\n".join(lines)


_SLOT_HEADER = re.compile(r"^===\s*SLOT\s+(\d{1,2}:\d{2})\s*===\s*$")
_FIELD_HEADER = re.compile(r"^(MAIN|REPLY\d+)\s*:\s*$")


def _parse(text: str) -> dict[str, dict]:
    """テキストを {slot: {"main": str, "replies": [..]}} に分解する。"""
    slots: dict[str, dict] = {}
    current_slot = None
    current_field = None
    buffers: dict[tuple[str, str], list[str]] = {}

    for raw in text.splitlines():
        line = raw.rstrip()
        ms = _SLOT_HEADER.match(line.strip())
        if ms:
            current_slot = ms.group(1)
            slots.setdefault(current_slot, {})
            current_field = None
            continue
        mf = _FIELD_HEADER.match(line.strip())
        if mf and current_slot is not None:
            current_field = mf.group(1)
            buffers[(current_slot, current_field)] = []
            continue
        if current_slot is not None and current_field is not None:
            buffers[(current_slot, current_field)].append(raw)

    result: dict[str, dict] = {}
    for slot in slots:
        main = "\n".join(buffers.get((slot, "MAIN"), [])).strip()
        replies = []
        for i in range(1, common.REPLIES_PER_POST + 1):
            body = "\n".join(buffers.get((slot, f"REPLY{i}"), [])).strip()
            if body:
                replies.append(body)
        result[slot] = {"main": main, "replies": replies}
    return result


def run(client, ideas: list[dict]) -> dict[str, dict]:
    system_prompt = common.load_prompt("system.md")
    user_prompt = _build_user_prompt(ideas)
    msg = client.messages.create(
        model=common.DEFAULT_MODEL,
        max_tokens=4000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    parsed = _parse(common.collect_text(msg))
    print(f"writer: {len(parsed)} スロット分を生成")
    return parsed
