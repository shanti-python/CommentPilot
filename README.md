# Instagram Comment Automation Platform

This repository contains the backend and frontend for the ManyChat-style Instagram comment automation platform.

## Directory Structure
*   **`backend/`**: FastAPI backend with SQLAlchemy + PostgreSQL/SQLite, Celery, and Redis integration.
*   **`frontend/`**: Vite + React + Vanilla CSS dashboard application featuring visual flow building, OAuth integration, and live simulation logs.

## Getting Started

### 1. Requirements
Ensure you have Python 3.10+, Node.js, and Redis installed.

### 2. Launch the Application
You can launch both services concurrently using the startup script:
```bash
./run_project.sh
```

This will spin up:
*   **Vite Dashboard**: [http://localhost:5173](http://localhost:5173)
*   **FastAPI backend**: [http://localhost:8000](http://localhost:8000)

For more detailed setup guides, check the individual readmes:
*   [Backend Setup Guide](file:///home/shanti/Insta-fb-comment/backend/README.md)
# Linkedin-Youtube-automation
