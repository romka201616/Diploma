import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# Создаем экземпляр приложения Flask
app = Flask(__name__)

# --- Конфигурация приложения ---
# SECRET_KEY: Очень важный ключ для безопасности сессий и других вещей.
# Обязательно замените 'your_very_secret_key_here' на свою СЛУЧАЙНУЮ строку!
# Как сгенерировать: можно использовать онлайн-генераторы или выполнить в Python:
# import secrets; secrets.token_hex(16)
app.config['SECRET_KEY'] = 'ce8de42314c87271ef469fbe5841e478'

# Определяем путь к папке проекта
basedir = os.path.abspath(os.path.dirname(__file__))
# Создаем папку instance, если ее нет (Flask может делать это сам)
instance_path = os.path.join(os.path.dirname(basedir), 'instance')
os.makedirs(instance_path, exist_ok=True)

# Путь к файлу базы данных SQLite внутри папки instance
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(instance_path, 'mydatabase.db')
# Отключаем отслеживание модификаций SQLAlchemy, чтобы не было предупреждений
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# --- Конец Конфигурации ---

# Инициализируем SQLAlchemy (для работы с базой данных)
db = SQLAlchemy(app)

# Инициализируем Flask-Login (для управления входом пользователей)
login_manager = LoginManager(app)
# Указываем Flask-Login, какая функция (view) обрабатывает вход пользователя.
# 'routes.login' - это имя функции 'login' в файле 'routes.py' (мы создадим его позже).
login_manager.login_view = 'routes.login'
# Сообщение, которое будет показано пользователю при попытке доступа к защищенной странице без входа
login_manager.login_message = 'Пожалуйста, войдите, чтобы получить доступ к этой странице.'
login_manager.login_message_category = 'info' # Категория для стилизации сообщения (если используем Bootstrap)

# Импортируем маршруты и модели в конце, чтобы избежать циклических зависимостей
# Эти файлы мы создадим/заполним на следующих шагах
from app import routes, models