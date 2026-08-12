"""회계 채널의 미처리 정산 요청을 담당자에게 매일 요약해 DM한다.

수동 실행:
    python -m automations.finance_reminder.main --dry-run
"""

import argparse
import os
import sys
import time
from datetime import datetime

from slack_sdk import WebClient

from automations.finance_reminder.format import Item, render_dm
from automations.finance_reminder.rules import Rules, find_unresolved, history_window
from shared.config import KST, ConfigError, load_config
from shared.dm import broadcast, usergroup_member_ids
from shared.slack import SlackError, fetch_history, permalink


def main(argv=None):
    args = _parse_args(argv)

    try:
        config = load_config(os.environ, now=datetime.now(KST))
        client = WebClient(token=config.bot_token)
        return _run(client, config, dry_run=args.dry_run)
    except ConfigError as error:
        print(f"설정 오류: {error}", file=sys.stderr)
        return 1
    except SlackError as error:
        print(f"Slack 오류: {error}", file=sys.stderr)
        return 1


def _run(client, config, *, dry_run):
    rules = Rules(
        cohort_start=config.cohort_start,
        remind_after=config.remind_after,
        done_emoji=config.done_emoji,
        skip_emoji=config.skip_emoji,
    )
    now = datetime.now(KST)
    oldest, latest = history_window(now=now, rules=rules)

    messages = fetch_history(
        client, config.channel_id, oldest=oldest, latest=latest, sleep=time.sleep
    )
    pending = find_unresolved(messages, now=now, rules=rules)
    print(f"조회 {len(messages)}건 · 미처리 {len(pending)}건")

    if not pending:
        return 0

    items = [
        Item(
            user=p.user,
            elapsed=p.elapsed,
            permalink=permalink(client, config.channel_id, p.ts, sleep=time.sleep),
        )
        for p in pending
    ]
    text = render_dm(items, done_emoji=config.done_emoji, skip_emoji=config.skip_emoji)

    recipients = usergroup_member_ids(client, config.usergroup, sleep=time.sleep)

    if dry_run:
        print(f"\n[드라이런] 수신자 {len(recipients)}명: {', '.join(recipients)}")
        print(f"[드라이런] 아래 본문을 보내지 않고 종료합니다.\n\n{text}")
        return 0

    failures = broadcast(client, recipients, text, sleep=time.sleep)
    for user_id, error in failures:
        print(f"DM 실패 {user_id}: {error}", file=sys.stderr)

    print(f"발송 {len(recipients) - len(failures)}/{len(recipients)}명")
    return 1 if failures else 0


def _parse_args(argv):
    parser = argparse.ArgumentParser(description="회계 송금 리마인더")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="판정까지만 수행하고 DM은 보내지 않는다",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    sys.exit(main())
