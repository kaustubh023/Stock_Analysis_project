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

Frontend runs at `http://localhost:5173` (or `http://127.0.0.1:5173`). The dev server proxies `/api` to the backend.

### Production deployment note
- In local development, Vite proxies `/api` to Django.
- In production, that proxy does not exist.
- If your frontend and backend are deployed to different Azure URLs, set `VITE_API_BASE_URL` during the frontend build, for example:
  - `VITE_API_BASE_URL=https://your-backend-app.azurewebsites.net/api`
- Without that, login requests may be sent to the frontend host instead of the Django API, which causes login/register to fail.
- For an Azure VM deployment where the frontend is on `http://<vm-ip>` and Django is on `http://<vm-ip>:8000`, the frontend now automatically falls back to `http://<current-host>:8000/api` in production when `VITE_API_BASE_URL` is not set.

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

## New: BTC‑USD Hourly Forecast
- Location: Other Features → “BTC‑USD Hourly Forecast”
- Backend API: `GET /api/crypto/btcusd-hourly/`
- What it shows:
  - Current BTC‑USD price
  - ARIMA‑based forecast for the next 1 hour
  - Chart combining recent hourly history and the next‑hour prediction

## Usage Notes
- Most APIs require authentication. Log in from the frontend; the app stores tokens and calls the backend with `Authorization: Bearer <token>`.
- Default dev URLs:
  - Frontend: `http://localhost:5173`
  - Backend: `http://127.0.0.1:8000`
