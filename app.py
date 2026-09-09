from flask import Flask
from models import db

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///netwatch.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Connect db with this app
db.init_app(app)

# Create tables
with app.app_context():
    db.create_all()

# Routes
@app.route('/')
def index():
    return "<h1>NetWatch is running!</h1>"


# Activate auto-reloader and debug mode
if __name__ == "__main__": 
    app.run(debug=True)