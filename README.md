# FactLens 친구 공유 패키지

FactLens는 AI 답변을 독립적인 기준 자료와 대조해 주장별로 `SUPPORTED`, `CONTRADICTED`, `INSUFFICIENT`, `UNVERIFIABLE` 상태를 보여주는 Codex 플러그인입니다.

## 빠른 설치

1. ZIP 파일을 원하는 폴더에 완전히 압축 해제합니다.
2. Codex 터미널에서 압축을 푼 폴더의 `INSTALL.cmd`를 실행합니다.
3. Codex에서 새 작업을 만들고 FactLens 플러그인을 선택합니다.
4. `FactLens 검증을 거쳐 답변해줘`라고 요청합니다.

직접 설치하려면 압축을 푼 폴더에서 다음 명령을 실행합니다.

```powershell
codex plugin marketplace add . --json
codex plugin add factlens@factlens-share --json
```

## 실행 요구사항

- Windows용 Codex 데스크톱 앱 또는 Codex CLI
- Node.js 20 이상
- Python 3.10 이상

Codex 데스크톱의 번들 런타임이 있으면 실행기가 이를 자동으로 사용합니다. 그렇지 않으면 `node.exe`와 `python.exe`가 `PATH`에 있어야 합니다.

## 확인 방법

새 작업에서 다음과 같이 요청합니다.

```text
FactLens 검증을 거쳐 답변해줘. 세종대왕은 언제 태어났어?
```

FactLens는 검색기가 아닙니다. Codex가 웹, 작업공간 파일 또는 사용자가 제공한 문서에서 독립 근거를 먼저 확보해야 합니다. 근거가 없으면 검증 완료로 표시하지 않습니다.

## 개발 및 공개 배포

- 플러그인 소스: `plugins/factlens`
- 로컬 MCP 검사: `node scripts/smoke_test.mjs`
- HTTP MCP 검사: `node scripts/http_smoke_test.mjs`
- HTTP 실행: `pnpm run start:http`
- Docker 실행 설정: `plugins/factlens/Dockerfile`
- 공개 제출 준비: `plugins/factlens/PUBLICATION.md`

GitHub 소스 체크아웃에서는 `plugins/factlens`로 이동해 `pnpm install --frozen-lockfile`과 `pnpm run build`를 먼저 실행합니다. 해커톤 제출용 공유 ZIP에는 빌드가 완료된 `dist/server.mjs`가 포함되어 있어 별도 `node_modules` 설치 없이 실행할 수 있습니다.
