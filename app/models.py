from app import db, login_manager
from flask_login import UserMixin # Специальный класс для модели пользователя Flask-Login
from werkzeug.security import generate_password_hash, check_password_hash

# Функция для Flask-Login: загружает пользователя по его ID из сессии
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Модель Пользователя
# UserMixin добавляет нужные свойства для Flask-Login (is_authenticated и т.д.)
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True) # Уникальный ID, первичный ключ
    username = db.Column(db.String(64), index=True, unique=True, nullable=False) # Имя пользователя, уникальное
    email = db.Column(db.String(120), index=True, unique=True, nullable=False) # Email, уникальный
    password_hash = db.Column(db.String(256)) # Хеш пароля (никогда не храним пароль в открытом виде!)

    # Связь с досками: один пользователь может иметь много досок
    # backref='owner' позволяет обращаться к пользователю от доски: board.owner
    # lazy=True означает, что доски будут загружены только когда мы к ним обратимся
    boards = db.relationship('Board', backref='owner', lazy=True, cascade="all, delete-orphan")

    # Метод для установки хеша пароля
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    # Метод для проверки пароля
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # Как объект будет выглядеть при печати (полезно для отладки)
    def __repr__(self):
        return f'<User {self.username}>'

# Модель Доски
class Board(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False) # Название доски
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) # Внешний ключ на пользователя (кто владелец)

    # Связь с колонками: одна доска может иметь много колонок
    columns = db.relationship('Column', backref='board', lazy=True, cascade="all, delete-orphan", order_by='Column.position') # Добавим order_by позже для сортировки

    def __repr__(self):
        return f'<Board {self.name}>'

# Модель Колонки
class Column(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False) # Название колонки
    position = db.Column(db.Integer, nullable=False, default=0) # Позиция для сортировки (добавим позже)
    board_id = db.Column(db.Integer, db.ForeignKey('board.id'), nullable=False) # Внешний ключ на доску

    # Связь с карточками: одна колонка может иметь много карточек
    cards = db.relationship('Card', backref='column', lazy='dynamic', cascade="all, delete-orphan") # lazy='dynamic' позволяет делать доп. запросы к карточкам

    def __repr__(self):
        return f'<Column {self.name}>'

# Модель Карточки (Задачи)
class Card(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False) # Заголовок карточки
    description = db.Column(db.Text, nullable=True) # Поле для описания карточки
    column_id = db.Column(db.Integer, db.ForeignKey('column.id'), nullable=False) # Внешний ключ на колонку

    def __repr__(self):
        return f'<Card {self.title}>'