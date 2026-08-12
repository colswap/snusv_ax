from dataclasses import dataclass
from datetime import timedelta

MAX_ITEMS = 20


@dataclass(frozen=True)
class Item:
    user: str
    elapsed: timedelta
    permalink: str


def render_dm(items, *, done_emoji, skip_emoji):
    """미처리 목록을 DM 본문으로 만든다. 보낼 것이 없으면 None.

    본문 미리보기는 넣지 않는다. 회계 채널 글에는 계좌번호와 금액이 들어 있어,
    DM에 복제하면 민감 정보가 한 군데 더 생긴다. 원문 링크로 충분하다.
    """
    if not items:
        return None

    shown = items[:MAX_ITEMS]
    hidden = len(items) - len(shown)

    lines = [f"💸 아직 송금 안 된 정산 요청 {len(items)}건입니다.", ""]
    lines += [
        f"{n}. <@{i.user}> — {i.elapsed.days}일 경과 · <{i.permalink}|원문 보기>"
        for n, i in enumerate(shown, start=1)
    ]
    if hidden:
        lines.append(f"…외 {hidden}건")
    lines += [
        "",
        f"송금하셨으면 원문에 :{done_emoji}: 를 달아주세요.",
        f"정산 대상이 아닌 글은 :{skip_emoji}: 로 빼면 다음부터 안 뜹니다.",
    ]
    return "\n".join(lines)
