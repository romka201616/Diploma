# app/routes.py

from flask import render_template, flash, redirect, url_for, request, jsonify, abort
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from app import app, db 
from app.forms import (
    LoginForm, RegistrationForm, BoardForm, ColumnForm, CardForm, CommentForm, 
    InviteUserForm, UpdateAccountForm, ChangePasswordForm, UpdateAvatarForm, AdminEditUserForm,
    TagForm 
)
from app.models import User, Board, Column, Card, Comment, Tag 
from sqlalchemy import or_, exc
import os
from functools import wraps
from wtforms import SelectField, SelectMultipleField
from datetime import datetime


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
    eligible_users = board.get_eligible_assignees()
    choices_for_multiple = [(user.id, user.username) for user in eligible_users]
    if hasattr(form, 'assignees') and isinstance(form.assignees, SelectMultipleField):
        form.assignees.choices = choices_for_multiple

# --- Helper function to populate tag choices ---
def _populate_tag_choices(form, board):
    if hasattr(form, 'tags') and isinstance(form.tags, SelectMultipleField):
        board_tags = board.tags.order_by(Tag.name).all()
        form.tags.choices = [(tag.id, tag.name) for tag in board_tags]


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
        flash('У вас нет прав для редактирования этой доски.', 'danger')
        return redirect(url_for('view_board', board_id=board.id))

    form = BoardForm(obj=board if request.method == 'GET' else None)
    invite_form = InviteUserForm() 

    if form.validate_on_submit() and 'submit_board_name' in request.form:
        board.name = form.name.data
        db.session.commit()
        flash('Название доски успешно обновлено!', 'success')
        return redirect(url_for('edit_board', board_id=board.id))
    
    if request.method == 'GET':
        form.name.data = board.name
    
    board_members_list = board.members.all()
    is_owner = (current_user == board.owner)

    return render_template('edit_board.html', title=f'Настройки доски: {board.name}', 
                           form=form, invite_form=invite_form, board=board,
                           board_members=board_members_list, is_owner=is_owner)


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
@app.route('/boards/<int:board_id>/cards/<int:card_id_in_url>', methods=['GET'])
@login_required
def view_board(board_id, card_id_in_url=None):
    board = Board.query.get_or_404(board_id)
    if not current_user.can_edit_board(board):
        flash('У вас нет доступа к этой доске.', 'danger')
        return redirect(url_for('dashboard'))

    column_form = ColumnForm()
    card_form = CardForm() 
    comment_form = CommentForm() 
    tag_form = TagForm() 

    _populate_assignee_choices(card_form, board) 
    _populate_tag_choices(card_form, board) 

    if request.method == 'POST': 
        if column_form.validate_on_submit() and 'submit_column' in request.form: 
            last_column = Column.query.filter_by(board_id=board.id).order_by(Column.position.desc()).first()
            new_position = (last_column.position + 1) if last_column else 0
            new_column = Column(name=column_form.name.data, board_id=board.id, position=new_position)
            db.session.add(new_column)
            db.session.commit()
            flash(f'Колонка "{new_column.name}" добавлена.', 'success')
            redirect_url = url_for('view_board', board_id=board.id, card_id_in_url=card_id_in_url) if card_id_in_url else url_for('view_board', board_id=board.id)
            return redirect(redirect_url)

    columns = board.columns
    
    card_to_open = None
    if card_id_in_url:
        card_to_open_query = Card.query.join(Column).filter(Card.id == card_id_in_url, Column.board_id == board_id)
        card_to_open = card_to_open_query.first()
        if not card_to_open:
            flash(f'Карточка с ID {card_id_in_url} не найдена на этой доске.', 'warning')
            return redirect(url_for('view_board', board_id=board_id))
    
    board_all_users = board.get_eligible_assignees() 
    board_all_tags = board.tags.order_by(Tag.name).all()


    return render_template('board.html', title=f"{board.name}", board=board,
                           columns=columns, column_form=column_form, card_form=card_form,
                           comment_form=comment_form, tag_form=tag_form, 
                           card_id_to_open_on_load=card_to_open.id if card_to_open else None,
                           board_all_users=board_all_users, board_all_tags=board_all_tags)


@app.route('/boards/<int:board_id>/invite', methods=['POST'])
@login_required
def invite_to_board(board_id):
    board = Board.query.get_or_404(board_id)
    if not current_user.can_delete_board(board): 
        flash('Только владелец доски может приглашать участников.', 'danger')
        return redirect(url_for('edit_board', board_id=board.id, _anchor='members-management'))

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
    return redirect(url_for('edit_board', board_id=board.id, _anchor='members-management'))

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
             flash('Владелец не может удалить себя из участников через эту форму. Передайте права или удалите доску.', 'warning')
    elif current_user == user_to_remove: 
        if user_to_remove != board.owner: 
            can_remove = True
    else: 
        flash('У вас нет прав для удаления этого участника.', 'danger')
        return redirect(url_for('edit_board', board_id=board.id, _anchor='members-management'))

    if can_remove:
        if user_to_remove in board.members:
            board.members.remove(user_to_remove)
            for column in board.columns: 
                for card in column.cards:
                    if user_to_remove in card.assignees:
                        card.assignees.remove(user_to_remove)
            db.session.commit()
            flash(f'Пользователь "{user_to_remove.username}" удален с доски "{board.name}".', 'success')
        elif user_to_remove == board.owner: 
             flash(f'Пользователь "{user_to_remove.username}" является владельцем и не может быть удален как участник.', 'info')
        else:
            flash(f'Пользователь "{user_to_remove.username}" не найден среди участников этой доски.', 'info')
    return redirect(url_for('edit_board', board_id=board.id, _anchor='members-management'))

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
    _populate_tag_choices(card_form, board) 

    if card_form.validate_on_submit():
        new_card = Card(
            title=card_form.title.data,
            description=card_form.description.data,
            column_id=column.id
        )
        selected_assignee_ids = card_form.assignees.data 
        if selected_assignee_ids:
            assignees_to_add = User.query.filter(User.id.in_(selected_assignee_ids)).all()
            for user in assignees_to_add:
                new_card.assignees.append(user)
        
        selected_tag_ids = card_form.tags.data
        if selected_tag_ids:
            tags_to_add = Tag.query.filter(Tag.id.in_(selected_tag_ids), Tag.board_id == board.id).all()
            for tag in tags_to_add:
                new_card.tags.append(tag)

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
                 flash(f"Ошибка в поле '{field_label}': {error} (для колонки {column.name})", 'danger')
                 
    return redirect(url_for('view_board', board_id=board.id, _anchor=f'column-{column.id}'))


@app.route('/cards/<int:card_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_card(card_id):
    card = Card.query.get_or_404(card_id)
    column = card.column
    board = column.board

    if not current_user.can_edit_board(board):
        app.logger.warning(f"User {current_user.id} tried to edit card {card_id} without permission.")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(success=False, error='Нет прав для редактирования этой карточки.'), 403
        flash('Нет прав для редактирования карточек на этой доске.', 'danger')
        return redirect(url_for('view_board', board_id=board.id))

    form = CardForm(request.form if request.method == 'POST' else None) 
    _populate_assignee_choices(form, board)
    _populate_tag_choices(form, board) 

    if request.method == 'GET':
        form.title.data = card.title
        form.description.data = card.description
        form.assignees.data = [assignee.id for assignee in card.assignees.all()]
        form.tags.data = [tag.id for tag in card.tags.all()] 
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest': 
            assignees_data = [{'id': u.id, 'username': u.username, 'avatar_url': u.get_avatar()} for u in card.assignees.all()]
            tags_data = [{'id': t.id, 'name': t.name, 'color': t.color} for t in card.tags.all()]
            
            board_tags_data = [{'id': t.id, 'name': t.name, 'color': t.color} for t in board.tags.order_by(Tag.name).all()]

            return jsonify(
                success=True, 
                card={
                    'id': card.id, 
                    'title': card.title, 
                    'description': card.description or "",
                    'assignees': assignees_data,
                    'assignee_ids': [u.id for u in card.assignees.all()],
                    'tags': tags_data, 
                    'tag_ids': [t.id for t in card.tags.all()] 
                },
                board_tags=board_tags_data 
            )
        else: 
            flash('Для редактирования карточек используется модальное окно.', 'info')
            return redirect(url_for('view_board', board_id=board.id, card_id_in_url=card.id))


    if request.method == 'POST':
        if form.validate_on_submit():
            try:
                card.title = form.title.data
                card.description = form.description.data
                
                new_assignee_ids = set(form.assignees.data if form.assignees.data else [])
                current_assignee_ids_on_card = {user.id for user in card.assignees}
                
                ids_to_remove_from_card = current_assignee_ids_on_card - new_assignee_ids
                if ids_to_remove_from_card:
                    users_to_remove = User.query.filter(User.id.in_(ids_to_remove_from_card)).all()
                    for user in users_to_remove:
                        if user in card.assignees: 
                            card.assignees.remove(user)
                
                ids_to_add_to_card = new_assignee_ids - current_assignee_ids_on_card
                if ids_to_add_to_card:
                    users_to_add = User.query.filter(User.id.in_(ids_to_add_to_card)).all()
                    for user in users_to_add:
                        if user not in card.assignees: 
                             card.assignees.append(user)

                new_tag_ids = set(form.tags.data if form.tags.data else [])
                current_tag_ids_on_card = {tag.id for tag in card.tags}

                tag_ids_to_remove = current_tag_ids_on_card - new_tag_ids
                if tag_ids_to_remove:
                    tags_to_remove_objs = Tag.query.filter(Tag.id.in_(tag_ids_to_remove)).all()
                    for tag_obj in tags_to_remove_objs:
                        if tag_obj in card.tags:
                            card.tags.remove(tag_obj)
                
                tag_ids_to_add = new_tag_ids - current_tag_ids_on_card
                if tag_ids_to_add:
                    tags_to_add_objs = Tag.query.filter(Tag.id.in_(tag_ids_to_add), Tag.board_id == board.id).all()
                    for tag_obj in tags_to_add_objs:
                        if tag_obj not in card.tags:
                            card.tags.append(tag_obj)
                
                db.session.commit()
                app.logger.info(f"Card {card.id} updated successfully by user {current_user.id}.")

                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    assignees_data = [{'id': u.id, 'username': u.username, 'avatar_url': u.get_avatar()} for u in card.assignees.all()]
                    tags_data = [{'id': t.id, 'name': t.name, 'color': t.color} for t in card.tags.all()]

                    return jsonify(success=True, card={
                        'id': card.id,
                        'title': card.title,
                        'description': card.description or "",
                        'assignees': assignees_data, 
                        'assignee_ids': [u.id for u in card.assignees.all()],
                        'tags': tags_data,
                        'tag_ids': [t.id for t in card.tags.all()]
                    })
                else: 
                    flash('Карточка обновлена.', 'success')
                    return redirect(url_for('view_board', board_id=board.id))
            except Exception as e:
                db.session.rollback()
                app.logger.error(f"Error updating card {card.id}: {e}", exc_info=True)
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify(success=False, error="Внутренняя ошибка сервера при обновлении карточки."), 500
                else:
                    flash('Ошибка при обновлении карточки. Пожалуйста, попробуйте снова.', 'danger')
                    return redirect(url_for('view_board', board_id=board.id, card_id_in_url=card.id))
        else: 
            app.logger.warning(f"Card {card.id} update form validation failed: {form.errors}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                errors = {field: error[0] for field, error in form.errors.items()}
                return jsonify(success=False, errors=errors), 400
            else: 
                flash('Пожалуйста, исправьте ошибки в форме.', 'danger')
                return redirect(url_for('view_board', board_id=board.id, card_id_in_url=card.id))

    app.logger.error(f"Unexpected state in edit_card for card {card_id}, method: {request.method}")
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


# --- Маршруты для комментариев (AJAX) ---

@app.route('/cards/<int:card_id>/comments', methods=['GET'])
@login_required
def get_comments(card_id):
    card = Card.query.get_or_404(card_id)
    if not current_user.can_edit_board(card.column.board): 
        return jsonify(success=False, error="Нет доступа к комментариям этой карточки."), 403
    
    comments = card.comments.order_by(Comment.timestamp.asc()).all()
    comments_data = []
    for comment in comments:
        comments_data.append({
            'id': comment.id,
            'text': comment.text,
            'timestamp': comment.timestamp.strftime('%d.%m.%Y %H:%M'),
            'author': {
                'id': comment.author.id,
                'username': comment.author.username,
                'avatar_url': comment.author.get_avatar()
            },
            'can_edit': current_user.id == comment.author.id,
            'can_delete': current_user.id == comment.author.id
        })
    return jsonify(success=True, comments=comments_data)

@app.route('/cards/<int:card_id>/comments/add', methods=['POST'])
@login_required
def add_comment(card_id):
    card = Card.query.get_or_404(card_id)
    if not current_user.can_edit_board(card.column.board):
        return jsonify(success=False, error="Вы не можете комментировать на этой доске."), 403

    form = CommentForm() 
    if form.validate_on_submit():
        comment = Comment(text=form.text.data, author=current_user, card_id=card.id)
        db.session.add(comment)
        db.session.commit()
        return jsonify(success=True, comment={
            'id': comment.id,
            'text': comment.text,
            'timestamp': comment.timestamp.strftime('%d.%m.%Y %H:%M'),
            'author': {
                'id': current_user.id,
                'username': current_user.username,
                'avatar_url': current_user.get_avatar()
            },
            'can_edit': True,
            'can_delete': True
        }), 201 
    
    errors = {field: error[0] for field, error in form.errors.items()}
    return jsonify(success=False, errors=errors), 400


@app.route('/comments/<int:comment_id>/edit', methods=['POST'])
@login_required
def edit_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    if comment.author != current_user:
        return jsonify(success=False, error="Вы не можете редактировать этот комментарий."), 403

    form = CommentForm() 
    if form.validate_on_submit():
        comment.text = form.text.data
        comment.timestamp = datetime.utcnow() 
        db.session.commit()
        return jsonify(success=True, comment={
            'id': comment.id,
            'text': comment.text,
            'timestamp': comment.timestamp.strftime('%d.%m.%Y %H:%M'),
             'author': { 
                'id': comment.author.id,
                'username': comment.author.username,
                'avatar_url': comment.author.get_avatar()
            },
            'can_edit': True,
            'can_delete': True
        })
    
    errors = {field: error[0] for field, error in form.errors.items()}
    return jsonify(success=False, errors=errors), 400


@app.route('/comments/<int:comment_id>/delete', methods=['POST'])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    if comment.author != current_user:
        return jsonify(success=False, error="Вы не можете удалить этот комментарий."), 403
    
    db.session.delete(comment)
    db.session.commit()
    return jsonify(success=True, message="Комментарий удален.")


# --- Маршруты для ТЕГОВ (AJAX) ---

@app.route('/api/boards/<int:board_id>/tags', methods=['GET'])
@login_required
def get_board_tags(board_id):
    board = Board.query.get_or_404(board_id)
    if not current_user.can_edit_board(board):
        return jsonify(success=False, error="Нет доступа к тегам этой доски."), 403
    
    tags = board.tags.order_by(Tag.name).all()
    tags_data = [{'id': tag.id, 'name': tag.name, 'color': tag.color} for tag in tags]
    return jsonify(success=True, tags=tags_data)

@app.route('/api/boards/<int:board_id>/tags/create', methods=['POST'])
@login_required
def create_tag_for_board(board_id):
    board = Board.query.get_or_404(board_id)
    if not current_user.can_edit_board(board): 
        return jsonify(success=False, error="Нет прав для создания тегов на этой доске."), 403

    form = TagForm()
    if form.validate_on_submit():
        try:
            new_tag = Tag(name=form.name.data, color=form.color.data, board_id=board.id)
            db.session.add(new_tag)
            db.session.commit()
            return jsonify(success=True, tag={'id': new_tag.id, 'name': new_tag.name, 'color': new_tag.color}), 201
        except exc.IntegrityError: 
            db.session.rollback()
            return jsonify(success=False, errors={'name': f'Тег с именем "{form.name.data}" уже существует на этой доске.'}), 400
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error creating tag for board {board_id}: {e}")
            return jsonify(success=False, error="Внутренняя ошибка сервера при создании тега."), 500
            
    errors = {field: error[0] for field, error in form.errors.items()}
    return jsonify(success=False, errors=errors), 400


@app.route('/api/tags/<int:tag_id>/edit', methods=['POST'])
@login_required
def edit_tag(tag_id):
    tag_to_edit = Tag.query.get_or_404(tag_id)
    board = tag_to_edit.board
    if not current_user.can_edit_board(board): 
        return jsonify(success=False, error="Нет прав для редактирования тегов этой доски."), 403

    form = TagForm()
    if form.validate_on_submit():
        try:
            if tag_to_edit.name != form.name.data:
                existing_tag = Tag.query.filter(Tag.name == form.name.data, Tag.board_id == board.id, Tag.id != tag_id).first()
                if existing_tag:
                    return jsonify(success=False, errors={'name': f'Тег с именем "{form.name.data}" уже существует на этой доске.'}), 400
            
            tag_to_edit.name = form.name.data
            tag_to_edit.color = form.color.data
            db.session.commit()
            return jsonify(success=True, tag={'id': tag_to_edit.id, 'name': tag_to_edit.name, 'color': tag_to_edit.color})
        except exc.IntegrityError: 
            db.session.rollback()
            return jsonify(success=False, errors={'name': f'Тег с именем "{form.name.data}" уже существует (ошибка Integrity).'}), 400
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error editing tag {tag_id}: {e}")
            return jsonify(success=False, error="Внутренняя ошибка сервера при редактировании тега."), 500

    errors = {field: error[0] for field, error in form.errors.items()}
    return jsonify(success=False, errors=errors), 400


@app.route('/api/tags/<int:tag_id>/delete', methods=['POST'])
@login_required
def delete_tag(tag_id):
    tag_to_delete = Tag.query.get_or_404(tag_id)
    board = tag_to_delete.board
    if not current_user.can_edit_board(board): 
        return jsonify(success=False, error="Нет прав для удаления тегов этой доски."), 403
    
    try:
        tag_name = tag_to_delete.name
        db.session.delete(tag_to_delete) 
        db.session.commit()
        return jsonify(success=True, message=f'Тег "{tag_name}" удален.')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting tag {tag_id}: {e}")
        return jsonify(success=False, error="Внутренняя ошибка сервера при удалении тега."), 500