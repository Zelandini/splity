# models.py
from __future__ import annotations
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Numeric
from datetime import datetime

db = SQLAlchemy()

expense_participants = db.Table(
    "expense_participants",
    db.Column("expense_id", db.Integer, db.ForeignKey("expenses.id"), primary_key=True),
    db.Column("person_id", db.Integer, db.ForeignKey("people.id"), primary_key=True),
)

class Person(db.Model):
    __tablename__ = "people"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)

    def __repr__(self) -> str:
        return f"<Person {self.name}>"

class Expense(db.Model):
    __tablename__ = "expenses"
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(255), nullable=False)
    # Store as Numeric, do cents math in Python to avoid drift
    amount = db.Column(Numeric(10, 2), nullable=False)
    paid_by_id = db.Column(db.Integer, db.ForeignKey("people.id"), nullable=False)
    date = db.Column(db.String(32), nullable=False, default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))

    paid_by = db.relationship("Person", backref="paid_expenses")
    participants = db.relationship("Person", secondary=expense_participants, backref="participated_expenses")

    def __repr__(self) -> str:
        return f"<Expense {self.description} ${self.amount}>"
