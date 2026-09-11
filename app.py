from flask import Flask, request
from models import db, Device, CheckLog
from checker import check_tcp
from flask_migrate import Migrate

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///netwatch.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Connect db with this app
db.init_app(app)

# Enable batch mode for sqlite
migrate = Migrate(app, db, render_as_batch=True)

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

@app.route('/api/devices', methods=["GET", "POST"])
def add_device():
    user_id = 1

    # [POST] requests
    # Handling incoming JSON
    if request.method == "POST":
        data = request.get_json()

        # Validate input
        if not data or not data.get("name") or not data.get("host"):
            # 400 status code for malformed requests
            return {"error": "Missing required fields"}, 400
        
        # Create instance of Device
        new_device = Device(
            user_id=user_id,
            name=data.get("name"),
            model=data.get("model"),
            host=data.get("host"),
            protocol=data.get("protocol", "HTTP"),
            port=data.get("port")
        )

        # Commit to the database
        db.session.add(new_device)
        db.session.commit()

        return {
            "message": "Device added succsessfully",
            "id": new_device.id
        }, 201

    # [GET] requests
    # Retrieve data from the devices table
    devices = Device.query.all()

    results = []

    # Serializing Python objects into JSON
    for d in devices:
        results.append({
            "id": d.id,
            "name": d.name,
            "host": d.host,
            "port": d.port,
            "protocol": d.protocol,
            "model": d.model
        })

    # Return with a status code of success
    return results, 200

@app.route('/api/devices/<int:device_id>', methods=["DELETE"])
def delete_device(device_id):
    # Lookup the device
    device = db.get_or_404(Device, device_id)
    
    # Execute a SQLAlchemy statement
    db.session.delete(device)
    db.session.commit()

    return {
        "message": "Device deleted",
        "id": device.id
    }, 200


@app.route('/api/devices/<int:device_id>/logs')
def device_logs(device_id):
    device = db.get_or_404(Device, device_id)
    logs = device.check_logs

    results = []

    for l in logs:
        results.append({
            "id": l.id,
            "status": l.status,
            "created_at": l.created_at,
            "response_time": l.response_time
        })

    return results, 200

# Activate auto-reloader and debug mode
if __name__ == "__main__": 
    app.run(debug=True)