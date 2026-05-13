# Hướng dẫn Setup YouTube Data API v3

## Bước 1: Tạo Google Cloud Project

1. Vào https://console.cloud.google.com
2. Click **"New Project"** → đặt tên (vd: `autoshorts`)
3. Chọn project vừa tạo

## Bước 2: Bật YouTube Data API v3

1. Vào **APIs & Services → Library**
2. Tìm **"YouTube Data API v3"**
3. Click **Enable**

## Bước 3: Tạo OAuth2 Credentials

1. Vào **APIs & Services → Credentials**
2. Click **"+ Create Credentials" → OAuth client ID**
3. Nếu chưa có OAuth consent screen → click **"Configure consent screen"**:
   - User Type: **External**
   - App name: `AutoShorts`
   - Support email: email của bạn
   - Scopes: thêm `youtube.upload` và `youtube.readonly`
   - Test users: thêm email YouTube channel của bạn
4. Quay lại tạo OAuth client ID:
   - Application type: **Web application**
   - Name: `AutoShorts`
   - Authorized redirect URIs: `http://localhost:8000/api/youtube/oauth/callback`
5. Click **Create** → copy **Client ID** và **Client Secret**

## Bước 4: Điền vào .env

```env
YOUTUBE_CLIENT_ID=123456789-abc...apps.googleusercontent.com
YOUTUBE_CLIENT_SECRET=GOCSPX-...
YOUTUBE_REDIRECT_URI=http://localhost:8000/api/youtube/oauth/callback
```

## Bước 5: Authorize lần đầu

1. Chạy backend: `uvicorn app.main:app --reload`
2. Truy cập: http://localhost:8000/api/youtube/oauth/authorize
3. Đăng nhập Google → chọn channel → Allow
4. Redirect về http://localhost:3000?youtube_connected=true
5. Token được lưu tại `backend/assets/youtube_token.json`

**Từ đó về sau không cần authorize lại** — token tự động refresh.

## Lưu ý quan trọng

- **Quota**: YouTube API miễn phí 10,000 units/ngày. Mỗi upload tốn ~1,600 units → ~6 video/ngày free
- **App chưa verified**: Khi test, Google sẽ hiện cảnh báo "App chưa được xác minh" → click "Advanced" → "Go to AutoShorts (unsafe)" → vẫn hoạt động bình thường
- **Production**: Nếu muốn dùng với nhiều user, cần submit app để Google review (mất 1-4 tuần)
- **Shorts requirement**: Video phải ≤60 giây và tỷ lệ 9:16 — app đã đáp ứng cả hai

## Quota tham khảo

| Action | Units |
|--------|-------|
| Upload video | 1,600 |
| Get channel info | 1 |
| Daily limit | 10,000 |
| **Video upload/ngày** | **~6** |

Để tăng quota → request tại Google Cloud Console → APIs & Services → YouTube Data API v3 → Quotas.
