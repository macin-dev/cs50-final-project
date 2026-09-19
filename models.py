from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey, String, desc
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from datetime import datetime, timezone

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Classes like Tables 
class User(db.Model):
    __tablename__ = "users"

    # Attributes
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    email: Mapped[str] = mapped_column(String(50), unique=True)
    password_hash: Mapped[str] = mapped_column(String(256))

    # Allow access back to the user's data trought the Device table
    devices: Mapped[list["Device"]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan"
    )


class Device(db.Model):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(50))
    model: Mapped[str | None] = mapped_column(String(50), nullable=True)
    host: Mapped[str] = mapped_column(String(50))
    protocol: Mapped[str | None] = mapped_column(nullable=True)
    port: Mapped[int | None] = mapped_column(nullable=True, default=80)

    # Allow access back to the device's data trought the CheckLog table
    owner: Mapped["User"] = relationship(back_populates="devices")

    check_logs: Mapped[list["CheckLog"]] = relationship(
        order_by=lambda: desc(CheckLog.created_at),
        back_populates="device",
        cascade="all, delete-orphan"
    )


class CheckLog(db.Model):
    __tablename__ = "check_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"))
    status: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    response_time: Mapped[float | None]

    device: Mapped["Device"] = relationship(
        back_populates="check_logs"
    )

    