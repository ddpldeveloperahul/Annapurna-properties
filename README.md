# Annapurna Pro — AI Calling & Real-Estate CRM Backend

**Annapurna Pro** is an end-to-end Real-Estate AI Calling and CRM Lead Automation backend built with **Django**, **Django REST Framework**, **PostgreSQL**, **SimpleJWT**, **Celery**, and **Redis**.

It automates customer voice qualification calls end-to-end: receiving incoming calls via cloud telephony (**Exotel**), managing live AI voice speech-to-speech qualification (**ElevenLabs**), creating/upserting leads in the CRM, generating post-call summaries using LLMs (**OpenAI GPT**), sending automated WhatsApp follow-up messages (**Meta WhatsApp Cloud API**), and managing human agent workloads and follow-ups.

---

## 🚀 Core Features & Architecture

1. **Unified Single-App Architecture (`myapp/`)**:
   - All models, serializers, views, selectors, filters, exceptions, and Celery tasks are consolidated under a clean single Django app (`myapp/`) maintaining database table integrity (`accounts_user`, `leads_lead`, `calls_call`, `whatsapp_whatsappmessage`, etc.).

2. **Authentication & Authorization**:
   - **JWT Authentication** (`djangorestframework-simplejwt`) with Token Blacklisting (`access` token valid for 20 days, `refresh` token valid for 30 days).
   - User Roles: `ADMIN` (Admin) and `CRM` (CRM Agent).
   - Complete Auth Suite: Signup, Login (Email or Username + Password), Refresh Token, Logout, Change Password, and **6-digit Email OTP Password Reset**.
   - Automatic Superuser Role assignment (`Role.ADMIN`).

3. **Incoming Call & Telephony Integration (Exotel)**:
   - Rate-throttled public webhook handlers (`/api/v1/telephony/webhooks/incoming-call/` and `/call-status/`).
   - Idempotent event logging via `CallEvent` (`event_type`: `incoming_call`, `status_update`, `ai_conversed`).

4. **Live AI Voice Qualification Flow (ElevenLabs)**:
   - Conversational voice agent supporting Hindi, Hinglish, and English.
   - Captures customer intent (`Buy` / `Rent` / `Sell`), property type, budget, location, and timeline.

5. **Post-Call Intelligence & Lead Qualification (OpenAI LLM)**:
   - Structured JSON summary & intent extraction via OpenAI GPT.
   - Auto-creates or updates Lead in CRM tagged as `source = 'AI Call'` with status `Qualified` or `Needs Human Follow-up`.

6. **Automated WhatsApp Follow-up (Meta Cloud API)**:
   - Asynchronous WhatsApp acknowledgment messages sent via Celery workers for High/Medium interest leads.

7. **Interactive Swagger Documentation**:
   - Integrated OpenAPI 3.0 schema and interactive Swagger UI documentation at `/api/docs/`.

8. **Dynamic CRM Agent Assignment**:
   - Transaction-safe, database-backed round-robin assignment supporting N agents.
   - Preserves existing agent assignments for returning callers and skips unavailable agents.

---

## 📁 Project Structure

```
annapurna_pro/
├── annapurna_pro/        # Core Django settings, URLs, Celery configuration & JWT settings
├── myapp/                # Unified Application Package
│   ├── models.py         # All DB Models (User, Agent, PasswordResetOTP, Lead, Call, etc.)
│   ├── serializers.py    # DRF Serializers (Auth, Leads, Calls, Followups, WhatsApp)
│   ├── views.py          # API Views (Auth, Leads, Calls, Webhooks, Dashboard)
│   ├── tasks.py          # Async Celery background workers
│   ├── selectors.py      # Data retrieval & business logic helpers
│   ├── filters.py        # Lead & Call filter sets
│   ├── pagination.py     # Standard DRF pagination (20 items/page)
│   ├── exceptions.py     # Unified API Exception Handler
│   └── urls.py           # Single app routing (/api/v1/...)
├── tests/                # Automated test suite (Auth, Leads, Webhooks)
├── requirements.txt      # Python dependencies
├── manage.py             # Django management CLI
└── README.md             # Project documentation
```

---

## ⚙️ Environment Configuration (`.env`)

Create a `.env` file in the project root:

### Local Development / Mock Mode (Default)
```env
DJANGO_SECRET_KEY=django-insecure-secret-key-change-in-production
DJANGO_DEBUG=true
DATABASE_ENGINE=postgres
POSTGRES_DB=annapurna
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_postgres_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

CELERY_TASK_ALWAYS_EAGER=true
AI_CALLING_MOCK_PROVIDERS=true
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

### Live Production Configuration
When going live, set `AI_CALLING_MOCK_PROVIDERS=false` and supply live credentials:

```env
DJANGO_SECRET_KEY=your-production-secret-key
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=*

AI_CALLING_MOCK_PROVIDERS=false
CELERY_TASK_ALWAYS_EAGER=false

# Exotel Telephony
EXOTEL_SID=your_exotel_sid
EXOTEL_TOKEN=your_exotel_token
EXOTEL_CALLER_ID=your_virtual_number
EXOTEL_WEBHOOK_SECRET=your_webhook_secret

# ElevenLabs Voice AI
ELEVENLABS_API_KEY=your_elevenlabs_key
ELEVENLABS_AGENT_ID=your_agent_id

# OpenAI LLM
OPENAI_API_KEY=your_openai_key
LLM_MODEL=gpt-4o

# Meta WhatsApp Business Cloud API
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WHATSAPP_ACCESS_TOKEN=your_whatsapp_token
```

---

## 🛠️ Quick Start & Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Database Migrations
```bash
python manage.py migrate
```

### 3. Seed Demo Data (Optional)
Populate 3 agents, 8 leads, 8 calls, 7 WhatsApp messages, and superuser `admin` / `admin-pass-123`:
```bash
python manage.py seed_demo_data
```

### 4. Create Superuser (Admin Role)
```bash
python manage.py createsuperuser
```

### 5. Start Development Server
```bash
python manage.py runserver
```
Server starts at `http://127.0.0.1:8000/`.

---

## 🧪 Running Tests

Run the complete 19-test automated test suite (including Assignment logic tests):
```bash
python manage.py test tests
```

---

## 🛰️ Key REST API Endpoints

### 🔐 Authentication (`/api/v1/auth/`)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/auth/signup/` | User Signup (Returns JWT Tokens) |
| `POST` | `/api/v1/auth/login/` | User Login (Email/Username + Password) |
| `POST` | `/api/v1/auth/refresh/` | Refresh Access Token |
| `POST` | `/api/v1/auth/logout/` | Blacklist Refresh Token |
| `POST` | `/api/v1/auth/change-password/` | Change Password |
| `POST` | `/api/v1/auth/reset-password/` | Request 6-digit Email OTP |
| `POST` | `/api/v1/auth/reset-password/confirm/` | Confirm Password Reset using OTP |
| `GET` | `/api/v1/me/` | Get Current User Profile |

### 🎯 CRM Leads & Management
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` / `POST` | `/api/v1/leads/` | List (Filterable & Searchable) or Create Lead |
| `GET` / `PATCH` | `/api/v1/leads/{display_id}/` | Get Lead Details / Update Status |
| `GET` | `/api/v1/agents/` | List Active CRM Agents & Workload |
| `POST` | `/api/v1/agents/{id}/activate/` | Activate CRM Agent |
| `POST` | `/api/v1/agents/{id}/deactivate/` | Deactivate CRM Agent |
| `GET` | `/api/v1/accounts/` | List User Accounts (Admin Only) |
| `POST` | `/api/v1/accounts/{id}/activate/` | Activate User Account |
| `POST` | `/api/v1/accounts/{id}/deactivate/` | Deactivate User Account |
| `GET` | `/api/v1/dashboard/metrics/` | Realtime Dashboard Analytics |

### 📞 Telephony, Calls & WhatsApp
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/telephony/webhooks/incoming-call/` | Exotel Incoming Call Callback |
| `POST` | `/api/v1/telephony/webhooks/call-status/` | Exotel Call Status Completion Callback |
| `GET` | `/api/v1/calls/` | List All Calls |
| `GET` | `/api/v1/calls/{display_id}/transcript/` | Get ElevenLabs Voice Transcript |
| `GET` | `/api/v1/calls/{display_id}/summary/` | Get OpenAI LLM Call Summary |
| `GET` | `/api/v1/followups/` | List Pending & Completed Follow-ups |
| `GET` | `/api/v1/whatsapp/` | List WhatsApp Sent Logs |
| `POST` | `/api/v1/whatsapp/{display_id}/resend/` | Resend Failed WhatsApp Message |

---

## 📖 Swagger Documentation
Interactive API Documentation is available at:
- **Swagger UI**: [http://127.0.0.1:8000/api/docs/](http://127.0.0.1:8000/api/docs/)
- **OpenAPI Schema**: [http://127.0.0.1:8000/api/schema/](http://127.0.0.1:8000/api/schema/)
