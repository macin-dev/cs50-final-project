import os
from flask import Flask, request, render_template, session, redirect
from models import db, Device, CheckLog, User
from checker import check_tcp
from flask_migrate import Migrate
from sqlalchemy import func, or_
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ["NETWATCH_SECRET_KEY"]
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

    # Filter data out through HX request when searching for a text
    search_term = request.args.get("search", "").strip()
    if search_term:
        # Filter out data through SQLAlchemy
        stmt = (
            stmt.where(
                or_(
                    Device.name.ilike(f"%{search_term}%"),
                    Device.host.ilike(f"%{search_term}%")
                ))
        )

    devices = db.session.execute(stmt).all()
    data = []

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

    # Return the filtered data as HTML table with rows
    if request.headers.get("Hx-Request"):
            return render_template('partials/_table_rows.html', items=data), 200

    # Return with a status code of success
    return render_template('index.html', data=data, user=user, search_term=search_term), 200


@app.route('/api/devices/<int:device_id>/check', methods=["POST"])
def check_device(device_id):
    # Redirect unauthorized users
    if not session.get("user_id"):
        return {"error": "Unauthorized"}, 401

    # Retrieve the device from the database 
    # and check the TCP connection
    device = db.get_or_404(Device, device_id)

    # Ensures the user owns this device
    if device.user_id != session.get("user_id"):
        return {"error": "Forbidden"}, 403

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
    if request.method == "POST":

        data =  request.form

        deviceName = data.get("name", "").strip()
        host = data.get("host", "").strip()
        protocol = data.get("protocol", "HTTP").strip().upper()
        raw_port = data.get("port")

        # [FORM VALIDATION]
        # Format error dic
        errors = {}

        if not raw_port:
            # Simple default port mapping table:
            DEFAULT_PORTS = {
                "HTTP": 80,
                "HTTPS": 443,
                "SSH": 22,
                "SMTP": 587,
                "DNS": 53
            }

            port = DEFAULT_PORTS.get(protocol, 80)
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
            host=host,
            protocol=protocol,
            port=port
        )

        # Commit to the database
        db.session.add(new_device)
        db.session.commit()

        if request.headers.get('Hx-Request'):
            return (
                "",
                200,
                { 
                    "HX-Trigger": "device-created"
                },
            )

        return {
            "message": "Device added succsessfully",
            "id": new_device.id
        }, 201

    return render_template('partials/_form.html'), 200


@app.route('/api/devices/<int:device_id>', methods=["DELETE"])
def delete_device(device_id):
    if not session.get("user_id"):
        return {"error": "Unauthorized"}, 401
    
    # Ensures the user owns this device
    device = db.get_or_404(Device, device_id)
    if device.user_id != session.get("user_id"):
        return {"error": "Forbidden"}, 403
    
    # Execute a SQLAlchemy statement
    db.session.delete(device)
    db.session.commit()

    if request.headers.get('Hx-Request'):
        return (
            "",
            200,
            {
                "HX-Trigger": "device-deleted"
            }
        )
    
    return {
        "message": "Device deleted",
        "id": device.id
    }, 200


@app.route('/api/devices/<int:device_id>/logs')
def device_logs(device_id):
    # Redirect unauthorized users
    if not session.get("user_id"):
       return {"error": "Unauthorized"}, 401

    device = db.get_or_404(Device, device_id)

    # Ensures the user owns this device
    if device.user_id != session.get("user_id"):
        return {"error": "Forbidden"}, 403

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
        email = request.form.get("email", "").lower().strip()
        password = request.form.get("password", "")

        errors = {}

        # Validate data
        if not email:
            errors["email"] = "Missing email"
        if not password:
            errors['password'] = "Missing password"

        if errors:
            if request.headers.get("Hx-Request"):
                return (
                    render_template("partials/_errors.html", errors=errors),
                    200,
                    {
                        "Hx-Retarget": "#auth-errors",
                        "Hx-Reswap": "innerHTML"
                    }
                )
            return errors, 400

        # Check against database information
        stmt = db.select(User).where(User.email == email)
        user = db.session.scalar(stmt)

        # Ensure user exists and password is correct
        if not user or not check_password_hash(user.password_hash, password):
            errors["error"] = "Invalid username and/or password"
            if request.headers.get("Hx-Request"):
                return (
                    render_template("partials/_errors.html", errors=errors),
                    200,
                    {
                        "Hx-Retarget": "#auth-errors",
                        "Hx-Reswap": "innerHTML"
                    }
                )
            return errors, 401

        # Remember which user has logged in
        session["user_id"] = user.id

        # Redirect
        return "", 200, {"HX-Redirect": "/"}

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():

    # [POST]
    if request.method == "POST":
        fullname = request.form.get("fullName", "").lower().strip()
        email = request.form.get("email", "").lower().strip()
        password = request.form.get("password", "")
        confirmation = request.form.get("confirmation", "")

        # Validate data
        errors = {}

        if not fullname:
            errors["fullName"] = "Missing name"
        if not email:
            errors["email"] = "Missing email"
        if not password:
            errors["password"] = "Missing password"

        if errors:
            if request.headers.get("Hx-Request"):
                return (
                    render_template("partials/_errors.html", errors=errors),
                    200,
                    {
                        "Hx-Retarget": "#auth-errors",
                        "Hx-Reswap": "innerHTML"
                    }
                )
            return errors, 400

        # Check for matched password 
        if password != confirmation:
            errors["error"] = "Password must be the same"
            if request.headers.get("Hx-Request"):
                return (
                    render_template("partials/_errors.html", errors=errors),
                    200,
                    {
                        "Hx-Retarget": "#auth-errors",
                        "Hx-Reswap": "innerHTML"
                    }
                )
            return errors, 400

        # Check duplicate emails
        existing_user = db.session.scalar(db.select(User).where(User.email == email))
        if existing_user: 
            errors["error"] = "Email is already registered"
            if request.headers.get("Hx-Request"):
                return (
                    render_template('partials/_errors.html', errors=errors),
                    200,
                    {
                        "Hx-Retarget": "#auth-errors",
                        "Hx-Reswap": "innerHTML"
                    }
                )
            return errors, 400
        
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

        if request.headers.get("Hx-Request"):
            return "", 200, {"HX-Redirect": "/login"}

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