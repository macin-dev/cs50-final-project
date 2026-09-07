from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

db = SQLAlchemy()

# Classes like Tables 
class User(db.Model):
    __tablename__ = "users"

    # Attributes
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50),unique=True, nullable=False)
    email = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    devices = db.relationship('Device', backref='owner', lazy=True, cascade='all, delete-orphan')


class Device(db.Model):
    __tablename__ = "devices"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'),  nullable=False)
    name = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(50), nullable=True)
    host = db.Column(db.String(50), nullable=False)
    protocol = db.Column(db.String(20), nullable=False)
    port = db.Column(db.Integer, nullable=True)

    checklogs = db.relationship('CheckLog', backref='device', lazy=True, cascade='all, delete-orphan')


class CheckLog(db.Model):
    __tablename__ = "check_logs"

    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id'), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    response_time = db.Column(db.Float, nullable=True)