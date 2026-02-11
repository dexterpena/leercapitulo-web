# FiebreReader

A manga reading web application that scrapes [leercapitulo.co](https://www.leercapitulo.co) with user accounts, personal library tracking, Anilist sync, an ebook-style reader, and PDF chapter downloads.

## Tech Stack

- **Backend:** Python / FastAPI
- **Frontend:** React / TypeScript / Vite
- **Database & Auth:** Supabase (PostgreSQL + Auth + Row Level Security)
- **Scraping:** BeautifulSoup + Playwright (headless Chrome for JS-rendered pages)
- **PDF Generation:** img2pdf

## Features

- **Browse manga** — popular, latest updates, and search
- **Manga details** — cover, author, genres, status, full chapter list
- **Online reader** — ebook-style page-by-page viewer with keyboard/click navigation and page selector
- **PDF download** — download any chapter as a PDF
- **User accounts** — signup/login via Supabase Auth
- **Personal library** — save manga, track reading progress, filter by status (reading, completed, plan to read, dropped)
- **Chapter tracking** — mark chapters as viewed, bookmark chapters, mark all previous as viewed
- **Anilist integration** — link your Anilist account, auto-sync chapter progress, import your manga list
- **Theme support** — light and dark mode toggle

## Setup

### 1. Supabase

1. Create a project at [supabase.com](https://supabase.com)
2. Go to the SQL Editor and run the contents of `supabase_schema.sql`
3. Copy your project URL, anon key, and service role key

### 2. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

Create a `.env` file in the `backend/` directory:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-role-key
ANILIST_CLIENT_ID=your-anilist-client-id
ANILIST_CLIENT_SECRET=your-anilist-client-secret
ANILIST_REDIRECT_URI=http://localhost:5173/settings?anilist_callback=true
FRONTEND_URL=http://localhost:5173
```

Start the server:

```bash
uvicorn app.main:app --reload
```

### 3. Frontend

```bash
cd frontend
npm install
```

Create a `.env.local` file in the `frontend/` directory:

```env
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
```

Start the dev server:

```bash
npm run dev
```

### 4. Anilist (optional)

1. Register an app at [anilist.co/settings/developer](https://anilist.co/settings/developer)
2. Set the redirect URI to `http://localhost:5173/settings?anilist_callback=true`
3. Add the client ID and secret to the backend `.env`

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/manga/popular?page=1` | Popular manga |
| GET | `/api/manga/latest?page=1` | Latest updates |
| GET | `/api/manga/search?q=...&page=1` | Search manga by title |
| GET | `/api/manga/detail?url=...` | Manga details |
| GET | `/api/manga/chapters?url=...` | Chapter list |
| GET | `/api/manga/chapter-images?url=...` | Chapter image URLs |
| GET | `/api/reader/image-proxy?url=...` | Proxy a manga image |
| GET | `/api/reader/download-pdf?url=...` | Download chapter as PDF |
| POST | `/api/auth/signup` | Create account |
| POST | `/api/auth/login` | Login |
| GET | `/api/library` | Get user's library |
| POST | `/api/library` | Add manga to library |
| PATCH | `/api/library/:id` | Update library entry |
| DELETE | `/api/library/:id` | Remove from library |
| GET | `/api/anilist/auth-url` | Get Anilist OAuth URL |
| POST | `/api/anilist/exchange-code` | Exchange OAuth code |
| GET | `/api/anilist/status` | Check Anilist link status |
| POST | `/api/anilist/sync` | Sync progress to Anilist |
| GET | `/api/chapters/status` | Get chapter read/bookmark status |
| POST | `/api/chapters/mark-read` | Mark chapter as read |
| POST | `/api/chapters/bookmark` | Bookmark a chapter |
| POST | `/api/chapters/mark-previous-read` | Mark all previous chapters as read |
