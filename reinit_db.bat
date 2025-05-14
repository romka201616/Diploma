@echo off
cls
echo ========================================================
echo ==           REINITIALIZING DATABASE SCRIPT           ==
echo ========================================================
echo.

REM Устанавливаем директорию скрипта как текущую
cd /d "%~dp0"

REM Проверка, находимся ли мы в корне проекта
IF NOT EXIST "venv\Scripts\activate.bat" (
    echo ERROR: Could not find 'venv\Scripts\activate.bat'.
    echo Make sure 'venv' directory is present in the current directory:
    echo %CD%
    echo And that this script is in the project root.
    goto :error_exit
)
IF NOT EXIST "run.py" (
    echo ERROR: Could not find 'run.py'.
    echo Make sure 'run.py' is present in the current directory:
    echo %CD%
    echo And that this script is in the project root.
    goto :error_exit
)

echo Activating virtual environment from %CD%\venv\Scripts\activate.bat ...
call "venv\Scripts\activate.bat"
IF ERRORLEVEL 1 (
    echo FAILED to activate virtual environment.
    goto :error_exit
)
echo Virtual environment activated.
echo.

echo Setting up Flask environment variables...
set "FLASK_APP=run.py"
set "FLASK_DEBUG=1"
echo   FLASK_APP set to: %FLASK_APP%
echo   FLASK_DEBUG set to: %FLASK_DEBUG%
echo.

echo Checking if Python and Flask module are available...
REM Проверяем, что python из venv доступен и может запустить flask как модуль
python -m flask --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: 'python -m flask' command is not working.
    echo Please ensure Python from venv is in PATH and Flask is installed.
    echo You might need to run: pip install Flask
    goto :error_exit
)
echo Flask module is available via Python.
echo.

echo Re-initializing database with 'python -m flask db-init --force'...
python -m flask db-init --force
echo.

echo ========================================================
echo ==  Database re-initialization process finished.      ==
echo ==  You can now run your application.                 ==
echo ========================================================
echo.
goto :success_exit

:error_exit
echo.
echo SCRIPT TERMINATED DUE TO AN ERROR.
echo Please review the messages above.
echo.
pause
exit /b 1

:success_exit
pause
exit /b 0