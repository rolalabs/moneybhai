# MoneyBhai Backend Architecture

## 1. Overview
MoneyBhai is a financial transaction tracking application that automates the extraction of transaction data from email alerts (banks, credit cards, UPI). The backend consists of a RESTful API for client interaction and data management, and a dedicated background worker service for processing emails using GenAI.

## 2. System Components

The architecture follows a microservices-lite approach with two main services:

### 2.1 Backend API Service (`src/`)
- **Role**: Serves as the central interface for the frontend and the worker service.
- **Framework**: FastAPI (Python).
- **Key Responsibilities**:
    - User Authentication (HTTP Basic & potentially Token-based for internal ops).
    - Database Management (CRUD operations for Users, Emails, Transactions).
    - Exposing endpoints for the Worker to sync data.
    - Logging and monitoring (Middleware).

### 2.2 Worker Service (`worker/`)
- **Role**: Handles asynchronous and resource-intensive background tasks.
- **Framework**: FastAPI (Python).
- **Key Responsibilities**:
    - **Gmail Integration**: Connects to the user's Gmail account using OAuth tokens.
    - **Email Fetching**: Retrieves relevant transaction alert emails.
    - **GenAI Processing**: Uses Google Gemini (via `google-genai` and `langsmith`) to parse unstructured email text into structured transaction data.
    - **Data Synchronization**: Pushes fetched emails and extracted transactions back to the Backend API.

### 2.3 Database
- **Type**: PostgreSQL.
- **ORM**: SQLAlchemy.
- **Migration Tool**: Alembic.
- **Stores**: User profiles, raw email metadata, and parsed transactions.

### 2.4 External Services
- **Google Gmail API**: For reading user emails.
- **Google Vertex AI (Gemini)**: For LLM-based entity extraction from emails.
- **LangSmith**: For tracing and monitoring LLM usage.

## 3. Data Pipeline Workflow

The core functionality revolves around the email-to-transaction pipeline:

1.  **Task Trigger**: A process task is initiated (likely via Cloud Scheduler or direct API call to Worker's `/tasks/process`).
2.  **User Context**: The Worker fetches the target User's details (including sync tokens and `lastSyncedAt` timestamp) from the Backend API.
3.  **Gmail Sync**:
    - Worker authenticates with Gmail API using the stored refresh token.
    - Queries for emails received `after` the `lastSyncedAt` timestamp.
    - Fetches full message details (Snippet, Sender, Subject, etc.).
4.  **Email Ingestion**:
    - Worker batches fetched emails and sends them to the Backend API (`/api/v1/emails/insert-bulk`).
    - Backend stores these in the `emails` table.
5.  **Intelligent Parsing (Gemini)**:
    - Worker constructs a prompt containing the email snippet.
    - Calls Gemini Pro/Flash model to extract fields: `amount`, `merchant`, `date`, `mode` (UPI/CC), `transaction_type` (Credit/Debit).
6.  **Transaction Storage**:
    - Worker receives structured JSON from Gemini.
    - Sends the transaction list to Backend API (`/api/v1/transactions/bulk-insert`).
    - Backend stores them in the `transactions` table, linking them to the original email and user.
7.  **State Update**:
    - Upon successful processing, the Worker updates the User's `lastSyncedAt` timestamp via the Backend API.

## 4. Database Schema

### Users (`users`)
- `id`: UUID (Primary Key)
- `email`: String (Unique)
- `name`: String
- `gmailRefreshToken`: String (Encrypted/Stored for offline access)
- `lastSyncedAt`: Timestamp (Tracks the last successful sync checkpoint)
- `isSyncing`: Boolean (Lock to prevent concurrent syncs)

### Emails (`emails`)
- `id`: String (Gmail Message ID, Primary Key)
- `thread_id`: String
- `snippet`: Text (Raw email preview/content)
- `emailSender`: String (e.g., "alerts@hdfcbank.net")
- `isTransaction`: Boolean (Flag if identified as transactional)
- `isGeminiParsed`: Boolean (Processing status)

### Transactions (`transactions`)
- `id`: String (Primary Key)
- `amount`: Float
- `transaction_type`: String (Debit/Credit)
- `source_identifier`: String (e.g., Account suffix)
- `destination`: String (Merchant/Receiver)
- `mode`: String (UPI, CARD, NEFT)
- `dateTime`: DateTime
- `userId`: UUID (Foreign Key)
- `emailId`: String (Link to source email)

## 5. Technology Stack

- **Language**: Python 3.11+
- **API Framework**: FastAPI, Uvicorn
- **Database**: PostgreSQL, SQLAlchemy, Alembic (Migrations)
- **AI/ML**: Google GenAI SDK (Gemini), LangChain/LangSmith
- **Containerization**: Docker
- **Cloud Infrastructure**: Likely Google Cloud Run (for stateless container deployment).

## 6. Directory Structure Overview

- `src/`: Main Backend Application
    - `api/`: Route definitions (v1).
    - `core/`: Database connections, Environment settings.
    - `modules/`: Domain logic (Users, Emails, Transactions) - separate folders for models, schemas, and operations.
- `worker/`: Background Worker Application
    - `connectors.py`: Database and API clients.
    - `operations.py`: Main business logic (Gmail fetcher, AI Manager).
    - `models.py`: Pydantic models for worker data exchange.
- `packages/`: Shared Pydantic models used by both services.
- `alembic/`: Database migration scripts.

## 7. Security & Configuration
- **Environment Variables**: Managed via `.env` (using `python-dotenv`).
- **Secrets**: API Keys (Gmail Client, LangSmith, Database URL) are injected at runtime.
- **CORS**: Configured to allow local frontend development (`localhost:3000`).
