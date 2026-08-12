import pytest
from slack_sdk.errors import SlackApiError

from shared.dm import broadcast, usergroup_member_ids
from shared.slack import SlackError


def noop_sleep(_seconds):
    pass


class FakeClient:
    def __init__(self, *, usergroups=None, members=None, failing_users=()):
        self._usergroups = usergroups if usergroups is not None else []
        self._members = members if members is not None else []
        self._failing_users = set(failing_users)
        self.posted = []

    def usergroups_list(self, **kwargs):
        return {"usergroups": self._usergroups}

    def usergroups_users_list(self, **kwargs):
        return {"users": self._members}

    def conversations_open(self, *, users, **kwargs):
        if users in self._failing_users:
            response = type(
                "R", (), {"status_code": 200, "headers": {}, "get": lambda s, k, d=None: "cannot_dm_bot"}
            )()
            raise SlackApiError("cannot_dm_bot", response)
        return {"channel": {"id": f"D_{users}"}}

    def chat_postMessage(self, *, channel, text, **kwargs):
        self.posted.append((channel, text))
        return {"ok": True}


ACCOUNTANTS = [{"id": "S1", "handle": "accountants"}]


def test_resolves_a_handle_to_its_member_ids():
    client = FakeClient(usergroups=ACCOUNTANTS, members=["U1", "U2"])

    assert usergroup_member_ids(client, "accountants", sleep=noop_sleep) == ["U1", "U2"]


def test_rejects_an_unknown_handle_and_lists_what_exists():
    client = FakeClient(usergroups=ACCOUNTANTS, members=["U1"])

    with pytest.raises(SlackError) as excinfo:
        usergroup_member_ids(client, "typo", sleep=noop_sleep)

    assert "typo" in str(excinfo.value)
    assert "accountants" in str(excinfo.value)


def test_rejects_an_empty_group_rather_than_silently_notifying_nobody():
    client = FakeClient(usergroups=ACCOUNTANTS, members=[])

    with pytest.raises(SlackError) as excinfo:
        usergroup_member_ids(client, "accountants", sleep=noop_sleep)

    assert "accountants" in str(excinfo.value)


def test_sends_the_same_text_to_every_member():
    client = FakeClient()

    failures = broadcast(client, ["U1", "U2"], "본문", sleep=noop_sleep)

    assert client.posted == [("D_U1", "본문"), ("D_U2", "본문")]
    assert failures == []


def test_keeps_delivering_after_one_member_fails():
    client = FakeClient(failing_users=["U1"])

    failures = broadcast(client, ["U1", "U2"], "본문", sleep=noop_sleep)

    assert client.posted == [("D_U2", "본문")]
    assert [user for user, _ in failures] == ["U1"]
