# House Rental Management System

## Setup
1. Create virtualenv: `python -m venv venv`
2. Activate: `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Linux/Mac)
3. Install: `pip install -r requirements.txt`
4. Create uploads folder: `mkdir -p static/uploads`
5. Run `python init_db.py` to create the SQLite DB
6. Start app: `python app.py`
7. Open `http://127.0.0.1:5000/` in browser

## Notes
- To enable email sending configure environment variables for MAIL_USERNAME, MAIL_PASSWORD, and MAIL_DEFAULT_SENDER.
- For production, disable `debug=True`, use a production server (gunicorn), and a proper DB (MySQL/Postgres).
