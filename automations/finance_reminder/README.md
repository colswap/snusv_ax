# finance_reminder

회계 채널에서 송금이 안 끝난 정산 요청을 매일 회계 담당자에게 요약해 DM한다.

## 흐름

```
매일 10:07 KST
   ↓
회계 채널 조회  [기수 시작일 … 48시간 전]
   ↓
미처리 판정     최상위 글 · 사람이 쓴 글 · ✅ 없음 · ❌ 없음
   ↓
0건이면 종료 (DM 없음)
   ↓
회계 User Group 멤버 각자에게 DM 한 통
```

## 파일

| 파일 | 역할 |
|---|---|
| `rules.py` | 미처리 판정. **Slack을 모르는 순수 함수**라 워크스페이스 없이 테스트된다 |
| `format.py` | DM 본문 렌더링 |
| `main.py` | 조립 · CLI |

규칙을 바꾸고 싶다면 `rules.py`만 보면 된다. `tests/test_rules.py`에 경계 케이스가 전부 들어 있으니 테스트를 먼저 고치고 구현을 맞추는 편이 빠르다.

## 판정 규칙

아래를 **전부** 만족하면 미처리다.

- 최상위 글 (스레드 답글 제외)
- 사람이 쓴 글 (입퇴장 알림·봇 메시지 제외)
- 기수 시작일 이후
- 48시간 이상 경과
- ✅(`white_check_mark`) 리액션 없음
- ❌(`x`) 리액션 없음

**누가 리액션을 눌렀는지는 따지지 않는다.** 실데이터를 보면 회계 담당자가 본인이 올린 지출 기록을 본인이 체크하는 경우가 가장 많았다.

## 왜 이렇게 만들었나

- [매일 요약을 택한 이유](../../docs/adr/0002-daily-digest-instead-of-per-post-alerts.md) — 상태 저장이 사라졌다
- [자동 판별 필터를 안 넣은 이유](../../docs/adr/0003-no-automatic-classification-filter.md) — 필터가 긴급 요청부터 놓쳤다
- [전체 설계 스펙](../../docs/superpowers/specs/2026-08-13-finance-reminder-design.md)

## 손으로 돌려보기

```bash
python -m automations.finance_reminder.main --dry-run
```

GitHub에서는 Actions → "회계 송금 리마인더" → Run workflow (`dry_run` 체크).
