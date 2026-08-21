# Instagram Comment Automation Platform (ManyChat-Style MVP Backend)

This is a production-ready, scalable FastAPI backend for an Instagram Comment Automation platform. It uses Meta's official Graph API and Instagram Graph Webhooks to automate comment replies, private direct messages (DMs), and contact tagging based on user-defined keyword flows.

## Core Features
1. **JWT Authentication & Security**: Fast password hashing using BCrypt and JWT session authorization.
2. **Meta OAuth Connect & Discovery**: Exchanged access tokens and auto-discovers Facebook Pages and associated Instagram Business Accounts.
3. **Encrypted Token Storage**: AES-128 Fernet encryption for Meta API access tokens.
4. **Media Cache Service**: Syncs and caches Instagram posts to speed up keyword-post attachments.
5. **Secure Webhook Receiver**: Verifies Meta webhook payloads using HMAC-SHA256 signature checking.
6. **Background Ingestion Queue**: Dispatches comment events to Redis and runs them asynchronously with Celery workers.
7. **Graph-based Flow Engine**: Traversable flow chart supporting triggers, public comment replies, direct messages (DMs), and customer tagging with `{{username}}` substitution.
8. **Dashboard APIs & Analytics**: Endpoints for accounts, cached posts, comment events log, automation CRUD, execution logs, and key engagement analytics (keyword counts, response times, success/failure metrics).

---

## Tech Stack
* **Backend Framework**: FastAPI (Python 3.10+)
* **Database**: PostgreSQL (SQLAlchemy Async Engine + Alembic migrations)
* **Caching & Queue**: Redis
* **Task Worker**: Celery
* **HTTP Client**: HTTPX (Async requests with retry backoff and rate limit handling)
* **Testing Suite**: Pytest (Pytest-Asyncio + In-Memory SQLite Testing)
* **Logging**: Loguru

---

## Installation & Setup

### 1. Prerequisites
Ensure you have the following installed:
* Python 3.10+
* Redis Server (listening on `redis://localhost:6379`)
* PostgreSQL Database (optional; SQLite is supported by default for local testing)

### 2. Install Dependencies
Clone the repository, navigate to the `backend` directory, create a virtual environment, and install requirements:
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Environment Configuration
Create a `.env` file in the `backend` directory (loaded automatically by Pydantic settings). Example values:
```ini
PROJECT_NAME="Instagram Comment Automation Platform"
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/insta_automator"
REDIS_URL="redis://localhost:6379/0"
JWT_SECRET="YOUR_SUPER_SECRET_JWT_SIGNING_KEY_HERE"
ENCRYPTION_KEY="YOUR_FERNET_32_BYTE_BASE64_KEY_HERE"

# Meta App Credentials
META_APP_ID="your_meta_app_id"
META_APP_SECRET="your_meta_app_secret"
META_VERIFY_TOKEN="your_webhook_verification_token"
```
*Note: If `ENCRYPTION_KEY` is not set, a key is automatically derived from the `JWT_SECRET` key.*

---

## Database Migrations
We use Alembic to manage database migrations.

Initialize migrations database schema:
```bash
# Generate the initial migration script based on SQLAlchemy models
./venv/bin/alembic revision --autogenerate -m "Initial database schema"

# Apply migrations to database
./venv/bin/alembic upgrade head
```

---

## Running the Application

### 1. Run the FastAPI Server
Start the development server using Uvicorn:
```bash
./venv/bin/uvicorn app.main:app --reload
```
The API documentation will be available at:
* Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
* ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### 2. Run the Celery Worker
Start the background Celery process (ensure Redis is running first):
```bash
./venv/bin/celery -A app.core.cel_app worker --loglevel=info
```

---

## Running the Test Suite
An isolated, comprehensive test suite is included in `tests/` using an in-memory SQLite database. Run the tests using the command below:
```bash
PYTHONPATH=. ./venv/bin/pytest -v
```

---

## Meta Webhook Integration Guidelines
1. In your Meta Developer App, configure the **Instagram Graph API Webhooks**.
2. Set the Callback URL to `https://yourdomain.com/webhooks/meta` (Note: Meta requires HTTPS. For local testing, use a tunnel like `ngrok` or `localtunnel`).
3. Set the Verification Token to the same value as `META_VERIFY_TOKEN` in your `.env`.
4. Subscribe to the `comments` feed event for the Instagram Graph API.
5. Direct message flows will require `instagram_manage_messages` and comment reply flows will require `instagram_basic` permissions.
