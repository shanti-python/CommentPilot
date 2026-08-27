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

## Running with Docker (Production Ready)

To run the entire application stack (PostgreSQL, Redis, FastAPI Backend, Celery Background Worker, and Nginx Frontend) inside Docker containers:

### 1. Run the Stack
Start the containers in detached mode:
```bash
docker compose up -d
```

This will build the custom images for the frontend and backend, pull stable Postgres and Redis images, and boot up all five containers linked in a dedicated private virtual network.

### 2. Access the Application
* **Vite Dashboard**: [http://localhost:5173](http://localhost:5173) (served through an Nginx proxy gateway)
* **API Documentation**: [http://localhost:5173/docs](http://localhost:5173/docs) (or directly at port 8000: [http://localhost:8000/docs](http://localhost:8000/docs))

### 3. Management Commands
* **Check Status**: `docker compose ps`
* **Check Logs**: `docker compose logs -f`
* **Stop Container Services**: `docker compose down`
* **Rebuild after source modifications**: `docker compose up -d --build`

