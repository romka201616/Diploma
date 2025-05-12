

from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import backref # Добавлено для явного указания backref

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Ассоциативная таблица для связи User и Board (участники доски)
board_members = db.Table('board_members',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('board_id', db.Integer, db.ForeignKey('board.id'), primary_key=True)
)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(256))

    # Доски, созданные пользователем
    owned_boards = db.relationship('Board', backref='owner', lazy='dynamic', foreign_keys='Board.user_id', cascade="all, delete-orphan")

    # Доски, в которых пользователь является участником (через ассоциативную таблицу)
    shared_boards = db.relationship('Board', secondary=board_members, lazy='dynamic',
                                    backref=db.backref('members', lazy='dynamic'))

    # Карточки, назначенные пользователю (через backref от Card.assignee)
    # assigned_cards = db.relationship('Card', backref='assignee', lazy='dynamic', foreign_keys='Card.assignee_id') # backref создается автоматически

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def can_edit_board(self, board):
        # Проверяем, является ли пользователь владельцем ИЛИ участником доски
        return board.owner == self or self in board.members

    def can_delete_board(self, board):
        return board.owner == self

    def __repr__(self):
        return f'<User {self.username}>'

class Board(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) # Владелец доски
    columns = db.relationship('Column', backref='board', lazy=True, cascade="all, delete-orphan", order_by='Column.position')
    # 'members' будет доступен через backref от User.shared_boards

    def get_eligible_assignees(self):
        """Возвращает список пользователей (владелец + участники), которых можно назначить."""
        assignees = [self.owner] + self.members.all()
        # Убираем дубликаты, если владелец есть и в members (хотя это не должно случаться по логике)
        unique_assignees = list({user.id: user for user in assignees}.values())
        return sorted(unique_assignees, key=lambda u: u.username.lower())


    def __repr__(self):
        return f'<Board {self.name}>'

class Column(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    position = db.Column(db.Integer, nullable=False, default=0)
    board_id = db.Column(db.Integer, db.ForeignKey('board.id'), nullable=False)
    cards = db.relationship('Card', backref='column', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Column {self.name}>'

class Card(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    column_id = db.Column(db.Integer, db.ForeignKey('column.id'), nullable=False)

    # --- Добавлено для исполнителя ---
    assignee_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True) # Может быть не назначен
    assignee = db.relationship('User', backref='assigned_cards', foreign_keys=[assignee_id])
    # --- Конец добавлений ---

    # Поля для комментариев будут добавлены позже

    def __repr__(self):
        return f'<Card {self.title}>'

