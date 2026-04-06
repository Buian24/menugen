from flask import (Blueprint, render_template, request,
                   redirect, url_for, send_from_directory,
                   session, jsonify, current_app, flash, Response)
from werkzeug.utils import secure_filename
import os
import uuid
import hashlib
import hmac
import urllib.parse
from datetime import datetime
from .parser import parse_excel
from .renderer import render_menu_pdf
from .models import db, Order
from payos import PayOS
from payos.type import ItemData, PaymentData
import pandas as pd
from .data import PAGES_CONTENT

main = Blueprint('main', __name__)

payos_client = PayOS(
    client_id=os.environ.get('PAYOS_CLIENT_ID', 'YOUR_CLIENT_ID'),
    api_key=os.environ.get('PAYOS_API_KEY', 'YOUR_API_KEY'),
    checksum_key=os.environ.get('PAYOS_CHECKSUM_KEY', 'YOUR_CHECKSUM_KEY')
)

ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_order_token(order_id):
    """Tạo token bảo mật để xác thực quyền truy cập đơn hàng thay cho session"""
    secret = current_app.secret_key.encode('utf-8') if current_app.secret_key else b'dev-secret'
    return hmac.new(secret, str(order_id).encode('utf-8'), hashlib.sha256).hexdigest()[:16]

def parse_manual_form(form_data):
    """Hàm mới để xử lý dữ liệu từ form nhập tay và chuyển đổi thành file Excel"""
    total_items = 0
    try:
        items = {}
        for key, value in form_data.items():
            if key.startswith('items['):
                parts = key.replace(']', '').split('[')
                index = int(parts[1])
                field = parts[2]
                if index not in items:
                    items[index] = {}
                items[index][field] = value

        data = []
        for index in sorted(items.keys()):
            item = items[index]
            ten_mon = item.get('ten_mon', '').strip()
            gia_str = item.get('gia', '0').strip()

            if not ten_mon or not gia_str:
                continue

            data.append({
                'ten_mon': ten_mon,
                'gia': gia_str,
                'nhom': item.get('nhom', 'Món khác').strip() or 'Món khác',
                'mo_ta': item.get('mo_ta', '').strip(),
                'ghi_chu': item.get('ghi_chu', '').strip(),
            })
            total_items += 1
        
        if total_items == 0:
            return {'success': False, 'error': 'Bạn chưa nhập món ăn nào.'}

        df = pd.DataFrame(data)
        filename = f'manual_{uuid.uuid4().hex}.xlsx'
        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        df.to_excel(upload_path, index=False)

        return {'success': True, 'filename': filename}
    except Exception as e:
        return {'success': False, 'error': f'Lỗi xử lý dữ liệu nhập tay: {e}'}

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/p/<slug>')
def niche_landing(slug):
    page_data = PAGES_CONTENT.get(slug)
    if not page_data:
        return redirect(url_for('main.index'))
    return render_template('niche_landing.html', page=page_data)

@main.route('/sitemap.xml')
def sitemap():
    pages = []
    # Trang chủ
    pages.append({'loc': url_for('main.index', _external=True), 'priority': '1.0'})
    
    # Tự động lấy tất cả các trang ngách từ data.py
    for slug in PAGES_CONTENT.keys():
        pages.append({
            'loc': url_for('main.niche_landing', slug=slug, _external=True),
            'priority': '0.8'
        })
        
    sitemap_xml = render_template('sitemap.xml', pages=pages)
    return Response(sitemap_xml, mimetype='application/xml')

@main.route('/upload', methods=['POST'])
def upload():
    shop_name = request.form.get('shop_name', 'Quán của tôi').strip()
    template_key = request.form.get('template', 'classic')
    input_method = request.form.get('input_method', 'excel')
    niche_slug = request.form.get('niche_slug', 'homepage')
    
    filename = None
    menu_data = {}

    if input_method == 'excel':
        if 'excel_file' not in request.files:
            flash('Chưa chọn file!', 'error')
            return redirect(request.referrer or url_for('main.index'))

        file = request.files['excel_file']

        if not file or not allowed_file(file.filename):
            flash('Chỉ chấp nhận file .xlsx hoặc .xls', 'error')
            return redirect(request.referrer or url_for('main.index'))

        filename = f'{uuid.uuid4().hex}_{secure_filename(file.filename)}'
        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(upload_path)
        menu_data = parse_excel(upload_path)
    
    elif input_method == 'manual':
        result = parse_manual_form(request.form)
        if not result['success']:
            flash(result['error'], 'error')
            return redirect(request.referrer or url_for('main.index'))
            
        filename = result['filename']
        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        menu_data = parse_excel(upload_path)


    if not menu_data.get('success'):
        flash(menu_data.get('error', 'Lỗi không xác định'), 'error')
        return redirect(request.referrer or url_for('main.index'))

    pdf_file = render_menu_pdf(menu_data, shop_name, template_key, watermark=True)

    # Lưu Order vào Database thay vì dùng Session
    new_order = Order(
        shop_name=shop_name,
        template_key=template_key,
        excel_filename=filename,
        amount=20000,
        niche_slug=niche_slug
    )
    db.session.add(new_order)
    db.session.commit()

    return render_template('preview.html',
                           pdf_file=pdf_file,
                           shop_name=shop_name,
                           order_id=new_order.id,
                           total_items=menu_data['total_items'],
                           groups=menu_data['groups'])

@main.route('/preview/<filename>')
def serve_preview(filename):
    return send_from_directory(current_app.config['OUTPUT_FOLDER'], filename)

@main.route('/download-sample')
def download_sample():
    # Sử dụng current_app.static_folder để lấy path tuyệt đối chuẩn trên VPS
    return send_from_directory(current_app.static_folder, 'sample.xlsx', as_attachment=True)

# ---- Tích hợp PayOS (VietQR) ----
@main.route('/payment/payos/<int:order_id>', methods=['POST'])
def payment_payos(order_id):
    order = Order.query.get_or_404(order_id)
    
    if order.status == 'PAID':
        return jsonify({'success': False, 'msg': 'Đơn hàng này đã được thanh toán.'}), 400

    item = ItemData(name=f"Tạo Menu - {order.shop_name}", quantity=1, price=order.amount)
    payment_data = PaymentData(
        orderCode=order.id,
        amount=order.amount,
        description=f"Thanh toan Menu {order.id}",
        items=[item],
        cancelUrl=url_for('main.index', _external=True),                 # Nơi user về nếu bấm Hủy
        returnUrl=url_for('main.payment_success', order_id=order.id, token=get_order_token(order.id), _external=True)  # Về trang kết quả
    )
    
    try:
        # Tạo link thanh toán
        payos_response = payos_client.createPaymentLink(paymentData=payment_data)
        return jsonify({'success': True, 'checkout_url': payos_response.checkoutUrl})
    except Exception as e:
        print(f"Chi tiết lỗi PayOS: {str(e)}")
        return jsonify({'success': False, 'msg': str(e)}), 500

@main.route('/payment/payos_webhook', methods=['POST'])
def payos_webhook():
    """IPN Lắng nghe thông báo từ PayOS khi có người chuyển khoản thành công"""
    try:
        webhook_body = request.json
        
        # Xác minh chữ ký webhook để đảm bảo dữ liệu chuẩn từ PayOS
        webhook_data = payos_client.verifyPaymentWebhookData(webhook_body)
        
        # Nếu hợp lệ, lấy mã đơn hàng
        order_id = webhook_data.orderCode
        order = Order.query.get(order_id)
        
        if order and order.status == 'PENDING':
            # Cập nhật trạng thái Database
            order.status = 'PAID'
            
            # Tạo PDF thật (Bỏ watermark)
            upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], order.excel_filename)
            menu_data = parse_excel(upload_path)
            paid_pdf = render_menu_pdf(menu_data, order.shop_name, order.template_key, watermark=False)
            
            order.paid_pdf = paid_pdf
            db.session.commit()
            
        return jsonify({"success": True, "message": "Ok"}), 200
        
    except Exception as e:
        print("Webhook Error:", e)
        return jsonify({"success": False, "message": "Invalid Webhook"}), 400

@main.route('/api/check-order/<int:order_id>')
def check_order(order_id):
    """API dùng để frontend gọi kiểm tra xem đơn đã thanh toán xong chưa"""
    order = Order.query.get_or_404(order_id)
    return jsonify({
        'status': order.status,
        'success_url': url_for('main.payment_success', order_id=order.id, token=get_order_token(order.id)) if order.status == 'PAID' else None
    })

@main.route('/success/<int:order_id>')
def payment_success(order_id):
    """Trang hiển thị Full và tải PDF sau khi thanh toán thành công"""
    order = Order.query.get_or_404(order_id)
    
    # Kiểm tra quyền sở hữu bằng token thay cho session
    token = request.args.get('token')
    if token != get_order_token(order.id):
        flash('Bạn không có quyền truy cập đơn hàng này.', 'error')
        return redirect(url_for('main.index'))
        
    # 1. Khách hàng chủ động bấm nút "Hủy" hoặc "Quay lại" trên trang PayOS
    if request.args.get('cancel') == 'true':
        flash('Bạn đã hủy quá trình thanh toán.', 'error')
        return redirect(url_for('main.index'))

    # 2. Khắc phục độ trễ của Webhook (Race Condition)
    if order.status != 'PAID':
        try:
            # Chủ động hỏi PayOS trạng thái thực tế của mã đơn hàng này
            payment_info = payos_client.getPaymentLinkInformation(order.id)
            if payment_info.status == 'PAID':
                order.status = 'PAID'
                # Nếu Webhook chưa kịp tạo file PDF thì ta tạo luôn tại đây
                if not order.paid_pdf:
                    upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], order.excel_filename)
                    menu_data = parse_excel(upload_path)
                    paid_pdf = render_menu_pdf(menu_data, order.shop_name, order.template_key, watermark=False)
                    order.paid_pdf = paid_pdf
                db.session.commit()
        except Exception as e:
            print(f"Lỗi khi kiểm tra PayOS trên trang success: {e}")

    # 3. Nếu kiểm tra xong vẫn chưa PAID (Do ngân hàng xử lý chậm)
    if order.status != 'PAID':
        return f"""
        <!DOCTYPE html>
        <html>
            <head><meta charset="UTF-8"><meta http-equiv="refresh" content="3"><title>Đang xử lý...</title></head>
            <body style="text-align:center; padding:50px; font-family:sans-serif; background-color:#f4f7f6;">
                <h2 style="color:#2E86AB;">Đang xác nhận thanh toán...</h2>
                <p>Hệ thống đang chờ phản hồi từ ngân hàng. Trang web sẽ tự động làm mới, vui lòng không đóng trang này.</p>
            </body>
        </html>
        """
    
    return render_template('success.html', order=order, pdf_file=order.paid_pdf, token=token)

@main.route('/download/paid/<int:order_id>')
def download_paid(order_id):
    order = Order.query.get_or_404(order_id)
    
    # Kiểm tra quyền sở hữu bằng token
    token = request.args.get('token')
    if token != get_order_token(order.id):
        flash('Bạn không có quyền tải xuống đơn hàng này.', 'error')
        return redirect(url_for('main.index'))
        
    if order.status != 'PAID' or not order.paid_pdf:
        flash('Đơn hàng chưa thanh toán hoặc chưa sẵn sàng!', 'error')
        return redirect(url_for('main.index'))
        
    return send_from_directory(
        current_app.config['OUTPUT_FOLDER'],
        order.paid_pdf,
        as_attachment=True,
        download_name='menu.pdf'
    )
