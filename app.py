# app.py
from __future__ import annotations
import os
from datetime import datetime
from decimal import Decimal
from flask import Flask, render_template, request, redirect, url_for, jsonify
from dotenv import load_dotenv
from models import db, Person, Expense, AppState
from logic import calculate_balances, calculate_settlements

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")

    # --- DB URL normalization (psycopg v3 driver) ---
    db_url = (os.getenv("DATABASE_URL") or "").strip()
    if db_url:
        # Providers sometimes give postgres:// or postgresql://
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql+psycopg://", 1)
        elif db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)
    else:
        # Fallback to SQLite locally
        db_url = "sqlite:///dev.db"

    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    with app.app_context():
        db.create_all()
        _ensure_state()

    # ---------- realtime version API ----------
    @app.route("/api/version")
    def api_version():
        return jsonify({"version": _get_state().version})

    # --------------- pages/routes ---------------
    @app.route("/")
    def index():
        people = [p.name for p in Person.query.order_by(Person.name).all()]

        expenses = []
        for e in Expense.query.order_by(Expense.id.desc()).all():
            expenses.append({
                "id": e.id,
                "description": e.description,
                "amount": float(e.amount),  # Decimal -> float for display
                "paid_by": e.paid_by.name,
                "participants": [p.name for p in e.participants],
                "date": e.date,
            })

        balances = calculate_balances(people, expenses)
        settlements = calculate_settlements(balances)

        return render_template(
            "index.html",
            people=people,
            expenses=expenses,
            balances=balances,
            settlements=settlements,
        )

    @app.route("/add_person", methods=["POST"])
    def add_person():
        name = (request.form.get("name") or "").strip()
        if not name:
            return redirect(url_for("index"))

        existing = Person.query.filter_by(name=name).first()
        if not existing:
            db.session.add(Person(name=name))
            db.session.commit()
            _bump_state()
        return redirect(url_for("index"))

    @app.route("/remove_person/<person>")
    def remove_person(person):
        p = Person.query.filter_by(name=person).first()
        if not p:
            return redirect(url_for("index"))

        # Detach from expenses where they are a participant
        for e in list(p.participated_expenses):
            e.participants = [x for x in e.participants if x.id != p.id]
            if not e.participants:  # if nobody left, delete expense
                db.session.delete(e)

        # Delete expenses they paid
        for e in list(p.paid_expenses):
            db.session.delete(e)

        db.session.delete(p)
        db.session.commit()
        _bump_state()
        return redirect(url_for("index"))

    @app.route("/add_expense", methods=["POST"])
    def add_expense():
        description = (request.form.get("description") or "").strip()
        amount_raw = (request.form.get("amount") or "").strip()
        paid_by_name = (request.form.get("paid_by") or "").strip()
        participants_names = [x for x in request.form.getlist("participants") if x.strip()]

        if not description or not amount_raw or not paid_by_name or not participants_names:
            return redirect(url_for("index"))

        try:
            amount = Decimal(amount_raw).quantize(Decimal("0.01"))  # Numeric(10,2)
        except Exception:
            return redirect(url_for("index"))

        paid_by = Person.query.filter_by(name=paid_by_name).first()
        if not paid_by:
            return redirect(url_for("index"))

        participants = Person.query.filter(Person.name.in_(participants_names)).all()
        if not participants:
            return redirect(url_for("index"))

        e = Expense(
            description=description,
            amount=amount,
            paid_by=paid_by,
            date=datetime.now().strftime("%Y-%m-%d"),
        )
        e.participants = participants

        db.session.add(e)
        db.session.commit()
        _bump_state()
        return redirect(url_for("index"))

    @app.route("/delete_expense/<int:expense_id>")
    def delete_expense(expense_id: int):
        e = Expense.query.get(expense_id)
        if e:
            db.session.delete(e)
            db.session.commit()
            _bump_state()
        return redirect(url_for("index"))

    return app

# ---------- state helpers (module-level) ----------
def _ensure_state():
    st = AppState.query.get(1)
    if not st:
        st = AppState(id=1, version=1)
        db.session.add(st)
        db.session.commit()

def _get_state() -> AppState:
    st = AppState.query.get(1)
    if not st:
        st = AppState(id=1, version=1)
        db.session.add(st)
        db.session.commit()
    return st

def _bump_state():
    st = _get_state()
    st.version += 1
    db.session.commit()

app = create_app()

if __name__ == "__main__":
    # For local dev: flask run OR python app.py
    app.run(debug=True, host="0.0.0.0", port=5000)
