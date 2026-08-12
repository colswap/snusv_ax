from datetime import timedelta

from automations.finance_reminder.format import Item, render_dm


def item(*, user="U_AUTHOR", days=3, permalink="https://slack.example/p1"):
    return Item(user=user, elapsed=timedelta(days=days), permalink=permalink)


def render(items, **overrides):
    kwargs = dict(done_emoji="white_check_mark", skip_emoji="x")
    kwargs.update(overrides)
    return render_dm(items, **kwargs)


def test_returns_none_when_nothing_is_pending():
    assert render([]) is None


def test_states_how_many_are_pending():
    text = render([item(), item(), item()])

    assert "3건" in text


def test_mentions_the_author_so_slack_renders_the_name():
    text = render([item(user="U_ABC")])

    assert "<@U_ABC>" in text


def test_shows_elapsed_days_per_item():
    text = render([item(days=5)])

    assert "5일" in text


def test_rounds_elapsed_down_to_whole_days():
    text = render([Item(user="U", elapsed=timedelta(hours=50), permalink="p")])

    assert "2일" in text


def test_links_to_the_original_message():
    text = render([item(permalink="https://slack.example/archives/C1/p123")])

    assert "https://slack.example/archives/C1/p123" in text


def test_tells_the_reader_which_emoji_completes_an_item():
    text = render([item()], done_emoji="heavy_check_mark", skip_emoji="no_entry")

    assert ":heavy_check_mark:" in text
    assert ":no_entry:" in text


def test_lists_every_item_when_under_the_cap():
    text = render([item(user=f"U{i}") for i in range(20)])

    assert all(f"<@U{i}>" in text for i in range(20))
    assert "외 " not in text


def test_truncates_beyond_the_cap_and_says_how_many_were_hidden():
    text = render([item(user=f"U{i}") for i in range(23)])

    assert "<@U19>" in text
    assert "<@U20>" not in text
    assert "외 3건" in text


def test_keeps_the_given_order():
    text = render([item(user="U_FIRST"), item(user="U_SECOND")])

    assert text.index("<@U_FIRST>") < text.index("<@U_SECOND>")
