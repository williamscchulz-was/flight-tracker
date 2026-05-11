# Routine Prompt — Flight Tracker NVT → MEX

Cola exatamente isso no campo "Prompt" da Routine:

---

You are running the daily flight tracker for trip NVT → MEX on 2026-10-30.

Steps:
1. Install dependencies: `pip install -r requirements.txt`
2. Run the script: `python flight_check.py`

The script queries Google Flights via fast-flights, filters by duration (≤16h) and price (<R$3000/adulto), and posts an embed to Discord. Errors are also posted as a red embed to the same webhook.

After execution:
- If exits 0 and printed "Discord delivered.", report success briefly.
- If exits non-zero, share the stderr output for debugging — don't try to "fix" the script automatically.
- If fast-flights raises a parser/network error, Google Flights likely changed something. Don't patch the code — report so I can update the library version or pivot to a paid API.

Do NOT modify `flight_check.py` unless I explicitly ask. Just execute and report.
