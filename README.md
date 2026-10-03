# Smart Expense Tracker

A lightweight Flask web app for tracking income, expenses, monthly budgets, and spending trends.

## Features

- Add income and expense transactions
- Group expenses into categories such as Food, Travel, Shopping, and more
- Set monthly budgets per category
- View monthly totals and net balance
- See category breakdowns and monthly trend charts
- Search and filter transactions
- Get budget alerts when spending nears or exceeds the budget

## Run locally

1. Open a terminal in this project folder.
2. Install dependencies:

   py -3 -m pip install -r requirements.txt

3. Start the app:

   py -3 -m flask --app app run --host 127.0.0.1 --port 5000

4. Open:

   http://127.0.0.1:5000

## Test

Run:

py -3 -m pytest -q

## Deploy on Render

The repository includes a `render.yaml` blueprint. Push the project files to the root of a GitHub repository, then create a new Blueprint on Render and select that repository. The blueprint starts the app with Gunicorn on Render's free web service plan. Its SQLite database is stored on temporary disk and may be erased after a restart or deploy.

The current app has no login or per-user data isolation. Treat a public deployment as a shared demo and do not enter private financial information. Add authentication and user-specific records before using it with real personal data.

The local `expenses.db` is intentionally excluded from Git; a deployed instance starts with its own empty database.
