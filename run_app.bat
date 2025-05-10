@echo off
REM Переход в папку проекта, если сценарий запущен из другого места
REM %~dp0 - это путь к каталогу, где лежит этот .bat файл
cd /d "%~dp0"

REM Активация виртуального окружения
REM Проверяем существование файла активации перед запуском
IF EXIST venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) ELSE (
    echo Ошибка: Виртуальное окружение не найдено по пути venv\Scripts\activate.bat
    pause
    exit /b 1
)

REM Установка переменных окружения для Flask
set FLASK_APP=run.py
set FLASK_DEBUG=1
REM Возможно, вам потребуется установить SECRET_KEY как переменную окружения,
REM но для разработки можно оставить в __init__.py
REM set SECRET_KEY=ваш_секретный_ключ

REM Запуск приложения Flask
echo Запуск Flask приложения на порту 5001...
flask run --port 5001

REM Деактивация виртуального окружения при завершении работы сервера (опционально)
REM deactivate

REM Пауза в конце, если запуск завершился ошибкой до flask run
REM pause