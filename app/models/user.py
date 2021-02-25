from __future__ import annotations

from sqlalchemy.sql import expression

from app.models.db import BaseModel, TimeBaseModel, db


class User(TimeBaseModel):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, index=True, unique=True)

    start_conversation = db.Column(db.Boolean, server_default=expression.false())
    lang = db.Column(db.String, default="fa")
    role = db.Column(db.Integer, default=0)  # 0==User, 1==Admin, 2==Superuser
    active = db.Column(db.Boolean, default=expression.false())


class UserRelatedModel(BaseModel):
    __abstract__ = True

    user_id = db.Column(
        db.ForeignKey(
            f"{User.__tablename__}.id", ondelete="CASCADE", onupdate="CASCADE"
        ),
        nullable=False,
    )
