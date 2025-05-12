# run.py

import os
import click # Для CLI команд
from app import app, db
from app.models import User, Board, Column, Card
from werkzeug.security import generate_password_hash
from sqlalchemy import inspect

# --- Функции для создания таблиц и наполнения данными (будут вызываться через CLI) ---

def _create_tables():
    """Создает таблицы БД, если их не существует."""
    print("Проверка и создание таблиц БД...")
    # Используем app_context, так как операции с БД требуют контекста приложения
    with app.app_context():
        inspector = inspect(db.engine)
        # Проверяем наличие ключевой таблицы, например 'user'
        if not inspector.has_table("user"):
            print("Таблицы не найдены, создаем...")
            db.create_all()
            print("Таблицы успешно созданы.")
        else:
            print("Таблицы уже существуют.")

def _seed_data():
    """Наполняет БД тестовыми данными (админ, пользователи, доски и т.д.), если админа нет."""
    # Используем app_context
    with app.app_context():
        inspector = inspect(db.engine)
        if not inspector.has_table("user"):
            print("Ошибка: Таблица 'user' не найдена. Сначала создайте таблицы командой 'flask db-create'.")
            return

        print("Проверка необходимости наполнения БД...")
        admin_user = User.query.filter_by(email='admin@gmai.com').first()
        if not admin_user:
            print("Администратор не найден, наполняем БД тестовыми данными...")

            # --- Создаем администратора ---
            admin = User(username='Admin', email='admin@gmai.com', is_admin=True)
            admin.set_password('password'); db.session.add(admin)

            # --- Создаем пользователей ---
            user1 = User(username='TestUser1', email='user1@example.com'); user1.set_password('password123'); db.session.add(user1)
            user2 = User(username='AnotherUser', email='user2@example.com'); user2.set_password('password456'); db.session.add(user2)

            try:
                db.session.commit() # Сохраняем пользователей, чтобы получить ID
                print("Пользователи (Admin, TestUser1, AnotherUser) созданы.")
            except Exception as e:
                db.session.rollback(); print(f"Ошибка при создании пользователей: {e}"); return

            # --- Создаем доски (снова получаем пользователей с ID) ---
            admin_user = User.query.filter_by(email='admin@gmai.com').first()
            user1 = User.query.filter_by(email='user1@example.com').first()
            user2 = User.query.filter_by(email='user2@example.com').first()
            if not all([admin_user, user1, user2]): print("Ошибка получения пользователей для досок."); return

            board1 = Board(name='Проект Альфа', owner=admin_user); board1.members.append(user1); db.session.add(board1)
            board2 = Board(name='Личные задачи User1', owner=user1); db.session.add(board2)
            board3 = Board(name='Общая доска команды', owner=user2); board3.members.extend([admin_user, user1]); db.session.add(board3)

            try:
                db.session.commit() # Сохраняем доски, чтобы получить ID
                print("Доски (Проект Альфа, Личные задачи User1, Общая доска команды) созданы.")
            except Exception as e:
                db.session.rollback(); print(f"Ошибка при создании досок: {e}"); return

            # --- Создаем колонки и карточки ---
            board1 = Board.query.filter_by(name='Проект Альфа').first()
            board2 = Board.query.filter_by(name='Личные задачи User1').first()

            if board1:
                col1_1 = Column(name='Бэклог', board_id=board1.id, position=0)
                col1_2 = Column(name='В работе', board_id=board1.id, position=1)
                col1_3 = Column(name='Готово', board_id=board1.id, position=2)
                db.session.add_all([col1_1, col1_2, col1_3])
                try: db.session.commit(); print("Колонки для Доски 1 созданы.")
                except Exception as e: db.session.rollback(); print(f"Ошибка колонок Д1: {e}"); return
                card1_1=Card(title='Настроить аутентификацию',column_id=col1_1.id,assignee_id=admin_user.id)
                card1_2=Card(title='Реализовать CRUD для досок',column_id=col1_1.id)
                card1_3=Card(title='Создать модели БД',column_id=col1_2.id,assignee_id=user1.id)
                card1_4=Card(title='Настроить базовый шаблон',column_id=col1_3.id)
                db.session.add_all([card1_1, card1_2, card1_3, card1_4]); print("Карточки для Д1 добавлены.")

            if board2:
                col2_1 = Column(name='Сделать', board_id=board2.id, position=0)
                col2_2 = Column(name='Сделано', board_id=board2.id, position=1)
                db.session.add_all([col2_1, col2_2])
                try: db.session.commit(); print("Колонки для Доски 2 созданы.")
                except Exception as e: db.session.rollback(); print(f"Ошибка колонок Д2: {e}"); return
                card2_1=Card(title='Купить продукты',column_id=col2_1.id)
                card2_2=Card(title='Закончить отчет',column_id=col2_2.id)
                db.session.add_all([card2_1, card2_2]); print("Карточки для Д2 добавлены.")

            try:
                db.session.commit() # Финальный коммит для карточек
                print("Наполнение БД тестовыми данными успешно завершено.")
            except Exception as e:
                db.session.rollback(); print(f"Ошибка при финальном сохранении карточек: {e}")

        else:
            print("Администратор уже существует. Наполнение БД пропускается.")


# --- Flask CLI Команды ---

@app.cli.command("db-create")
def create_tables_command():
    """Создает таблицы БД, если они не существуют."""
    _create_tables()

@app.cli.command("db-seed")
def seed_db_command():
    """Наполняет БД тестовыми данными (если админ отсутствует)."""
    _seed_data()

@app.cli.command("db-init")
@click.option('--force', is_flag=True, help='Удалить существующую БД перед инициализацией.')
def init_db_command(force):
    """Инициализирует БД: удаляет (если --force), создает таблицы и наполняет данными."""
    db_path = os.path.join(app.instance_path, 'mydatabase.db')
    if force:
        if os.path.exists(db_path):
            print(f"Удаление существующей БД: {db_path}...")
            os.remove(db_path)
            print("Существующая БД удалена.")
        else:
            print("Файл БД не найден, удаление не требуется.")
    elif os.path.exists(db_path):
         print(f"Файл БД '{db_path}' уже существует. Используйте '--force', чтобы удалить и пересоздать.")
         print("Инициализация прервана.")
         return # Не продолжаем, если файл есть и force не указан

    print("Создание таблиц...")
    _create_tables()
    print("Наполнение данными...")
    _seed_data()
    print("Инициализация БД завершена.")


# --- Запуск основного приложения ---
if __name__ == '__main__':
    # Инициализация БД теперь выполняется через команду 'flask db-init'
    print("Запуск Flask development-сервера...")
    print("Для создания/пересоздания БД выполните: flask db-init --force")
    print("Для простого создания таблиц (если БД нет): flask db-create")
    print("Для наполнения данными (если БД пуста): flask db-seed")
    app.run(debug=True, port=5001) # Можно вернуть use_reloader=True