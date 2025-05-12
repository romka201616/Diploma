# app/__init__.py

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
# from flask_migrate import Migrate # <--- УБРАТЬ или закомментировать

app = Flask(__name__)

# --- Конфигурация приложения ---
app.config['SECRET_KEY'] = 'ce8de42314c87271ef469fbe5841e478' # ЗАМЕНИТЬ!

basedir = os.path.abspath(os.path.dirname(__file__))
instance_path = os.path.join(os.path.dirname(basedir), 'instance')
os.makedirs(instance_path, exist_ok=True)

app.config['UPLOADED_AVATARS_DEST'] = os.path.join(basedir, 'static', 'avatars')
os.makedirs(app.config['UPLOADED_AVATARS_DEST'], exist_ok=True)
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(instance_path, 'mydatabase.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# --- Конец Конфигурации ---

db = SQLAlchemy(app)
csrf = CSRFProtect(app)
login_manager = LoginManager(app)
# migrate = Migrate(app, db) # <--- УБРАТЬ или закомментировать

login_manager.login_view = 'login'
login_manager.login_message = 'Пожалуйста, войдите, чтобы получить доступ к этой странице.'
login_manager.login_message_category = 'info'

from app import routes, models