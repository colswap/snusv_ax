"""User Group 멤버 각자에게 DM을 보낸다.

회계 봇 고유 로직이 아니라 앞으로 추가될 자동화가 공유할 부품이므로
automations/ 밖에 둔다.
"""

from shared.slack import SlackError, call


def usergroup_member_ids(client, handle, *, sleep):
    """User Group 핸들을 멤버 ID 목록으로 바꾼다.

    빈 그룹은 오류로 처리한다. 아무에게도 보내지 않고 성공하면 봇이 죽은 것을
    아무도 알아채지 못한다.
    """
    groups = call(client.usergroups_list, sleep=sleep).get("usergroups", [])
    match = next((g for g in groups if g.get("handle") == handle), None)
    if match is None:
        available = ", ".join(sorted(g.get("handle", "?") for g in groups)) or "(없음)"
        raise SlackError(
            f"User Group '{handle}'을(를) 찾을 수 없습니다. "
            f"ACCOUNTANT_USERGROUP 값을 확인하세요. 사용 가능한 핸들: {available}"
        )

    members = call(
        client.usergroups_users_list, sleep=sleep, usergroup=match["id"]
    ).get("users", [])
    if not members:
        raise SlackError(
            f"User Group '{handle}'에 멤버가 없습니다. "
            "Slack에서 회계 담당자를 그룹에 추가하세요."
        )
    return list(members)


def broadcast(client, user_ids, text, *, sleep):
    """전원에게 같은 본문을 보낸다. 실패한 사람이 있어도 나머지는 계속 보낸다.

    반환값은 (user_id, 오류) 목록이다. 비어 있지 않으면 호출자가 실패로 끝내야 한다.
    """
    failures = []
    for user_id in user_ids:
        try:
            channel = call(client.conversations_open, sleep=sleep, users=user_id)
            call(
                client.chat_postMessage,
                sleep=sleep,
                channel=channel["channel"]["id"],
                text=text,
            )
        except SlackError as error:
            failures.append((user_id, error))
    return failures
