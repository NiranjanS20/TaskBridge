# TaskBridge 

TaskBridge (also known as VASAE - Volunteer Allocation System and AI Engine) is an AI-powered NGO resource allocation system. It is designed to intelligently match volunteers to tasks based on complex scoring mechanisms while maintaining fairness, preventing burnout, and providing full explainability.

## 🚀 Key Features

* **Intelligent Allocation Engine**: AI-powered matching using VAS (Volunteer Allocation Score), balancing efficiency, travel distance, skill match, and workload fairness.
* **Real-Time Map & Dashboard**: Live visualization of volunteers and tasks using Leaflet with heatmap support.
* **Explainability Panel**: Transparent breakdown of why specific volunteers were assigned to tasks, helping coordinators trust AI decisions.
* **Burnout & Fairness Constraints**: Built-in mechanisms to prevent overworking individual volunteers by monitoring historical load and priority queues.
* **Real-time WebSockets**: Instant updates across all dashboards when assignments, tasks, or volunteer statuses change.
* **Role-Based Access Control**: Secure organization-scoped authentication and authorization.

## 🛠️ Technology Stack

### Frontend
* **Framework**: React 18 with Vite & TypeScript
* **Styling**: Tailwind CSS & Radix UI Primitives
* **Routing**: React Router DOM v7
* **Mapping**: Leaflet & React-Leaflet
* **Data Visualization**: Recharts
* **Real-time**: Native WebSockets

### Backend
* **Framework**: FastAPI & Python 3
* **Database**: PostgreSQL (via async SQLAlchemy) & Alembic for migrations
* **Background Jobs**: Celery & Redis
* **Data Validation**: Pydantic v2
* **Authentication**: JWT (python-jose) + bcrypt
* **Math/Core**: NumPy

## 📁 Project Structure

```text
TaskBridge/
├── backend/            # FastAPI application and core logic
│   ├── app/
│   │   ├── api/        # REST endpoints and WebSocket routers
│   │   ├── core/       # Allocation engine, fairness, ML scoring
│   │   ├── db/         # SQLAlchemy models and session management
│   │   ├── models/     # Database table definitions
│   │   ├── schemas/    # Pydantic validation schemas
│   │   ├── services/   # Business logic layer
│   │   └── workers/    # Celery tasks
│   ├── requirements.txt
│   └── run.bat         # Start script
├── frontend/           # React application
│   ├── src/
│   │   ├── components/ # Reusable UI, Map, Auth, Chat, Explainability
│   │   ├── hooks/      # Custom React hooks (useWebSocket, useRealtimeData)
│   │   ├── pages/      # Route components (Dashboard, Analytics, Maps)
│   │   └── lib/        # API clients and utilities
│   ├── package.json
│   └── vite.config.ts
├── docs/               # Architecture documents (HLD.md, LLD.md, API.md)
├── infra/              # Deployment configurations (Docker, Vercel, Render)
└── shared/             # Shared assets or configurations
```

## 🏃‍♂️ Getting Started

### Prerequisites
* Node.js v18+
* Python 3.9+
* PostgreSQL
* Redis (for background workers)

### 1. Backend Setup
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Or `.venv\Scripts\activate` on Windows
pip install -r requirements.txt

# Copy env template and configure your DB/Redis URLs
cp .env.example .env

# Run the server
uvicorn app.main:app --reload --port 8002
```

### 2. Frontend Setup
```bash
cd frontend
npm install

# Start the Vite development server
npm run dev
```

## 📖 Documentation
Detailed architectural documents are located in the `docs/` directory:
* **[High Level Design (HLD)](docs/HLD.md)**: System architecture and core components overview.
* **[Low Level Design (LLD)](docs/LLD.md)**: Database schemas, internal class structures, and workflows.
* **[API Documentation](docs/API.md)**: Details on REST endpoints and WebSocket events.

## 🚀 Deployment
Deployment configurations are available in the `infra/` folder, including `docker-compose.yml` for containerized setups, `render.yaml` for backend deployment on Render, and `vercel.json` for frontend deployment on Vercel.
