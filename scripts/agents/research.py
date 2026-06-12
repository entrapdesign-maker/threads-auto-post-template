"""リサーチ・エージェント (PDCA の P)。

prompts/research.md の分野・キーワード・競合をもとに、
Anthropic の web search ツールで最新情報を集め、4枠分の投稿テーマ案を出す。

出力: {"date": ..., "ideas": [{"slot","theme","angle","evidence"}, ... x4]}
      research/YYYY-MM-DD.json にも保存する。

Web検索が使えない/失敗する環境向けに、検索なしフォールバックを持つ。
"""

from __future__ import annotations

import json
import re

from . import common

# Anthropic サーバーサイドの web search ツール (動的フィルタリング対応版)。
WEB_SEARCH_TOOL = {"type": "web_search_20260209", "name": "web_search"}

_SYSTEM = """あなたはThreads運用のリサーチャーです。
指定された分野について、Web検索で「いま話題になっていること・最新の事実・競合がよく語る切り口」を調べ、
今日投稿すべきテーマ案を4つ出します。

ルール:
- 4案はテーマが互いに被らないようにする (時間帯ごとに役割を変える: 朝=気づき, 昼=ノウハウ, 夜=本音/体験, 深夜=問いかけ など)。
- 各案には、投稿の核になる主張(angle)と、根拠/出典メモ(evidence)を添える。
- 一次情報・最新の数値・具体的な出来事を重視し、一般論で埋めない。
- 最終出力は必ず次のJSONのみ。前置きや解説は書かない。

{"ideas": [{"slot": "07:00", "theme": "...", "angle": "...", "evidence": "..."}, ... 4件]}"""


def _extract_json(text: str) -> dict | None:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def _build_user_prompt(date_str: str) -> str:
    research_brief = common.load_prompt("research.md")
    learnings = common.load_learnings()
    parts = [
        f"日付: {date_str}",
        "",
        "## 投稿分野・条件",
        research_brief,
    ]
    if learnings:
        parts += [
            "",
            "## これまでの計測から分かった『伸びる投稿』の傾向 (必ず反映する)",
            learnings,
        ]
    parts += [
        "",
        f"投稿スロット {common.POST_SLOTS} それぞれに1案、合計{len(common.POST_SLOTS)}案のテーマを、上記JSON形式で出してください。",
    ]
    return "\n".join(parts)


def _run_with_search(client, user_prompt: str) -> str:
    """web search ツールを有効にして実行。pause_turn を継いで最終テキストを得る。"""
    messages = [{"role": "user", "content": user_prompt}]
    text = ""
    for _ in range(6):  # server tool ループの継続上限
        msg = client.messages.create(
            model=common.DEFAULT_MODEL,
            max_tokens=2000,
            system=_SYSTEM,
            tools=[WEB_SEARCH_TOOL],
            messages=messages,
        )
        text = common.collect_text(msg)
        if msg.stop_reason == "pause_turn":
            # サーバーツールが途中。assistant の content を積んで継続。
            messages.append({"role": "assistant", "content": msg.content})
            continue
        break
    return text


def _run_without_search(client, user_prompt: str) -> str:
    msg = client.messages.create(
        model=common.DEFAULT_MODEL,
        max_tokens=2000,
        system=_SYSTEM + "\n\n(このリクエストではWeb検索は使えません。知識ベースで最善のテーマ案を出してください。)",
        messages=[{"role": "user", "content": user_prompt}],
    )
    return common.collect_text(msg)


def _fallback_ideas() -> list[dict]:
    angles = [
        ("07:00", "業界で当たり前すぎて語られないこと", "朝の気づき投稿", ""),
        ("12:00", "続けて初めて分かった地味な工夫", "昼のノウハウ投稿", ""),
        ("19:00", "やめて良かったこと/失敗から学んだこと", "夜の本音・体験投稿", ""),
        ("21:00", "同業によく聞かれる質問への自分の答え", "深夜の問いかけ投稿", ""),
    ]
    return [
        {"slot": s, "theme": t, "angle": a, "evidence": e} for s, t, a, e in angles
    ]


def run(client, date_str: str) -> dict:
    user_prompt = _build_user_prompt(date_str)

    try:
        text = _run_with_search(client, user_prompt)
        data = _extract_json(text)
    except Exception as e:  # web search 非対応リージョン/権限など
        print(f"research: web search 失敗のためフォールバックします: {e}")
        data = None

    if data is None:
        try:
            data = _extract_json(_run_without_search(client, user_prompt))
        except Exception as e:
            print(f"research: 検索なし生成も失敗: {e}")
            data = None

    ideas = (data or {}).get("ideas") if isinstance(data, dict) else None
    if not ideas:
        print("research: 構造化出力を取得できず、定型テーマにフォールバック")
        ideas = _fallback_ideas()

    # スロット数に合わせて整える
    ideas = ideas[: len(common.POST_SLOTS)]
    for i, slot in enumerate(common.POST_SLOTS):
        if i < len(ideas):
            ideas[i]["slot"] = slot
        else:
            fb = _fallback_ideas()[i]
            ideas.append(fb)

    result = {"date": date_str, "ideas": ideas}

    common.RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
    out = common.RESEARCH_DIR / f"{date_str}.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"research: {len(ideas)} 案を生成 -> {out.name}")
    return result
