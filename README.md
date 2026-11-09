# StockSaathi

StockSaathi is a voice-first inventory assistant for shop owners. The voice conversation is the primary way to change stock; the dashboard is for viewing inventory, activity, and business summaries.

## Run locally

1. Keep the existing Neon/Google auth configuration and provider keys in `.env`. Required backend settings are `DATABASE_URL`, `NEON_AUTH_BASE_URL`, `GROQ_API_KEY`, and `GNANI_API_KEY`.
2. Install Python dependencies: `pip install -r requirements.txt`.
3. Build the React app: `cd frontend`, `npm install`, `npm run build`.
4. From the project root, start the API and UI: `uvicorn main:app --reload`.
5. Open `http://127.0.0.1:8000` and choose **Continue with Google**. Neon Auth completes sign-in, the client obtains its JWT, and the backend verifies it against Neon JWKS. If this is the first login for that user, StockSaathi asks for shop details and creates the profile; returning users go straight to the dashboard.

For frontend development, run `npm run dev` from `frontend`; Vite proxies API and WebSocket requests to `http://127.0.0.1:8000`.

## Voice workflow

The browser sends mono 16 kHz PCM16 microphone chunks over `/voice/ws/voice`. The server authenticates the existing Neon access token, streams audio to Gnani Prisma STT, and sends the transcript to the Qwen-powered LangGraph manager. The manager returns ordered tasks with task-specific details. Deterministic validation asks for missing information; stock-changing tasks are read back and require a clear yes/no confirmation. After confirmation, the inventory specialist calls the existing stock services, which update inventory and append stock movement records. Read-only questions go to the business intelligence specialist. The final response is returned as text and generated as WAV audio with Gnani TTS.

The React dashboard has Overview, Inventory, Products, Activity, and Insights views. Overview keeps the voice assistant centered and includes sales/purchases timeline charts, stock alerts, and top sellers.

## Notes

- Stock changes are initiated through the voice assistant. Dashboard APIs are read-only; product catalogue CRUD remains available.
- Dashboard analytics use stock movement records. Gross profit is an estimate based on the stored weighted-average purchase cost; it is not net profit.
- Tables are created from SQLAlchemy models at startup for this WIP app. `create_all` creates missing tables but does not migrate existing columns.
- For safer production conversation continuity, replace the current in-memory voice session store with a persistent LangGraph checkpointer.
