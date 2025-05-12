
from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import backref

# --- Ассоциативная таблица для связи Card и User (исполнители) ---
# Эта таблица будет создана позже, когда мы перейдем к "нескольким исполнителям"
# card_assignees = db.Table('card_assignees',
#     db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
#     db.Column('card_id', db.Integer, db.ForeignKey('card.id'), primary_key=True)
# )

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

board_members = db.Table('board_members',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('board_id', db.Integer, db.ForeignKey('board.id'), primary_key=True)
)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    avatar_url = db.Column(db.String(200), nullable=True, default='default_avatar.png') # Путь к файлу относительно static/avatars/
    is_admin = db.Column(db.Boolean, nullable=False, default=False)

    owned_boards = db.relationship('Board', backref='owner', lazy='dynamic', foreign_keys='Board.user_id', cascade="all, delete-orphan")
    shared_boards = db.relationship('Board', secondary=board_members, lazy='dynamic',
                                    backref=db.backref('members', lazy='dynamic'))
    
    # Связь для исполнителей карточек (будет изменена на many-to-many)
    # Пока оставим существующую, чтобы не сломать текущий функционал
    # assigned_cards = db.relationship('Card', backref='assignee', lazy='dynamic', foreign_keys='Card.assignee_id')


    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def can_edit_board(self, board):
        return board.owner == self or self in board.members

    def can_delete_board(self, board):
        return board.owner == self
    
    def get_avatar(self):
        # Предполагаем, что аватарки хранятся в static/avatars/
        # и avatar_url это имя файла, например 'user_1.jpg' или 'default_avatar.png'
        from flask import url_for
        if self.avatar_url and self.avatar_url != 'default_avatar.png':
             # Если есть кастомный аватар, строим путь к нему
             return url_for('static', filename=f'avatars/{self.avatar_url}')
        # Иначе возвращаем путь к дефолтному аватару
        return url_for('static', filename='images/default_avatar.png')


    def __repr__(self):
        return f'<User {self.username}>'

class Board(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    columns = db.relationship('Column', backref='board', lazy=True, cascade="all, delete-orphan", order_by='Column.position')

    def get_eligible_assignees(self):
        assignees = [self.owner] + self.members.all()
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
    
    # Текущая связь один-ко-многим для исполнителя (будет изменена)
    assignee_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    assignee = db.relationship('User', backref=backref('assigned_cards', lazy='dynamic'), foreign_keys=[assignee_id])
    
    # Для нескольких исполнителей (будет реализовано позже):
    # assignees = db.relationship('User', secondary=card_assignees, lazy='dynamic',
    #                             backref=db.backref('assigned_to_cards', lazy='dynamic'))


    def __repr__(self):
        return f'<Card {self.title}>'
