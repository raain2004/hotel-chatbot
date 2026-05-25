# Hướng dẫn các bước thủ công

File `.env` đã được tạo sẵn với `SECRET_KEY`, `ADMIN_API_KEY`, `FB_VERIFY_TOKEN`.
Giữ bí mật các giá trị này — không commit `.env` lên Git.

## 1. Chạy nhanh bằng Docker (không cần cài Python)

```powershell
cd c:\Users\vugam\Downloads\hotel-chatbot
.\scripts\setup.ps1
```

Hoặc từng bước:

```powershell
docker compose up -d db
docker compose -f docker-compose.test.yml run --rm test
docker compose up -d api
curl -X POST http://localhost:8000/api/dev/seed
```

- API: http://localhost:8000/docs
- Admin key (trong `.env`): dùng header `X-Admin-Key`

## 2. Cài Python trên Windows (tùy chọn, dev local)

**Không dùng** thư mục source `D:\Python-3.12.13` (không có `python.exe`).

1. Tải **Windows installer (64-bit)**: https://www.python.org/downloads/
2. Cài, bật **Add python.exe to PATH**
3. Terminal mới:

```powershell
cd c:\Users\vugam\Downloads\hotel-chatbot
python -m pip install -r requirements.txt
docker compose up -d db
python -m uvicorn app.main:app --reload
```

## 3. Anthropic API (Claude)

1. Đăng ký https://console.anthropic.com
2. Tạo API key
3. Sửa `.env`:

```
ANTHROPIC_API_KEY=sk-ant-api03-...
CLAUDE_MOCK_MODE=false
```

4. Khởi động lại API: `docker compose restart api`

## 4. Facebook Messenger + ngrok

### 4.1 Tạo app Meta

1. https://developers.facebook.com → **Create App** → loại Business
2. Thêm sản phẩm **Messenger**
3. **Messenger → Settings** → Connect Facebook Page → lấy **Page Access Token**
4. **App Settings → Basic** → copy **App Secret**

### 4.2 Cập nhật `.env`

```
FB_PAGE_ACCESS_TOKEN=EAAxxxxx...
FB_APP_SECRET=xxxxxxxx
FB_VERIFY_TOKEN=hotel_verify_token_dev
```

`FB_VERIFY_TOKEN` phải **trùng** với giá trị nhập trên Meta khi đăng ký webhook.

### 4.3 Expose local ra internet (ngrok)

```powershell
# Cài ngrok: https://ngrok.com/download
ngrok config add-authtoken <token_từ_dashboard_ngrok>
ngrok http 8000
```

Copy URL dạng `https://xxxx.ngrok-free.app`.

### 4.4 Đăng ký Webhook trên Meta

**Messenger → Webhooks → Add Callback URL**

| Trường | Giá trị |
|--------|---------|
| Callback URL | `https://xxxx.ngrok-free.app/webhook` |
| Verify Token | `hotel_verify_token_dev` (hoặc giá trị trong `.env`) |

Subscribe: `messages`, `messaging_postbacks`.

### 4.5 Test

Nhắn tin vào Facebook Page → bot trả lời (cần `ANTHROPIC_API_KEY` nếu `CLAUDE_MOCK_MODE=false`).

## 5. Checklist

- [ ] `docker compose up -d db` — Postgres chạy
- [ ] `docker compose -f docker-compose.test.yml run --rm test` — tests pass
- [ ] `docker compose up -d api` + seed
- [ ] `ANTHROPIC_API_KEY` trong `.env`
- [ ] Meta app + Page token + App Secret
- [ ] ngrok + webhook verified
- [ ] Nhắn thử trên Messenger
