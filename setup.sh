#!/bin/bash
# AutoShorts - Setup Script

set -e

echo "🚀 AutoShorts Setup"
echo "==================="

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 chưa được cài đặt"
    exit 1
fi

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js chưa được cài đặt"
    exit 1
fi

# Check FFmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️  FFmpeg chưa được cài đặt. Đang cài..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew install ffmpeg
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo apt-get update && sudo apt-get install -y ffmpeg
    fi
fi

echo ""
echo "📦 Cài đặt Backend dependencies..."
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp -n .env.example .env || true

echo ""
echo "🔤 Tải font Roboto (hỗ trợ tiếng Việt)..."
python download_fonts.py
echo "✅ Backend ready"

echo ""
echo "📦 Cài đặt Frontend dependencies..."
cd ../frontend
npm install
echo "✅ Frontend ready"

cd ..

echo ""
echo "✅ Setup hoàn tất!"
echo ""
echo "📋 Bước tiếp theo:"
echo "  1. Điền API keys vào backend/.env"
echo "     - OPENAI_API_KEY (bắt buộc)"
echo "     - PEXELS_API_KEY (bắt buộc, miễn phí tại pexels.com/api)"
echo "     - ELEVENLABS_API_KEY (optional - mặc định dùng edge-tts miễn phí)"
echo "  2. Thêm nhạc nền vào backend/assets/music/ (xem add_music.md)"
echo "  3. Chạy Redis: docker run -d -p 6379:6379 redis:alpine"
echo "  4. Terminal 1: cd backend && source venv/bin/activate && uvicorn app.main:app --reload"
echo "  5. Terminal 2: cd backend && source venv/bin/activate && celery -A app.celery_app worker --loglevel=info"
echo "  6. Terminal 3: cd frontend && npm run dev"
echo ""
echo "🎙️  TTS mặc định: Microsoft Edge TTS (vi-VN-HoaiMyNeural) — MIỄN PHÍ"
echo "🌐 Truy cập: http://localhost:3000"
