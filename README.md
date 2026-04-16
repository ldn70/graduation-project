# Graduation Project Rebuild

This repository contains the rebuild of the "51job recruitment analysis system".

## Progress (Day 1)
- Django + DRF backend scaffold.
- User APIs: register, login, update profile, delete account.
- Job API: search with pagination.
- Resume APIs: generate and download.
- Vue3 demo UI: login, job search, resume generation, ECharts chart.
- Planning and delivery docs under `docs/`.

## Local Run

### 1) Backend
```powershell
cd D:\GraduationProject
.\.venv\Scripts\python -m pip install -r .\backend\requirements.txt
cd .\backend
..\.venv\Scripts\python manage.py migrate
..\.venv\Scripts\python manage.py seed_jobs
..\.venv\Scripts\python manage.py runserver
```

### 2) Frontend
```powershell
cd D:\GraduationProject\frontend
npm install
npm run dev
```

Access:
- Frontend: `http://127.0.0.1:5173`
- Backend: `http://127.0.0.1:8000`

## Docker Run (Optional)
```powershell
cd D:\GraduationProject
docker compose up --build
```

## Main APIs
- `POST /api/users/register`
- `POST /api/users/login`
- `PUT /api/users/profile`
- `DELETE /api/users/delete`
- `GET /api/jobs/search`
- `GET /api/recommend/jobs`
- `GET /api/skills/demand`
- `GET /api/skills/match`
- `POST /api/salary/predict`
- `GET /api/trends/jobs`
- `POST /api/resume/generate`
- `GET /download/<filename>`

## CSV Data Import
```powershell
cd D:\GraduationProject\backend
..\.venv\Scripts\python manage.py import_jobs_csv --file D:\GraduationProject\backend\data\sample_jobs.csv --truncate
```
