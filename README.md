# 🎬 AutoShorts - AI Video Generator SaaS

Ứng dụng web tự động tạo video ngắn cho TikTok, Reels và YouTube Shorts sử dụng AI.

## Tech Stack

- **Frontend**: Next.js 14 (App Router), Tailwind CSS, Lucide Icons
- **Backend**: Python FastAPI + Celery + Redis
- **Video Processing**: MoviePy + FFmpeg
- **AI**: OpenAI GPT-4o (Script), ElevenLabs (TTS), Pexels (B-roll)

## Cấu trúc dự án

```
autoshorts/
├── frontend/          # Next.js App
├── backend/           # FastAPI + Celery
├── docker-compose.yml
└── README.md
```

## Setup

### 1. Clone & cài đặt

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Frontend
cd frontend
npm install
```

### 2. Cấu hình biến môi trường

```bash
# backend/.env
cp backend/.env.example backend/.env
# Điền API keys vào file .env
```

### 3. Chạy Redis (cần Docker)

```bash
docker run -d -p 6379:6379 redis:alpine
```

### 4. Chạy ứng dụng

```bash
# Terminal 1: Backend API
cd backend && uvicorn app.main:app --reload --port 8000

# Terminal 2: Celery Worker
cd backend && celery -A app.celery_app worker --loglevel=info

# Terminal 3: Frontend
cd frontend && npm run dev
```

### 5. Truy cập

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
