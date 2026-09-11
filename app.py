from flask import Flask
from models import db, Device, CheckLog
from checker import check_tcp

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

@app.route('/api/devices/<int:device_id>/check')
def check_device(device_id):
    # Retrieve the device from the database 
    # and check the TCP connection
    device = db.get_or_404(Device, device_id)
    conn = check_tcp(device.host, device.port)

    # Record new row in the check_logs
    new_log = CheckLog(
        device_id=device_id,
        status=conn["status"],
        response_time=conn["response_time"],
    )

    # Commit changes to the database
    db.session.add(new_log)
    db.session.commit()

    # Returns a JSON response with the result
    return { 
        "message": "log created successfully"
    }, 200


# Activate auto-reloader and debug mode
if __name__ == "__main__": 
    app.run(debug=True)