from app import create_app
from dotenv import load_dotenv
import os

# Tải các biến môi trường từ file .env.
# Điều này hữu ích khi chạy gunicorn trực tiếp từ terminal.
# Khi dùng systemd, file .env sẽ được nạp qua chỉ thị 'EnvironmentFile'.
load_dotenv()

app = create_app()