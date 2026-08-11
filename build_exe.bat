@echo off
REM 东方天空街 ~ Touhou Sky Street
REM 打包为单文件 EXE（PyInstaller）

cd /d "%~dp0"

echo Building TouHouSkyStreet.exe...
echo.

python -m PyInstaller --onefile --name "TouHouSkyStreet" --add-data "assets;assets" --noconsole main.py

echo.
echo Done! EXE is in dist\TouHouSkyStreet.exe
pause