"""미처리 정산 요청 판정.

이 모듈은 Slack을 모른다. 입력은 메시지 딕셔너리 목록이고 출력은 판정 결과다.
네트워크 호출도 SDK import도 없으므로 워크스페이스 없이 전부 테스트할 수 있다.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass(frozen=True)
class Rules:
    cohort_start: datetime
    remind_after: timedelta
    done_emoji: str
    skip_emoji: str


@dataclass(frozen=True)
class Pending:
    ts: str
    user: str
    elapsed: timedelta


def history_window(*, now, rules):
    """조회할 구간을 (oldest, latest) epoch 초로 반환한다. 양 끝을 포함한다."""
    return rules.cohort_start.timestamp(), (now - rules.remind_after).timestamp()


def find_unresolved(messages, *, now, rules):
    """미처리 정산 요청을 오래된 순으로 반환한다."""
    found = [
        Pending(ts=m["ts"], user=m.get("user", ""), elapsed=now - _posted_at(m))
        for m in messages
        if _is_pending(m, now=now, rules=rules)
    ]
    return sorted(found, key=lambda p: p.elapsed, reverse=True)


def _is_pending(message, *, now, rules):
    if not _is_human_top_level_post(message):
        return False

    posted_at = _posted_at(message)
    if posted_at < rules.cohort_start:
        return False
    if now - posted_at < rules.remind_after:
        return False

    return not _has_reaction(message, rules.done_emoji) and not _has_reaction(
        message, rules.skip_emoji
    )


def _is_human_top_level_post(message):
    """스레드 답글·시스템 메시지·봇 메시지를 걸러낸다."""
    thread_ts = message.get("thread_ts")
    if thread_ts is not None and thread_ts != message["ts"]:
        return False
    if message.get("subtype") is not None:
        return False
    return not message.get("bot_id") and not message.get("app_id")


def _has_reaction(message, emoji):
    """누가 눌렀는지는 따지지 않는다.

    회계 담당자가 본인이 올린 지출 기록을 본인이 체크하는 경우가
    실데이터에서 가장 많았다.
    """
    return any(r.get("name") == emoji for r in message.get("reactions", []))


def _posted_at(message):
    return datetime.fromtimestamp(float(message["ts"]), tz=timezone.utc)
