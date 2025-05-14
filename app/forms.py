# app/forms.py

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed # Для загрузки файлов
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, SelectField, SelectMultipleField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Optional
from app.models import User
from flask_login import current_user # Для валидации текущего пароля


class RegistrationForm(FlaskForm):
    username = StringField('Имя пользователя',
                           validators=[DataRequired(message="Это поле обязательно."),
                                       Length(min=4, max=64, message="Имя должно быть от 4 до 64 символов.")])
    email = StringField('Email',
                        validators=[DataRequired(message="Это поле обязательно."),
                                    Email(message="Введите корректный email.")])
    password = PasswordField('Пароль',
                             validators=[DataRequired(message="Это поле обязательно."),
                                         Length(min=6, message="Пароль должен быть не менее 6 символов.")])
    confirm_password = PasswordField('Подтвердите пароль',
                                     validators=[DataRequired(message="Это поле обязательно."),
                                                 EqualTo('password', message="Пароли должны совпадать.")])
    submit = SubmitField('Зарегистрироваться')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Это имя пользователя уже занято. Пожалуйста, выберите другое.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Этот email уже зарегистрирован. Пожалуйста, используйте другой.')

class LoginForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(message="Это поле обязательно."),
                                    Email(message="Введите корректный email.")])
    password = PasswordField('Пароль', validators=[DataRequired(message="Это поле обязательно.")])
    remember_me = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')

class BoardForm(FlaskForm):
    name = StringField('Название доски',
                       validators=[DataRequired(message="Название доски не может быть пустым."),
                                   Length(min=1, max=100, message="Название должно быть от 1 до 100 символов.")])
    submit = SubmitField('Создать/Сохранить доску')

class ColumnForm(FlaskForm):
    name = StringField('Название колонки',
                       validators=[DataRequired(message="Название колонки не может быть пустым."),
                                   Length(min=1, max=100)])
    submit_column = SubmitField('Добавить/Сохранить колонку')

class CardForm(FlaskForm):
    title = StringField('Заголовок карточки',
                        validators=[DataRequired(message="Заголовок не может быть пустым."),
                                    Length(min=1, max=150)])
    description = TextAreaField('Описание', validators=[Length(max=1000), Optional()])
    
    # Поле для нескольких исполнителей
    assignees = SelectMultipleField('Исполнители', coerce=int, validators=[Optional()])
    
    submit_card = SubmitField('Добавить/Сохранить карточку')


class InviteUserForm(FlaskForm):
    email_or_username = StringField('Email или Имя пользователя для приглашения',
                                    validators=[DataRequired(message="Введите email или имя пользователя.")])
    submit_invite = SubmitField('Пригласить')

# --- Формы для Профиля Пользователя ---
class UpdateAccountForm(FlaskForm):
    username = StringField('Имя пользователя',
                           validators=[DataRequired(), Length(min=4, max=64)])
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    submit = SubmitField('Обновить профиль')

    def validate_username(self, username):
        if username.data != current_user.username: 
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('Это имя пользователя уже занято. Пожалуйста, выберите другое.')

    def validate_email(self, email):
        if email.data != current_user.email: 
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('Этот email уже зарегистрирован. Пожалуйста, используйте другой.')

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Текущий пароль', validators=[DataRequired()])
    new_password = PasswordField('Новый пароль',
                                 validators=[DataRequired(), Length(min=6)])
    confirm_new_password = PasswordField('Подтвердите новый пароль',
                                         validators=[DataRequired(), EqualTo('new_password', message='Пароли должны совпадать.')])
    submit = SubmitField('Сменить пароль')

    def validate_current_password(self, current_password):
        if not current_user.check_password(current_password.data):
            raise ValidationError('Неверный текущий пароль.')

class UpdateAvatarForm(FlaskForm):
    avatar = FileField('Новый аватар (макс 2МБ, jpg, png, gif)',
                       validators=[DataRequired(message="Выберите файл для загрузки."),
                                   FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Разрешены только изображения (jpg, png, gif)!')])
    submit = SubmitField('Загрузить аватар')

# --- Формы для Панели Администратора ---
class AdminEditUserForm(FlaskForm):
    username = StringField('Имя пользователя',
                           validators=[DataRequired(), Length(min=4, max=64)])
    email = StringField('Email (не редактируется администратором)', render_kw={'readonly': True})
    is_admin = BooleanField('Права администратора') 
    submit = SubmitField('Сохранить изменения')

    def __init__(self, original_username, *args, **kwargs):
        super(AdminEditUserForm, self).__init__(*args, **kwargs)
        self.original_username = original_username

    def validate_username(self, username):
        if username.data != self.original_username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('Это имя пользователя уже занято.')