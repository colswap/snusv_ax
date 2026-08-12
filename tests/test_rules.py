from datetime import datetime, timedelta, timezone

import pytest

from automations.finance_reminder.rules import Rules, find_unresolved, history_window

KST = timezone(timedelta(hours=9))
NOW = datetime(2026, 8, 13, 10, 0, tzinfo=KST)
COHORT_START = datetime(2026, 8, 1, 0, 0, tzinfo=KST)


def rules(**overrides):
    base = dict(
        cohort_start=COHORT_START,
        remind_after=timedelta(hours=48),
        done_emoji="white_check_mark",
        skip_emoji="x",
    )
    base.update(overrides)
    return Rules(**base)


def message(*, hours_ago=72, reactions=None, user="U_AUTHOR", **overrides):
    """기본값은 '미처리로 판정되어야 하는' 메시지."""
    ts = (NOW - timedelta(hours=hours_ago)).timestamp()
    msg = {"type": "message", "ts": f"{ts:.6f}", "user": user, "text": "정산 요청"}
    if reactions is not None:
        msg["reactions"] = [
            {"name": name, "count": 1, "users": ["U_ACCOUNTANT"]} for name in reactions
        ]
    msg.update(overrides)
    return msg


def test_returns_message_that_is_old_enough_and_unchecked():
    found = find_unresolved([message()], now=NOW, rules=rules())

    assert len(found) == 1
    assert found[0].user == "U_AUTHOR"


def test_excludes_message_with_done_emoji():
    found = find_unresolved(
        [message(reactions=["white_check_mark"])], now=NOW, rules=rules()
    )

    assert found == []


def test_excludes_message_with_skip_emoji():
    found = find_unresolved([message(reactions=["x"])], now=NOW, rules=rules())

    assert found == []


def test_excludes_message_carrying_both_done_and_skip_emoji():
    found = find_unresolved(
        [message(reactions=["white_check_mark", "x"])], now=NOW, rules=rules()
    )

    assert found == []


def test_includes_message_reacted_with_unrelated_emoji_only():
    found = find_unresolved(
        [message(reactions=["eyes", "sob"])], now=NOW, rules=rules()
    )

    assert len(found) == 1


def test_excludes_message_younger_than_remind_after():
    found = find_unresolved([message(hours_ago=47.99)], now=NOW, rules=rules())

    assert found == []


def test_includes_message_exactly_at_remind_after_boundary():
    found = find_unresolved([message(hours_ago=48)], now=NOW, rules=rules())

    assert len(found) == 1


def test_excludes_message_posted_before_cohort_start():
    before = COHORT_START - timedelta(hours=1)
    hours_ago = (NOW - before).total_seconds() / 3600

    found = find_unresolved([message(hours_ago=hours_ago)], now=NOW, rules=rules())

    assert found == []


def test_includes_message_posted_exactly_at_cohort_start():
    hours_ago = (NOW - COHORT_START).total_seconds() / 3600

    found = find_unresolved([message(hours_ago=hours_ago)], now=NOW, rules=rules())

    assert len(found) == 1


def test_excludes_thread_reply():
    reply = message(thread_ts="1000000.000000", ts="2000000.000000")

    found = find_unresolved([reply], now=NOW, rules=rules())

    assert found == []


def test_includes_thread_parent():
    parent = message()
    parent["thread_ts"] = parent["ts"]

    found = find_unresolved([parent], now=NOW, rules=rules())

    assert len(found) == 1


def test_excludes_message_with_subtype():
    found = find_unresolved(
        [message(subtype="channel_join")], now=NOW, rules=rules()
    )

    assert found == []


def test_excludes_bot_message():
    found = find_unresolved([message(bot_id="B123")], now=NOW, rules=rules())

    assert found == []


def test_excludes_app_message():
    found = find_unresolved([message(app_id="A123")], now=NOW, rules=rules())

    assert found == []


def test_includes_message_with_only_a_file_and_no_text():
    """영수증 이미지만 올리는 경우가 실데이터에 존재한다."""
    found = find_unresolved(
        [message(text="", files=[{"id": "F1", "name": "receipt.png"}])],
        now=NOW,
        rules=rules(),
    )

    assert len(found) == 1


def test_orders_oldest_first():
    found = find_unresolved(
        [
            message(hours_ago=50, user="U_NEWER"),
            message(hours_ago=100, user="U_OLDER"),
            message(hours_ago=72, user="U_MIDDLE"),
        ],
        now=NOW,
        rules=rules(),
    )

    assert [item.user for item in found] == ["U_OLDER", "U_MIDDLE", "U_NEWER"]


def test_reports_elapsed_time_since_posting():
    found = find_unresolved([message(hours_ago=72)], now=NOW, rules=rules())

    assert found[0].elapsed == timedelta(hours=72)


def test_respects_custom_emoji_names():
    custom = rules(done_emoji="heavy_check_mark", skip_emoji="no_entry")

    assert find_unresolved([message(reactions=["heavy_check_mark"])], now=NOW, rules=custom) == []
    assert find_unresolved([message(reactions=["no_entry"])], now=NOW, rules=custom) == []
    assert len(find_unresolved([message(reactions=["white_check_mark"])], now=NOW, rules=custom)) == 1


def test_ignores_who_reacted():
    """회계 담당자가 자기 글을 자기가 체크하는 경우가 실데이터에서 가장 많다."""
    own = message(user="U_ACCOUNTANT", reactions=["white_check_mark"])
    own["reactions"][0]["users"] = ["U_ACCOUNTANT"]

    found = find_unresolved([own], now=NOW, rules=rules())

    assert found == []


def test_returns_empty_for_empty_input():
    assert find_unresolved([], now=NOW, rules=rules()) == []


def test_history_window_starts_at_cohort_start():
    oldest, _ = history_window(now=NOW, rules=rules())

    assert oldest == COHORT_START.timestamp()


def test_history_window_ends_at_the_remind_cutoff():
    _, latest = history_window(now=NOW, rules=rules())

    assert latest == (NOW - timedelta(hours=48)).timestamp()


def test_history_window_respects_custom_remind_after():
    _, latest = history_window(now=NOW, rules=rules(remind_after=timedelta(hours=12)))

    assert latest == (NOW - timedelta(hours=12)).timestamp()
