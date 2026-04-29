"""
任意のテキストをThreadsに即時投稿する (workflow_dispatch経由)。

環境変数:
  THREADS_USER_ID
  THREADS_ACCESS_TOKEN
  POST_TEXT       : メイン投稿本文 (必須)
  POST_REPLY_TEXT : ツリー返信本文 (任意, 改行は \\n で区切る)
"""

from __future__ import annotations

import os
import sys

from post_threads import ThreadsClient


def main() -> int:
    user_id = os.environ.get("THREADS_USER_ID")
    token = os.environ.get("THREADS_ACCESS_TOKEN")
    text = os.environ.get("POST_TEXT", "").replace("\\n", "\n").strip()
    reply_text = os.environ.get("POST_REPLY_TEXT", "").replace("\\n", "\n").strip()

    if not user_id or not token:
        print("ERROR: THREADS_USER_ID / THREADS_ACCESS_TOKEN が未設定", file=sys.stderr)
        return 1
    if not text:
        print("ERROR: POST_TEXT が空です", file=sys.stderr)
        return 1

    client = ThreadsClient(user_id, token)
    main_id = client.post_text(text)
    print(f"posted: {main_id}")

    parent = main_id
    if reply_text:
        for chunk in [c.strip() for c in reply_text.split("---") if c.strip()]:
            rid = client.post_text(chunk, reply_to_id=parent)
            print(f"reply: {rid}")
            parent = rid

    return 0


if __name__ == "__main__":
    sys.exit(main())
