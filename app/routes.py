from flask import render_template, flash, redirect, url_for, request, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from app import app, db
from app.forms import LoginForm, RegistrationForm, BoardForm, ColumnForm, CardForm, InviteUserForm # Добавили InviteUserForm
from app.models import User, Board, Column, Card # Модели уже импортированы
from sqlalchemy import or_ # Для запроса по email или username

@app.route('/')
@app.route('/index')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    form = BoardForm()
    if form.validate_on_submit():
        new_board = Board(name=form.name.data, owner=current_user)
        db.session.add(new_board)
        db.session.commit()
        flash(f'Доска "{new_board.name}" успешно создана!', 'success')
        return redirect(url_for('dashboard'))
    
    owned_boards = current_user.owned_boards.order_by(Board.id.desc()).all()
    shared_boards_list = current_user.shared_boards.order_by(Board.id.desc()).all()
    
    # Объединяем и убираем дубликаты, если пользователь является и владельцем и участником (хотя это не должно происходить)
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
    if not current_user.can_delete_board(board): # can_delete_board проверяет, что current_user == board.owner
        flash('У вас нет прав для редактирования названия этой доски.', 'danger')
        return redirect(url_for('view_board', board_id=board.id)) # или dashboard
    
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
    db.session.delete(board_to_delete)
    db.session.commit()
    flash(f'Доска "{board_name}" удалена.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/boards/<int:board_id>', methods=['GET', 'POST'])
@login_required
def view_board(board_id):
    board = Board.query.get_or_404(board_id)
    if not current_user.can_edit_board(board): # Проверяем, владелец ли или участник
        flash('У вас нет доступа к этой доске.', 'danger')
        return redirect(url_for('dashboard'))

    column_form = ColumnForm()
    card_form = CardForm()
    invite_form = InviteUserForm() # Форма для приглашения

    if request.method == 'POST':
        if column_form.validate_on_submit() and 'submit_column' in request.form:
            last_column = Column.query.filter_by(board_id=board.id).order_by(Column.position.desc()).first()
            new_position = (last_column.position + 1) if last_column else 0
            new_column = Column(name=column_form.name.data, board_id=board.id, position=new_position)
            db.session.add(new_column)
            db.session.commit()
            flash(f'Колонка "{new_column.name}" добавлена.', 'success')
            return redirect(url_for('view_board', board_id=board.id))
        
        # Обработка формы приглашения (будет добавлена ниже в отдельном маршруте, но можно и здесь)
        # Этот блок пока закомментирован, так как приглашение будет через свой маршрут
        # if invite_form.validate_on_submit() and 'submit_invite' in request.form:
        #     pass # логика приглашения

    columns = board.columns
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
        elif user_to_invite == current_user:
            flash('Вы не можете пригласить самого себя.', 'info')
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
    if not current_user.can_delete_board(board): # Только владелец может удалять
        flash('Только владелец доски может удалять участников.', 'danger')
        return redirect(url_for('view_board', board_id=board.id))

    user_to_remove = User.query.get_or_404(user_id)
    if user_to_remove == current_user: # Владелец не может удалить сам себя как участника
        flash('Владелец не может быть удален из участников.', 'warning')
    elif user_to_remove in board.members:
        board.members.remove(user_to_remove)
        db.session.commit()
        flash(f'Пользователь "{user_to_remove.username}" удален с доски "{board.name}".', 'success')
    else:
        flash(f'Пользователь "{user_to_remove.username}" не является участником этой доски.', 'info')
    
    return redirect(url_for('view_board', board_id=board.id))


# --- Маршруты для КОЛОНОК ---
@app.route('/columns/<int:column_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_column(column_id):
    column = Column.query.get_or_404(column_id)
    board = column.board
    if not current_user.can_edit_board(board): # Проверяем, владелец ли или участник
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
    if not current_user.can_edit_board(board): # Проверяем, владелец ли или участник
        flash('У вас нет прав для удаления элементов этой доски.', 'danger')
        return redirect(url_for('view_board', board_id=board.id))
    
    column_name = column_to_delete.name
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
    if not current_user.can_edit_board(board): # Проверяем, владелец ли или участник
        flash('У вас нет прав для добавления карточек на эту доску.', 'danger')
        return redirect(url_for('view_board', board_id=board.id))
    
    card_form = CardForm()
    if card_form.validate_on_submit():
        new_card = Card(title=card_form.title.data, description=card_form.description.data, column_id=column.id)
        db.session.add(new_card)
        db.session.commit()
        flash(f'Карточка "{new_card.title}" добавлена в колонку "{column.name}".', 'success')
    else:
        for field, errors in card_form.errors.items():
            for error in errors:
                flash(f"Ошибка в поле '{getattr(card_form, field).label.text}': {error}", 'danger')
    return redirect(url_for('view_board', board_id=board.id))

@app.route('/cards/<int:card_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_card(card_id):
    card = Card.query.get_or_404(card_id)
    column = card.column
    board = column.board
    if not current_user.can_edit_board(board): # Проверяем, владелец ли или участник
        flash('Нет прав для редактирования карточек на этой доске.', 'danger')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(success=False, error='Нет прав'), 403
        return redirect(url_for('view_board', board_id=board.id))

    form = CardForm(obj=card if request.method == 'GET' else None)
    if form.validate_on_submit():
        card.title = form.title.data
        card.description = form.description.data
        db.session.commit()
        flash('Карточка обновлена.', 'success')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(success=True, card={'id': card.id, 'title': card.title, 'description': card.description})
        return redirect(url_for('view_board', board_id=board.id))
    
    if request.method == 'GET':
        current_title = card.title
        return render_template('edit_card.html', title='Редактировать карточку', form=form, card_id=card_id, board_id=board.id, current_title=current_title)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest': # Ошибки валидации для AJAX
        errors = {field: error[0] for field, error in form.errors.items()}
        return jsonify(success=False, errors=errors), 400
    
    current_title = card.title
    return render_template('edit_card.html', title='Редактировать карточку', form=form, card_id=card_id, board_id=board.id, current_title=current_title)


@app.route('/cards/<int:card_id>/delete', methods=['POST'])
@login_required
def delete_card(card_id):
    card_to_delete = Card.query.get_or_404(card_id)
    column = card_to_delete.column
    board = column.board
    if not current_user.can_edit_board(board): # Проверяем, владелец ли или участник
        flash('У вас нет прав для удаления карточек на этой доске.', 'danger')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(success=False, error='Нет прав'), 403
        return redirect(url_for('view_board', board_id=board.id))
    
    card_title = card_to_delete.title
    db.session.delete(card_to_delete)
    db.session.commit()
    flash(f'Карточка "{card_title}" удалена.', 'success')
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify(success=True)
    return redirect(url_for('view_board', board_id=board.id))

# --- API маршрут для перемещения карточек ---
@app.route('/api/cards/<int:card_id>/move', methods=['POST'])
@login_required
def move_card(card_id):
    card = Card.query.get_or_404(card_id)
    board = card.column.board

    if not current_user.can_edit_board(board): # Проверяем, владелец ли или участник
        return jsonify(success=False, error="Нет прав для изменения этой карточки."), 403

    data = request.get_json()
    if not data or 'new_column_id' not in data:
        return jsonify(success=False, error="Отсутствует ID новой колонки."), 400

    new_column_id = data.get('new_column_id')
    new_column = Column.query.get(new_column_id)

    if not new_column or new_column.board_id != board.id: # Проверяем, что новая колонка принадлежит той же доске
        return jsonify(success=False, error="Некорректный ID новой колонки."), 400

    if card.column_id != new_column_id:
        card.column_id = new_column_id
        db.session.commit()
        return jsonify(success=True, message="Карточка перемещена.")
    
    return jsonify(success=True, message="Карточка осталась в той же колонке.")