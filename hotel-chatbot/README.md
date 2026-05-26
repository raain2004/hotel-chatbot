# 🏨 Hotel Chatbot — Claude AI + Facebook Messenger

Chatbot quản lý khách sạn tích hợp Claude AI, PostgreSQL và Facebook Messenger.

## Lộ trình phát triển

| Giai đoạn | Nội dung | Trạng thái |
|-----------|----------|------------|
| 1 | Setup, Database Schema, Models | ✅ Hoàn thành |
| 2 | Claude Service + Booking Service | ✅ Hoàn thành |
| 3 | Facebook Messenger Webhook | ✅ Hoàn thành |
| 4 | Quản lý Conversation & Context | ✅ Hoàn thành |
| 5 | Dashboard quản lý + Notifications | ✅ Hoàn thành |

## Cài đặt nhanh (Docker — khuyến nghị)

```powershell
# File .env đã có sẵn — chỉ cần điền ANTHROPIC_API_KEY và FB_* khi dùng thật
.\scripts\setup.ps1
```

Hoặc thủ công:

```bash
docker compose up -d db
docker compose up -d --build api
curl -X POST http://localhost:8000/api/dev/seed
```

Chi tiết Meta / ngrok / Python: [docs/CAI_DAT_THU_CONG.md](docs/CAI_DAT_THU_CONG.md)

## API Giai đoạn 2

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/api/bookings/availability` | Kiểm tra phòng trống |
| POST | `/api/bookings` | Tạo booking |
| GET | `/api/bookings/{code}` | Tra cứu theo mã |
| GET | `/api/bookings?phone=` | Tra cứu theo SĐT |
| POST | `/api/bookings/{code}/confirm` | Xác nhận booking |
| POST | `/api/bookings/{code}/cancel` | Hủy booking |
| POST | `/api/chat` | Chat với Claude (test) |
| POST | `/api/dev/seed` | Seed dữ liệu mẫu (dev) |

## API Giai đoạn 4–5 (Admin)

### Authentication

Có 2 phương thức xác thực:

1. **JWT Token** (khuyến nghị cho dashboard & production):
   - Lấy token: `POST /api/auth/token` với body `{"username": "admin", "password": "<ADMIN_API_KEY>"}`
   - Sử dụng: Header `Authorization: Bearer <token>`

2. **X-Admin-Key** (cho development/testing):
   - Header: `X-Admin-Key: <ADMIN_API_KEY>`
   - Chỉ hoạt động khi `APP_ENV=development` hoặc `test`

| Method | Endpoint | Mô tả | Auth Required |
|--------|----------|-------|---------------|
| POST | `/api/auth/token` | Login lấy JWT token | ❌ |
| GET | `/api/auth/me` | Thông tin user hiện tại | ✅ JWT |
| POST | `/api/auth/refresh` | Làm mới token | ❌ |
| POST | `/api/auth/logout` | Logout | ✅ JWT |
| GET | `/api/conversations` | Danh sách hội thoại | ✅ |
| GET | `/api/conversations/{id}` | Chi tiết + messages | ✅ |
| PATCH | `/api/conversations/{id}/context` | Cập nhật context | ✅ |
| PATCH | `/api/conversations/{id}/status` | active / resolved / waiting_human | ✅ |
| GET | `/api/dashboard/stats` | Thống kê tổng quan | ✅ JWT |
| GET | `/api/dashboard/bookings/recent` | Booking gần đây | ✅ JWT |
| GET | `/api/dashboard/notifications` | Thông báo nội bộ | ✅ JWT |
| POST | `/api/dashboard/notifications/{id}/read` | Đánh dấu đã đọc | ✅ JWT |

## Chạy tests

```bash
pip install -r requirements.txt
pytest -v

# Windows (PowerShell)
.\scripts\run_tests.ps1

# Hoặc qua Docker
docker compose -f docker-compose.test.yml run --rm test
```

Tests dùng SQLite in-memory + `CLAUDE_MOCK_MODE=true` (không gọi API Claude thật).

## Facebook Messenger (Giai đoạn 3)

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/webhook` | Xác minh webhook (Meta gọi khi setup) |
| POST | `/webhook` | Nhận tin nhắn từ khách |

### Cấu hình Meta Developer

1. Tạo app tại [developers.facebook.com](https://developers.facebook.com) → thêm sản phẩm **Messenger**.
2. Tạo **Page** và liên kết với app, lấy **Page Access Token**.
3. Trong **Messenger → Settings → Webhooks**:
   - **Callback URL**: `https://<domain-công-khai>/webhook` (dùng [ngrok](https://ngrok.com) khi dev local)
   - **Verify Token**: trùng `FB_VERIFY_TOKEN` trong `.env`
   - Subscribe: `messages`, `messaging_postbacks`
4. Điền `.env`:
   ```
   FB_PAGE_ACCESS_TOKEN=...
   FB_VERIFY_TOKEN=...
   FB_APP_SECRET=...
   ```

### Dev local với ngrok

```bash
uvicorn app.main:app --reload --port 8000
ngrok http 8000
# Dán URL https://xxxx.ngrok.io/webhook vào Meta Developer
```

Luồng: khách nhắn Page → Meta POST `/webhook` → xử lý nền → gọi Claude → gửi reply qua Send API.

## Cấu trúc project

```
hotel-chatbot/
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── config.py            # Cấu hình env vars
│   ├── database.py          # PostgreSQL connection
│   ├── models/              # SQLAlchemy ORM models
│   │   ├── hotel.py         # Hotels, Rooms, RoomTypes
│   │   ├── booking.py       # Bookings, Guests
│   │   └── conversation.py  # Chat sessions, Messages
│   ├── core/
│   │   ├── prompts.py       # System prompts cho Claude
│   │   └── actions.py       # Parse thẻ <action> từ Claude
│   ├── schemas/             # Pydantic request/response
│   ├── services/
│   │   ├── booking_service.py
│   │   ├── claude_service.py
│   │   ├── conversation_service.py
│   │   └── messenger_service.py
│   └── api/
│       ├── bookings.py
│       ├── chat.py
│       ├── dev.py
│       └── webhook.py
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## Cập nhật gần đây (v1.1)

### ✅ Đã hoàn thiện
- **JWT Authentication**: Dashboard API yêu cầu JWT token thay vì chỉ X-Admin-Key
- **Auth Endpoints**: Thêm `/api/auth/token`, `/api/auth/me`, `/api/auth/refresh`, `/api/auth/logout`
- **Test Coverage**: 19/19 tests pass (100%)
- **Security Fix**: Sửa lỗi `verify_jwt_token` không nhận header đúng cách

### 📋 Các tính năng đã có
- ✅ 5/5 giai đoạn phát triển hoàn thành
- ✅ Database migrations với Alembic
- ✅ CI/CD pipeline (GitHub Actions)
- ✅ Docker & docker-compose
- ✅ Rate limiting (chưa áp dụng)
- ✅ Redis caching (chưa sử dụng)

### 🔜 Next Steps (đề xuất)
1. Áp dụng rate limiting cho API endpoints
2. Sử dụng Redis cache cho Claude responses
3. Build admin dashboard UI (React/Vue)
4. Tích hợp payment gateway (VNPay/Stripe)
5. Thêm monitoring (Sentry, Prometheus)
6. Implement token blacklist cho logout
