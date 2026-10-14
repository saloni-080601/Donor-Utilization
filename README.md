# Donor Utilization Automation

Web app that turns Tally exports into donor reports. Donor rules live in settings, not code. Money is stored as exact decimals in Postgres.

## Stack

- Postgres 16 (local Homebrew, or Docker Compose)
- FastAPI allocation engine, publish checks, audit log
- Next.js dashboard
- Excel (openpyxl) and PDF (ReportLab) UC exports

## Run locally

Postgres is expected on `localhost:5432` as the current macOS user, database `donor_uc`.

```bash
# already created during setup:
# brew services start postgresql@16
# createdb donor_uc

cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

cd ../frontend
npm install
npm run dev
```

Open http://localhost:3000

| Role | Email | Password | Access |
| --- | --- | --- | --- |
| Finance | finance@org.local | finance123 | All grants, uploads, mappings, publish |
| Programme lead | lead@org.local | lead123 | EDU-PILOT only |

Sample Tally files: `backend/sample_data/`.

## How the numbers work

1. Pool share = grant approved ÷ total approved in that pool.
2. Ledger cost = direct + (campus pool × campus share) + (central pool × central share).
3. Pace flags spend behind a straight line to the grant end date.
4. Budget vs actual groups ledger costs by budget head.

Publish is blocked when a ledger is unmapped, mapped actuals miss the grant total by more than ₹1, pool shares miss 100%, location figures miss the approved amount, or the period is inverted.

## Tests

```bash
cd backend && .venv/bin/pytest
```

The EDU-PILOT sample must match to the rupee: direct ₹15,80,000 + campus ₹1,20,000 + central ₹1,20,000 = ₹18,20,000.
# Donor-Utilization
