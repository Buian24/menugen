from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Order(db.Model):
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True) # orderCode cho PayOS
    shop_name = db.Column(db.String(100), nullable=False)
    template_key = db.Column(db.String(50), nullable=False)
    excel_filename = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Integer, default=20000)
    status = db.Column(db.String(20), default='PENDING') # PENDING, PAID, FAILED
    paid_pdf = db.Column(db.String(255), nullable=True)  # Tên file PDF sau khi thanh toán
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    niche_slug = db.Column(db.String(50), default='homepage')