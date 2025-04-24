# Убедитесь, что эти импорты есть, добавьте недостающие:
from flask import render_template, flash, redirect, url_for, request
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from app import app, db
from app.forms import LoginForm, RegistrationForm, BoardForm, ColumnForm, CardForm # Добавили ColumnForm, CardForm
from app.models import User, Board, Column, Card # Добавили Column, Card

# Маршрут для главной страницы (пока просто редирект на логин или дашборд)
@app.route('/')
@app.route('/index')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard')) # Если вошел, перенаправляем на дашборд
    return redirect(url_for('login')) # Если не вошел, перенаправляем на логин

# Маршрут для панели управления (доступ только для вошедших)
# Маршрут для панели управления (ОБНОВЛЕННЫЙ)
# Теперь обрабатывает и GET, и POST запросы
@app.route('/dashboard', methods=['GET', 'POST'])
@login_required # Доступ только для вошедших
def dashboard():
    form = BoardForm() # Создаем экземпляр формы для создания доски

    # Обработка POST-запроса (когда пользователь нажал "Создать доску")
    if form.validate_on_submit():
        # Создаем новую доску в базе данных
        new_board = Board(name=form.name.data, owner=current_user) # Связываем с текущим пользователем (owner)
        db.session.add(new_board)
        db.session.commit()
        flash(f'Доска "{new_board.name}" успешно создана!', 'success')
        return redirect(url_for('dashboard')) # Перенаправляем на эту же страницу, чтобы избежать повторной отправки формы

    # Обработка GET-запроса (когда пользователь просто открыл страницу)
    # Получаем все доски, принадлежащие текущему пользователю
    user_boards = Board.query.filter_by(user_id=current_user.id).order_by(Board.id.desc()).all() # Сортируем по ID в обратном порядке (новые сверху)

    # Отображаем шаблон dashboard.html, передавая в него:
    # - Заголовок страницы
    # - Форму для создания доски
    # - Список досок пользователя
    return render_template('dashboard.html',
                           title='Мои доски',
                           form=form,
                           boards=user_boards)

# Новый маршрут для удаления доски (используем POST для безопасности)
@app.route('/boards/<int:board_id>/delete', methods=['POST'])
@login_required
def delete_board(board_id):
    # Ищем доску по ID
    board_to_delete = Board.query.get_or_404(board_id) # get_or_404 вернет 404, если доска не найдена

    # Проверяем, является ли текущий пользователь владельцем доски
    if board_to_delete.owner != current_user:
        flash('У вас нет прав для удаления этой доски.', 'danger')
        # В реальном приложении здесь может быть редирект на 'dashboard' или показ ошибки 403 (Forbidden)
        # from flask import abort
        # abort(403)
        return redirect(url_for('dashboard')) # Пока просто вернем на дашборд

    # Удаляем доску из базы данных
    board_name = board_to_delete.name # Сохраняем имя для сообщения
    db.session.delete(board_to_delete)
    db.session.commit()
    flash(f'Доска "{board_name}" удалена.', 'success')
    return redirect(url_for('dashboard')) # Возвращаемся на панель управления

# Добавьте эту функцию в app/routes.py

# Маршрут для просмотра конкретной доски (ОБНОВЛЕННЫЙ)
@app.route('/boards/<int:board_id>', methods=['GET', 'POST']) # Разрешаем POST для формы создания колонки
@login_required
def view_board(board_id):
    board = Board.query.get_or_404(board_id)
    if board.owner != current_user:
        flash('У вас нет доступа к этой доске.', 'danger')
        return redirect(url_for('dashboard'))

    column_form = ColumnForm() # Форма для создания колонки
    card_form = CardForm()     # Форма для создания карточки (будет использоваться в шаблоне)

    # Обработка создания НОВОЙ КОЛОНКИ (если отправлена форма колонки)
    # Мы проверяем имя кнопки, чтобы отличить от формы карточки, если бы обе отправлялись на этот же URL
    # В нашем случае форма колонки отправляется сюда, а форма карточки - на другой URL,
    # но проверка validate_on_submit() сработает только для column_form, если она была отправлена.
    if column_form.validate_on_submit() and 'submit_column' in request.form:
         # Определяем следующую позицию для колонки
        last_column = Column.query.filter_by(board_id=board.id).order_by(Column.position.desc()).first()
        new_position = (last_column.position + 1) if last_column else 0

        new_column = Column(name=column_form.name.data, board_id=board.id, position=new_position)
        db.session.add(new_column)
        db.session.commit()
        flash(f'Колонка "{new_column.name}" добавлена.', 'success')
        # Важно сделать редирект, чтобы избежать повторной отправки формы при обновлении страницы
        return redirect(url_for('view_board', board_id=board.id))

    # Получаем все колонки этой доски, отсортированные по позиции
    # Модель уже настроена на сортировку (`order_by='Column.position'` в Board.columns),
    # но для ясности можно добавить .order_by() и здесь.
    columns = board.columns # Это уже отсортированный список благодаря настройке в models.py

    # Собираем карточки для каждой колонки.
    # Так как у нас lazy='dynamic' в Column.cards, нужно выполнить запрос для каждой колонки.
    # Мы передадим `columns` в шаблон, а уже там будем получать `column.cards.all()`
    # Или можно подготовить данные здесь, если становится сложнее:
    # columns_with_cards = []
    # for col in columns:
    #     cards = col.cards.order_by(Card.id.asc()).all() # Получаем карточки для колонки
    #     columns_with_cards.append({'column': col, 'cards': cards})
    # Но для начала оставим простой вариант: передадим `columns` и `card_form`.

    return render_template('board.html',
                           title=f"Доска: {board.name}",
                           board=board,
                           columns=columns, # Передаем список объектов колонок
                           column_form=column_form, # Передаем форму для создания колонки
                           card_form=card_form)     # Передаем форму для создания карточки

# ----- Маршруты для КОЛОНОК -----

@app.route('/columns/<int:column_id>/delete', methods=['POST'])
@login_required
def delete_column(column_id):
    column_to_delete = Column.query.get_or_404(column_id)
    board = column_to_delete.board # Получаем родительскую доску

    # Проверка прав: пользователь должен быть владельцем доски
    if board.owner != current_user:
        flash('У вас нет прав для удаления этой колонки.', 'danger')
        return redirect(url_for('dashboard')) # Или на доску, если хотим

    # Удаляем колонку (связанные карточки удалятся каскадно благодаря настройке в models.py)
    column_name = column_to_delete.name
    db.session.delete(column_to_delete)
    db.session.commit()
    flash(f'Колонка "{column_name}" удалена.', 'success')
    return redirect(url_for('view_board', board_id=board.id)) # Возвращаемся на страницу доски

@app.route('/columns/<int:column_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_column(column_id):
    column = Column.query.get_or_404(column_id)
    board = column.board
    if board.owner != current_user:
        flash('Нет прав для редактирования этой колонки.', 'danger')
        return redirect(url_for('view_board', board_id=board.id))

    # Используем ColumnForm, предзаполняем
    form = ColumnForm(obj=column)

    if form.validate_on_submit():
        column.name = form.name.data
        db.session.commit()
        flash('Название колонки обновлено.', 'success')
        return redirect(url_for('view_board', board_id=board.id))

    current_name = column.name
    return render_template('edit_column.html', title='Редактировать колонку', form=form, column_id=column_id, board_id=board.id, current_name=current_name)

@app.route('/boards/<int:board_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_board(board_id):
    board = Board.query.get_or_404(board_id)
    # Проверка прав
    if board.owner != current_user:
        flash('У вас нет прав для редактирования этой доски.', 'danger')
        return redirect(url_for('dashboard'))

    # Используем ту же форму BoardForm, но предзаполняем ее текущим названием
    form = BoardForm(obj=board) # obj=board автоматически заполнит поле 'name' значением board.name

    if form.validate_on_submit():
        # Обновляем данные доски из формы
        board.name = form.name.data
        db.session.commit() # Сохраняем изменения в БД
        flash('Название доски успешно обновлено!', 'success')
        return redirect(url_for('dashboard')) # Возвращаемся на панель управления

    # Если GET-запрос или форма не валидна, показываем шаблон с формой
    # Передаем текущее название для отображения в заголовке или где-то еще
    current_name = board.name
    return render_template('edit_board.html', title='Редактировать доску', form=form, board_id=board_id, current_name=current_name)

# ----- Маршруты для КАРТОЧЕК -----

@app.route('/columns/<int:column_id>/cards/create', methods=['POST'])
@login_required
def create_card(column_id):
    column = Column.query.get_or_404(column_id)
    board = column.board

    # Проверка прав
    if board.owner != current_user:
        flash('У вас нет прав для добавления карточек в эту колонку.', 'danger')
        return redirect(url_for('dashboard'))

    # Используем ту же форму CardForm
    card_form = CardForm() # Создаем экземпляр формы

    # Валидируем форму (она была отправлена на этот URL из шаблона board.html)
    if card_form.validate_on_submit() and 'submit_card' in request.form:
        new_card = Card(title=card_form.title.data, column_id=column.id)
        db.session.add(new_card)
        db.session.commit()
        flash(f'Карточка "{new_card.title}" добавлена в колонку "{column.name}".', 'success')
    else:
        # Если форма не валидна (например, пустое название)
        # Собрать ошибки и показать их
        for field, errors in card_form.errors.items():
             for error in errors:
                 flash(f"Ошибка в поле '{getattr(card_form, field).label.text}': {error}", 'danger')

    # Всегда возвращаемся на страницу доски
    return redirect(url_for('view_board', board_id=board.id))

@app.route('/cards/<int:card_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_card(card_id):
    card = Card.query.get_or_404(card_id)
    column = card.column
    board = column.board
    if board.owner != current_user:
        flash('Нет прав для редактирования этой карточки.', 'danger')
        return redirect(url_for('view_board', board_id=board.id))

    # Используем CardForm, предзаполняем
    form = CardForm(obj=card) # Заполнит title и description

    if form.validate_on_submit():
        card.title = form.title.data
        card.description = form.description.data # Сохраняем описание
        db.session.commit()
        flash('Карточка обновлена.', 'success')
        return redirect(url_for('view_board', board_id=board.id))

    current_title = card.title
    return render_template('edit_card.html', title='Редактировать карточку', form=form, card_id=card_id, board_id=board.id, current_title=current_title)

@app.route('/cards/<int:card_id>/delete', methods=['POST'])
@login_required
def delete_card(card_id):
    card_to_delete = Card.query.get_or_404(card_id)
    column = card_to_delete.column
    board = column.board

    # Проверка прав
    if board.owner != current_user:
        flash('У вас нет прав для удаления этой карточки.', 'danger')
        return redirect(url_for('dashboard'))

    card_title = card_to_delete.title
    db.session.delete(card_to_delete)
    db.session.commit()
    flash(f'Карточка "{card_title}" удалена.', 'success')
    return redirect(url_for('view_board', board_id=board.id))

# (Опционально) Маршрут для редактирования карточки можно добавить позже
# @app.route('/cards/<int:card_id>/edit', methods=['GET', 'POST'])
# ...

# (Опционально) Маршрут для перемещения карточки можно добавить позже (сложнее)
# @app.route('/cards/<int:card_id>/move/<int:new_column_id>', methods=['POST'])
# ...

# Маршрут для страницы входа
@app.route('/login', methods=['GET', 'POST']) # Разрешаем методы GET (показать форму) и POST (отправить форму)
def login():
    # Если пользователь уже вошел, перенаправляем его на дашборд
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    form = LoginForm() # Создаем экземпляр формы входа
    # Если форма отправлена (POST) и прошла валидацию
    if form.validate_on_submit():
        # Ищем пользователя в базе по введенному email
        user = User.query.filter_by(email=form.email.data).first()
        # Если пользователь не найден ИЛИ пароль неверный
        if user is None or not user.check_password(form.password.data):
            flash('Неверный email или пароль.', 'danger') # Показываем сообщение об ошибке (категория danger для красного цвета в Bootstrap)
            return redirect(url_for('login')) # Перенаправляем обратно на страницу входа
        # Если пользователь найден и пароль верный - логиним его
        login_user(user, remember=form.remember_me.data) # Функция Flask-Login для входа
        flash(f'Добро пожаловать, {user.username}!', 'success') # Сообщение об успехе

        # Перенаправляем на страницу, на которую пользователь пытался попасть до логина,
        # или на дашборд, если он пришел сразу на страницу логина
        next_page = request.args.get('next')
        if not next_page or not next_page.startswith('/'):
            next_page = url_for('dashboard')
        return redirect(next_page)

    # Если это GET-запрос (просто открыли страницу) или форма не прошла валидацию,
    # отображаем шаблон login.html, передавая в него форму
    return render_template('login.html', title='Вход', form=form)

# Маршрут для выхода
@app.route('/logout')
def logout():
    logout_user() # Функция Flask-Login для выхода
    flash('Вы успешно вышли из системы.', 'info')
    return redirect(url_for('login')) # Перенаправляем на страницу входа

# Маршрут для страницы регистрации
@app.route('/register', methods=['GET', 'POST'])
def register():
    # Если пользователь уже вошел, перенаправляем его на дашборд
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    form = RegistrationForm() # Создаем экземпляр формы регистрации
    if form.validate_on_submit(): # Если форма отправлена (POST) и валидна (включая наши проверки уникальности)
        # Создаем нового пользователя
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data) # Устанавливаем хеш пароля
        db.session.add(user) # Добавляем пользователя в сессию базы данных
        db.session.commit() # Сохраняем изменения в базе данных
        flash('Поздравляем, вы успешно зарегистрированы! Теперь вы можете войти.', 'success')
        return redirect(url_for('login')) # Перенаправляем на страницу входа

    # Если GET-запрос или форма не валидна, отображаем шаблон регистрации
    return render_template('register.html', title='Регистрация', form=form)