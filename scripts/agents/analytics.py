"""計測エージェント (PDCA の C と A)。

C: Threads Insights API で、直近に投稿したメイン投稿のインサイトを取得・集計する。
A: 数値の良い投稿の傾向をClaudeに言語化させ、prompts/learnings.md を更新する。
   → 次回の research / writer がこの learnings を読み込み、生成に反映する。

必要な権限: threads_manage_insights (アクセストークンに付与しておくこと)。
メトリクス: views, likes, replies, reposts, quotes, shares
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta

import requests

from . import common

API_BASE = "https://graph.threads.net/v1.0"
METRICS = ["views", "likes", "replies", "reposts", "quotes", "shares"]
# エンゲージメント率の重み付け (views を除いた反応の合計をスコアにする)
ENGAGEMENT_METRICS = ["likes", "replies", "reposts", "quotes", "shares"]


def fetch_insights(media_id: str, token: str) -> dict:
    """1投稿(media_id)のインサイトを {metric: value} で返す。"""
    url = f"{API_BASE}/{media_id}/insights"
    params = {"metric": ",".join(METRICS), "access_token": token}
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    body = r.json()
    values: dict[str, int] = {}
    for entry in body.get("data", []):
        name = entry.get("name")
        vals = entry.get("values", [])
        total = sum(int(v.get("value", 0)) for v in vals) if vals else 0
        values[name] = total
    return values


def _recent_posted(days: int) -> list[dict]:
    """直近 days 日の drafts から、投稿済み(posted)のメイン投稿を集める。"""
    today = datetime.now(common.JST).date()
    records: list[dict] = []
    for offset in range(days):
        d = (today - timedelta(days=offset)).isoformat()
        path = common.DRAFTS_DIR / f"{d}.json"
        if not path.exists():
            continue
        data = common.normalize_draft(common.load_draft(path), d)
        for post in data.get("posts", []):
            if post.get("posted") and post.get("post_ids"):
                records.append(
                    {
                        "date": data.get("date", d),
                        "slot": post.get("slot", ""),
                        "theme": post.get("theme", ""),
                        "main": post.get("main", ""),
                        "media_id": post["post_ids"][0],  # メイン投稿のID
                    }
                )
    return records


def collect(days: int = 14) -> list[dict]:
    token = os.environ.get("THREADS_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("THREADS_ACCESS_TOKEN が未設定です")

    records = _recent_posted(days)
    measured: list[dict] = []
    for rec in records:
        try:
            metrics = fetch_insights(rec["media_id"], token)
        except Exception as e:
            print(f"analytics: insights取得失敗 {rec['media_id']}: {e}")
            continue
        score = sum(metrics.get(m, 0) for m in ENGAGEMENT_METRICS)
        measured.append({**rec, "metrics": metrics, "engagement": score})

    measured.sort(key=lambda x: x["engagement"], reverse=True)

    date_str = datetime.now(common.JST).date().isoformat()
    common.INSIGHTS_DIR.mkdir(parents=True, exist_ok=True)
    out = common.INSIGHTS_DIR / f"{date_str}.json"
    out.write_text(
        json.dumps({"date": date_str, "posts": measured}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"analytics: {len(measured)} 投稿のインサイトを取得 -> {out.name}")
    return measured


_LEARN_SYSTEM = """あなたはThreadsグロースの分析担当です。
投稿ごとのインサイト(views/likes/replies/reposts/quotes/shares)を見て、
『数値が伸びた投稿に共通する特徴』を、次の投稿生成にそのまま使える指示として日本語でまとめます。

観点: 投稿時間帯, フックの型, テーマ, 文の長さ, 語り口/トーン, ツリーの作り方。
出力はMarkdownの箇条書きのみ。前置き・講評・指標の再掲は不要。
伸びた投稿の真似すべき点と、伸びなかった投稿の避けるべき点を、断定形で書く。"""


def update_learnings(client, measured: list[dict]) -> str:
    if not measured:
        print("analytics: 計測データが無いため learnings は更新しません")
        return ""

    top = measured[: min(10, len(measured))]
    bottom = measured[-min(5, len(measured)) :]
    digest = {
        "上位(伸びた)": [
            {"slot": p["slot"], "theme": p["theme"], "main": p["main"], "metrics": p["metrics"]}
            for p in top
        ],
        "下位(伸びなかった)": [
            {"slot": p["slot"], "theme": p["theme"], "main": p["main"], "metrics": p["metrics"]}
            for p in bottom
        ],
    }
    user_prompt = (
        "次のインサイトから、次回投稿に反映すべき『伸びる投稿の傾向』をまとめてください。\n\n"
        + json.dumps(digest, ensure_ascii=False, indent=2)
    )
    msg = client.messages.create(
        model=common.DEFAULT_MODEL,
        max_tokens=1200,
        system=_LEARN_SYSTEM,
        messages=[{"role": "user", "content": user_prompt}],
    )
    body = common.collect_text(msg).strip()

    date_str = datetime.now(common.JST).date().isoformat()
    header = f"# 計測フィードバック (自動更新: {date_str})\n\n"
    note = (
        "<!-- このファイルは scripts/measure.py が自動生成します。"
        "research / writer エージェントが生成時に読み込み、投稿へ反映します。 -->\n\n"
    )
    (common.PROMPTS_DIR / "learnings.md").write_text(header + note + body + "\n", encoding="utf-8")
    print("analytics: prompts/learnings.md を更新")
    return body
