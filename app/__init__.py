from flask import Flask
import os
from werkzeug.middleware.proxy_fix import ProxyFix

def create_app():
    app = Flask(__name__)

    # Nhận diện đúng HTTPS khi chạy phía sau Cloudflare Tunnel hoặc Reverse Proxy
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    # Dùng đường dẫn tuyệt đối, tính từ vị trí file __init__.py
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    app.config['UPLOAD_FOLDER'] = os.path.join(base_dir, 'uploads')
    app.config['OUTPUT_FOLDER'] = os.path.join(base_dir, 'outputs')
    app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024
    app.secret_key = os.environ.get('SECRET_KEY', 'menugen-dev-key')
    
    # Cấu hình SQLAlchemy (Dùng SQLite cho MVP)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(base_dir, 'menugen.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    from .models import db
    db.init_app(app)
    with app.app_context():
        db.create_all()  # Tự động tạo file database menugen.db nếu chưa có

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

    from .routes import main
    app.register_blueprint(main)

    return app
