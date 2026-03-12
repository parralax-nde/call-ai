# BookCaller

A microservices-based platform for AI calling workflows using Telnyx API and voice AI tools.

## Tech Stack

- **Backend**: FastAPI, Python 3.12
- **Frontend**: Single-page application (vanilla HTML/CSS/JavaScript)
- **Database**: MySQL (SQLite for development/testing)
- **Message Queue**: RabbitMQ
- **API Gateway**: Nginx
- **Containerization**: Docker, Kubernetes
- **Third-Party**: Telnyx API, Resend, Pesapal

## Architecture

The platform consists of 11 microservices that can run independently or as a monolith:

| Service | Description |
|---------|-------------|
| **Auth Service** | User authentication (email/password, Google OAuth), JWT management |
| **User Service** | Profile management, RBAC, API key generation |
| **Telnyx Integration** | Telnyx API wrapper for call initiation, webhooks, Voice AI |
| **AI Config Service** | AI prompt templates, personas, conversational flows with versioning |
| **Scheduler Service** | One-time/recurring call scheduling, event-based triggers |
| **Call Management** | Call logs, real-time status, dashboard stats, recordings |
| **Webhook Service** | User-defined webhooks with HMAC signing and delivery logs |
| **Notification Service** | Email via Resend, Jinja2 templates, system alerts, preferences |
| **Billing Service** | Usage tracking, subscriptions, Pesapal payments, invoices |
| **Admin Service** | System health monitoring, audit logs, gateway analytics |

## Quick Start

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
uvicorn main:app --reload

# Access the frontend at http://localhost:8000/
# Access API docs at http://localhost:8000/docs
```

### Docker

```bash
docker-compose up -d
```

### Frontend

The platform includes a built-in web dashboard served by FastAPI. No separate frontend build step is required.

**Access**: Navigate to `http://localhost:8000/` after starting the server.

**Features**:
- **Authentication** – Register and sign in with email/password
- **Dashboard** – Real-time call statistics (total, active, completed, failed calls)
- **Calls** – Initiate new AI-powered calls and view call history
- **AI Config** – Create and manage AI session behavior and voices
- **Scheduler** – Schedule one-time or recurring calls
- **Settings** – Configure Telnyx credentials, manage your profile, and generate API keys

**Static files** are served from the `frontend/` directory and mounted at `/static`. The SPA entry point is available at `/`.

### Configuration

Set environment variables (or create a `.env` file):

```
SECRET_KEY=your-secret-key
DATABASE_URL=mysql+pymysql://user:pass@localhost/callai
TELNYX_API_KEY=your-telnyx-key
RESEND_API_KEY=your-resend-key
PESAPAL_CONSUMER_KEY=your-pesapal-key
PESAPAL_CONSUMER_SECRET=your-pesapal-secret
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
```

## Testing

```bash
# Run all tests (196 tests)
python -m pytest tests/ -v

# Run specific service tests
python -m pytest tests/test_auth.py -v
python -m pytest tests/test_user.py -v
python -m pytest tests/test_telnyx.py -v
python -m pytest tests/test_ai_config.py -v
python -m pytest tests/test_scheduler.py -v
python -m pytest tests/test_call_management.py -v
```

## Project Structure

```
call-ai/
├── main.py              # API Gateway (monolith mode)
├── shared/              # Shared library
│   ├── auth.py          # JWT & password utilities
│   ├── config.py        # Centralized configuration
│   ├── database.py      # SQLAlchemy setup
│   ├── exceptions.py    # Custom exceptions
│   └── schemas.py       # Base schemas/DTOs
├── frontend/            # Web dashboard (SPA)
│   ├── index.html       # Main HTML entry point
│   ├── css/style.css    # Application styles
│   └── js/
│       ├── api.js       # API client library
│       └── app.js       # Application logic & UI controllers
├── services/            # Microservices
│   ├── auth/            # Authentication service
│   ├── user/            # User management service
│   ├── telnyx_integration/  # Telnyx API service
│   ├── ai_config/       # AI assistant configuration
│   ├── scheduler/       # Call scheduling service
│   ├── call_management/ # Call monitoring service
│   ├── webhook/         # Webhook management
│   ├── notification/    # Notification service
│   ├── billing/         # Billing & payments
│   └── admin/           # Admin dashboard
├── tests/               # Automated tests
├── docker/              # Docker configs
├── k8s/                 # Kubernetes manifests
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```