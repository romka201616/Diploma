from flask import render_template, flash, redirect, url_for, request, jsonify # Добавили jsonify
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from app import app, db
from app.forms import LoginForm, RegistrationForm, BoardForm, ColumnForm, CardForm
from app.models import User, Board, Column, Card

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
    user_boards = Board.query.filter_by(user_id=current_user.id).order_by(Board.id.desc()).all()
    return render_template('dashboard.html', title='Мои доски', form=form, boards=user_boards)

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
    if board.owner != current_user:
        flash('У вас нет прав для редактирования этой доски.', 'danger')
        return redirect(url_for('dashboard'))
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
    if board_to_delete.owner != current_user:
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
    if board.owner != current_user:
        flash('У вас нет доступа к этой доске.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Передаем обе формы в шаблон
    column_form = ColumnForm()
    card_form = CardForm() # Эта форма будет использоваться модальным окном и формой создания карточки

    if request.method == 'POST': # Обработка POST запросов (создание колонки)
        if column_form.validate_on_submit() and 'submit_column' in request.form:
            last_column = Column.query.filter_by(board_id=board.id).order_by(Column.position.desc()).first()
            new_position = (last_column.position + 1) if last_column else 0
            new_column = Column(name=column_form.name.data, board_id=board.id, position=new_position)
            db.session.add(new_column)
            db.session.commit()
            flash(f'Колонка "{new_column.name}" добавлена.', 'success')
            return redirect(url_for('view_board', board_id=board.id))
        # Ошибки валидации формы колонки будут отображены в шаблоне автоматически
        # Ошибки формы карточки (при обычном создании) обрабатываются в create_card
        
    columns = board.columns # Уже отсортированы по position благодаря order_by в модели
    return render_template('board.html', title=f"Доска: {board.name}", board=board, columns=columns, column_form=column_form, card_form=card_form)


# --- Маршруты для КОЛОНОК ---
@app.route('/columns/<int:column_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_column(column_id):
    column = Column.query.get_or_404(column_id)
    board = column.board
    if board.owner != current_user:
        flash('Нет прав для редактирования этой колонки.', 'danger')
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
    if board.owner != current_user:
        flash('У вас нет прав для удаления этой колонки.', 'danger')
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
    if board.owner != current_user:
        flash('У вас нет прав для добавления карточек в эту колонку.', 'danger')
        return redirect(url_for('view_board', board_id=board.id))
    
    card_form = CardForm() # Создаем экземпляр формы
    if card_form.validate_on_submit(): # CSRF-токен будет проверен здесь
        new_card = Card(title=card_form.title.data, description=card_form.description.data, column_id=column.id)
        db.session.add(new_card)
        db.session.commit()
        flash(f'Карточка "{new_card.title}" добавлена в колонку "{column.name}".', 'success')
    else:
        # Если валидация не прошла (например, пустое название), показываем ошибки
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
    if board.owner != current_user:
        flash('Нет прав для редактирования этой карточки.', 'danger')
        # Если это AJAX запрос, можно вернуть JSON с ошибкой
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(success=False, error='Нет прав'), 403
        return redirect(url_for('view_board', board_id=board.id))

    form = CardForm(obj=card if request.method == 'GET' else None) # Заполняем форму из объекта при GET

    if form.validate_on_submit(): # request.method == 'POST'
        card.title = form.title.data
        card.description = form.description.data
        db.session.commit()
        flash('Карточка обновлена.', 'success')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
             # Можно вернуть обновленные данные карточки, если JS их использует
            return jsonify(success=True, card={'id': card.id, 'title': card.title, 'description': card.description})
        return redirect(url_for('view_board', board_id=board.id))
    
    if request.method == 'GET': # Для обычного GET запроса (страница редактирования)
        current_title = card.title
        return render_template('edit_card.html', title='Редактировать карточку', form=form, card_id=card_id, board_id=board.id, current_title=current_title)
    
    # Если POST и валидация не прошла (например, для AJAX из модального окна)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        errors = {field: error[0] for field, error in form.errors.items()}
        return jsonify(success=False, errors=errors), 400
    
    # Если это обычный POST с ошибками (маловероятно, т.к. редирект выше)
    # но для полноты можно вернуть на страницу редактирования с ошибками
    current_title = card.title # или form.title.data если уже пытались изменить
    return render_template('edit_card.html', title='Редактировать карточку', form=form, card_id=card_id, board_id=board.id, current_title=current_title)


@app.route('/cards/<int:card_id>/delete', methods=['POST'])
@login_required
def delete_card(card_id):
    card_to_delete = Card.query.get_or_404(card_id)
    column = card_to_delete.column
    board = column.board
    if board.owner != current_user:
        flash('У вас нет прав для удаления этой карточки.', 'danger')
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

    if board.owner != current_user:
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
        # Если бы мы реализовывали позиционирование:
        # if 'new_position' in data:
        #     card.position = data['new_position']
        #     # Здесь также нужна логика для сдвига других карточек в старой и новой колонках
        db.session.commit()
        return jsonify(success=True, message="Карточка перемещена.")
    
    # Если карточка перемещается внутри той же колонки (только порядок меняется)
    # или если колонка не изменилась, но мы все равно хотим подтверждение
    # if 'new_position' in data and card.column_id == new_column_id:
    #     card.position = data['new_position']
    #     # Логика для сдвига других карточек в той же колонке
    #     db.session.commit()
    #     return jsonify(success=True, message="Порядок карточки обновлен.")

    return jsonify(success=True, message="Карточка осталась в той же колонке.") # или success=False, если это ошибка