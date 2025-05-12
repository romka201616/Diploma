#--- START OF FILE __init__.py ---

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect # <--- Добавлено

app = Flask(__name__)

# --- Конфигурация приложения ---
# Обязательно замените 'your_very_secret_key_here' на свою СЛУЧАЙНУЮ строку!
# Генерация: import secrets; secrets.token_hex(16)
app.config['SECRET_KEY'] = 'ce8de42314c87271ef469fbe5841e478' # ЗАМЕНИТЬ!

basedir = os.path.abspath(os.path.dirname(__file__))
instance_path = os.path.join(os.path.dirname(basedir), 'instance')
os.makedirs(instance_path, exist_ok=True)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(instance_path, 'mydatabase.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# --- Конец Конфигурации ---

db = SQLAlchemy(app)
login_manager = LoginManager(app)
csrf = CSRFProtect(app) # <--- Инициализация CSRFProtect

login_manager.login_view = 'login' # Имя функции маршрута для страницы входа
login_manager.login_message = 'Пожалуйста, войдите, чтобы получить доступ к этой странице.'
login_manager.login_message_category = 'info'

from app import routes, models
#--- END OF FILE __init__.py ---