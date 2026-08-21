# Instagram & Facebook Comment Automation Platform (ManyChat-Style)

This repository contains the source code for a production-ready, scalable **Instagram and Facebook Comment Automation Platform** (ManyChat-style MVP). The platform allows social media managers and businesses to automate responses to public comments, send private direct messages (DMs), and manage customer tags based on user-defined interactive keyword triggers and logic flows.

---

## 🏗️ System Architecture

The application is split into a modern decoupled architecture consisting of three main tiers:

```mermaid
graph TD
    User([User / Browser]) -->|HTTP / JS| Frontend[React + Vite Frontend]
    MetaWebhook([Meta Graph API Webhooks]) -->|HTTPS POST| Backend[FastAPI Server]
    Frontend -->|REST APIs / JWT| Backend
    
    subgraph Backend Core
        Backend -->|Async Engine| DB[(PostgreSQL / SQLite)]
        Backend -->|Publish Task| Redis[(Redis Broker)]
        CeleryWorker[Celery Background Worker] -->|Consume Task| Redis
        CeleryWorker -->|Read/Write| DB
        CeleryWorker -->|Send Callbacks| MetaAPI[Meta Graph API]
    end
    
    MetaAPI -.->|Comments / DMs| EndUser([Instagram / Facebook User])
```

1. **Frontend (Dashboard & Flow Builder)**: A React-based Single Page Application (SPA) powered by Vite. Features dynamic analytics, credential syncing, post management, historical logs, and a visual canvas builder for creating automation graphs.
2. **Backend (FastAPI)**: An asynchronous high-performance Python backend managing business logic, secure Meta authentication, post caching, analytics compilation, and API serving.
3. **Queue & Worker (Celery + Redis)**: Ensures that high-throughput webhook events from Meta are ingested instantly without blocking the server, queueing comment analysis and dispatching API executions in the background.

---

## 🌟 Key Capabilities & Features

### 1. Interactive Visual Flow Builder
* **Graph Canvas**: Create structured automation scripts by connecting nodes (triggers, conditions, and actions).
* **Multiple Node Support**:
  * **Trigger Nodes**: Match comments against a list of keywords (supports exact-matching or partial substring matching).
  * **Public Reply Actions**: Post a public reply to the comment on the user's feed, supporting dynamic placeholder variables like `{{username}}`.
  * **Direct Message Actions**: Initiate a private DM thread containing details, promo codes, or links to the commenter.
  * **Condition Nodes**: Split paths ("Yes" / "No") by checking variables like text contents or username attributes (e.g., checks if a username equals or contains a specific string).
  * **Customer Tagging**: Automatically tag responders (e.g., `lead`, `hot_buyer`) for database segmentation and retargeting.

### 2. Meta OAuth & Multi-Account Discovery
* Connect Facebook profiles using Meta OAuth flows.
* Automatically discover all associated Facebook Pages and linked Instagram Business accounts.
* Safe and secure credentials storage with **AES-128 Fernet encryption** on all Meta Page Access Tokens.

### 3. Media Caching & Linkage
* Retrieve and sync media posts from Instagram and Facebook feeds.
* Attach specific automation flows to individual posts, reels, or apply them globally across the entire account feed.

### 4. Real-time Log Simulation & Analytics
* View real-time webhook payloads, processing status (`pending`, `processed`, `ignored`, `failed`), and failure reasons.
* A step-by-step Execution Log detailing exactly which node was executed, the values parsed, and API response metadata.
* Rich dashboard analytics tracking total impressions, trigger counts, response speed, and automation success/failure rates.

---

## 🗄️ Database Models & Schema

The backend uses SQLAlchemy (Async Engine) to map out the relational data:

* **User**: Platform managers credentials, encrypted password hashes, and registration metadata.
* **InstagramAccount / FacebookAccount**: Cached references to linked social pages, profile graphics, and Fernet-encrypted Access Tokens.
* **Post / FacebookPost**: Caches for post thumbnails, captions, media type, and permalinks to speed up frontend linking.
* **AutomationFlow**: The container mapping name, state (active/inactive), and relationships between nodes and edges.
* **FlowNode / FlowEdge**: Structured schema containing type identifiers, position coords (X, Y), and execution configs (e.g., messages, conditions, keywords).
* **CommentEvent / FacebookCommentEvent**: Audit logs recording every incoming webhook comment, sender username, raw text, processing timestamps, and final execution state.
* **AutomationLog**: Granular step-by-step logs recording trace lines for every node executed within a running flow instance.

---

## 🔄 Live Webhook Data Flow

Here is what happens when a customer comments on a registered post:

```mermaid
sequenceDiagram
    autonumber
    actor Customer as Instagram User
    participant Meta as Meta Graph Webhook
    participant WebhookAPI as FastAPI Webhook Endpoint
    participant Celery as Celery Worker Queue
    participant Engine as Automation Engine
    
    Customer->>Meta: Comments "Send link" on a post
    Meta->>WebhookAPI: Delivers secure HTTPS POST payload with HMAC-SHA256 signature
    WebhookAPI->>WebhookAPI: Validates signature using META_VERIFY_TOKEN
    WebhookAPI->>Celery: Dispatches event to Redis queue & instantly returns 200 OK to Meta
    Celery->>Engine: Launches processor worker
    Engine->>Engine: Pulls active flows for the account
    Engine->>Engine: Evaluates trigger keywords ("Send link")
    
    rect rgb(200, 230, 255)
        Note over Engine: Traverses automation graph nodes
        Engine->>Meta: Calls Meta API to reply publicly ("Check your DMs!")
        Engine->>Meta: Calls Meta API to send private DM ("Here is your link...")
        Engine->>Engine: Logs execution history details to Database
    end
```

---

## 🛠️ Getting Started & Local Launch

### 1. Prerequisites
Ensure you have the following services installed and running locally:
* **Node.js** (v18+)
* **Python** (3.10+)
* **Redis** (listening on port `6379`)

### 2. Installation
Install frontend and backend packages:
```bash
# Setup backend dependencies
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Setup frontend dependencies
cd ../frontend
npm install
```

### 3. Configuration
Add a `.env` file inside the `backend` folder:
```ini
PROJECT_NAME="Instagram Comment Automation Platform"
DATABASE_URL="sqlite+aiosqlite:///./sql_app.db" # Or PostgreSQL: postgresql+asyncpg://postgres:postgres@localhost:5432/insta_automator
REDIS_URL="redis://localhost:6379/0"
JWT_SECRET="YOUR_SECRET_JWT_KEY"
ENCRYPTION_KEY="YOUR_FERNET_32_BYTE_BASE64_KEY"
META_APP_ID="your_meta_app_id"
META_APP_SECRET="your_meta_app_secret"
META_VERIFY_TOKEN="your_webhook_verification_token"
```

### 4. Running the Complete Stack
You can launch the frontend, backend FastAPI server, and Celery background workers concurrently using the included helper script:
```bash
chmod +x run_project.sh
./run_project.sh
```

* **Frontend Dashboard**: [http://localhost:5173](http://localhost:5173)
* **Backend Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
