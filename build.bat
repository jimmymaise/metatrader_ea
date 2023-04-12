@echo off

REM Get current build time
for /f %%a in ('wmic os get LocalDateTime ^| findstr ^^[0-9]') do set BUILD_TIME=%%a
set BUILD_TIME=%BUILD_TIME:~0,4%-%BUILD_TIME:~4,2%-%BUILD_TIME:~6,2% %BUILD_TIME:~8,2%:%BUILD_TIME:~10,2%:%BUILD_TIME:~12,2%

REM Write the build time to version.py
echo BUILD_TIME = '%BUILD_TIME%' > version.py

REM Run the PyInstaller command
poetry run pyinstaller -c ea_bot_exe_build.py --onefile --name ea_bot --hiddenimport=numpy.core

REM Copy the terminal_login.json file to the dist directory
copy terminal_login.json ".\dist\terminal_login.json"
