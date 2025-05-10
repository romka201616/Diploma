from app import app, db
from app.models import User, Board, Column, Card

if __name__ == '__main__':
    app.run(debug=True) # debug=True здесь, или через set FLASK_DEBUG=1