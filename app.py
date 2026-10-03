import os
import sqlite3
from datetime import datetime

from flask import Flask, current_app, jsonify, render_template, request

DATABASE = os.environ.get(
    "DATABASE_PATH", os.path.join(os.path.dirname(__file__), "expenses.db")
)


def get_db_connection():
    database = current_app.config["DATABASE"]
    os.makedirs(os.path.dirname(os.path.abspath(database)), exist_ok=True)
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    conn = get_db_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
            category TEXT NOT NULL,
            description TEXT,
            amount REAL NOT NULL,
            date TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            month TEXT NOT NULL,
            UNIQUE(category, month)
        )
        """
    )
    conn.commit()
    conn.close()


def get_month_name(month_str):
    try:
        return datetime.strptime(month_str, "%Y-%m").strftime("%B %Y")
    except ValueError:
        return month_str


def get_current_month():
    return datetime.now().strftime("%Y-%m")


def get_budget_alerts(month=None):
    month = month or get_current_month()
    conn = get_db_connection()
    budgets = conn.execute(
        "SELECT category, amount FROM budgets WHERE month = ? ORDER BY category",
        (month,),
    ).fetchall()

    expenses = conn.execute(
        "SELECT category, SUM(amount) AS total FROM transactions WHERE type = 'expense' AND substr(date, 1, 7) = ? GROUP BY category",
        (month,),
    ).fetchall()
    expense_map = {row["category"]: float(row["total"] or 0) for row in expenses}

    alerts = []
    for item in budgets:
        category = item["category"]
        budget = float(item["amount"])
        spent = expense_map.get(category, 0.0)
        percent = round((spent / budget * 100), 1) if budget else 0
        warning = budget > 0 and spent >= budget * 0.8
        if warning:
            alerts.append(
                {
                    "category": category,
                    "budget": budget,
                    "spent": spent,
                    "percent": percent,
                    "warning": True,
                }
            )
    conn.close()
    return alerts


def get_summary(month=None):
    month = month or get_current_month()
    conn = get_db_connection()

    totals = conn.execute(
        """
        SELECT
            SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) AS income,
            SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) AS expenses
        FROM transactions
        WHERE substr(date, 1, 7) = ?
        """,
        (month,),
    ).fetchone()

    category_totals = conn.execute(
        """
        SELECT category, SUM(amount) AS total
        FROM transactions
        WHERE type = 'expense' AND substr(date, 1, 7) = ?
        GROUP BY category
        ORDER BY total DESC
        """,
        (month,),
    ).fetchall()

    budgets = conn.execute(
        "SELECT category, amount FROM budgets WHERE month = ? ORDER BY category",
        (month,),
    ).fetchall()

    budget_alerts = []
    for budget in budgets:
        category = budget["category"]
        limit = float(budget["amount"])
        spent = 0.0
        for row in category_totals:
            if row["category"] == category:
                spent = float(row["total"] or 0)
                break
        percent = round((spent / limit * 100), 1) if limit else 0
        warning = limit > 0 and spent >= limit * 0.8
        if warning:
            budget_alerts.append(
                {
                    "category": category,
                    "budget": limit,
                    "spent": spent,
                    "percent": percent,
                    "warning": True,
                }
            )

    income_total = float(totals["income"] or 0)
    expense_total = float(totals["expenses"] or 0)
    summary = {
        "month": month,
        "month_label": get_month_name(month),
        "totals": {
            "income": income_total,
            "expenses": expense_total,
            "net": income_total - expense_total,
        },
        "categories": [
            {"category": row["category"], "total": float(row["total"] or 0)}
            for row in category_totals
        ],
        "budgets": [
            {"category": row["category"], "amount": float(row["amount"])}
            for row in budgets
        ],
        "budget_alerts": budget_alerts,
        "budget_warning": bool(budget_alerts),
    }
    conn.close()
    return summary


def get_monthly_trend():
    conn = get_db_connection()
    months = []
    current = datetime.now()
    for offset in range(5, -1, -1):
        target = (current.replace(day=1).month - offset) % 12 or 12
        year = current.year if (current.month - offset) > 0 else current.year - 1
        month = f"{year}-{target:02d}"
        months.append(month)

    trend = []
    for month in months:
        totals = conn.execute(
            """
            SELECT
                SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) AS expenses,
                SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) AS income
            FROM transactions
            WHERE substr(date, 1, 7) = ?
            """,
            (month,),
        ).fetchone()
        trend.append(
            {
                "month": month,
                "label": get_month_name(month),
                "income": float(totals["income"] or 0),
                "expenses": float(totals["expenses"] or 0),
            }
        )
    conn.close()
    return trend


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(DATABASE=DATABASE)
    if test_config:
        app.config.update(test_config)
    with app.app_context():
        init_db()

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/transactions", methods=["GET", "POST"])
    def transactions():
        if request.method == "GET":
            month = request.args.get("month") or get_current_month()
            search = request.args.get("search", "").strip()
            category = request.args.get("category", "").strip()
            conn = get_db_connection()
            query = "SELECT * FROM transactions WHERE 1=1"
            params = []

            if month:
                query += " AND substr(date, 1, 7) = ?"
                params.append(month)
            if category:
                query += " AND category = ?"
                params.append(category)
            if search:
                query += " AND (description LIKE ? OR category LIKE ?)"
                search_value = f"%{search}%"
                params.extend([search_value, search_value])

            query += " ORDER BY date DESC, id DESC"
            rows = conn.execute(query, params).fetchall()
            conn.close()
            return jsonify([dict(row) for row in rows])

        payload = request.get_json(silent=True) or {}
        required = ["type", "category", "amount", "date"]
        missing = [field for field in required if not payload.get(field)]
        if missing:
            return jsonify({"success": False, "error": f"Missing fields: {', '.join(missing)}"}), 400

        transaction_type = payload["type"].lower()
        if transaction_type not in {"income", "expense"}:
            return jsonify({"success": False, "error": "Type must be 'income' or 'expense'"}), 400

        try:
            amount = float(payload["amount"])
        except (TypeError, ValueError):
            return jsonify({"success": False, "error": "Amount must be a number"}), 400

        if amount <= 0:
            return jsonify({"success": False, "error": "Amount must be greater than zero"}), 400

        date_value = payload["date"]
        month = date_value[:7] if len(date_value) >= 7 else get_current_month()

        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO transactions (type, category, description, amount, date)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                transaction_type,
                payload["category"],
                payload.get("description", ""),
                amount,
                date_value,
            ),
        )
        conn.commit()
        conn.close()

        alerts = get_budget_alerts(month)
        return jsonify(
            {
                "success": True,
                "message": "Transaction added successfully",
                "warning": bool(alerts),
                "budget_alerts": alerts,
            }
        )

    @app.route("/api/budgets", methods=["GET", "POST"])
    def budgets():
        if request.method == "GET":
            month = request.args.get("month") or get_current_month()
            conn = get_db_connection()
            rows = conn.execute(
                "SELECT category, amount, month FROM budgets WHERE month = ? ORDER BY category",
                (month,),
            ).fetchall()
            conn.close()
            return jsonify([dict(row) for row in rows])

        payload = request.get_json(silent=True) or {}
        required = ["category", "amount", "month"]
        missing = [field for field in required if not payload.get(field)]
        if missing:
            return jsonify({"success": False, "error": f"Missing fields: {', '.join(missing)}"}), 400

        try:
            amount = float(payload["amount"])
        except (TypeError, ValueError):
            return jsonify({"success": False, "error": "Amount must be a number"}), 400

        if amount <= 0:
            return jsonify({"success": False, "error": "Amount must be greater than zero"}), 400

        app_month = payload["month"]
        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO budgets (category, amount, month)
            VALUES (?, ?, ?)
            ON CONFLICT(category, month) DO UPDATE SET amount = excluded.amount
            """,
            (payload["category"], amount, app_month),
        )
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Budget saved"})

    @app.route("/api/summary")
    def summary():
        month = request.args.get("month") or get_current_month()
        summary_data = get_summary(month)
        summary_data["monthly_trend"] = get_monthly_trend()
        return jsonify(summary_data)

    @app.route("/api/categories")
    def categories():
        conn = get_db_connection()
        rows = conn.execute(
            "SELECT DISTINCT category FROM transactions ORDER BY category"
        ).fetchall()
        conn.close()
        return jsonify([row["category"] for row in rows])

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "5000")),
        debug=os.environ.get("FLASK_DEBUG") == "1",
    )
