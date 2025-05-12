# app/routes.py

from flask import render_template, flash, redirect, url_for, request, jsonify, abort
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from app import app, db
from app.forms import (
    LoginForm, RegistrationForm, BoardForm, ColumnForm, CardForm, InviteUserForm,
    UpdateAccountForm, ChangePasswordForm, UpdateAvatarForm, AdminEditUserForm
)
from app.models import User, Board, Column, Card
from sqlalchemy import or_
import os
from functools import wraps
from wtforms import SelectField, SelectMultipleField # Импорт остается

# --- Декоратор для проверки прав администратора ---
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Доступ запрещен. У вас нет прав администратора.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# --- Helper function to populate assignee choices ---
def _populate_assignee_choices(form, board):
    """Заполняет поле(я) выбора исполнителя(ей) в форме."""
    eligible_users = board.get_eligible_assignees()
    choices_for_single = [(0, '--- Не назначен ---')] + [(user.id, user.username) for user in eligible_users]
    choices_for_multiple = [(user.id, user.username) for user in eligible_users]

    # Для SelectField (одиночный выбор)
    if hasattr(form, 'assignee_id') and isinstance(form.assignee_id, SelectField): # Проверяем сам объект form.assignee_id
        form.assignee_id.choices = choices_for_single
    # Для SelectMultipleField (множественный выбор, будет использоваться позже)
    # elif hasattr(form, 'assignees') and isinstance(form.assignees, SelectMultipleField): # Проверяем сам объект form.assignees
    #     form.assignees.choices = choices_for_multiple


@app.route('/')
@app.route('/index')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html', title='Главная')


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

    all_boards_dict = {board.id: board for board in owned_boards}
    for board in shared_boards_list:
        if board.id not in all_boards_dict:
             all_boards_dict[board.id] = board
    all_user_boards = sorted(all_boards_dict.values(), key=lambda b: b.id, reverse=True)

    return render_template('dashboard.html', title='Мои доски', form=form, boards=all_user_boards)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
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
            if current_user.is_admin:
                 next_page = url_for('admin_dashboard')
            else:
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
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Поздравляем, вы успешно зарегистрированы! Теперь вы можете войти.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Регистрация', form=form)

@app.route('/profile', methods=['GET'])
@login_required
def profile():
    update_account_form = UpdateAccountForm(obj=current_user)
    if request.method == 'GET':
        update_account_form.username.data = current_user.username
        update_account_form.email.data = current_user.email
        
    change_password_form = ChangePasswordForm()
    update_avatar_form = UpdateAvatarForm()
    return render_template('profile.html', title='Мой профиль',
                           update_account_form=update_account_form,
                           change_password_form=change_password_form,
                           update_avatar_form=update_avatar_form)

@app.route('/profile/edit_account', methods=['POST'])
@login_required
def edit_account():
    form = UpdateAccountForm() 
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Данные профиля успешно обновлены.', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Ошибка обновления профиля ({getattr(form, field).label.text}): {error}", 'danger')
    return redirect(url_for('profile'))


@app.route('/profile/change_password', methods=['POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        current_user.set_password(form.new_password.data)
        db.session.commit()
        flash('Пароль успешно изменен.', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                if field == 'current_password' and form.current_password.errors:
                     flash(form.current_password.errors[0], 'danger') 
                else:
                    flash(f"Ошибка смены пароля ({getattr(form, field).label.text}): {error}", 'danger')
    return redirect(url_for('profile'))

@app.route('/profile/update_avatar', methods=['POST'])
@login_required
def update_avatar():
    form = UpdateAvatarForm()
    if form.validate_on_submit():
        file = form.avatar.data
        filename = secure_filename(file.filename)
        _, f_ext = os.path.splitext(filename)
        if not f_ext: 
            flash('Файл должен иметь расширение (например, .jpg, .png).', 'warning')
            return redirect(url_for('profile'))
            
        avatar_fn = f"user_{current_user.id}{f_ext.lower()}"
        
        if current_user.avatar_url and current_user.avatar_url != 'default_avatar.png':
            try:
                old_avatar_path = os.path.join(app.config['UPLOADED_AVATARS_DEST'], current_user.avatar_url)
                if os.path.exists(old_avatar_path):
                    os.remove(old_avatar_path)
            except Exception as e:
                app.logger.error(f"Error deleting old avatar: {e}")

        file_path = os.path.join(app.config['UPLOADED_AVATARS_DEST'], avatar_fn)
        try:
            file.save(file_path)
            current_user.avatar_url = avatar_fn
            db.session.commit()
            flash('Аватар успешно обновлен.', 'success')
        except Exception as e:
            app.logger.error(f"Error saving avatar: {e}")
            flash('Не удалось сохранить аватар. Попробуйте еще раз.', 'danger')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Ошибка загрузки аватара: {error}", 'danger')
    return redirect(url_for('profile'))


@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    users = User.query.order_by(User.id).all()
    return render_template('admin_dashboard.html', title='Панель администратора', users=users)

@app.route('/admin/user/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_edit_user(user_id):
    user_to_edit = User.query.get_or_404(user_id)
    form = AdminEditUserForm(original_username=user_to_edit.username, obj=user_to_edit if request.method == 'GET' else None)

    if form.validate_on_submit():
        if user_to_edit == current_user and not form.is_admin.data:
            admins_count = User.query.filter_by(is_admin=True).count()
            if admins_count <= 1:
                flash('Вы не можете снять с себя права администратора, если вы единственный администратор.', 'warning')
                return redirect(url_for('admin_edit_user', user_id=user_id))
        
        user_to_edit.username = form.username.data
        user_to_edit.is_admin = form.is_admin.data
        db.session.commit()
        flash(f'Данные пользователя {user_to_edit.username} обновлены.', 'success')
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'GET': 
        form.username.data = user_to_edit.username
        form.is_admin.data = user_to_edit.is_admin
    form.email.data = user_to_edit.email 
    
    return render_template('admin_edit_user.html', title=f'Редактировать пользователя: {user_to_edit.username}',
                           form=form, user_to_edit=user_to_edit)

@app.route('/admin/user/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def admin_delete_user(user_id):
    user_to_delete = User.query.get_or_404(user_id)
    if user_to_delete == current_user:
        flash('Вы не можете удалить свой собственный аккаунт из панели администратора.', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    if user_to_delete.owned_boards.count() > 0:
        flash(f'Нельзя удалить пользователя {user_to_delete.username}, так как он владеет досками. Сначала удалите или переназначьте его доски.', 'warning')
        return redirect(url_for('admin_dashboard'))

    for board in list(user_to_delete.shared_boards): 
        board.members.remove(user_to_delete)
    
    for card in list(user_to_delete.assigned_cards): 
        card.assignee_id = None
    
    username = user_to_delete.username
    db.session.delete(user_to_delete)
    db.session.commit()
    flash(f'Пользователь {username} удален.', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/boards/<int:board_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_board(board_id):
    board = Board.query.get_or_404(board_id)
    if not current_user.can_delete_board(board):
        flash('У вас нет прав для редактирования названия этой доски.', 'danger')
        return redirect(url_for('view_board', board_id=board.id))

    form = BoardForm(obj=board)
    if form.validate_on_submit():
        board.name = form.name.data
        db.session.commit()
        flash('Название доски успешно обновлено!', 'success')
        return redirect(url_for('dashboard'))
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
    board_to_delete.members = []
    db.session.delete(board_to_delete)
    db.session.commit()
    flash(f'Доска "{board_name}" удалена.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/boards/<int:board_id>', methods=['GET', 'POST'])
@login_required
def view_board(board_id):
    board = Board.query.get_or_404(board_id)
    if not current_user.can_edit_board(board):
        flash('У вас нет доступа к этой доске.', 'danger')
        return redirect(url_for('dashboard'))

    column_form = ColumnForm()
    card_form = CardForm() 
    invite_form = InviteUserForm()

    _populate_assignee_choices(card_form, board) # Заполняем choices для селекта в card_form

    if request.method == 'POST': 
        if column_form.validate_on_submit() and 'submit_column' in request.form: 
            last_column = Column.query.filter_by(board_id=board.id).order_by(Column.position.desc()).first()
            new_position = (last_column.position + 1) if last_column else 0
            new_column = Column(name=column_form.name.data, board_id=board.id, position=new_position)
            db.session.add(new_column)
            db.session.commit()
            flash(f'Колонка "{new_column.name}" добавлена.', 'success')
            return redirect(url_for('view_board', board_id=board.id))
        # Остальные POST (создание карточки, приглашение) обрабатываются в своих маршрутах

    columns = board.columns # Уже упорядочены по position из модели
    board_members_list = board.members.all() 
    is_owner = (current_user == board.owner)

    return render_template('board.html', title=f"Доска: {board.name}", board=board,
                           columns=columns, column_form=column_form, card_form=card_form,
                           invite_form=invite_form, board_members=board_members_list, is_owner=is_owner)


@app.route('/boards/<int:board_id>/invite', methods=['POST'])
@login_required
def invite_to_board(board_id):
    board = Board.query.get_or_404(board_id)
    if not current_user.can_delete_board(board):
        flash('Только владелец доски может приглашать участников.', 'danger')
        return redirect(url_for('view_board', board_id=board.id))

    invite_form = InviteUserForm()
    if invite_form.validate_on_submit():
        identifier = invite_form.email_or_username.data
        user_to_invite = User.query.filter(or_(User.email == identifier, User.username == identifier)).first()

        if not user_to_invite:
            flash(f'Пользователь с email/именем "{identifier}" не найден.', 'warning')
        elif user_to_invite == board.owner:
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
    can_remove = False
    if current_user.can_delete_board(board): 
        if user_to_remove != current_user: 
            can_remove = True
        else:
             flash('Владелец не может удалить себя из участников через эту форму.', 'warning')
    elif current_user == user_to_remove: 
        if user_to_remove != board.owner: 
            can_remove = True
        else:
            flash('Владелец не может покинуть собственную доску. Передайте права или удалите доску.', 'warning')
    else: 
        flash('У вас нет прав для удаления этого участника.', 'danger')
        return redirect(url_for('view_board', board_id=board.id))

    if can_remove:
        if user_to_remove in board.members:
            board.members.remove(user_to_remove)
            for column in board.columns: 
                for card in column.cards.filter(Card.assignee_id == user_to_remove.id).all():
                    card.assignee_id = None 
            db.session.commit()
            flash(f'Пользователь "{user_to_remove.username}" удален с доски "{board.name}".', 'success')
        elif user_to_remove == board.owner: 
             flash(f'Пользователь "{user_to_remove.username}" является владельцем и не может быть удален как участник.', 'info')
        else:
            flash(f'Пользователь "{user_to_remove.username}" не найден среди участников этой доски.', 'info')
    return redirect(url_for('view_board', board_id=board.id))

@app.route('/columns/<int:column_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_column(column_id):
    column = Column.query.get_or_404(column_id)
    board = column.board
    if not current_user.can_edit_board(board):
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
    if not current_user.can_edit_board(board):
        flash('У вас нет прав для удаления элементов этой доски.', 'danger')
        return redirect(url_for('view_board', board_id=board.id))
    column_name = column_to_delete.name
    db.session.delete(column_to_delete)
    db.session.commit()
    flash(f'Колонка "{column_name}" удалена.', 'success')
    return redirect(url_for('view_board', board_id=board.id))


@app.route('/columns/<int:column_id>/cards/create', methods=['POST'])
@login_required
def create_card(column_id):
    column = Column.query.get_or_404(column_id)
    board = column.board
    if not current_user.can_edit_board(board):
        flash('У вас нет прав для добавления карточек на эту доску.', 'danger')
        return redirect(url_for('view_board', board_id=board.id, _anchor=f'column-{column.id}'))

    card_form = CardForm(request.form) 
    _populate_assignee_choices(card_form, board)

    if card_form.validate_on_submit():
        selected_assignee_id = card_form.assignee_id.data
        assignee_id_to_save = selected_assignee_id if selected_assignee_id != 0 else None
        new_card = Card(
            title=card_form.title.data,
            description=card_form.description.data,
            column_id=column.id,
            assignee_id=assignee_id_to_save
        )
        db.session.add(new_card)
        db.session.commit()
        flash(f'Карточка "{new_card.title}" добавлена в колонку "{column.name}".', 'success')
    else:
        for field_name, errors in card_form.errors.items():
            field_label = field_name
            try:
                field_label = getattr(card_form, field_name).label.text
            except AttributeError:
                pass 
            for error in errors:
                 flash(f"Ошибка в поле '{field_label}': {error}", 'danger')
                 
    return redirect(url_for('view_board', board_id=board.id, _anchor=f'column-{column.id}'))


@app.route('/cards/<int:card_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_card(card_id):
    card = Card.query.get_or_404(card_id)
    column = card.column
    board = column.board
    if not current_user.can_edit_board(board):
        flash('Нет прав для редактирования карточек на этой доске.', 'danger')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(success=False, error='Нет прав'), 403
        return redirect(url_for('view_board', board_id=board.id))

    form = CardForm(request.form if request.method == 'POST' else None, obj=card if request.method == 'GET' else None)
    _populate_assignee_choices(form, board)
    
    if request.method == 'GET':
        form.assignee_id.data = card.assignee_id or 0

    if form.validate_on_submit() and request.method == 'POST':
        card.title = form.title.data
        card.description = form.description.data
        selected_assignee_id = form.assignee_id.data
        card.assignee_id = selected_assignee_id if selected_assignee_id != 0 else None
        db.session.commit()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            assignee_data = None
            assignee_avatar_url = url_for('static', filename='images/default_avatar.png')
            if card.assignee:
                assignee_data = {'id': card.assignee.id, 'username': card.assignee.username}
                assignee_avatar_url = card.assignee.get_avatar()

            return jsonify(success=True, card={
                'id': card.id,
                'title': card.title,
                'description': card.description or "", # Передаем пустую строку, если null
                'assignee': assignee_data, 
                'assignee_id': card.assignee_id or 0, 
                'assignee_avatar_url': assignee_avatar_url 
            })
        flash('Карточка обновлена.', 'success')
        return redirect(url_for('view_board', board_id=board.id))
    
    if request.method == 'GET' and not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        current_title = card.title
        return render_template('edit_card.html', title='Редактировать карточку', form=form, card_id=card_id, board_id=board.id, current_title=current_title)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and form.errors:
        errors = {field: error[0] for field, error in form.errors.items()}
        return jsonify(success=False, errors=errors), 400
    
    if request.method == 'POST' and form.errors:
         flash('Пожалуйста, исправьте ошибки в форме.', 'danger')
         current_title = form.title.data if form.title.data else card.title
         # Заполняем форму данными из запроса для отображения ошибок
         form = CardForm(request.form, obj=card) # Перезаполняем с request.form
         _populate_assignee_choices(form, board) # И снова choices
         return render_template('edit_card.html', title='Редактировать карточку', form=form, card_id=card_id, board_id=board.id, current_title=current_title)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.method == 'GET':
         assignee_data = None
         assignee_avatar_url = url_for('static', filename='images/default_avatar.png')
         if card.assignee:
             assignee_data = {'id': card.assignee.id, 'username': card.assignee.username}
             assignee_avatar_url = card.assignee.get_avatar()
         return jsonify(
             success=True, 
             card={
                 'id': card.id, 
                 'title': card.title, 
                 'description': card.description or "",
                 'assignee_id': card.assignee_id or 0,
                 'assignee': assignee_data,
                 'assignee_avatar_url': assignee_avatar_url
             },
         )

    return redirect(url_for('view_board', board_id=board.id))


@app.route('/cards/<int:card_id>/delete', methods=['POST'])
@login_required
def delete_card(card_id):
    card_to_delete = Card.query.get_or_404(card_id)
    column = card_to_delete.column
    board = column.board
    if not current_user.can_edit_board(board):
        flash('У вас нет прав для удаления карточек на этой доске.', 'danger')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(success=False, error='Нет прав'), 403
        return redirect(url_for('view_board', board_id=board.id))

    card_title = card_to_delete.title
    db.session.delete(card_to_delete)
    db.session.commit()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify(success=True, message=f'Карточка "{card_title}" удалена.')
    flash(f'Карточка "{card_title}" удалена.', 'success')
    return redirect(url_for('view_board', board_id=board.id))

@app.route('/api/cards/<int:card_id>/move', methods=['POST'])
@login_required
def move_card(card_id):
    card = Card.query.get_or_404(card_id)
    board = card.column.board
    if not current_user.can_edit_board(board):
        return jsonify(success=False, error="Нет прав для изменения этой карточки."), 403

    data = request.get_json()
    if not data or 'new_column_id' not in data:
        return jsonify(success=False, error="Отсутствует ID новой колонки."), 400

    new_column_id = data.get('new_column_id')
    new_column = Column.query.get(new_column_id)
    if not new_column or new_column.board_id != board.id:
        return jsonify(success=False, error="Некорректный ID новой колонки."), 400

    if card.column_id != new_column_id:
        card.column_id = new_column_id
        db.session.commit()
        return jsonify(success=True, message="Карточка перемещена.")
    return jsonify(success=True, message="Карточка осталась в той же колонке.")