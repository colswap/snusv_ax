from datetime import datetime, timedelta, timezone

import pytest

from shared.config import KST, ConfigError, load_config

NOW = datetime(2026, 8, 13, 10, 0, tzinfo=KST)

COMPLETE_ENV = {
    "SLACK_BOT_TOKEN": "xoxb-test",
    "FINANCE_CHANNEL_ID": "C123",
    "ACCOUNTANT_USERGROUP": "accountants",
    "COHORT_START_DATE": "2026-08-01",
}


def load(**overrides):
    env = dict(COMPLETE_ENV)
    for key, value in overrides.items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = value
    return load_config(env, now=NOW)


def test_loads_a_complete_environment():
    config = load()

    assert config.bot_token == "xoxb-test"
    assert config.channel_id == "C123"
    assert config.usergroup == "accountants"


def test_reads_cohort_start_as_midnight_kst():
    config = load()

    assert config.cohort_start == datetime(2026, 8, 1, 0, 0, tzinfo=KST)


@pytest.mark.parametrize("missing", sorted(COMPLETE_ENV))
def test_rejects_missing_required_variable(missing):
    with pytest.raises(ConfigError) as excinfo:
        load(**{missing: None})

    assert missing in str(excinfo.value)


@pytest.mark.parametrize("blank", ["", "   "])
def test_rejects_blank_required_variable(blank):
    with pytest.raises(ConfigError) as excinfo:
        load(FINANCE_CHANNEL_ID=blank)

    assert "FINANCE_CHANNEL_ID" in str(excinfo.value)


def test_rejects_unparseable_cohort_start():
    with pytest.raises(ConfigError) as excinfo:
        load(COHORT_START_DATE="2026/08/01")

    assert "COHORT_START_DATE" in str(excinfo.value)
    assert "YYYY-MM-DD" in str(excinfo.value)


def test_rejects_cohort_start_in_the_future():
    with pytest.raises(ConfigError) as excinfo:
        load(COHORT_START_DATE="2026-12-25")

    assert "COHORT_START_DATE" in str(excinfo.value)


def test_defaults_remind_after_to_48_hours():
    assert load().remind_after == timedelta(hours=48)


def test_reads_custom_remind_after():
    assert load(REMIND_AFTER_HOURS="72").remind_after == timedelta(hours=72)


@pytest.mark.parametrize("bad", ["abc", "0", "-5"])
def test_rejects_non_positive_or_unparseable_remind_after(bad):
    with pytest.raises(ConfigError) as excinfo:
        load(REMIND_AFTER_HOURS=bad)

    assert "REMIND_AFTER_HOURS" in str(excinfo.value)


def test_defaults_emojis_to_the_conventions_already_in_use():
    config = load()

    assert config.done_emoji == "white_check_mark"
    assert config.skip_emoji == "x"


def test_reads_custom_emojis():
    config = load(DONE_EMOJI="heavy_check_mark", SKIP_EMOJI="no_entry")

    assert config.done_emoji == "heavy_check_mark"
    assert config.skip_emoji == "no_entry"


def test_strips_surrounding_colons_from_emoji_names():
    """설정에 :x: 형태로 넣는 실수가 잦다."""
    config = load(DONE_EMOJI=":white_check_mark:", SKIP_EMOJI=":x:")

    assert config.done_emoji == "white_check_mark"
    assert config.skip_emoji == "x"


def test_strips_leading_at_from_usergroup_handle():
    assert load(ACCOUNTANT_USERGROUP="@accountants").usergroup == "accountants"
