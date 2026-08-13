# RUNBOOK

운영 중 생기는 일들의 대처법. 코드를 안 읽어도 되도록 쓴다.

---

## ⚠️ 절대 하면 안 되는 것 두 가지

### 1. Slack 앱을 "배포(Distribute App)" 상태로 만들지 말 것

Slack 앱 설정에 배포 관련 메뉴가 보여도 **켜지 말 것.**

Slack은 2025년 5월부터 마켓플레이스 외부에 배포된 앱의 채널 히스토리 조회를 **요청당 15건, 분당 1회**로 제한했고, 기존 설치분 유예도 2026년 3월 3일에 끝났다. 반면 **워크스페이스 내부용 커스텀 앱은 예외**로 요청당 1,000건·분당 50회 이상을 유지한다.

지금 이 봇은 내부 앱이라 한 기수치를 요청 한 번에 가져온다. 배포를 켜는 순간 같은 작업이 수십 분짜리 폴링으로 변한다. **코드는 그대로인데 봇만 느려지므로 원인을 찾기가 매우 어렵다.**

### 2. 60일 넘게 커밋을 멈추지 말 것

퍼블릭 레포는 60일간 활동이 없으면 스케줄 워크플로가 **자동으로 꺼진다.** 타이머를 리셋하는 건 커밋뿐이고 이슈·PR·릴리스는 인정되지 않는다.

방학이 정확히 이 구간에 걸리므로, 매월 1일에 자동 커밋하는 `keepalive.yml`을 넣어뒀다. **이 워크플로를 지우면 안 된다.** 지웠다면 두 달 안에 봇이 조용히 멈춘다.

---

## 처음 설치하기

한 번만 하면 되는 작업이다. 순서를 지킨다.

### 1. Slack 앱 만들기

1. https://api.slack.com/apps → Create New App
2. **From a manifest** 를 고른다 (`Upload JSON or YAML config`)
3. 워크스페이스를 선택하고, 레포의 [`slack-app-manifest.yml`](slack-app-manifest.yml) 내용을 붙여넣는다
4. 좌측 **OAuth & Permissions** → `Install to Workspace` → **Bot User OAuth Token**(`xoxb-`로 시작) 복사
5. **배포(Distribute App)는 켜지 않는다.** 위 경고 참조

> **필요한 값은 `xoxb-` 토큰 하나뿐이다.** Basic Information 페이지의 App Credentials가 먼저 눈에 띄지만 그것들은 쓰지 않는다.
>
> | 값 | 용도 | 이 봇이 쓰나 |
> |---|---|---|
> | Client ID / Secret | OAuth 인증 흐름 (남의 워크스페이스에 설치할 때) | ✗ |
> | Signing Secret | Slack이 **우리 서버로** 보내는 요청을 검증할 때 | ✗ (서버가 없다) |
> | Verification Token | 위의 구버전, 폐기 예정 | ✗ |
> | **Bot User OAuth Token** | Web API 호출 | **✓** |
>
> 이 봇은 요청을 받지 않고 Slack을 호출하기만 하므로 Signing Secret이 필요 없다.
>
> **`xoxb-` 토큰은 채널 히스토리를 읽고 DM을 보낼 수 있는 실제 권한이다.** 채팅·문서·레포 어디에도 붙여넣지 말고 GitHub Secrets에 직접 입력한다. 실수로 노출했다면 즉시 위의 "봇 토큰을 재발급해야 할 때" 절차를 따른다.

매니페스트에 스코프 넷이 이미 들어 있으므로 권한을 손으로 고를 필요가 없다. 4단계 화면에서 **Bot Token Scopes에 넷이 들어 있는지 눈으로 확인**한다.

> **"Install Slack CLI" 화면이 뜨면 무시하고 넘어간다.** `slack login` · `slack create` · `slack run` 은 Slack 차세대 플랫폼(Bolt/Deno) 앱을 만들 때 쓰는 것이고, 이 봇과는 무관하다. 이 봇은 GitHub Actions에서 도는 파이썬 스크립트이며 Web API만 호출한다. 그 플랫폼은 Slack 유료 플랜도 요구한다 — [0005](docs/adr/0005-build-instead-of-buying-a-triage-tool.md) 참조.
>
> 좌측 메뉴에서 **OAuth & Permissions** 로 바로 이동하면 된다.

> 화면에 **AI agent / Starter app / From a manifest / Blank app** 이 보인다. 예전에는 "From scratch"였던 것이 **Blank app**으로 이름이 바뀌었다. Blank app으로 만들어도 되지만, 그러면 OAuth & Permissions에서 스코프 넷(`channels:history` · `usergroups:read` · `chat:write` · `im:write`)을 손으로 추가해야 하고 빠뜨리기 쉽다. **From a manifest 를 권한다.**

### 2. 봇을 회계 채널에 초대

회계 채널에서 `/invite @봇이름`. 스코프만으로는 히스토리를 못 읽는다.

### 3. 회계 User Group 만들기

Slack → 좌측 사이드바 → 사용자 그룹 → 새 그룹. 핸들을 정하고(예: `accounting`) 이번 기수 회계 담당자를 멤버로 넣는다.

**기수가 바뀌면 이 그룹의 멤버만 교체한다.** 그래서 코드를 안 건드려도 된다.

### 4. GitHub 설정값 입력

레포 → Settings → Secrets and variables → Actions. 아래 "설정값 전체" 표대로 채운다.

채널 ID는 Slack에서 채널 우클릭 → 링크 복사 → URL 끝의 `C`로 시작하는 문자열이다.

### 5. 드라이런으로 검증

Actions → "회계 송금 리마인더" → Run workflow → `dry_run` 체크한 채로 실행.

로그에 조회 건수와 미처리 목록, 수신자가 찍힌다. DM은 나가지 않는다. **여기서 이상이 없어야 실제 발송을 맡긴다.**

### 6. 첫 자동 실행 확인

다음 날 09:00 KST 이후 Actions 탭에서 실행 기록을 확인한다.

## 기수가 바뀌었을 때

1. GitHub 레포 → Settings → Secrets and variables → Actions → **Variables** 탭
2. `COHORT_START_DATE`를 새 기수 시작일(`YYYY-MM-DD`)로 수정
3. `README.md` 맨 위의 "현 기수" 줄을 새 기수로 수정

**코드는 건드리지 않는다.**

3번은 동작에 영향이 없지만, 빠뜨리면 README와 실제 설정이 어긋나 다음 사람이 헷갈린다. 동작을 결정하는 값은 언제나 `COHORT_START_DATE`다.

회계 담당자도 함께 바뀌었다면 아래 항목을 이어서 본다.

## 회계 담당자가 바뀌었을 때

Slack에서 회계 User Group의 멤버만 교체한다. **레포는 건드리지 않는다.**

그룹 자체를 다른 것으로 바꿔야 한다면 Variables의 `ACCOUNTANT_USERGROUP`을 새 핸들(`@` 없이)로 수정한다.

## 봇 토큰을 재발급해야 할 때

1. https://api.slack.com/apps 에서 해당 앱 → OAuth & Permissions
2. Reinstall to Workspace → 새 Bot User OAuth Token(`xoxb-`로 시작) 복사
3. 레포 Settings → Secrets and variables → Actions → **Secrets** 탭 → `SLACK_BOT_TOKEN` 수정

## DM이 안 올 때 — 점검 순서

**0단계. 미처리가 정말 0건인가?**
미처리가 없으면 DM을 보내지 않는다. 이건 정상이다. 채널에 ✅ 없는 글이 이틀 넘게 있는지 눈으로 확인한다.

**1단계. 워크플로가 돌긴 했나?**
레포 → Actions 탭 → "회계 송금 리마인더". 실행 기록이 없으면 60일 비활성화를 의심한다(위 참조). 워크플로 페이지에 "이 워크플로가 비활성화되었습니다" 배너가 뜨면 버튼을 눌러 다시 켠다.

**2단계. 실패했나?**
빨간 X가 있으면 클릭해서 로그를 본다. 에러 메시지에 무엇을 고쳐야 하는지가 적혀 있다.

**3단계. 손으로 돌려본다.**
Actions → "회계 송금 리마인더" → Run workflow → `dry_run` 체크한 채로 실행. DM은 안 나가고 판정 결과만 로그에 찍힌다.

## 자주 나오는 에러

| 로그 메시지 | 원인과 대처 |
|---|---|
| `봇이 채널에 없습니다` | 회계 채널에서 `/invite @봇이름` |
| `채널을 찾을 수 없습니다` | Variables의 `FINANCE_CHANNEL_ID` 확인 |
| `봇 토큰이 유효하지 않습니다` | 토큰 재발급 (위 참조) |
| `봇에 필요한 권한이 없습니다` | 아래 스코프 목록과 대조 |
| `User Group을 찾을 수 없습니다` | `ACCOUNTANT_USERGROUP` 확인. 로그에 사용 가능한 핸들이 함께 찍힌다 |
| `User Group에 멤버가 없습니다` | Slack에서 그룹에 회계 담당자 추가 |
| `COHORT_START_DATE가 ... 미래입니다` | 기수 시작일을 오늘 이전으로 |

## 설정값 전체

레포 Settings → Secrets and variables → Actions

**Secrets** (값이 숨겨짐)

| 이름 | 설명 |
|---|---|
| `SLACK_BOT_TOKEN` | 봇 토큰 (`xoxb-`로 시작) |

**Variables** (값이 보임)

| 이름 | 필수 | 설명 |
|---|---|---|
| `FINANCE_CHANNEL_ID` | 필수 | 회계 채널 ID (`C`로 시작). 채널 우클릭 → 링크 복사 |
| `ACCOUNTANT_USERGROUP` | 필수 | 회계 User Group 핸들 (`@` 없이) |
| `COHORT_START_DATE` | 필수 | 기수 시작일 `YYYY-MM-DD` |
| `REMIND_AFTER_HOURS` | 선택 | 며칠 지나면 알릴지. 기본 `48` |
| `DONE_EMOJI` | 선택 | 완료 표시 이모지. 기본 `white_check_mark` |
| `SKIP_EMOJI` | 선택 | 제외 표시 이모지. 기본 `x` |

## Slack 앱 스코프

봇 토큰 스코프는 이 넷이면 충분하다. 더 달라고 요청하지 않는다.

- `channels:history` — 채널 히스토리 조회 (비공개 채널이면 `groups:history`)
- `usergroups:read` — 회계 담당자 그룹 멤버 조회
- `chat:write` — DM 발송
- `im:write` — DM 채널 열기

그리고 **봇을 회계 채널에 초대해야 한다.** 스코프만으로는 못 읽는다.

## 이 봇을 쓰는 사람에게

- 송금을 마쳤으면 원문에 ✅ 를 단다. 그러면 다음 날부터 목록에서 사라진다.
- 정산과 무관한 글(잡담, 질문)이 목록에 꼈으면 그 글에 ❌ 를 단다. 영구히 제외된다.
- 누가 ✅ 를 눌렀는지는 따지지 않는다. 본인 글에 본인이 눌러도 된다.
