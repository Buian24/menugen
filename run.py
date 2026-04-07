from app import create_app
from dotenv import load_dotenv

# Tự động nạp biến môi trường từ file .env khi chạy ở máy tính cá nhân
load_dotenv()

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
