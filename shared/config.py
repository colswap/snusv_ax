from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Config:
    bot_token: str
    channel_id: str
    usergroup: str
    cohort_start: datetime
    remind_after: timedelta
    done_emoji: str
    skip_emoji: str


def load_config(env, *, now):
    """환경변수를 검증해 Config로 만든다. 문제가 있으면 즉시 ConfigError.

    조용한 실패를 막기 위해 시작 시점에 전부 검증한다. 설정이 틀린 채로
    실행되어 "미처리 0건"으로 성공하는 것이 이 봇의 가장 위험한 상태다.
    """
    return Config(
        bot_token=_required(env, "SLACK_BOT_TOKEN"),
        channel_id=_required(env, "FINANCE_CHANNEL_ID"),
        usergroup=_required(env, "ACCOUNTANT_USERGROUP").lstrip("@"),
        cohort_start=_cohort_start(env, now=now),
        remind_after=_remind_after(env),
        done_emoji=_emoji(env, "DONE_EMOJI", "white_check_mark"),
        skip_emoji=_emoji(env, "SKIP_EMOJI", "x"),
    )


def _required(env, name):
    value = (env.get(name) or "").strip()
    if not value:
        raise ConfigError(
            f"{name}이(가) 비어 있습니다. "
            f"GitHub 레포 Settings > Secrets and variables > Actions 에서 {name}을(를) 설정하세요."
        )
    return value


def _cohort_start(env, *, now):
    raw = _required(env, "COHORT_START_DATE")
    try:
        day = datetime.strptime(raw, "%Y-%m-%d")
    except ValueError:
        raise ConfigError(
            f"COHORT_START_DATE가 '{raw}'인데 YYYY-MM-DD 형식이어야 합니다. 예: 2026-08-01"
        ) from None

    start = day.replace(tzinfo=KST)
    if start > now:
        raise ConfigError(
            f"COHORT_START_DATE가 '{raw}'로 미래입니다. "
            "기수 시작일은 오늘이거나 과거여야 합니다."
        )
    return start


def _remind_after(env):
    raw = (env.get("REMIND_AFTER_HOURS") or "48").strip()
    try:
        hours = int(raw)
    except ValueError:
        raise ConfigError(
            f"REMIND_AFTER_HOURS가 '{raw}'인데 정수여야 합니다. 기본값은 48입니다."
        ) from None

    if hours <= 0:
        raise ConfigError(
            f"REMIND_AFTER_HOURS가 {hours}인데 1 이상이어야 합니다. 기본값은 48입니다."
        )
    return timedelta(hours=hours)


def _emoji(env, name, default):
    return ((env.get(name) or "").strip() or default).strip(":")
