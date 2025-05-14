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
from app.models import User, Board, Column, Card # card_assignees не нужен здесь
from sqlalchemy import or_
import os
from functools import wraps
from wtforms import SelectField, SelectMultipleField


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
    """Заполняет поле выбора исполнителей в форме."""
    eligible_users = board.get_eligible_assignees()
    # choices_for_single = [(0, '--- Не назначен ---')] + [(user.id, user.username) for user in eligible_users]
    choices_for_multiple = [(user.id, user.username) for user in eligible_users]

    # Для SelectMultipleField (множественный выбор)
    if hasattr(form, 'assignees') and isinstance(form.assignees, SelectMultipleField):
        form.assignees.choices = choices_for_multiple
    # Для SelectField (одиночный выбор, если он еще где-то используется)
    # elif hasattr(form, 'assignee_id') and isinstance(form.assignee_id, SelectField):
    #     form.assignee_id.choices = choices_for_single


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
                if os.path.exists(old_avatar_path) and os.path.isfile(old_avatar_path):
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

    # Открепляем пользователя от всех досок, где он участник
    for board in list(user_to_delete.shared_boards): 
        board.members.remove(user_to_delete)
    
    # Открепляем пользователя от всех карточек, где он исполнитель
    for card in list(user_to_delete.assigned_cards.all()): # .all() т.к. assigned_cards - dynamic
        card.assignees.remove(user_to_delete)
    
    username = user_to_delete.username
    db.session.delete(user_to_delete)
    db.session.commit()
    flash(f'Пользователь {username} удален.', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/boards/<int:board_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_board(board_id):
    board = Board.query.get_or_404(board_id)
    if not current_user.can_delete_board(board): # Только владелец может редактировать название
        flash('У вас нет прав для редактирования названия этой доски.', 'danger')
        return redirect(url_for('view_board', board_id=board.id))

    form = BoardForm(obj=board)
    if form.validate_on_submit():
        board.name = form.name.data
        db.session.commit()
        flash('Название доски успешно обновлено!', 'success')
        return redirect(url_for('dashboard')) # Или view_board
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
    # Участники отвяжутся автоматически из-за cascade на User.shared_boards -> board_members
    # Карточки и колонки удалятся из-за cascade на Board.columns -> Column.cards
    # Связи исполнителей с карточками удалятся из-за cascade на Card.assignees -> card_assignees
    db.session.delete(board_to_delete)
    db.session.commit()
    flash(f'Доска "{board_name}" удалена.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/boards/<int:board_id>', methods=['GET', 'POST'])
@login_required
def view_board(board_id):
    board = Board.query.get_or_404(board_id)
    if not current_user.can_edit_board(board): # Проверяем, может ли пользователь просматривать/редактировать
        flash('У вас нет доступа к этой доске.', 'danger')
        return redirect(url_for('dashboard'))

    column_form = ColumnForm()
    card_form = CardForm() 
    invite_form = InviteUserForm()

    _populate_assignee_choices(card_form, board) 

    if request.method == 'POST': 
        if column_form.validate_on_submit() and 'submit_column' in request.form: 
            last_column = Column.query.filter_by(board_id=board.id).order_by(Column.position.desc()).first()
            new_position = (last_column.position + 1) if last_column else 0
            new_column = Column(name=column_form.name.data, board_id=board.id, position=new_position)
            db.session.add(new_column)
            db.session.commit()
            flash(f'Колонка "{new_column.name}" добавлена.', 'success')
            return redirect(url_for('view_board', board_id=board.id))
        # Обработка создания карточки и приглашения перенесена в отдельные роуты

    columns = board.columns # Уже упорядочены по position
    board_members_list = board.members.all() 
    is_owner = (current_user == board.owner)

    return render_template('board.html', title=f"Доска: {board.name}", board=board,
                           columns=columns, column_form=column_form, card_form=card_form,
                           invite_form=invite_form, board_members=board_members_list, is_owner=is_owner)


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
    # Владелец может удалять любого участника, кроме себя самого (он не "участник", а "владелец")
    if current_user.can_delete_board(board): 
        if user_to_remove != current_user: # Владелец не может удалить себя таким способом
            can_remove = True
        else:
             flash('Владелец не может удалить себя из участников через эту форму. Передайте права или удалите доску.', 'warning')
    # Участник может сам себя удалить (покинуть доску)
    elif current_user == user_to_remove: 
        if user_to_remove != board.owner: # Участник не может быть владельцем
            can_remove = True
        # else: # Этот случай не должен произойти, т.к. can_delete_board(board) был бы True для владельца
    else: 
        flash('У вас нет прав для удаления этого участника.', 'danger')
        return redirect(url_for('view_board', board_id=board.id))

    if can_remove:
        if user_to_remove in board.members:
            board.members.remove(user_to_remove)
            # Открепить пользователя от всех карточек на этой доске
            for column in board.columns: 
                for card in column.cards:
                    if user_to_remove in card.assignees:
                        card.assignees.remove(user_to_remove)
            db.session.commit()
            flash(f'Пользователь "{user_to_remove.username}" удален с доски "{board.name}".', 'success')
        elif user_to_remove == board.owner: 
             # Этого не должно произойти из-за логики выше, но на всякий случай
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
    
    # Связи card_assignees для карточек в этой колонке удалятся через cascade
    # Card.assignees -> card_assignees (ondelete='CASCADE')
    # Column.cards -> Card (cascade="all, delete-orphan")
    column_name = column_to_delete.name
    db.session.delete(column_to_delete) # Удалит колонку и все её карточки, и связанные записи в card_assignees
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
        new_card = Card(
            title=card_form.title.data,
            description=card_form.description.data,
            column_id=column.id
        )
        selected_assignee_ids = card_form.assignees.data # Это список ID
        if selected_assignee_ids:
            assignees_to_add = User.query.filter(User.id.in_(selected_assignee_ids)).all()
            for user in assignees_to_add:
                new_card.assignees.append(user)
        
        db.session.add(new_card)
        db.session.commit()
        flash(f'Карточка "{new_card.title}" добавлена в колонку "{column.name}".', 'success')
    else:
        # Сохраняем id колонки, для которой была ошибка, чтобы отобразить ее в нужном месте
        error_column_id = column.id 
        # Передаем id в сессию или как-то еще, если нужно отобразить ошибки под конкретной формой
        # flash(f"Ошибка при создании карточки в колонке {column.name}:", 'danger')
        for field_name, errors in card_form.errors.items():
            field_label = field_name
            try:
                field_label = getattr(card_form, field_name).label.text
            except AttributeError:
                pass 
            for error in errors:
                 flash(f"Ошибка в поле '{field_label}': {error} (для колонки {column.name})", 'danger')
                 
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

    # Используем request.form для POST, чтобы получить последние данные, если была ошибка валидации
    # Используем obj=card для GET, чтобы предзаполнить форму
    form_data = request.form if request.method == 'POST' else None
    form = CardForm(form_data, obj=card if request.method == 'GET' else None)
    _populate_assignee_choices(form, board)
    
    if request.method == 'GET':
        # Предзаполняем поле assignees текущими исполнителями для GET запроса
        form.assignees.data = [assignee.id for assignee in card.assignees.all()]


    if form.validate_on_submit() and request.method == 'POST':
        card.title = form.title.data
        card.description = form.description.data
        
        # Обновление исполнителей
        current_assignees = {user.id for user in card.assignees.all()}
        selected_assignee_ids = set(form.assignees.data) # Это список ID из формы

        # Удаляем тех, кого нет в новом списке
        ids_to_remove = current_assignees - selected_assignee_ids
        if ids_to_remove:
            users_to_remove = User.query.filter(User.id.in_(ids_to_remove)).all()
            for user in users_to_remove:
                if user in card.assignees: # Доп. проверка, т.к. card.assignees - Query
                    card.assignees.remove(user)
        
        # Добавляем новых
        ids_to_add = selected_assignee_ids - current_assignees
        if ids_to_add:
            users_to_add = User.query.filter(User.id.in_(ids_to_add)).all()
            for user in users_to_add:
                if user not in card.assignees: # Доп. проверка
                     card.assignees.append(user)
        
        db.session.commit()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            assignees_data = [{
                'id': u.id, 
                'username': u.username, 
                'avatar_url': u.get_avatar()
            } for u in card.assignees.all()]

            return jsonify(success=True, card={
                'id': card.id,
                'title': card.title,
                'description': card.description or "",
                'assignees': assignees_data, 
                'assignee_ids': [u.id for u in card.assignees.all()] # для <select multiple>
            })
        flash('Карточка обновлена.', 'success')
        return redirect(url_for('view_board', board_id=board.id))
    
    # Если GET и не AJAX - показываем страницу редактирования
    if request.method == 'GET' and not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        current_title = card.title
        return render_template('edit_card.html', title='Редактировать карточку', form=form, card_id=card_id, board_id=board.id, current_title=current_title)
    
    # Если AJAX POST с ошибками валидации
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and form.errors and request.method == 'POST':
        errors = {field: error[0] for field, error in form.errors.items()}
        return jsonify(success=False, errors=errors), 400
    
    # Если обычный POST с ошибками валидации (не AJAX)
    if request.method == 'POST' and form.errors:
         flash('Пожалуйста, исправьте ошибки в форме.', 'danger')
         current_title = form.title.data if form.title.data else card.title
         # Форма уже содержит данные из request.form и ошибки
         return render_template('edit_card.html', title='Редактировать карточку', form=form, card_id=card_id, board_id=board.id, current_title=current_title)

    # Если AJAX GET - возвращаем JSON с данными карточки
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.method == 'GET':
         assignees_data = [{
             'id': u.id, 
             'username': u.username, 
             'avatar_url': u.get_avatar()
         } for u in card.assignees.all()]
         return jsonify(
             success=True, 
             card={
                 'id': card.id, 
                 'title': card.title, 
                 'description': card.description or "",
                 'assignees': assignees_data,
                 'assignee_ids': [u.id for u in card.assignees.all()]
             },
         )

    # Фоллбэк, если что-то пошло не так
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
    # Связи в card_assignees удалятся автоматически благодаря ondelete='CASCADE' в ForeignKey
    # или SQLAlchemy сам обработает удаление из ассоциативной таблицы при удалении card_to_delete
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
    # new_position = data.get('new_position') # Если будем реализовывать сортировку внутри колонки

    new_column = Column.query.get(new_column_id)
    if not new_column or new_column.board_id != board.id:
        return jsonify(success=False, error="Некорректный ID новой колонки."), 400

    if card.column_id != new_column_id:
        card.column_id = new_column_id
        # if new_position is not None: card.position = new_position # Если есть сортировка
        db.session.commit()
        return jsonify(success=True, message="Карточка перемещена.")
    # elif new_position is not None and card.position != new_position: # Если только сортировка
        # card.position = new_position
        # db.session.commit()
        # return jsonify(success=True, message="Порядок карточки изменен.")
    return jsonify(success=True, message="Карточка осталась в той же колонке и на той же позиции.")