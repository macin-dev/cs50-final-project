from flask import Flask, request, render_template, session, redirect
from models import db, Device, CheckLog, User
from checker import check_tcp
from flask_migrate import Migrate
from sqlalchemy import func
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

app.config["SECRET_KEY"] = "secret-key-netwatch"
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
    # Redirect unauthorized users
    if not session.get("user_id"):
        return redirect("/login")

    # Find user
    user = db.get_or_404(User, session.get("user_id"))

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
        .where(Device.user_id == session.get("user_id"))
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
    return render_template('index.html', data=data, user=user), 200

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


@app.route('/api/devices', methods=["GET", "POST"])
def add_device():

    user_id = session.get("user_id")

    # Deny access to not logged in users
    if not user_id:
        return {"error": "Unauthorized. Please log in."}, 401

    # [POST] requests
    # Handling incoming JSON
    if request.method == "POST":

        data = request.get_json(silent=True) or request.form

        deviceName = data.get("name", "").strip()
        host = data.get("host", "").strip()
        model = data.get("model", "").strip()
        protocol = data.get("protocol", "HTTP")
        raw_port = data.get("port")

        # [FORM VALIDATION]
        # Format error dic
        errors = {}

        if not raw_port:
            errors['port'] = "Port is missing"
        else: 
            try: 
                port = int(raw_port)

                if port < 1 or port > 65535:
                    errors["port"] = "Invalid port, valid range: 1 - 65535"
            except ValueError:
                errors["port"] = "Invalid port, valid range: 1 - 65535"

        if not deviceName or not host:
            if not deviceName: 
                errors['name'] = "Device name is missing" 
            if not host: 
                errors["host"] = "Host is missing"

        if errors:
            if request.headers.get('Hx-Request'):
                return (
                    render_template('partials/_errors.html', errors=errors), 
                    200, 
                    {
                        "Hx-Retarget": "#form-errors",
                        "Hx-Reswap": "innerHTML"
                    }
                )
            else: 
                return errors, 400
        
        # Create instance of Device
        new_device = Device(
            user_id=user_id,
            name=deviceName,
            model=model,
            host=host,
            protocol=protocol,
            port=port
        )

        # Commit to the database
        db.session.add(new_device)
        db.session.commit()

        row = {
            "id": new_device.id,
            "name": new_device.name,
            "host": new_device.host,
            "port": new_device.port,
            "status": "UNCHECKED",
            "latency": None,
            "created_at": "Never"
        }

        if (request.headers.get('Hx-Request')):
            return (
                render_template("partials/_row.html", row=row), 
                200,
                { 
                    "HX-Trigger-After-Swap": "device-created"
                },
            )

        return {
            "message": "Device added succsessfully",
            "id": new_device.id
        }, 201

    return render_template('partials/_form.html'), 200

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


    if request.headers.get('Hx-Request'):
        return render_template('partials/_history.html', device=device, logs=results), 200

    return results, 200


@app.route("/login", methods=["GET", "POST"])
def login():
    # [POST]
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        errors = {}

        # Validate data
        if not email:
            errors["email"] = "Missing email"
        if not password:
            errors['password'] = "Missing password"

        if errors:
            return errors, 400

        # Check against database information
        stmt = db.select(User).where(User.email == email)
        user = db.session.scalar(stmt)

        # Ensure user exists and password is correct
        if not user or not check_password_hash(user.password_hash, password):
            return {"message": "Invalid username and/or password"}, 401

        # Remember which user has logged in
        session["user_id"] = user.id

        # Redirect
        return redirect('/')

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():

    # [POST]
    if request.method == "POST":
        fullname = request.form.get("fullName", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        confirmation = request.form.get("confirmation", "").strip()

        # Validate data
        errors = {}

        if not fullname:
            errors["fullname"] = "Missing name"
        if not email:
            errors["email"] = "Missing email"
        if not password:
            errors["password"] = "Missing password"

        if errors:
            return errors, 400

        # Check duplicate emails
        existing_user = db.session.scalar(db.select(User).where(User.email == email))
        if existing_user: 
            return {"error": "Email is already registered"}, 400

        if password != confirmation:
            return {"message": "Password must be the same"}, 400
        
        # Hash the password
        hashed = generate_password_hash(password)

        # Create the user
        new_user = User(
            name=fullname,
            email=email,
            password_hash=hashed
        )

        # Commit it to the database
        db.session.add(new_user)
        db.session.commit()

        return redirect("/login")

    # [GET]
    return render_template("register.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# Activate auto-reloader and debug mode
if __name__ == "__main__": 
    app.run(debug=True)