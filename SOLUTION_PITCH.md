# StockSaathi — 1-Page Solution Pitch

**Tagline:** Voice-first AI inventory & retail intelligence partner for Indian shop owners  
**Challenge:** Great Indian AI Internship Challenge by Gnani.ai  
**Live Demo:** [https://stock-saathi.vercel.app](https://stock-saathi.vercel.app) | **Backend API:** [https://stock-saathi-backend-ynd4.onrender.com](https://stock-saathi-backend-ynd4.onrender.com)  

---

### 1. Problem Statement
Millions of small retail and kirana shop owners across India handle dozens of sales, purchases, and supplier deliveries every single day while attending to customers. Complex POS systems and manual ledger registers (bahi-khata) lead to unrecorded sales, inventory mismatches, forgotten stock reorders, and stock damage losses. Busy shopkeepers do not have time to sit at a computer or navigate complex software menus during peak business hours.

### 2. Proposed Solution: StockSaathi
**StockSaathi** is a hands-free, voice-first inventory assistant that allows shopkeepers to run their entire store simply by speaking in their everyday language (Hindi, Hinglish, or English). With real-time voice streaming powered by **Gnani AI's Prisma (STT)** and **Timbre (TTS)**, a shopkeeper speaks naturally, and the system instantly interprets the intent, updates inventory, and confirms the action aloud.

### 3. Agentic Multi-Agent Architecture
StockSaathi uses a modular multi-agent workflow where responsibilities are cleanly divided:

1. **Supervisor Agent (Orchestrator & Dispatcher):**
   - Receives the transcribed voice stream or text input.
   - Detects user intent and parses multi-product requests within a single sentence (e.g., *"Amul butter 2 packet becha aur 5 soap purchase kiya"*).
   - Extracts key entities (product name, quantity, purchase/selling price, reason).
   - Validates required fields deterministically; asks follow-up clarification questions if critical data is missing.
   - Provides direct consultative guidance for general business questions (e.g., *"bikri kaise badhaun"*).
   - **Assigns and routes validated tasks** to the appropriate specialized sub-agent:
     - **Inventory & Product Agent:** Executes all stock movements and catalog operations directly in the database.
     - **BI (Business Intelligence) Agent:** Runs read-only analytical queries for sales, revenue, and store performance.

2. **Inventory & Product Agent (Specialist):**
   - **Sales / Stock-Out:** Deducts sold units, calculates revenue, and appends real-time audit movements.
   - **Purchases / Stock-In:** Increments stock quantity and recalculates weighted average unit cost.
   - **Stock Adjustments:** Reconciles physical counts against digital records with reason logging.
   - **Damaged / Expired Stock:** Records unsellable items and logs financial loss.
   - **Opening Stock:** Initializes baseline inventory during new store setup.
   - **Product Catalog Management:** Adds new items, updates selling/purchase prices, and removes obsolete items.
   - **Inventory Lookup:** Provides instant real-time quantity checks.

3. **BI (Business Intelligence) Agent (Specialist):**
   - **Total Sales & Revenue Queries:** Computes sales revenue and transaction counts across customizable time windows (today, yesterday, this week, this month).
   - **Profit & Margin Analysis:** Calculates estimated gross profits based on stored unit costs.
   - **Low-Stock Alerts:** Identifies critical inventory items at or below reorder thresholds.
   - **Top-Selling Insights & Suggestions:** Highlights fastest-moving goods and provides actionable restocking recommendations.

### 4. Technical Architecture
- **Voice Stack:** Gnani Prisma (real-time 16kHz PCM streaming STT) + Gnani Timbre (natural neural TTS).
- **Backend & Agents:** FastAPI, WebSockets, LangGraph state orchestration, deterministic validation guards.
- **Database & Authentication:** PostgreSQL (Neon Serverless) with Google OAuth via Neon Auth.
- **Frontend:** React 18, Vite, Tailwind CSS, Lucide icons, responsive interactive charts and live voice visualizer.
