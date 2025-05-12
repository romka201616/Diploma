#--- START OF FILE routes.py ---

from flask import render_template, flash, redirect, url_for, request, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from app import app, db
from app.forms import LoginForm, RegistrationForm, BoardForm, ColumnForm, CardForm, InviteUserForm
from app.models import User, Board, Column, Card
from sqlalchemy import or_

# --- Helper function to populate assignee choices ---
def _populate_assignee_choices(form, board):
    """Заполняет поле assignee_id формы списком доступных пользователей."""
    eligible_users = board.get_eligible_assignees()
    # Добавляем опцию "Не назначен" со значением 0
    choices = [(0, '--- Не назначен ---')] + [(user.id, user.username) for user in eligible_users]
    form.assignee_id.choices = choices

@app.route('/')
@app.route('/index')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    # Если не аутентифицирован, index.html покажет ссылки на логин/регистрацию
    return render_template('index.html', title='Главная')


@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    form = BoardForm()
    if form.validate_on_submit():
        new_board = Board(name=form.name.data, owner=current_user)
        # Автоматически добавляем владельца в участники (хотя доступ и так есть через owner)
        # new_board.members.append(current_user) # Это необязательно, т.к. owner и так имеет доступ
        db.session.add(new_board)
        db.session.commit()
        flash(f'Доска "{new_board.name}" успешно создана!', 'success')
        return redirect(url_for('dashboard'))

    owned_boards = current_user.owned_boards.order_by(Board.id.desc()).all()
    shared_boards_list = current_user.shared_boards.order_by(Board.id.desc()).all()

    # Объединяем и убираем дубликаты
    all_boards_dict = {board.id: board for board in owned_boards}
    for board in shared_boards_list:
        if board.id not in all_boards_dict:
             all_boards_dict[board.id] = board

    # Сортируем все доски по ID для консистентного отображения
    all_user_boards = sorted(all_boards_dict.values(), key=lambda b: b.id, reverse=True)

    return render_template('dashboard.html', title='Мои доски', form=form, boards=all_user_boards)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Неверный email или пароль.', 'danger')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        flash(f'Добро пожаловать, {user.username}!', 'success')
        next_page = request.args.get('next')
        if not next_page or not next_page.startswith('/'):
            next_page = url_for('dashboard')
        return redirect(next_page)
    return render_template('login.html', title='Вход', form=form)

@app.route('/logout')
def logout():
    logout_user()
    flash('Вы успешно вышли из системы.', 'info')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Поздравляем, вы успешно зарегистрированы! Теперь вы можете войти.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Регистрация', form=form)

# --- Маршруты для ДОСОК ---
@app.route('/boards/<int:board_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_board(board_id):
    board = Board.query.get_or_404(board_id)
    # Редактировать название доски может только владелец
    if not current_user.can_delete_board(board):
        flash('У вас нет прав для редактирования названия этой доски.', 'danger')
        return redirect(url_for('view_board', board_id=board.id))

    form = BoardForm(obj=board)
    if form.validate_on_submit():
        board.name = form.name.data
        db.session.commit()
        flash('Название доски успешно обновлено!', 'success')
        return redirect(url_for('dashboard')) # или view_board
    current_name = board.name
    return render_template('edit_board.html', title='Редактировать доску', form=form, board_id=board_id, current_name=current_name)

@app.route('/boards/<int:board_id>/delete', methods=['POST'])
@login_required
def delete_board(board_id):
    board_to_delete = Board.query.get_or_404(board_id)
    if not current_user.can_delete_board(board_to_delete):
        flash('У вас нет прав для удаления этой доски.', 'danger')
        return redirect(url_for('dashboard'))

    board_name = board_to_delete.name
    # Важно: Удаление доски каскадно удалит колонки и карточки (cascade="all, delete-orphan")
    # Также нужно разорвать связи с участниками в таблице board_members
    # SQLAlchemy обычно делает это автоматически при удалении объекта из сессии,
    # если связь настроена правильно (через secondary).
    # Но для надежности можно очистить список members перед удалением.
    board_to_delete.members = [] # Очищаем связь many-to-many перед удалением доски
    db.session.delete(board_to_delete)
    db.session.commit()
    flash(f'Доска "{board_name}" удалена.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/boards/<int:board_id>', methods=['GET', 'POST'])
@login_required
def view_board(board_id):
    board = Board.query.get_or_404(board_id)
    if not current_user.can_edit_board(board): # Проверяем доступ (владелец или участник)
        flash('У вас нет доступа к этой доске.', 'danger')
        return redirect(url_for('dashboard'))

    column_form = ColumnForm()
    card_form = CardForm()
    invite_form = InviteUserForm()

    # --- Заполняем список исполнителей для формы создания карточки ---
    _populate_assignee_choices(card_form, board)
    # ---

    if request.method == 'POST':
        # Проверяем, какая кнопка была нажата (для колонок или карточек)
        # Важно: Форма создания карточки теперь обрабатывается в 'create_card'
        if column_form.validate_on_submit() and 'submit_column' in request.form:
            last_column = Column.query.filter_by(board_id=board.id).order_by(Column.position.desc()).first()
            new_position = (last_column.position + 1) if last_column else 0
            new_column = Column(name=column_form.name.data, board_id=board.id, position=new_position)
            db.session.add(new_column)
            db.session.commit()
            flash(f'Колонка "{new_column.name}" добавлена.', 'success')
            return redirect(url_for('view_board', board_id=board.id))
        # Логика приглашения обрабатывается в 'invite_to_board'
        # Логика создания карточки обрабатывается в 'create_card'

    columns = board.columns # Получаем колонки, упорядоченные по position (задано в модели)
    board_members_list = board.members.all()
    is_owner = (current_user == board.owner)

    return render_template('board.html', title=f"Доска: {board.name}", board=board,
                           columns=columns, column_form=column_form, card_form=card_form,
                           invite_form=invite_form, board_members=board_members_list, is_owner=is_owner)


# --- Маршруты для УПРАВЛЕНИЯ УЧАСТНИКАМИ ДОСКИ ---
@app.route('/boards/<int:board_id>/invite', methods=['POST'])
@login_required
def invite_to_board(board_id):
    board = Board.query.get_or_404(board_id)
    if not current_user.can_delete_board(board): # Только владелец может приглашать
        flash('Только владелец доски может приглашать участников.', 'danger')
        return redirect(url_for('view_board', board_id=board.id))

    invite_form = InviteUserForm()
    if invite_form.validate_on_submit():
        identifier = invite_form.email_or_username.data
        user_to_invite = User.query.filter(or_(User.email == identifier, User.username == identifier)).first()

        if not user_to_invite:
            flash(f'Пользователь с email/именем "{identifier}" не найден.', 'warning')
        elif user_to_invite == board.owner: # Нельзя пригласить владельца (он и так имеет доступ)
             flash('Владелец уже имеет полный доступ к доске.', 'info')
        elif user_to_invite in board.members.all():
            flash(f'Пользователь "{user_to_invite.username}" уже является участником этой доски.', 'info')
        else:
            board.members.append(user_to_invite)
            db.session.commit()
            flash(f'Пользователь "{user_to_invite.username}" успешно приглашен на доску "{board.name}".', 'success')
    else:
        for field, errors in invite_form.errors.items():
            for error in errors:
                flash(f"Ошибка в поле приглашения: {error}", 'danger')

    return redirect(url_for('view_board', board_id=board.id))

@app.route('/boards/<int:board_id>/members/<int:user_id>/remove', methods=['POST'])
@login_required
def remove_from_board(board_id, user_id):
    board = Board.query.get_or_404(board_id)
    user_to_remove = User.query.get_or_404(user_id)

    # Удалять может только владелец ИЛИ сам пользователь может покинуть доску
    can_remove = False
    if current_user.can_delete_board(board): # Владелец может удалять кого угодно (кроме себя)
        if user_to_remove != current_user:
            can_remove = True
        else:
             flash('Владелец не может удалить себя из участников. Для передачи прав нужна другая логика.', 'warning')
    elif current_user == user_to_remove: # Сам пользователь покидает доску
        can_remove = True
    else: # Другой участник не может удалять
        flash('У вас нет прав для удаления этого участника.', 'danger')
        return redirect(url_for('view_board', board_id=board.id))

    if can_remove:
        if user_to_remove in board.members:
            board.members.remove(user_to_remove)
            db.session.commit()
            flash(f'Пользователь "{user_to_remove.username}" удален с доски "{board.name}".', 'success')
        else:
            # Эта проверка нужна, если пользователь является владельцем, но не в 'members'
            if user_to_remove == board.owner:
                 flash(f'Пользователь "{user_to_remove.username}" является владельцем и не может быть удален как участник.', 'info')
            else:
                flash(f'Пользователь "{user_to_remove.username}" не найден среди участников этой доски.', 'info')

    return redirect(url_for('view_board', board_id=board.id))


# --- Маршруты для КОЛОНОК ---
@app.route('/columns/<int:column_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_column(column_id):
    column = Column.query.get_or_404(column_id)
    board = column.board
    if not current_user.can_edit_board(board): # Проверяем доступ
        flash('Нет прав для редактирования элементов этой доски.', 'danger')
        return redirect(url_for('view_board', board_id=board.id))

    form = ColumnForm(obj=column)
    if form.validate_on_submit():
        column.name = form.name.data
        db.session.commit()
        flash('Название колонки обновлено.', 'success')
        return redirect(url_for('view_board', board_id=board.id))
    current_name = column.name
    return render_template('edit_column.html', title='Редактировать колонку', form=form, column_id=column_id, board_id=board.id, current_name=current_name)

@app.route('/columns/<int:column_id>/delete', methods=['POST'])
@login_required
def delete_column(column_id):
    column_to_delete = Column.query.get_or_404(column_id)
    board = column_to_delete.board
    if not current_user.can_edit_board(board): # Проверяем доступ
        flash('У вас нет прав для удаления элементов этой доски.', 'danger')
        return redirect(url_for('view_board', board_id=board.id))

    column_name = column_to_delete.name
    # Удаление колонки каскадно удалит все карточки в ней (cascade="all, delete-orphan")
    db.session.delete(column_to_delete)
    db.session.commit()
    flash(f'Колонка "{column_name}" удалена.', 'success')
    return redirect(url_for('view_board', board_id=board.id))

# --- Маршруты для КАРТОЧЕК ---
@app.route('/columns/<int:column_id>/cards/create', methods=['POST'])
@login_required
def create_card(column_id):
    column = Column.query.get_or_404(column_id)
    board = column.board
    if not current_user.can_edit_board(board): # Проверяем доступ
        flash('У вас нет прав для добавления карточек на эту доску.', 'danger')
        return redirect(url_for('view_board', board_id=board.id))

    card_form = CardForm()
    # --- Заполняем список исполнителей ПЕРЕД валидацией ---
    _populate_assignee_choices(card_form, board)
    # ---

    if card_form.validate_on_submit():
        # Получаем ID исполнителя, если он выбран (и не равен 0)
        selected_assignee_id = card_form.assignee_id.data
        assignee_id_to_save = selected_assignee_id if selected_assignee_id != 0 else None

        new_card = Card(
            title=card_form.title.data,
            description=card_form.description.data,
            column_id=column.id,
            assignee_id=assignee_id_to_save # Сохраняем ID исполнителя (или None)
        )
        db.session.add(new_card)
        db.session.commit()
        flash(f'Карточка "{new_card.title}" добавлена в колонку "{column.name}".', 'success')
    else:
        # Если форма не прошла валидацию, показываем ошибки
        for field, errors in card_form.errors.items():
            # Исключаем assignee_id из общих ошибок, если проблема была только в выборе
            if field != 'assignee_id':
                 for error in errors:
                     flash(f"Ошибка в поле '{getattr(card_form, field).label.text}': {error}", 'danger')
            # Можно добавить отдельную логику для ошибок assignee_id, если они возможны
            # (например, если значение было подделано и не входит в choices),
            # но стандартные валидаторы WTForms должны это покрыть.

    return redirect(url_for('view_board', board_id=board.id))


@app.route('/cards/<int:card_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_card(card_id):
    card = Card.query.get_or_404(card_id)
    column = card.column
    board = column.board
    if not current_user.can_edit_board(board): # Проверяем доступ
        flash('Нет прав для редактирования карточек на этой доске.', 'danger')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(success=False, error='Нет прав'), 403
        # Редирект на страницу доски, если это не AJAX запрос
        return redirect(url_for('view_board', board_id=board.id))

    # Создаем форму. Если GET, заполняем из объекта card. Если POST, из request.form.
    form = CardForm(obj=card if request.method == 'GET' else None)
    # --- Заполняем список исполнителей и устанавливаем текущее значение ---
    _populate_assignee_choices(form, board)
    if request.method == 'GET':
        form.assignee_id.data = card.assignee_id or 0 # Устанавливаем текущего исполнителя (или 0 для 'Не назначен')
    # ---

    if form.validate_on_submit():
        card.title = form.title.data
        card.description = form.description.data
        # Обрабатываем ID исполнителя
        selected_assignee_id = form.assignee_id.data
        card.assignee_id = selected_assignee_id if selected_assignee_id != 0 else None

        db.session.commit()
        flash('Карточка обновлена.', 'success')

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Если это AJAX запрос (из модального окна), возвращаем JSON
            assignee_data = None
            if card.assignee:
                assignee_data = {'id': card.assignee.id, 'username': card.assignee.username}
            return jsonify(success=True, card={
                'id': card.id,
                'title': card.title,
                'description': card.description,
                'assignee': assignee_data # Добавляем информацию об исполнителе
            })
        # Если обычный POST (из отдельной страницы редактирования), редирект
        return redirect(url_for('view_board', board_id=board.id))

    # Если GET запрос или форма не прошла валидацию (для не-AJAX случая)
    if request.method == 'GET':
        # Отображаем страницу редактирования (если используется отдельная страница)
        current_title = card.title # Для заголовка страницы
        return render_template('edit_card.html', title='Редактировать карточку', form=form, card_id=card_id, board_id=board.id, current_title=current_title)

    # Если POST запрос не прошел валидацию (для AJAX)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        errors = {field: error[0] for field, error in form.errors.items()}
        return jsonify(success=False, errors=errors), 400

    # Если POST не прошел валидацию и это не AJAX (возврат на страницу редактирования)
    current_title = form.title.data or card.title # Показать введенное или старое название
    flash('Пожалуйста, исправьте ошибки в форме.', 'danger')
    return render_template('edit_card.html', title='Редактировать карточку', form=form, card_id=card_id, board_id=board.id, current_title=current_title)


@app.route('/cards/<int:card_id>/delete', methods=['POST'])
@login_required
def delete_card(card_id):
    card_to_delete = Card.query.get_or_404(card_id)
    column = card_to_delete.column
    board = column.board
    if not current_user.can_edit_board(board): # Проверяем доступ
        flash('У вас нет прав для удаления карточек на этой доске.', 'danger')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(success=False, error='Нет прав'), 403
        return redirect(url_for('view_board', board_id=board.id))

    card_title = card_to_delete.title
    db.session.delete(card_to_delete)
    db.session.commit()
    flash(f'Карточка "{card_title}" удалена.', 'success')
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Возвращаем JSON для AJAX запроса (из модального окна)
        return jsonify(success=True, message=f'Карточка "{card_title}" удалена.')
    # Обычный редирект, если удаление было не из модального окна
    return redirect(url_for('view_board', board_id=board.id))

# --- API маршрут для перемещения карточек ---
@app.route('/api/cards/<int:card_id>/move', methods=['POST'])
@login_required
def move_card(card_id):
    card = Card.query.get_or_404(card_id)
    board = card.column.board

    if not current_user.can_edit_board(board): # Проверяем доступ
        return jsonify(success=False, error="Нет прав для изменения этой карточки."), 403

    data = request.get_json()
    if not data or 'new_column_id' not in data:
        return jsonify(success=False, error="Отсутствует ID новой колонки."), 400

    new_column_id = data.get('new_column_id')
    new_column = Column.query.get(new_column_id)

    # Проверяем, что новая колонка существует и принадлежит той же доске
    if not new_column or new_column.board_id != board.id:
        return jsonify(success=False, error="Некорректный ID новой колонки."), 400

    if card.column_id != new_column_id:
        old_column_id = card.column_id
        card.column_id = new_column_id
        db.session.commit()
        # Можно добавить логирование или доп. действия
        return jsonify(success=True, message="Карточка перемещена.")
    else:
        # Карточка осталась в той же колонке (например, изменился только порядок)
        # В текущей реализации мы не сохраняем порядок внутри колонки
        return jsonify(success=True, message="Карточка осталась в той же колонке.")

#--- END OF FILE routes.py ---