# snusv_ax

SNUSV 운영 자동화 모음. 서버 없이 GitHub Actions에서 하루 한 번씩 도는 작은 스크립트들이다.

## 자동화 목록

| 자동화 | 하는 일 | 실행 |
|---|---|---|
| [`finance_reminder`](automations/finance_reminder/) | 회계 채널에서 ✅가 안 달린 정산 요청을 매일 회계 담당자에게 DM | 매일 10:07 KST |

## 설계 원칙

**서버를 두지 않는다.** 판정 기준이 "며칠 지났는가"라 실시간 처리가 필요 없다. 서버는 계속 관리할 사람을 요구하는데, 매년 운영진이 바뀌는 조직에서 그건 자동화가 죽는 가장 빠른 길이다.

**상태를 저장하지 않는다.** 매 실행마다 채널을 새로 훑어 결과를 계산한다. "이미 알림 보낸 글" 같은 걸 기억하지 않으므로 DB가 없고, 실행이 한 번 실패해도 다음 날 저절로 정상으로 돌아온다.

**조용히 실패하지 않는다.** 설정이 틀렸거나 API가 실패하면 워크플로를 실패로 끝낸다. 그래야 GitHub이 메일을 보낸다. 아무 일도 안 하고 초록불이 뜨는 것이 가장 위험한 상태다.

**판정 로직은 Slack을 모른다.** 각 자동화의 `rules.py`는 순수 함수라 워크스페이스 없이 전부 테스트된다. 규칙을 고칠 때 이게 제일 고맙다.

## 구조

```
shared/              자동화들이 공유하는 부품
  config.py          환경변수 로딩·검증
  slack.py           Slack API 호출·재시도
  dm.py              User Group 조회 → 멤버별 DM
automations/         자동화 하나 = 폴더 하나
tests/               pytest
.github/workflows/   자동화 하나 = 워크플로 하나
docs/adr/            왜 그렇게 정했는지
docs/superpowers/specs/  설계 문서
```

자동화를 추가하려면 `automations/` 아래 폴더 하나와 `.github/workflows/` 아래 yml 하나를 만든다.

## 개발

```bash
pip install -r requirements.txt pytest
python -m pytest
```

DM을 보내지 않고 판정만 확인:

```bash
python -m automations.finance_reminder.main --dry-run
```

## 인수인계

운영 중 문제가 생겼거나 기수가 바뀌었다면 **[RUNBOOK.md](RUNBOOK.md)** 를 먼저 읽는다. 대부분의 상황이 거기 적혀 있다.
