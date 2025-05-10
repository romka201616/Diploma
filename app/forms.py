from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from app.models import User

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
    description = TextAreaField('Описание', validators=[Length(max=1000)])
    submit_card = SubmitField('Добавить/Сохранить карточку')

class InviteUserForm(FlaskForm):
    email_or_username = StringField('Email или Имя пользователя для приглашения',
                                    validators=[DataRequired(message="Введите email или имя пользователя.")])
    submit_invite = SubmitField('Пригласить')