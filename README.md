# StockSaathi — 1-Page Solution Pitch

> **Challenge:** Great Indian AI Internship Challenge by [Gnani.ai](https://gnani.ai)  
> **Tagline:** Voice-first AI inventory & retail intelligence partner for Indian shop owners  
> **Live App:** [https://stock-saathi.vercel.app](https://stock-saathi-2ijoazgs7-bushras-projects-61528a62.vercel.app/) | **Backend API:** [https://stock-saathi-backend-ynd4.onrender.com](https://stock-saathi-backend-ynd4.onrender.com)  

---

### 1. Problem Statement
Millions of small retail and kirana shop owners across India manage dozens of customer transactions and supplier deliveries every single day. Traditional POS software and manual pen-and-paper registers (bahi-khata) cause friction: unrecorded sales, inventory mismatches, forgotten stock reorders, and unaccounted damaged goods. Shopkeepers cannot waste time navigating complex desktop menus or typing on keyboards while attending to customers.

### 2. Proposed Solution: StockSaathi
**StockSaathi** is a hands-free, voice-first inventory companion built specifically for Indian retail. Shopkeepers manage their store simply by speaking in their natural language (Hindi, Hinglish, or English). Powered by **Gnani AI's Prisma (STT)** and **Timbre (TTS)**, StockSaathi streams audio in real time, interprets intent with high accuracy, executes inventory transactions, and replies back with natural spoken voice feedback.

### 3. Agentic Architecture & Accurate Agent Roles

```
[Shopkeeper Voice / Text]
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│                 SUPERVISOR AGENT                            │
│  • Listens via Gnani Prisma STT (16kHz PCM streaming)       │
│  • Detects intent & splits multi-item sentences             │
│  • Extracts entities (Product, Qty, Price, Reason)         │
│  • Validates missing data & asks clarification questions    │
│  • Provides consultative retail advice ("bikri kaise badhe")│
│  • ASSIGNS / ROUTES validated tasks to specialist agents:   │
└───────────────────────┬─────────────────────────────────────┘
                        │
         ┌──────────────┴──────────────┐
         ▼                             ▼
┌───────────────────────────┐ ┌───────────────────────────┐
│ INVENTORY & PRODUCT AGENT │ │   BUSINESS INTELLIGENCE   │
│       (Specialist)        │ │      (BI) AGENT           │
│                           │ │       (Specialist)        │
│ • Sales (Stock-Out)       │ │ • Total Sales Summary     │
│ • Purchases (Stock-In)    │ │ • Revenue & Profit Trends │
│ • Stock Adjustments       │ │ • Low-Stock Alerts        │
│ • Damaged / Expired Stock │ │ • Top-Selling Products    │
│ • Opening Stock Setup     │ │ • Restocking Suggestions  │
│ • Add / Edit / Remove     │ └───────────────────────────┘
│   Product Catalog         │
│ • Live Stock Lookup       │
└───────────────────────────┘
```

1. **Supervisor Agent (Orchestrator & Dispatcher):**
   - Transcribes voice via Gnani Prisma STT and understands commands in Hindi, Hinglish, and English.
   - Extracts products, quantities, prices, and reasons, handling multiple actions in one sentence (e.g., *"Amul butter 2 packet becha aur 5 soap purchase kiya"*).
   - Validates required fields; prompts the user with conversational clarification questions if information is missing.
   - Responds directly with consultative advice for strategic business questions (e.g., *"sales kaise badhaun"*).
   - **Assigns and routes each task** to the dedicated specialist sub-agent. Does not perform direct database writes.

2. **Inventory & Product Agent (Execution Specialist):**
   - **Sales / Stock-Out:** Deducts sold inventory, calculates sale value, and writes movement audit logs.
   - **Purchases / Stock-In:** Increments stock and updates weighted-average purchase cost.
   - **Stock Adjustments:** Reconciles physical count differences with reason tags.
   - **Damaged / Expired Stock:** Records damaged goods and logs inventory loss.
   - **Opening Stock:** Initializes baseline inventory during store onboarding.
   - **Product Catalog Management:** Adds new products, updates selling/purchase prices, and deletes discontinued products.
   - **Inventory Lookup:** Answers real-time stock availability queries.

3. **BI (Business Intelligence) Agent (Analytics Specialist):**
   - **Total Sales & Revenue:** Aggregates sales figures across customizable timeframes (today, yesterday, this week, this month).
   - **Profit & Margin Analysis:** Computes estimated gross profit and margin percentages.
   - **Low-Stock Alerts:** Highlights items at or below reorder threshold.
   - **Top-Selling Insights:** Identifies best-performing items to guide inventory planning.

---

### 4. Technical Stack
- **Voice Infrastructure:** Gnani Prisma (real-time streaming Speech-to-Text) & Gnani Timbre (neural Text-to-Speech).
- **Backend & Orchestration:** FastAPI, WebSockets, LangGraph state machine, deterministic validation guards.
- **Database & Authentication:** PostgreSQL (Neon Serverless) with Google OAuth via Neon Auth.
- **Frontend:** React 18, Vite, Tailwind CSS, Lucide icons, live audio visualizer and analytics dashboard.

---

## Local Development & Setup

1. Configure environment variables in `.env`:
   - `DATABASE_URL` (Neon PostgreSQL)
   - `NEON_AUTH_BASE_URL`
   - `GNANI_API_KEY`
2. Install backend dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Build the frontend:
   ```bash
   cd frontend
   npm install
   npm run build
   cd ..
   ```
4. Start the application:
   ```bash
   uvicorn main:app --reload
   ```
5. Open `http://127.0.0.1:8000` and sign in with Google.
