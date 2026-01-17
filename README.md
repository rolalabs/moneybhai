# MoneyBhai Backend

MoneyBhai is an automated personal finance tracking backend that parses financial transaction alerts from emails (Banks, UPI, Credit Cards) using GenAI to build a structured database of your expenses and income.

## 📖 Documentation
Detailed architecture documentation is available in [doc/architecture.md](doc/architecture.md).

## 🚀 Features

- **Automated Email Parsing**: Fetches transaction emails from Gmail using OAuth.
- **AI-Powered Extraction**: Uses Google Gemini (Vertex AI) to intelligently extract transaction details (Amount, Merchant, Mode, Date) from unstructured email text.
- **REST API**: FastAPI-based interface for user management and data access.
- **Background Worker**: Dedicated service for handling email synchronization and LLM processing asynchronously.
- **Secure**: Uses OAuth2 for Gmail access; credentials are encrypted.

## 🛠️ Tech Stack

- **Language**: Python 3.11+
- **Framework**: FastAPI
- **Database**: PostgreSQL (SQLAlchemy ORM + Alembic Migrations)
- **AI Model**: Google Gemini (via `google-genai`)
- **Tracing**: LangSmith
- **Containerization**: Docker

## 📂 Project Structure

```
.
├── src/                # Main Backend API Service
│   ├── api/            # API Route Definitions (v1)
│   ├── core/           # Config, Database, Auth
│   └── modules/        # Domain logic (Users, Emails, Transactions)
├── worker/             # Background Worker Service
│   ├── connectors.py   # External clients (Gmail, DB)
│   └── operations.py   # Business logic (Email fetch, Gemini parsing)
├── packages/           # Shared Pydantic Models & Enums
├── alembic/            # Database Migrations
├── doc/                # Documentation
└── main.py             # API Entry point
```

## ⚡ Getting Started

### Prerequisites
- Python 3.11+
- PostgreSQL
- Google Cloud Project (with Gmail API and Vertex AI enabled)

### Local Setup

1. **Clone the repository**
   ```bash
   git clone <repository_url>
   cd moneybhai
   ```

2. **Create Virtual Environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration**
   Copy `.env.example` to `.env` and fill in the required values:
   ```bash
   cp .env.example .env
   ```
   *Required variables: `DATABASE_URL`, `GCP_CREDENTIALS`, `LANGSMITH_API_KEY`, etc.*

5. **Run Migrations**
   ```bash
   alembic upgrade head
   ```

6. **Start the API Server**
   ```bash
   uvicorn main:app --reload --port 8080
   ```

7. **Start the Worker Service** (in a separate terminal)
   ```bash
   uvicorn worker.main:app --reload --port 8081
   ```

## 🔐 Auth Flow (Gmail)
1. Mobile App obtains ID Token via Google Sign-In.
2. Backend verifies ID Token.
3. User grants Gmail permissions via OAuth Consent.
4. Backend stores Refresh Token for offline access.
5. Worker uses Refresh Token to fetch and process emails periodically.
