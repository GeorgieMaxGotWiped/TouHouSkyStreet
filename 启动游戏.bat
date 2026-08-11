@echo off
REM 东方天空街 ~ Touhou Sky Street
REM 启动游戏（Python 源码版）
REM 自动检测用户电脑上的 Python 与依赖，无需手动配置

cd /d "%~dp0"

REM ========== 第一步：查找 Python（优先选择带运行依赖的版本） ==========
set "PY_CMD="
set "PY_CMD_FALLBACK="

REM 1) 用户自定义路径：python_path.txt 第一行（优先级最高）
set "PY_CMD_FILE="
if exist "%~dp0python_path.txt" (
    for /f "usebackq delims=" %%p in ("%~dp0python_path.txt") do if not defined PY_CMD_FILE set "PY_CMD_FILE=%%p"
)
if defined PY_CMD_FILE if exist "%PY_CMD_FILE%" call :TRY_CANDIDATE "%PY_CMD_FILE%"

REM 2) PATH 中的 python（自动跳过 Microsoft Store 占位符）
if not defined PY_CMD (
    for /f "delims=" %%i in ('where python 2^>nul') do if not defined PY_CMD call :TRY_CANDIDATE "%%i"
)

REM 3) py 启动器（-3 保证使用 Python 3）
if not defined PY_CMD (
    where py >nul 2>nul
    if not errorlevel 1 call :TRY_PY
)

REM 4) python.org 常见安装目录
if not defined PY_CMD (
    for %%V in (313 312 311 310 39 38) do (
        if not defined PY_CMD if exist "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe" call :TRY_CANDIDATE "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe"
        if not defined PY_CMD if exist "%ProgramFiles%\Python\Python%%V\python.exe" call :TRY_CANDIDATE "%ProgramFiles%\Python\Python%%V\python.exe"
    )
)

if defined PY_CMD goto PY_READY
if not defined PY_CMD_FALLBACK goto NO_PYTHON
set "PY_CMD=%PY_CMD_FALLBACK%"

:PY_READY
echo 使用 Python：%PY_CMD%
echo.

REM ========== 第二步：检查依赖（逐个模块，缺失时自动安装） ==========
set "MISSING_DEPS="
%PY_CMD% -c "import pygame" >nul 2>nul
if errorlevel 1 (
    echo   [缺失] pygame
    set "MISSING_DEPS=1"
)
%PY_CMD% -c "import numpy" >nul 2>nul
if errorlevel 1 (
    echo   [缺失] numpy
    set "MISSING_DEPS=1"
)
%PY_CMD% -c "import PIL" >nul 2>nul
if errorlevel 1 (
    echo   [缺失] Pillow
    set "MISSING_DEPS=1"
)

if defined MISSING_DEPS (
    echo.
    echo [提示] 当前 Python 缺少运行依赖，正在自动安装...
    %PY_CMD% -m pip install -r requirements.txt
    if errorlevel 1 (
        echo   首次安装失败，尝试 --user 安装...
        %PY_CMD% -m pip install --user -r requirements.txt
        if errorlevel 1 goto INSTALL_FAIL
    )
    %PY_CMD% -c "import pygame, numpy, PIL" >nul 2>nul
    if errorlevel 1 goto INSTALL_STILL_MISSING
    echo [完成] 依赖安装成功。
)

REM ========== 第三步：启动游戏 ==========
%PY_CMD% main.py %*
if errorlevel 1 (
    echo.
    echo [错误] 游戏异常退出，请截图上方报错信息反馈给开发者。
)
echo.
pause
exit /b 0

:NO_PYTHON
echo [错误] 未找到 Python，请先安装 Python 3 并勾选 "Add Python to PATH"。
echo 下载地址：https://www.python.org/downloads/
echo 或在根目录新建 python_path.txt，第一行填写 Python 可执行文件完整路径。
echo.
pause
exit /b 1

:INSTALL_FAIL
echo.
echo [错误] 依赖安装失败，请检查网络后重试，或手动执行：
echo   %PY_CMD% -m pip install -r requirements.txt
echo.
pause
exit /b 1

:INSTALL_STILL_MISSING
echo.
echo [错误] 依赖安装后仍无法导入 pygame / numpy / Pillow，请手动执行：
echo   %PY_CMD% -m pip install -r requirements.txt
echo.
pause
exit /b 1

REM ========== 子程序：尝试一个 Python 候选（%~1 为完整路径） ==========
:TRY_CANDIDATE
"%~1" -c "import sys" >nul 2>nul
if errorlevel 1 exit /b 0
if not defined PY_CMD_FALLBACK set "PY_CMD_FALLBACK="%~1""
"%~1" -c "import pygame, numpy, PIL" >nul 2>nul
if not errorlevel 1 set "PY_CMD="%~1""
exit /b 0

:TRY_PY
py -3 -c "import sys" >nul 2>nul
if errorlevel 1 exit /b 0
if not defined PY_CMD_FALLBACK set "PY_CMD_FALLBACK=py -3"
py -3 -c "import pygame, numpy, PIL" >nul 2>nul
if not errorlevel 1 set "PY_CMD=py -3"
exit /b 0