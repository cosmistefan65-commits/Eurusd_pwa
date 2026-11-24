# EUR/USD Intelligence — PWA

## File principali
- `app.py`: backend FastAPI, chiave Twelve Data solo lato server.
- `static/`: interfaccia PWA.
- `requirements.txt`: dipendenze.
- `runtime.txt`: Python 3.12 per Render.

## Pubblicazione su Render
1. Caricare tutti i file nella radice della repository GitHub, mantenendo la cartella `static`.
2. Creare un Web Service collegato alla repository.
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `python -m uvicorn app:app --host 0.0.0.0 --port $PORT`
5. Environment: `TWELVE_DATA_KEY` = la propria chiave Twelve Data.

Non inserire la chiave API in `app.py` o nei file della cartella `static`.
