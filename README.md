# CivicAI India 🇮🇳

**Offline-first civic issue reporting with AI-powered triage for Indian citizens.**

Citizens photograph or describe a civic problem (pothole, water leak, garbage, electrical hazard, etc.) and the AI instantly classifies it, assigns priority, routes it to the correct government department, and flags duplicates automatically. Built as a Progressive Web App (PWA) — works fully offline and is installable on any phone.

---

## Features

| Feature | Details |
|---|---|
| 📸 **AI Photo Analysis** | Upload a photo — Google Gemini classifies the issue type, priority, department, and writes the report description for you |
| 🤖 **Text AI Classification** | Keyword-weighted offline classifier works without internet or API key |
| 🔁 **Duplicate Detection** | Jaccard similarity detects near-duplicate reports and auto-upvotes the existing one |
| 🗺️ **Hotspot Detection** | Flags locations with repeated complaints for escalation |
| 🔒 **Privacy Protection** | Strips phone numbers, emails, Aadhaar, and house numbers before saving |
| 📲 **PWA / Offline-first** | Service Worker caches the app shell — works offline, installable on Android/iOS |
| 🛡️ **Admin Panel** | Custom session-based admin at `/admin-panel/` for moderation, analytics, CSV export |
| 🚨 **Emergency Contacts** | Directory of India's civic emergency helpline numbers |
| 🤝 **Civic Assistant** | FAQ-style chatbot for common civic questions |

---

## Tech Stack

- **Backend:** Django 4.2, Python 3.11, Gunicorn
- **Database:** PostgreSQL (production) / SQLite (development)
- **Image Storage:** Cloudinary free tier
- **AI:** Google Gemini 1.5 Flash API + offline keyword classifier fallback
- **Frontend:** Tailwind CSS (CDN), Chart.js, GSAP animations
- **PWA:** Service Worker, Web App Manifest, offline caching
- **Hosting:** Render.com (free tier)

---

## Project Structure

```
CivicAI_India/               ← Repository root
├── manage.py                ← Django management script
├── requirements.txt         ← Python dependencies
├── Procfile                 ← Gunicorn start command
├── render.yaml              ← Render.com deployment config
├── gunicorn_config.py       ← Production server configuration
├── runtime.txt              ← Python version pin
├── .env.example             ← Environment variable template
│
├── janrakshak_django/       ← Django settings package
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
├── portal/                  ← Main Django app
│   ├── models.py            ← CivicReport, AuditLog, HotspotAnalysis
│   ├── views.py             ← Public-facing views & API endpoints
│   ├── services.py          ← AI engine, duplicate detector, data protection
│   ├── admin_views.py       ← Custom admin panel views
│   ├── admin_urls.py        ← Admin panel URL routing
│   ├── urls.py              ← Public URL routing
│   ├── admin.py             ← Django built-in admin config
│   └── migrations/          ← Database migrations
│
├── templates/               ← Django HTML templates
│   ├── base.html
│   ├── portal/              ← Public pages
│   ├── admin_panel/         ← Admin panel pages
│   └── pwa/                 ← PWA offline fallback
│
├── static/                  ← Static assets
│   ├── css/custom.css
│   ├── js/                  ← app.js, report.js, dashboard.js
│   ├── icons/               ← PWA icons (192×192, 512×512)
│   └── pwa/                 ← manifest.json, serviceworker.js
│
├── media/                   ← User-uploaded images (local dev only)
├── logs/                    ← Application logs
└── data/                    ← Audit log
```

---

## Local Development

### Prerequisites
- Python 3.11+
- Git

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/CivicAI_India.git
cd CivicAI_India

# 2. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate        # Linux/Mac
# .venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create your .env file
cp .env.example .env
```

Edit `.env` and set at minimum:
```env
DJANGO_DEBUG=True
DJANGO_SECRET_KEY=any-random-string-for-local-dev
GEMINI_API_KEY=your-gemini-api-key   # optional — offline AI works without it
```

```bash
# 5. Run database migrations
python3 manage.py migrate

# 6. Create an admin superuser (for /django-admin/)
python3 manage.py createsuperuser

# 7. Start the development server
python3 manage.py runserver
```

Open **http://127.0.0.1:8000** in your browser.

### Key URLs

| URL | Description |
|---|---|
| `http://127.0.0.1:8000/` | Analytics dashboard |
| `http://127.0.0.1:8000/report/` | Submit a civic issue report |
| `http://127.0.0.1:8000/reports/` | View all reports |
| `http://127.0.0.1:8000/emergency/` | Emergency contacts directory |
| `http://127.0.0.1:8000/admin-panel/` | Custom admin panel |
| `http://127.0.0.1:8000/django-admin/` | Django built-in admin |

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/analyze-photo/` | Analyze uploaded photo with Gemini AI |
| `POST` | `/api/preview-analysis/` | Preview AI classification before saving |
| `POST` | `/api/submit-report/` | Submit a civic issue report |
| `POST` | `/api/upvote-report/` | Upvote an existing report |
| `POST` | `/api/toggle-spam/<id>/` | Toggle spam status on a report |
| `POST` | `/api/ask/` | Ask the civic assistant a question |

---

## PWA Installation

On **Android (Chrome):** Visit the site → tap the install banner or ⋮ menu → **Add to Home screen**

On **iOS (Safari):** Visit the site → tap Share → **Add to Home Screen**

The app works offline after the first visit — the service worker caches all pages and static assets.

---

## License

MIT License — see [LICENSE](LICENSE) for details.
