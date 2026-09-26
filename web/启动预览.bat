@echo off
REM 东方天空街 ~ Touhou Sky Street · 官网一键预览
REM 启动本地服务并打开浏览器；站点根目录为 web/

cd /d "%~dp0"

set PORT=8100
set PY=python
if exist "..\python_path.txt" (
  for /f "usebackq delims=" %%i in ("..\python_path.txt") do set PY=%%i
)

echo 正在启动预览服务：http://127.0.0.1:%PORT%/
start "" "http://127.0.0.1:%PORT%/"
"%PY%" serve.py %PORT%

pause
