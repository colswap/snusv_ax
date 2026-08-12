import pytest
from slack_sdk.errors import SlackApiError

from shared.slack import SlackError, call, fetch_history, permalink


class FakeResponse:
    def __init__(self, *, status_code=200, headers=None, data=None):
        self.status_code = status_code
        self.headers = headers or {}
        self.data = data or {}

    def get(self, key, default=None):
        return self.data.get(key, default)

    def __getitem__(self, key):
        return self.data[key]


def api_error(error_code, *, status_code=200, retry_after=None):
    headers = {"Retry-After": str(retry_after)} if retry_after is not None else {}
    response = FakeResponse(
        status_code=status_code, headers=headers, data={"error": error_code}
    )
    return SlackApiError(f"error: {error_code}", response)


class Recorder:
    """sleep 호출을 기록하는 대역."""

    def __init__(self):
        self.slept = []

    def __call__(self, seconds):
        self.slept.append(seconds)


def responses(*results):
    """호출할 때마다 results를 차례로 반환하거나 raise 하는 대역."""
    queue = list(results)

    def operation(**kwargs):
        operation.calls.append(kwargs)
        outcome = queue.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    operation.calls = []
    return operation


def test_returns_result_without_sleeping_when_the_call_succeeds():
    sleep = Recorder()
    operation = responses({"ok": True})

    assert call(operation, sleep=sleep) == {"ok": True}
    assert sleep.slept == []


def test_waits_the_retry_after_interval_then_retries_on_rate_limit():
    sleep = Recorder()
    operation = responses(
        api_error("ratelimited", status_code=429, retry_after=7), {"ok": True}
    )

    assert call(operation, sleep=sleep) == {"ok": True}
    assert sleep.slept == [7]
    assert len(operation.calls) == 2


def test_falls_back_to_one_second_when_rate_limited_without_a_header():
    sleep = Recorder()
    operation = responses(api_error("ratelimited", status_code=429), {"ok": True})

    call(operation, sleep=sleep)

    assert sleep.slept == [1]


def test_gives_up_after_the_attempt_limit():
    sleep = Recorder()
    operation = responses(*[api_error("ratelimited", status_code=429, retry_after=1)] * 3)

    with pytest.raises(SlackError):
        call(operation, sleep=sleep, max_attempts=3)

    assert len(operation.calls) == 3


def test_explains_how_to_fix_a_missing_channel_membership():
    operation = responses(api_error("not_in_channel"))

    with pytest.raises(SlackError) as excinfo:
        call(operation, sleep=Recorder())

    assert "초대" in str(excinfo.value)


def test_does_not_retry_a_configuration_error():
    operation = responses(api_error("channel_not_found"))

    with pytest.raises(SlackError):
        call(operation, sleep=Recorder(), max_attempts=3)

    assert len(operation.calls) == 1


def test_retries_a_transient_server_error():
    sleep = Recorder()
    operation = responses(api_error("internal_error"), {"ok": True})

    assert call(operation, sleep=sleep) == {"ok": True}
    assert len(operation.calls) == 2


class FakeClient:
    def __init__(self, pages=None, permalink_url="https://slack.example/p"):
        self._pages = pages or []
        self._permalink_url = permalink_url
        self.history_calls = []

    def conversations_history(self, **kwargs):
        self.history_calls.append(kwargs)
        return self._pages[len(self.history_calls) - 1]

    def chat_getPermalink(self, **kwargs):
        return {"permalink": self._permalink_url}


def test_fetches_a_single_page_of_history():
    client = FakeClient(pages=[{"messages": [{"ts": "1"}, {"ts": "2"}]}])

    messages = fetch_history(
        client, "C1", oldest=100.0, latest=200.0, sleep=Recorder()
    )

    assert [m["ts"] for m in messages] == ["1", "2"]


def test_passes_the_time_window_to_slack():
    client = FakeClient(pages=[{"messages": []}])

    fetch_history(client, "C1", oldest=100.0, latest=200.0, sleep=Recorder())

    sent = client.history_calls[0]
    assert sent["channel"] == "C1"
    assert float(sent["oldest"]) == 100.0
    assert float(sent["latest"]) == 200.0


def test_follows_the_cursor_across_pages():
    client = FakeClient(
        pages=[
            {
                "messages": [{"ts": "1"}],
                "has_more": True,
                "response_metadata": {"next_cursor": "CUR"},
            },
            {"messages": [{"ts": "2"}]},
        ]
    )

    messages = fetch_history(
        client, "C1", oldest=100.0, latest=200.0, sleep=Recorder()
    )

    assert [m["ts"] for m in messages] == ["1", "2"]
    assert client.history_calls[1]["cursor"] == "CUR"


def test_reads_the_permalink_of_a_message():
    client = FakeClient(permalink_url="https://slack.example/archives/C1/p1")

    url = permalink(client, "C1", "1739.0001", sleep=Recorder())

    assert url == "https://slack.example/archives/C1/p1"
