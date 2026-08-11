@echo off
REM 东方天空街 ~ Touhou Sky Street
REM 打包为单文件 EXE（PyInstaller）
REM 自动检测用户电脑上的 Python 与 PyInstaller，无需手动配置

cd /d "%~dp0"

REM ========== 第一步：自动查找 Python ==========
set "PY_CMD="

REM 1) PATH 中的 python（含完整路径，自动跳过 Microsoft Store 占位符）
for /f "delims=" %%i in ('where python 2^>nul') do (
    if not defined PY_CMD (
        "%%i" -c "import sys" >nul 2>nul
        if not errorlevel 1 set "PY_CMD="%%i""
    )
)

REM 2) py 启动器（-3 保证使用 Python 3）
if not defined PY_CMD (
    where py >nul 2>nul
    if not errorlevel 1 (
        py -3 -c "import sys" >nul 2>nul
        if not errorlevel 1 set "PY_CMD=py -3"
    )
)

REM 3) 用户自定义路径：python_path.txt 第一行（可选）
if not defined PY_CMD if exist "%~dp0python_path.txt" (
    set "PY_CMD_FILE="
    for /f "usebackq delims=" %%p in ("%~dp0python_path.txt") do if not defined PY_CMD_FILE set "PY_CMD_FILE=%%p"
)
if not defined PY_CMD_FILE goto :python_common
if not exist "%PY_CMD_FILE%" goto :python_common
set "PY_CMD="%PY_CMD_FILE%""

REM 4) python.org 常见安装目录
:python_common
for %%V in (313 312 311 310 39 38) do (
    if not defined PY_CMD if exist "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe" set "PY_CMD="%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe""
    if not defined PY_CMD if exist "%ProgramFiles%\Python\Python%%V\python.exe" set "PY_CMD="%ProgramFiles%\Python\Python%%V\python.exe""
)

if not defined PY_CMD (
    echo [错误] 未找到 Python，请先安装 Python 3 并勾选 "Add Python to PATH"。
    echo 下载地址：https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo 使用 Python：%PY_CMD%
echo.

REM ========== 第二步：检查并安装运行依赖与 PyInstaller ==========
%PY_CMD% -c "import pygame, numpy, PIL" >nul 2>nul
if errorlevel 1 (
    echo [提示] 缺少运行依赖（pygame / numpy / Pillow），正在安装...
    %PY_CMD% -m pip install -r requirements.txt
    if errorlevel 1 goto DEP_FAIL
)

%PY_CMD% -m PyInstaller --version >nul 2>nul
if errorlevel 1 (
    echo [提示] 未检测到 PyInstaller，正在安装...
    %PY_CMD% -m pip install pyinstaller
    if errorlevel 1 goto DEP_FAIL
)

REM ========== 第三步：打包 ==========
echo Building TouHouSkyStreet.exe...
echo.
%PY_CMD% -m PyInstaller --onefile --name "TouHouSkyStreet" --add-data "assets;assets" --noconsole main.py

echo.
echo Done! EXE is in dist\TouHouSkyStreet.exe
pause
exit /b 0

:DEP_FAIL
echo.
echo [错误] 依赖安装失败，请检查网络后重试，或手动执行：
echo   %PY_CMD% -m pip install -r requirements.txt
echo   %PY_CMD% -m pip install pyinstaller
echo.
pause
exit /b 1