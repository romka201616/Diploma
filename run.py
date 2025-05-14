# run.py

import os
import click # Для CLI команд
from app import app, db
from app.models import User, Board, Column, Card # card_assignees не нужно импортировать явно
from werkzeug.security import generate_password_hash
from sqlalchemy import inspect

# --- Функции для создания таблиц и наполнения данными (будут вызываться через CLI) ---

def _create_tables():
    """Создает таблицы БД, если их не существует."""
    print("Проверка и создание таблиц БД...")
    with app.app_context():
        inspector = inspect(db.engine)
        if not inspector.has_table("user"): 
            print("Таблицы не найдены, создаем...")
            db.create_all() 
            print("Таблицы успешно созданы.")
        else:
            if not inspector.has_table("card_assignees"):
                print("Таблица 'card_assignees' не найдена, создаем все таблицы (на случай других отсутствующих)...")
                db.create_all()
                print("Таблица 'card_assignees' (и возможно другие) успешно создана.")
            else:
                print("Таблицы уже существуют.")


def _seed_data():
    """Наполняет БД тестовыми данными (админ, пользователи, доски и т.д.), если админа нет."""
    with app.app_context():
        inspector = inspect(db.engine)
        if not inspector.has_table("user"): 
            print("Ошибка: Таблица 'user' не найдена. Сначала создайте таблицы командой 'flask db-create' или 'flask db-init'.")
            return
        if not inspector.has_table("card_assignees"):
            print("Ошибка: Таблица 'card_assignees' не найдена. Выполните 'flask db-create' или 'flask db-init'.")
            return

        print("Проверка необходимости наполнения БД...")
        admin_user = User.query.filter_by(email='admin@gmai.com').first()
        if not admin_user:
            print("Администратор не найден, наполняем БД тестовыми данными...")

            admin = User(username='Admin', email='admin@gmai.com', is_admin=True)
            admin.set_password('password'); db.session.add(admin)

            user1 = User(username='TestUser1', email='user1@example.com'); user1.set_password('password123'); db.session.add(user1)
            user2 = User(username='AnotherUser', email='user2@example.com'); user2.set_password('password456'); db.session.add(user2)

            try:
                db.session.commit()
                print("Пользователи (Admin, TestUser1, AnotherUser) созданы.")
            except Exception as e:
                db.session.rollback(); print(f"Ошибка при создании пользователей: {e}"); return

            admin_user = User.query.filter_by(email='admin@gmai.com').first()
            user1 = User.query.filter_by(email='user1@example.com').first()
            user2 = User.query.filter_by(email='user2@example.com').first()
            if not all([admin_user, user1, user2]): print("Ошибка получения пользователей для досок."); return

            board1 = Board(name='Проект Альфа', owner=admin_user); board1.members.append(user1); db.session.add(board1)
            board2 = Board(name='Личные задачи User1', owner=user1); db.session.add(board2)
            board3 = Board(name='Общая доска команды', owner=user2); board3.members.extend([admin_user, user1]); db.session.add(board3)

            try:
                db.session.commit()
                print("Доски (Проект Альфа, Личные задачи User1, Общая доска команды) созданы.")
            except Exception as e:
                db.session.rollback(); print(f"Ошибка при создании досок: {e}"); return

            board1 = Board.query.filter_by(name='Проект Альфа').first()
            board2 = Board.query.filter_by(name='Личные задачи User1').first()

            if board1:
                col1_1 = Column(name='Бэклог', board_id=board1.id, position=0)
                col1_2 = Column(name='В работе', board_id=board1.id, position=1)
                col1_3 = Column(name='Готово', board_id=board1.id, position=2)
                db.session.add_all([col1_1, col1_2, col1_3])
                try: db.session.commit(); print("Колонки для Доски 1 созданы.")
                except Exception as e: db.session.rollback(); print(f"Ошибка колонок Д1: {e}"); return

                card1_1 = Card(title='Настроить аутентификацию', column_id=col1_1.id)
                db.session.add(card1_1) 
                card1_1.assignees.append(admin_user)

                card1_2 = Card(title='Реализовать CRUD для досок', column_id=col1_1.id)
                db.session.add(card1_2)

                card1_3 = Card(title='Создать модели БД', column_id=col1_2.id)
                db.session.add(card1_3)
                card1_3.assignees.append(user1)
                card1_3.assignees.append(admin_user)

                card1_4 = Card(title='Настроить базовый шаблон', column_id=col1_3.id)
                db.session.add(card1_4)
                
                print("Карточки для Д1 добавлены и исполнители назначены.")

            if board2:
                col2_1 = Column(name='Сделать', board_id=board2.id, position=0)
                col2_2 = Column(name='Сделано', board_id=board2.id, position=1)
                db.session.add_all([col2_1, col2_2])
                try: db.session.commit(); print("Колонки для Доски 2 созданы.")
                except Exception as e: db.session.rollback(); print(f"Ошибка колонок Д2: {e}"); return

                card2_1 = Card(title='Купить продукты', column_id=col2_1.id)
                db.session.add(card2_1)

                card2_2 = Card(title='Закончить отчет', column_id=col2_2.id)
                db.session.add(card2_2)
                card2_2.assignees.append(user1)
                
                print("Карточки для Д2 добавлены и исполнители назначены.")

            try:
                db.session.commit()
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

# run.py
# ... (весь остальной код остается без изменений) ...

@app.cli.command("db-init")
@click.option('--force', is_flag=True, help='Удалить существующую БД перед инициализацией.')
def init_db_command(force):
    """Инициализирует БД: удаляет (если --force), создает таблицы и наполняет данными."""
    db_path = os.path.join(app.instance_path, 'mydatabase.db')
    db_exists_at_start = os.path.exists(db_path)

    if force:
        if db_exists_at_start:
            print(f"Попытка удаления существующей БД: {db_path}...")
            
            # Сначала попробуем удалить таблицы через SQLAlchemy
            # Это требует контекста приложения
            with app.app_context():
                print("Попытка закрыть активные сессии и удалить таблицы через SQLAlchemy...")
                try:
                    # db.session.close_all() # SQLAlchemy < 2.0
                    db.session.close() # Закрываем текущую сессию, если она есть
                    # db.engine.dispose() # Можно попробовать закрыть все соединения в пуле
                    print("Сессия SQLAlchemy закрыта (если была активна).")
                except Exception as e_session:
                    print(f"Примечание: Ошибка при попытке закрыть сессию SQLAlchemy: {e_session}")

                try:
                    db.drop_all()       # Удаляет все таблицы
                    print("Таблицы БД успешно удалены через SQLAlchemy.")
                except Exception as e_drop:
                    print(f"Ошибка при удалении таблиц через SQLAlchemy: {e_drop}")
                    print("Это может произойти, если файл БД все еще заблокирован.")

            # После попытки drop_all, проверим и попробуем удалить файл физически
            if os.path.exists(db_path):
                print(f"Файл БД все еще существует ({db_path}). Попытка физического удаления...")
                try:
                    os.remove(db_path)
                    print("Файл БД успешно физически удален.")
                except PermissionError as e_perm: # Явно ловим PermissionError
                    print(f"ОШИБКА ФИЗИЧЕСКОГО УДАЛЕНИЯ: {e_perm}")
                    print(f"Файл '{db_path}' заблокирован другим процессом.")
                    print("Пожалуйста, убедитесь, что Flask-приложение и другие программы,")
                    print("использующие эту БД (например, DB Browser for SQLite), закрыты, и попробуйте снова.")
                    # На этом этапе можно либо прервать скрипт, либо продолжить создание таблиц "поверх"
                    # Если drop_all не удался, то create_all тоже может не сработать корректно
                    # print("Инициализация прервана из-за невозможности удалить файл БД.")
                    # return # Раскомментируйте, если хотите прерывать выполнение
                except Exception as e_rem:
                    print(f"Не удалось физически удалить файл БД: {e_rem}")
            else:
                # Если drop_all успешно удалил и файл (иногда бывает с SQLite), то файла уже нет
                if db_exists_at_start: # Только если он изначально существовал
                     print("Файл БД был удален (вероятно, в результате db.drop_all()).")

        else: # if db_exists_at_start
            print("Файл БД не найден, удаление не требуется.")
    
    elif db_exists_at_start: # if not force and db_exists_at_start
         print(f"Файл БД '{db_path}' уже существует. Используйте '--force', чтобы удалить и пересоздать.")
         print("Инициализация прервана.")
         return 

    # Если мы дошли сюда, значит либо файла не было, либо он был удален (или его не удалось удалить, но мы продолжаем)
    print("Создание таблиц...")
    _create_tables() 
    print("Наполнение данными...")
    _seed_data()   
    print("Инициализация БД завершена.")

# ... (остальной код run.py) ...


# --- Запуск основного приложения ---
if __name__ == '__main__':
    print("Запуск Flask development-сервера...")
    print("Для создания/пересоздания БД выполните: flask db-init --force")
    print("Для простого создания таблиц (если БД нет): flask db-create")
    print("Для наполнения данными (если БД пуста): flask db-seed")
    app.run(debug=True, port=5001)