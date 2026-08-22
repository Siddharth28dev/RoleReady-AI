@echo off
REM ============================================================
REM start-project.bat
REM One-click launcher: starts MariaDB (if not already running),
REM waits for it to be ready, then starts the Flask backend.
REM
REM Adjust the paths below ONLY if your folders change.
REM ============================================================

set MYSQL_BIN=C:\downloads\mysql\bin
set MYSQL_INI=C:\downloads\mysql\bin\my.ini
set BACKEND_DIR=C:\Users\siddh\Downloads\ai-resume-analyzer-claude\ai-resume-analyzer\backend
set VENV_ACTIVATE=C:\Users\siddh\Downloads\ai-resume-analyzer-claude\.venv\Scripts\activate.bat

echo ============================================
echo   Checking if MariaDB is already running...
echo ============================================

REM Check if port 3306 is already listening. If yes, skip starting MariaDB.
netstat -ano | findstr :3306 >nul
if %errorlevel%==0 (
    echo MariaDB is already running on port 3306. Skipping startup.
) else (
    echo MariaDB is NOT running. Starting it now in a new window...
    start "MariaDB Server" cmd /k ""%MYSQL_BIN%\mysqld.exe" --defaults-file="%MYSQL_INI%" --console"

    echo Waiting for MariaDB to be ready...
    :waitloop
    timeout /t 2 /nobreak >nul
    netstat -ano | findstr :3306 >nul
    if errorlevel 1 (
        echo Still waiting...
        goto waitloop
    )
    echo MariaDB is up.
)

echo ============================================
echo   Starting Flask backend...
echo ============================================

cd /d "%BACKEND_DIR%"
call "%VENV_ACTIVATE%"
python run.py

pause