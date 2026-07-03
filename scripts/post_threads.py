"""
予約時刻に到達したdraftをThreadsに投稿する (自動投稿エージェント)。
- 毎時0分にcronで起動 → 該当日のJSONを開き、各枠(slot)で scheduled_at <= now かつ posted=False なら投稿。
- 1日4枠 (07:00/12:00/19:00/21:00) × 各5ツリー(メイン+返信4) に対応。
- メイン投稿 + replies をツリー形式で投稿。
- 投稿成功後、その枠に posted=True と post_ids を書き戻す。
- 旧スキーマ(トップレベル main/replies)のJSONも後方互換で読める。

環境変数:
  THREADS_USER_ID     : Threads APIのユーザーID
  THREADS_ACCESS_TOKEN: Long-livedアクセストークン
  FORCE_DATE          : (任意) 強制的に処理する日付 YYYY-MM-DD
  TZ                  : Asia/Tokyo を想定
"""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

from agents import common as agents_common

JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent
DRAFTS_DIR = ROOT / "drafts"
API_BASE = "https://graph.threads.net/v1.0"


class ThreadsClient:
    def __init__(self, user_id: str, access_token: str) -> None:
        self.user_id = user_id
        self.access_token = access_token

    def create_container(self, text: str, reply_to_id: str | None = None) -> str:
        url = f"{API_BASE}/{self.user_id}/threads"
        payload = {
            "media_type": "TEXT",
            "text": text,
            "access_token": self.access_token,
        }
        if reply_to_id:
            payload["reply_to_id"] = reply_to_id
        r = requests.post(url, data=payload, timeout=30)
        r.raise_for_status()
        return r.json()["id"]

    def publish(self, creation_id: str) -> str:
        """
        コンテナ生成 → publish。
        Meta公式: コンテナはサーバー側処理が必要なため、生成から少なくとも30秒待機を推奨。
        ここでは初回30秒、失敗時は15秒間隔で最大5回リトライ。
        """
        url = f"{API_BASE}/{self.user_id}/threads_publish"
        time.sleep(30)
        last_error: Exception | None = None
        for attempt in range(5):
            try:
                r = requests.post(
                    url,
                    data={
                        "creation_id": creation_id,
                        "access_token": self.access_token,
                    },
                    timeout=30,
                )
                r.raise_for_status()
                return r.json()["id"]
            except requests.HTTPError as e:
                last_error = e
                body = ""
                try:
                    body = e.response.text[:300] if e.response is not None else ""
                except Exception:
                    pass
                print(f"publish retry {attempt + 1}/5: {e} {body}", file=sys.stderr)
                time.sleep(15)
        raise RuntimeError(f"publish failed after retries: {last_error}")

    def post_text(self, text: str, reply_to_id: str | None = None) -> str:
        container_id = self.create_container(text, reply_to_id)
        return self.publish(container_id)


def load_draft(path: Path) -> dict:
    return agents_common.load_draft(path)


def save_draft(path: Path, data: dict) -> None:
    agents_common.save_draft(path, data)


def parse_iso_jst(s: str) -> datetime:
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=JST)
    return dt


def find_target_drafts(now: datetime, force_date: str) -> list[Path]:
    if force_date:
        path = DRAFTS_DIR / f"{force_date}.json"
        return [path] if path.exists() else []
    # 当日のJSONがあれば対象、なければ過去2日分まで救済する
    candidates = []
    today = now.date()
    for offset in range(0, 3):
        d = today - timedelta(days=offset)
        p = DRAFTS_DIR / f"{d.isoformat()}.json"
        if p.exists():
            candidates.append(p)
    return candidates


def post_tree(client: ThreadsClient, post: dict) -> tuple[list[str], bool]:
    """1枠(メイン+返信)をツリー投稿する。

    メイン投稿は必須。失敗したら例外を送出する(その枠は未投稿のまま)。
    返信(ツリー化)は best-effort: 1件でも失敗したらそこで打ち切り、
    それまでに成功した post_ids と replies_ok=False を返す。
    こうすることで、メインは上がったのに返信の権限エラー等で例外になり、
    枠が「未投稿」のまま毎時メインを重複投稿してしまう事故を防ぐ。
    """
    post_ids: list[str] = []
    main_id = client.post_text(post["main"])  # 失敗時はここで例外 → 枠は未投稿
    post_ids.append(main_id)
    parent = main_id
    replies_ok = True
    for reply in post.get("replies", []):
        try:
            rid = client.post_text(reply, reply_to_id=parent)
        except Exception as e:  # 返信は best-effort。失敗しても main は済んでいる
            print(f"  reply failed (main は投稿済み, 返信は打ち切り): {e}", file=sys.stderr)
            replies_ok = False
            break
        post_ids.append(rid)
        parent = rid
    return post_ids, replies_ok


def main() -> int:
    user_id = os.environ.get("THREADS_USER_ID")
    token = os.environ.get("THREADS_ACCESS_TOKEN")
    if not user_id or not token:
        print("ERROR: THREADS_USER_ID / THREADS_ACCESS_TOKEN が未設定です", file=sys.stderr)
        return 1

    force_date = os.environ.get("FORCE_DATE", "").strip()
    now = datetime.now(JST)
    targets = find_target_drafts(now, force_date)
    if not targets:
        print(f"no draft for {now.date().isoformat()}")
        return 0

    client = ThreadsClient(user_id, token)
    for path in targets:
        date_str = path.stem
        data = agents_common.normalize_draft(load_draft(path), date_str)
        changed = False

        for post in data.get("posts", []):
            if post.get("posted"):
                continue
            if not post.get("main"):
                continue  # 生成に失敗した空き枠はスキップ
            scheduled = parse_iso_jst(post["scheduled_at"])
            if not force_date and now < scheduled:
                print(f"not yet: {path.name} [{post.get('slot')}] scheduled at {scheduled.isoformat()}")
                continue

            print(f"posting: {path.name} [{post.get('slot')}]")
            post_ids, replies_ok = post_tree(client, post)
            # メインが上がった時点で posted=True にする。返信が失敗しても
            # 枠を「投稿済み」にして毎時の重複メイン投稿を防ぐ。
            post["posted"] = True
            post["post_ids"] = post_ids
            post["posted_at"] = datetime.now(JST).isoformat(timespec="seconds")
            post["replies_ok"] = replies_ok  # 返信が全て上がったか(要再挑戦の判定用)
            changed = True
            status = "posted" if replies_ok else "posted(main only, replies failed)"
            print(f"{status}: {path.name} [{post.get('slot')}] -> {post_ids}")

        if changed:
            save_draft(path, data)

    return 0


if __name__ == "__main__":
    sys.exit(main())
