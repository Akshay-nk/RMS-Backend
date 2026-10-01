# RMS-Backend
## Restaurant POS and Website

The project is a React frontend backed by a Python FastAPI service and SQLite.

### Run locally

Requirements: Python 3.10+ and Node.js 20.19+ or 22.12+.

1. Create a virtual environment with `python -m venv .venv`.
2. Install backend dependencies with `.venv\\Scripts\\pip install -r backend\\requirements.txt` on Windows, or activate `.venv` and run `pip install -r backend/requirements.txt` on macOS/Linux.
3. Install frontend dependencies with `cd frontend && npm install`.
4. Start both services with `run.bat` on Windows. To start them separately, run `python main.py` from `backend/` and `npm run dev` from `frontend/`.
5. Open `http://localhost:5173`; FastAPI docs are at `http://127.0.0.1:8000/docs`.

The application includes customer accounts, menu browsing, reservations, membership profiles, staff login, POS ordering and payments, kitchen orders, management panels, and sales/revenue reports. The starter database is created at `backend/restaurant.db` from `backend/seed_data.sql` on first startup. Keep the local database to preserve changes.

## Example accounts

| Role | Email | Password |
|---|---|---|
| Customer | dadsvawvid@gmail.com | david4pass |
| Customer | zoe@gmail.com | passworddef |
| Customer | jackie@gmail.com | passwordstu |
| Staff | 1 | password123 |
| Staff | 10 | davidpa2ss |
| Staff | 7 | robertpass |
| Admin | 99999 | 12345 |

## Screenshots

![Restaurant home page](frontend/public/screenshots/homehomepage.png)

## Contributors

| Name | Github |
|---|---|
| Bryan | https://github.com/BryanTheLai |
| Yong | https://github.com/ahhyang |
| Kevin | https://github.com/kevin07212004 |
| Edzer | https://github.com/edsaur |


