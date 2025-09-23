from flask import Flask

app = Flask(__name__)
app.config.from_pyfile("config.py")

from models import *

db.init_app(app)

from routes import bp

app.register_blueprint(bp)

from services.load_data import load_map

with app.app_context():
    db.create_all()
    load_map()

if __name__ == "__main__":
    app.run(debug=True)
