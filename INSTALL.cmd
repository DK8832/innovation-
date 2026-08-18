@echo off
setlocal
set "PACKAGE_ROOT=%~dp0"

where codex.exe >nul 2>nul
if errorlevel 1 (
  echo Codex CLI를 찾지 못했습니다. Codex 터미널에서 이 파일을 실행해 주세요.
  exit /b 1
)

codex plugin marketplace add "%PACKAGE_ROOT%" --json
if errorlevel 1 exit /b 1

codex plugin add factlens@factlens-share --json
if errorlevel 1 exit /b 1

echo FactLens 설치가 완료되었습니다. Codex에서 새 작업을 열어 사용하세요.
