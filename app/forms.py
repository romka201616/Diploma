from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from app.models import User # Импортируем модель User, чтобы проверять уникальность email/username

# Форма регистрации
class RegistrationForm(FlaskForm):
    # Поле для имени пользователя
    username = StringField('Имя пользователя',
                           validators=[DataRequired(message="Это поле обязательно."),
                                       Length(min=4, max=64, message="Имя должно быть от 4 до 64 символов.")])
    # Поле для email
    email = StringField('Email',
                        validators=[DataRequired(message="Это поле обязательно."),
                                    Email(message="Введите корректный email.")])
    # Поле для пароля
    password = PasswordField('Пароль',
                             validators=[DataRequired(message="Это поле обязательно."),
                                         Length(min=6, message="Пароль должен быть не менее 6 символов.")])
    # Поле для подтверждения пароля
    confirm_password = PasswordField('Подтвердите пароль',
                                     validators=[DataRequired(message="Это поле обязательно."),
                                                 EqualTo('password', message="Пароли должны совпадать.")])
    # Кнопка отправки формы
    submit = SubmitField('Зарегистрироваться')

    # Пользовательские валидаторы для проверки уникальности
    # WTForms автоматически вызывает методы, начинающиеся с validate_<имя_поля>

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Это имя пользователя уже занято. Пожалуйста, выберите другое.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Этот email уже зарегистрирован. Пожалуйста, используйте другой.')

# Форма входа
class LoginForm(FlaskForm):
    # Поле для email
    email = StringField('Email',
                        validators=[DataRequired(message="Это поле обязательно."),
                                    Email(message="Введите корректный email.")])
    # Поле для пароля
    password = PasswordField('Пароль', validators=[DataRequired(message="Это поле обязательно.")])
    # Галочка "Запомнить меня"
    remember_me = BooleanField('Запомнить меня')
    # Кнопка отправки формы
    submit = SubmitField('Войти')

# Добавьте это в конец файла app/forms.py

# Форма для создания новой доски
class BoardForm(FlaskForm):
    name = StringField('Название доски',
                       validators=[DataRequired(message="Название доски не может быть пустым."),
                                   Length(min=1, max=100, message="Название должно быть от 1 до 100 символов.")])
    submit = SubmitField('Создать доску')

# Добавьте это в конец файла app/forms.py

# Форма для создания новой колонки
class ColumnForm(FlaskForm):
    name = StringField('Название колонки',
                       validators=[DataRequired(message="Название колонки не может быть пустым."),
                                   Length(min=1, max=100)])
    submit_column = SubmitField('Добавить колонку') # Используем другое имя для submit, чтобы различать формы

# Форма для создания новой карточки
class CardForm(FlaskForm):
    title = StringField('Заголовок карточки',
                        validators=[DataRequired(message="Заголовок не может быть пустым."),
                                    Length(min=1, max=150)])
    # --- ДОБАВЬТЕ ЭТУ СТРОКУ ---
    description = TextAreaField('Описание', validators=[Length(max=1000)]) # Описание, не обязательное, макс. длина
    # --------------------------
    submit_card = SubmitField('Добавить/Сохранить') # Переименуем кнопку для универсальности