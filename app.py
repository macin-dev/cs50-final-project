from flask import Flask, request, render_template
from models import db, Device, CheckLog
from checker import check_tcp
from flask_migrate import Migrate
from sqlalchemy import func

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
    # Retrieve data from the devices table
    # Find the highest log by ID for each device
    latest_device_log = (
        db.select(
            CheckLog.device_id,
            func.max(CheckLog.id).label("max_id")
        )
        .group_by(CheckLog.device_id)
        .subquery()
    )

    # Match each device's id with the last device's id log
    stmt = (
        db.select(Device, CheckLog)
        .outerjoin(latest_device_log, Device.id == latest_device_log.c.device_id)
        .outerjoin(CheckLog, CheckLog.id == latest_device_log.c.max_id)
    )

    devices = db.session.execute(stmt).all()
    data = []

    # Serializing Python objects into JSON
    for device, log in devices:
        data.append({
            "id": device.id,
            "name": device.name,
            "host": device.host,
            "port": device.port,
            "status": log.status if log else "UNCHECKED",
            "latency": log.response_time if log else None,
            "created_at": log.created_at if log else "Never"
        })

    # Return with a status code of success
    return render_template('index.html', data=data), 200

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

    # [ROW DATA]
    row = {
        "id": device.id,
        "name": device.name,
        "host": device.host,
        "port": device.port,
        "status": new_log.status,
        "latency": new_log.response_time,
        "created_at": new_log.created_at
    }

    if  request.headers.get('Hx-Request'):
        # Return the new generated HTML template with the newest data
        return render_template('partials/_row.html', row=row)

    return row, 200


@app.route('/api/devices', methods=["POST"])
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