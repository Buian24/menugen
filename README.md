# MenuGen AI – MVP

Tool tạo menu quán ăn từ file Excel.

## Cài đặt nhanh

```bash
# 1. Clone/copy project
cd menugen

# 2. Cài dependencies (môi trường local)
pip install -r requirements.txt

# 3. Chạy local test
python run.py
# Mở http://localhost:5000

# 4. Hoặc chạy Docker
cp .env.example .env
# Điền CLOUDFLARE_TUNNEL_TOKEN vào .env
docker-compose up -d
```

## Format file Excel

| ten_mon | gia | nhom | mo_ta | ghi_chu |
|---------|-----|------|-------|---------|
| Phở bò  | 65000 | Món nước | Tái nạm | |

Tải file mẫu tại: /download-sample

## Luồng hoạt động

1. Upload Excel → validate → parse
2. Chọn template → render PDF preview (có watermark)
3. Thanh toán → download PDF sạch
