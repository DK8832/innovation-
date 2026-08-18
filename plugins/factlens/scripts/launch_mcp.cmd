@echo off
setlocal
set "PLUGIN_ROOT=%~dp0.."

if defined CODEX_MCP_NODE_PATH if exist "%CODEX_MCP_NODE_PATH%" (
  set "NODE_BIN=%CODEX_MCP_NODE_PATH%"
)

if not defined NODE_BIN (
  set "NODE_BIN=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
)

if not exist "%NODE_BIN%" (
  for %%I in (node.exe) do set "NODE_BIN=%%~$PATH:I"
)

if not defined NODE_BIN (
  echo FactLens MCP: Node.js runtime was not found. 1>&2
  exit /b 1
)

if not defined FACTLENS_PYTHON if exist "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" (
  set "FACTLENS_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
)

"%NODE_BIN%" "%PLUGIN_ROOT%\dist\server.mjs"
