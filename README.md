# PrimeStay Pro – Flask Property Manager

Features
- Public listings with search/filter
- Property detail with gallery
- Applications & contact form (stored in DB)
- Admin dashboard with auth (Flask-Login)
- Multiple admins supported
- Create/Edit/Delete properties
- Multiple image uploads per property (stored in static/uploads/<property_id>/)
- Deployment ready (Procfile, requirements.txt)

## Quick Start (Local)
```
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
export FLASK_SECRET="change-me"  # Windows: set FLASK_SECRET=change-me
export ADMIN_EMAIL="admin@example.com"
export ADMIN_PASSWORD="changeme123"
python app.py
```
Open http://127.0.0.1:5000/

## Admin Login
- Go to /admin/login
- Use ADMIN_EMAIL / ADMIN_PASSWORD (change via env variables). The first run auto-creates this admin.

## Deploy (Render/Heroku)
- Make sure to set env vars: FLASK_SECRET, ADMIN_EMAIL, ADMIN_PASSWORD
- Render: create a new Web Service, Build command `pip install -r requirements.txt`, Start command `gunicorn app:app`
- Heroku: `heroku create && git push heroku main` (or use dashboard), set Config Vars accordingly.
