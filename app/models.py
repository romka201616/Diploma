# app/models.py

from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import backref
from sqlalchemy import UniqueConstraint # Добавлено для UniqueConstraint
from flask import url_for
from datetime import datetime

# --- Ассоциативная таблица для связи Card и User (исполнители) ---
card_assignees = db.Table('card_assignees',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), primary_key=True),
    db.Column('card_id', db.Integer, db.ForeignKey('card.id', ondelete='CASCADE'), primary_key=True)
)

# --- Ассоциативная таблица для связи Card и Tag ---
card_tags = db.Table('card_tags',
    db.Column('card_id', db.Integer, db.ForeignKey('card.id', ondelete='CASCADE'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id', ondelete='CASCADE'), primary_key=True)
)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

board_members = db.Table('board_members',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), primary_key=True),
    db.Column('board_id', db.Integer, db.ForeignKey('board.id', ondelete='CASCADE'), primary_key=True)
)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    avatar_url = db.Column(db.String(200), nullable=True, default='default_avatar.png')
    is_admin = db.Column(db.Boolean, nullable=False, default=False)

    owned_boards = db.relationship('Board', backref='owner', lazy='dynamic', foreign_keys='Board.user_id', cascade="all, delete-orphan")
    shared_boards = db.relationship('Board', secondary=board_members, lazy='dynamic',
                                    backref=db.backref('members', lazy='dynamic'))
    
    # assigned_cards (многие-ко-многим с Card) создается через backref в Card.assignees
    # comments (один-ко-многим с Comment) создается через backref в Comment.author

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def can_edit_board(self, board):
        return board.owner == self or self in board.members

    def can_delete_board(self, board):
        return board.owner == self
    
    def get_avatar(self):
        if self.avatar_url and self.avatar_url != 'default_avatar.png':
             return url_for('static', filename=f'avatars/{self.avatar_url}')
        return url_for('static', filename='images/default_avatar.png')

    def __repr__(self):
        return f'<User {self.username}>'

class Board(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) 
    columns = db.relationship('Column', backref='board', lazy=True, cascade="all, delete-orphan", order_by='Column.position')
    tags = db.relationship('Tag', backref='board', lazy='dynamic', cascade="all, delete-orphan") # Связь с тегами

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
    
    assignees = db.relationship(
        'User', secondary=card_assignees,
        backref=db.backref('assigned_cards', lazy='dynamic'), 
        lazy='dynamic'
    )
    tags = db.relationship( # Связь с тегами
        'Tag', secondary=card_tags,
        backref=db.backref('cards', lazy='dynamic'),
        lazy='dynamic'
    )
    # comments (один-ко-многим с Comment) создается через backref в Comment.card

    def __repr__(self):
        return f'<Card {self.title}>'

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    color = db.Column(db.String(7), nullable=False, default='#808080') # HEX color, e.g., #FF0000
    board_id = db.Column(db.Integer, db.ForeignKey('board.id', ondelete='CASCADE'), nullable=False)

    __table_args__ = (UniqueConstraint('name', 'board_id', name='uq_tag_name_board'),)

    def __repr__(self):
        return f'<Tag {self.name} ({self.color}) Board: {self.board_id}>'

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    card_id = db.Column(db.Integer, db.ForeignKey('card.id', ondelete='CASCADE'), nullable=False)

    author = db.relationship('User', backref=db.backref('comments', lazy='dynamic', cascade="all, delete-orphan"))
    card = db.relationship('Card', backref=db.backref('comments', lazy='dynamic', cascade="all, delete-orphan"))

    def __repr__(self):
        return f'<Comment {self.id} by User {self.author.username if self.author else "Unknown"} on Card {self.card_id}>'