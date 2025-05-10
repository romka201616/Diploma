from app import app, db
from app.models import User, Board, Column, Card # Убедитесь, что все модели импортированы

# Создание таблиц перед первым запросом, если они не существуют
# Это нужно делать в контексте приложения
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, port=5001) # Убедитесь, что порт указан, если вы его меняли, debug=True здесь, или через set FLASK_DEBUG=1