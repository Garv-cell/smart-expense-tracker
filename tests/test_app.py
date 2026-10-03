from app import create_app


def test_homepage_loads(tmp_path):
    app = create_app({"DATABASE": str(tmp_path / "expenses.db")})
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b"Smart Expense Tracker" in response.data


def test_transaction_and_budget_summary(tmp_path):
    app = create_app({"DATABASE": str(tmp_path / "expenses.db")})
    client = app.test_client()

    client.post(
        "/api/budgets",
        json={
            "category": "Food",
            "amount": 100,
            "month": "2026-10",
        },
    )

    response = client.post(
        "/api/transactions",
        json={
            "type": "expense",
            "category": "Food",
            "amount": 80,
            "description": "Groceries",
            "date": "2026-10-03",
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True

    summary = client.get("/api/summary?month=2026-10")
    assert summary.status_code == 200
    summary_data = summary.get_json()
    assert summary_data["totals"]["expenses"] == 80
    assert summary_data["budget_warning"] is True
    assert any(item["category"] == "Food" for item in summary_data["budget_alerts"])
