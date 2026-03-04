# KP Stock Project

## Backend (Django)
1. `cd backend`
2. `python -m venv .venv`
3. `.venv\Scripts\activate`
4. `pip install -r requirements.txt`
5. `python manage.py migrate`
6. `python manage.py runserver`

Backend runs at `http://127.0.0.1:8000`.

## Frontend (React + Vite)
1. `cd frontend`
2. `npm install`
3. `npm run dev`

Frontend runs at `http://127.0.0.1:5173`.

## Implemented Features
- User register and login (JWT)
- Portfolio type creation
- Sector selection and Indian stock search (name or ticker)
- Add selected stock to user portfolio
- Stock details screen with:
  - Symbol, company, PE ratio, min, max, current, EPS, market cap, intrinsic, discount %, opportunity
  - Opportunity graph, discount graph, PE graph (last 1 year yfinance data)
- Portfolio PE ratio comparison graph
- Compare 2 portfolio stocks by return/volatility/sharpe and identify more profitable stock
- Gold/Silver 5-year correlation module with:
  - Correlation value
  - Line graph
  - Scatter graph
  - Linear regression graph
