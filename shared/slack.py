"""Slack Web API 호출을 감싼다.

재시도할 가치가 있는 오류(속도 제한, 일시적 서버 오류)와 재시도해도 소용없는
설정 오류를 구분한다. 설정 오류를 세 번 반복하는 것은 로그만 어지럽힌다.
"""

from slack_sdk.errors import SlackApiError

PAGE_SIZE = 200

_RETRYABLE = {
    "ratelimited",
    "internal_error",
    "service_unavailable",
    "fatal_error",
    "request_timeout",
}

_HINTS = {
    "not_in_channel": "봇이 채널에 없습니다. 채널에서 `/invite @봇이름` 으로 초대하세요.",
    "channel_not_found": "채널을 찾을 수 없습니다. FINANCE_CHANNEL_ID 값을 확인하세요.",
    "invalid_auth": "봇 토큰이 유효하지 않습니다. SLACK_BOT_TOKEN을 재발급해 갱신하세요.",
    "account_inactive": "봇 토큰이 비활성화되었습니다. Slack 앱 설정을 확인하세요.",
    "missing_scope": "봇에 필요한 권한이 없습니다. RUNBOOK의 스코프 목록과 대조하세요.",
    "subteam_not_found": "User Group을 찾을 수 없습니다. ACCOUNTANT_USERGROUP 값을 확인하세요.",
}


class SlackError(Exception):
    pass


def call(operation, *, sleep, max_attempts=3, **kwargs):
    """operation(**kwargs)를 호출하고, 재시도할 가치가 있는 실패만 재시도한다."""
    for attempt in range(1, max_attempts + 1):
        try:
            return operation(**kwargs)
        except SlackApiError as error:
            code = _error_code(error)
            if not _is_retryable(error, code):
                raise SlackError(_message(code)) from error
            if attempt == max_attempts:
                raise SlackError(
                    f"Slack 호출이 {max_attempts}회 모두 실패했습니다 (마지막 오류: {code})."
                ) from error
            sleep(_retry_after(error))
    raise AssertionError("unreachable")


def fetch_history(client, channel_id, *, oldest, latest, sleep):
    """구간 내 메시지를 전부 가져온다. 경계값을 포함한다."""
    messages = []
    cursor = None
    while True:
        page = call(
            client.conversations_history,
            sleep=sleep,
            channel=channel_id,
            oldest=str(oldest),
            latest=str(latest),
            inclusive=True,
            limit=PAGE_SIZE,
            **({"cursor": cursor} if cursor else {}),
        )
        messages.extend(page.get("messages", []))
        cursor = (page.get("response_metadata") or {}).get("next_cursor")
        if not cursor:
            return messages


def permalink(client, channel_id, ts, *, sleep):
    response = call(
        client.chat_getPermalink, sleep=sleep, channel=channel_id, message_ts=ts
    )
    return response["permalink"]


def _error_code(error):
    response = error.response
    return (response.get("error") if response is not None else None) or "unknown"


def _is_retryable(error, code):
    status = getattr(error.response, "status_code", None)
    return code in _RETRYABLE or status == 429 or (status or 0) >= 500


def _retry_after(error):
    header = (getattr(error.response, "headers", None) or {}).get("Retry-After")
    try:
        return max(1, int(header))
    except (TypeError, ValueError):
        return 1


def _message(code):
    return _HINTS.get(code, f"Slack API 오류: {code}")
