import os, json, bcrypt, csv, io, struct, zlib
from flask import Flask, render_template, request, redirect, session, Response, make_response
from supabase import create_client, Client
from werkzeug.utils import secure_filename
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dawalink-secret')

SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

PHARMACY_NAME = "DawaLink"
PHARMACY_PHONE = "+254792524333"
PHARMACY_EMAIL = "info@dawalink.co.ke"

# ---------- Context processor (cart total, user, notifications) ----------
@app.context_processor
def utility_processor():
    user_id = session.get('user_id')
    cart_total = 0.0
    if user_id:
        try:
            response = supabase.table('cart').select('quantity, products(price)').eq('user_id', user_id).execute()
            for item in response.data:
                prod = item.get('products')
                if prod and prod.get('price'):
                    cart_total += float(prod['price']) * item['quantity']
        except:
            pass
    else:
        guest_cart = session.get('cart', [])
        cart_total = sum(it['price'] * it['qty'] for it in guest_cart)

    wishlist_count = 0
    if user_id:
        try:
            count_res = supabase.table('wishlist').select('id', count='exact').eq('user_id', user_id).execute()
            wishlist_count = count_res.count if count_res.count else 0
        except:
            pass

    compare_ids = []
    try:
        compare_ids = json.loads(request.cookies.get('compare', '[]'))
    except:
        pass
    compare_count = len(compare_ids)

    user = None
    if user_id:
        try:
            user_res = supabase.table('users').select('full_name, email, is_admin, approved').eq('id', user_id).single().execute()
            user = user_res.data
        except:
            pass

    # Notifications for admin bell
    pending_orders = []
    pending_prescriptions = []
    if user and user.get('is_admin'):
        try:
            pending_orders = supabase.table('orders').select('id, shipping_name, total_amount').eq('order_status', 'pending').order('created_at', desc=True).limit(5).execute().data or []
        except:
            pass
        try:
            pending_prescriptions = supabase.table('prescriptions').select('id, customer_name, created_at').eq('status', 'pending').order('created_at', desc=True).limit(5).execute().data or []
        except:
            pass

    return dict(user=user, cart_total=cart_total,
                wishlist_count=wishlist_count, compare_count=compare_count,
                pharmacy_name=PHARMACY_NAME, phone=PHARMACY_PHONE, email=PHARMACY_EMAIL,
                pending_orders=pending_orders, pending_prescriptions=pending_prescriptions)

# ---------- Public pages (shop, cart, checkout, etc.) ----------
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']
        try:
            supabase.table('inquiries').insert({'name': name, 'email': email, 'message': message}).execute()
        except:
            pass
        return redirect('/contact?sent=1')
    return render_template('contact.html')

@app.route('/blog')
def blog():
    posts = [
        {"title":"Understanding Pain Relief","date":"2026-04-15","snippet":"Learn about different types of OTC pain relievers."},
        {"title":"Essential Baby Care Products","date":"2026-04-10","snippet":"A guide for new parents."},
        {"title":"Probiotics & Gut Health","date":"2026-04-02","snippet":"How probiotics improve wellness."}
    ]
    return render_template('blog.html', posts=posts)

@app.route('/shop')
def shop():
    search = request.args.get('search', '')
    category = request.args.get('category', '')
    page = int(request.args.get('page', 1))
    per_page = 6
    offset = (page - 1) * per_page

    query = supabase.table('products').select('*', count='exact').eq('active', True)
    if search:
        query = query.or_(f"name.ilike.%{search}%,category.ilike.%{search}%")
    if category:
        query = query.or_(f"category.ilike.%{category}%")
    total_res = query.execute()
    total = total_res.count if total_res.count else 0

    data_query = supabase.table('products').select('*').eq('active', True)
    if search:
        data_query = data_query.or_(f"name.ilike.%{search}%,category.ilike.%{search}%")
    if category:
        data_query = data_query.or_(f"category.ilike.%{category}%")
    result = data_query.range(offset, offset + per_page - 1).execute()
    products = result.data or []

    total_pages = max(1, (total + per_page - 1) // per_page)
    return render_template('shop.html', products=products, search=search, category=category,
                           page=page, total_pages=total_pages)

@app.route('/prescription', methods=['GET', 'POST'])
def prescription_upload():
    if request.method == 'POST':
        name = request.form['customer_name']
        email = request.form['customer_email']
        phone = request.form['customer_phone']
        notes = request.form.get('notes', '')
        file = request.files.get('prescription_file')
        file_url = None
        if file and file.filename:
            try:
                filename = secure_filename(file.filename)
                unique_name = f"rx_{os.urandom(4).hex()}_{filename}"
                file_bytes = file.read()
                supabase.storage.from_("product-images").upload(unique_name, file_bytes, {"content-type": file.content_type})
                file_url = f"{SUPABASE_URL}/storage/v1/object/public/product-images/{unique_name}"
            except:
                pass
        try:
            supabase.table('prescriptions').insert({
                'customer_name': name,
                'customer_email': email,
                'customer_phone': phone,
                'notes': notes,
                'file_url': file_url,
                'status': 'pending'
            }).execute()
        except:
            pass
        return render_template('prescription_success.html')
    return render_template('prescription_upload.html')

@app.route('/cart/add', methods=['POST'])
def add_to_cart():
    product_id = request.form['productId']
    quantity = int(request.form.get('quantity', 1))
    try:
        product = supabase.table('products').select('id, name, price').eq('id', product_id).single().execute()
    except:
        return 'Product not found', 404
    if not product.data:
        return 'Product not found', 404
    prod = product.data
    if 'user_id' in session:
        user_id = session['user_id']
        try:
            existing = supabase.table('cart').select('id, quantity').eq('user_id', user_id).eq('product_id', product_id).execute()
        except:
            return redirect('/cart')
        if existing.data:
            supabase.table('cart').update({'quantity': existing.data[0]['quantity'] + quantity}).eq('id', existing.data[0]['id']).execute()
        else:
            supabase.table('cart').insert({'user_id': user_id, 'product_id': product_id, 'quantity': quantity}).execute()
    else:
        cart = session.get('cart', [])
        found = False
        for item in cart:
            if item['productId'] == product_id:
                item['qty'] += quantity
                found = True
                break
        if not found:
            cart.append({'productId': product_id, 'qty': quantity, 'price': float(prod['price']), 'name': prod['name']})
        session['cart'] = cart
    return redirect('/cart')

@app.route('/cart')
def view_cart():
    cart_items = []
    total = 0.0
    if 'user_id' in session:
        user_id = session['user_id']
        try:
            db_cart = supabase.table('cart').select('quantity, product_id, products(name, price)').eq('user_id', user_id).execute()
        except:
            db_cart = []
        for item in db_cart.data if db_cart else []:
            prod = item.get('products')
            if prod:
                cart_items.append({'productId': item['product_id'], 'name': prod['name'], 'price': float(prod['price']), 'qty': item['quantity']})
                total += float(prod['price']) * item['quantity']
    else:
        cart_items = session.get('cart', [])
        total = sum(it['price'] * it['qty'] for it in cart_items)
    return render_template('cart.html', cart=cart_items, total=total)

@app.route('/cart/remove/<product_id>')
def remove_from_cart(product_id):
    if 'user_id' in session:
        try:
            supabase.table('cart').delete().eq('user_id', session['user_id']).eq('product_id', product_id).execute()
        except:
            pass
    else:
        cart = [i for i in session.get('cart', []) if i['productId'] != product_id]
        session['cart'] = cart
    return redirect('/cart')

@app.route('/checkout')
def checkout_form():
    return render_template('checkout.html')

@app.route('/checkout', methods=['POST'])
def place_order():
    guest_email = request.form.get('guest_email')
    user_id = session.get('user_id')

    delivery_method = request.form.get('delivery_method', 'delivery')
    shipping = {}
    if delivery_method == 'pickup':
        pickup_location = request.form.get('pickup_location', '')
        shipping['shipping_name'] = request.form.get('shipping_name', 'Pickup Customer')
        shipping['shipping_address'] = pickup_location
        shipping['shipping_city'] = ''
        shipping['shipping_phone'] = request.form.get('shipping_phone', '')
    else:
        shipping['shipping_name'] = request.form['shipping_name']
        shipping['shipping_address'] = request.form['shipping_address']
        shipping['shipping_city'] = request.form['shipping_city']
        shipping['shipping_phone'] = request.form['shipping_phone']

    shipping['payment_method'] = request.form['payment_method']

    cart_items = []
    if user_id:
        db_cart = supabase.table('cart').select('quantity, product_id, products(name, price)').eq('user_id', user_id).execute()
        if not db_cart.data:
            return 'Cart is empty.'
        for item in db_cart.data:
            prod = item['products']
            cart_items.append({'productId': item['product_id'], 'name': prod['name'], 'price': float(prod['price']), 'qty': item['quantity']})
    else:
        guest_cart = session.get('cart', [])
        if not guest_cart:
            return 'Cart is empty.'
        if not guest_email:
            return 'Please provide your email.'
        cart_items = guest_cart

    total = sum(it['price'] * it['qty'] for it in cart_items)

    discount_applied = 0
    discount_code = request.form.get('discount_code', '').strip().upper()
    if discount_code:
        try:
            code_res = supabase.table('discount_codes').select('*').eq('code', discount_code).eq('active', True).single().execute()
            if code_res.data:
                code = code_res.data
                if code.get('usage_limit') is None or code.get('used_count', 0) < code['usage_limit']:
                    if not code.get('min_order_amount') or total >= code['min_order_amount']:
                        if code.get('discount_percent'):
                            discount_applied = total * code['discount_percent'] / 100
                        elif code.get('discount_amount'):
                            discount_applied = code['discount_amount']
                        total -= discount_applied
                        supabase.table('discount_codes').update({'used_count': code['used_count'] + 1}).eq('id', code['id']).execute()
                        session['discount_applied'] = discount_applied
        except:
            pass

    order_data = {**shipping, 'total_amount': total}
    if user_id:
        order_data['user_id'] = user_id
    else:
        order_data['guest_email'] = guest_email

    try:
        order_res = supabase.table('orders').insert(order_data).execute()
        order_id = order_res.data[0]['id']
    except Exception as e:
        return f"<h2>Order failed</h2><p>{str(e)}</p><a href='/cart'>Back to Cart</a>"

    for item in cart_items:
        supabase.table('order_items').insert({
            'order_id': order_id,
            'product_id': item['productId'],
            'product_name': item['name'],
            'quantity': item['qty'],
            'unit_price': item['price'],
            'total_price': item['price'] * item['qty']
        }).execute()

    if user_id:
        supabase.table('cart').delete().eq('user_id', user_id).execute()
    else:
        session.pop('cart', None)

    session['last_order_id'] = order_id
    return redirect('/order-confirmation')

# Inline order confirmation – no template needed
@app.route('/order-confirmation')
def order_confirmation():
    order_id = session.pop('last_order_id', None)
    discount = session.pop('discount_applied', 0)
    if not order_id:
        return redirect('/')
    order = supabase.table('orders').select('*').eq('id', order_id).single().execute().data
    items = supabase.table('order_items').select('*').eq('order_id', order_id).execute().data
    item_rows = ''
    for i in items:
        item_rows += f'<tr><td>{i["product_name"]}</td><td>{i["quantity"]}</td><td>KSh {i["unit_price"]}</td><td>KSh {i["total_price"]}</td></tr>'
    html = f'''<!DOCTYPE html>
<html><head><title>Order Confirmed – DawaLink</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>body{{background:#f4f6f9;padding:2rem;}}</style></head><body>
<div class="container" style="max-width:600px;margin:auto;background:white;border-radius:20px;padding:2rem;box-shadow:0 10px 30px rgba(0,0,0,0.1);">
    <h2 class="text-success"><i class="fas fa-check-circle"></i> Thank You!</h2>
    <p>Your order <strong>#{order_id}</strong> has been placed successfully.</p>
    <p>Total: <strong>KSh {order['total_amount']}</strong></p>
    <p>Status: <span class="badge bg-warning">{order.get('order_status','pending')}</span></p>
    <hr>
    <h5>Items</h5>
    <table class="table table-sm">
        <thead><tr><th>Product</th><th>Qty</th><th>Unit Price</th><th>Subtotal</th></tr></thead>
        <tbody>{item_rows}</tbody>
    </table>
    <a href="/shop" class="btn btn-primary rounded-pill">Continue Shopping</a>
</div></body></html>'''
    return html

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user_res = supabase.table('users').select('*').eq('email', email).execute()
        if not user_res.data:
            return render_template('login.html', error='Invalid credentials')
        user = user_res.data[0]
        if not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            return render_template('login.html', error='Invalid credentials')

        is_admin = user.get('is_admin', False)
        approved = user.get('approved', False)

        if email == 'rodriguezgeorge089@gmail.com':
            approved = True
            if not user.get('approved'):
                supabase.table('users').update({'approved': True}).eq('id', user['id']).execute()

        if not is_admin and not approved:
            return render_template('login.html', error='Your account is pending approval.')

        if is_admin and not approved:
            supabase.table('users').update({'approved': True}).eq('id', user['id']).execute()

        session['user_id'] = user['id']
        session['user_name'] = user['full_name']
        session['is_admin'] = is_admin
        if 'cart' in session:
            for item in session['cart']:
                existing = supabase.table('cart').select('id').eq('user_id', user['id']).eq('product_id', item['productId']).execute()
                if existing.data:
                    supabase.table('cart').update({'quantity': existing.data[0]['quantity'] + item['qty']}).eq('id', existing.data[0]['id']).execute()
                else:
                    supabase.table('cart').insert({'user_id': user['id'], 'product_id': item['productId'], 'quantity': item['qty']}).execute()
            session.pop('cart', None)
        return redirect('/')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        password = request.form['password']
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        try:
            supabase.table('users').insert({'full_name': full_name, 'email': email, 'password_hash': hashed}).execute()
        except:
            return render_template('register.html', error='Email already exists.')
        return render_template('register_success.html')
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/my-account')
def my_account():
    if not session.get('user_id'):
        return redirect('/login')
    user_id = session['user_id']
    try:
        orders = supabase.table('orders').select('*').eq('user_id', user_id).order('created_at', desc=True).execute().data or []
    except:
        orders = []

    for order in orders:
        try:
            order['items'] = supabase.table('order_items').select('*').eq('order_id', order['id']).execute().data or []
        except:
            order['items'] = []

    if not orders:
        return '<h2>No orders yet</h2><a href="/shop">Shop</a>'

    order_html = ''
    for o in orders:
        oid = str(o['id'])[:8]
        status = o.get('order_status', 'pending')
        items_rows = ''
        for item in o['items']:
            items_rows += f'<tr><td>{item["product_name"]}</td><td>{item["quantity"]}</td><td>KSh {item["unit_price"]}</td><td>KSh {item["total_price"]}</td></tr>'
        order_html += f'''
        <div class="card mb-3">
            <div class="card-header d-flex justify-content-between align-items-center" data-bs-toggle="collapse" data-bs-target="#order{o['id']}">
                <span><strong>Order #{oid}</strong> – {o['created_at'][:10]}</span>
                <span class="badge bg-{'warning' if status=='pending' else 'info' if status=='confirmed' else 'primary' if status=='shipped' else 'success'}">{status}</span>
                <span class="fw-bold">KSh {o['total_amount']}</span>
            </div>
            <div class="collapse" id="order{o['id']}">
                <div class="card-body">
                    <table class="table table-sm"><thead><tr><th>Product</th><th>Qty</th><th>Unit Price</th><th>Subtotal</th></tr></thead><tbody>{items_rows}</tbody></table>
                </div>
            </div>
        </div>
        '''
    return f'''<!DOCTYPE html><html><head><title>My Orders</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>body{{background:#f4f6f9;padding:2rem;}}</style></head><body>
    <div class="container"><h2>My Orders</h2>{order_html}</div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    </body></html>'''

# ---------- Admin decorator ----------
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated

# ==================== ADMIN PANEL (INLINE SIDEBAR + CONTENT) ====================
def admin_layout(content_html, active_page='dashboard'):
    sidebar = f"""
    <div class="d-flex flex-column p-3 bg-dark text-white" style="width: 250px; min-height: 100vh;">
        <h4 class="text-warning"><i class="fas fa-pills"></i> {PHARMACY_NAME}</h4>
        <hr>
        <a href="/admin" class="btn btn-outline-light mb-1 {'active' if active_page=='dashboard' else ''}">Dashboard</a>
        <a href="/admin/orders" class="btn btn-outline-light mb-1 {'active' if active_page=='orders' else ''}">Orders</a>
        <a href="/admin/products" class="btn btn-outline-light mb-1 {'active' if active_page=='products' else ''}">Products</a>
        <a href="/admin/prescriptions" class="btn btn-outline-light mb-1 {'active' if active_page=='prescriptions' else ''}">Prescriptions</a>
        <a href="/admin/customers" class="btn btn-outline-light mb-1 {'active' if active_page=='customers' else ''}">Customers</a>
        <a href="/admin/users" class="btn btn-outline-light mb-1 {'active' if active_page=='users' else ''}">Customer Care</a>
        <a href="/admin/create-user" class="btn btn-outline-light mb-1 {'active' if active_page=='create' else ''}">Add Agent</a>
        <a href="/admin/settings" class="btn btn-outline-light mb-1 {'active' if active_page=='settings' else ''}">Settings</a>
        <a href="/admin/export-orders" class="btn btn-outline-light mb-1">Export CSV</a>
        <hr>
        <a href="/" class="btn btn-outline-light btn-sm">View Site</a>
        <a href="/logout" class="btn btn-outline-danger btn-sm mt-auto">Logout</a>
    </div>
    """
    return f"""<!DOCTYPE html>
<html><head><title>Admin Panel – {PHARMACY_NAME}</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>body{{display:flex;margin:0;font-family:'Segoe UI',sans-serif;}}{sidebar}{content_html}</style></head>
<body>{sidebar}
<div class="flex-grow-1 p-4" style="background:#f4f6f9;">{content_html}</div>
</body></html>"""

@app.route('/admin')
@admin_required
def admin_dashboard():
    orders_list = supabase.table('orders').select('*').order('created_at', desc=True).limit(10).execute()
    total_sales = sum(o['total_amount'] for o in orders_list.data) if orders_list.data else 0
    total_orders = supabase.table('orders').select('count', count='exact').execute().count or 0
    total_products = supabase.table('products').select('count', count='exact').execute().count or 0
    customers = set()
    if orders_list.data:
        for o in orders_list.data:
            e = o.get('customer_email') or o.get('guest_email')
            if e: customers.add(e)
    total_customers = len(customers)

    rows = ''
    for o in orders_list.data:
        oid = str(o['id'])[:8]
        status = o.get('order_status', 'pending')
        rows += f'<tr><td>#{oid}</td><td>{o.get("shipping_name","Guest")}</td><td>KSh {o["total_amount"]}</td><td><span class="badge bg-{"warning" if status=="pending" else "info"}">{status}</span></td><td>{o["created_at"][:10]}</td></tr>'

    content = f"""
    <h2>Dashboard</h2>
    <div class="row mb-4">
        <div class="col-md-3"><div class="card text-white bg-success mb-3"><div class="card-body"><h5>Total Sales</h5><h3>KSh {total_sales:,.2f}</h3></div></div></div>
        <div class="col-md-3"><div class="card text-white bg-warning mb-3"><div class="card-body"><h5>Orders</h5><h3>{total_orders}</h3></div></div></div>
        <div class="col-md-3"><div class="card text-white bg-primary mb-3"><div class="card-body"><h5>Products</h5><h3>{total_products}</h3></div></div></div>
        <div class="col-md-3"><div class="card text-white bg-danger mb-3"><div class="card-body"><h5>Customers</h5><h3>{total_customers}</h3></div></div></div>
    </div>
    <h4>Recent Orders</h4>
    <table class="table table-striped">
        <thead class="table-dark"><tr><th>Order ID</th><th>Customer</th><th>Total</th><th>Status</th><th>Date</th></tr></thead>
        <tbody>{rows}</tbody>
    </table>
    """
    return admin_layout(content, 'dashboard')

@app.route('/admin/orders')
@admin_required
def admin_orders():
    orders = supabase.table('orders').select('*').order('created_at', desc=True).execute().data or []
    rows = ''
    for o in orders:
        oid = str(o['id'])[:8]
        status = o.get('order_status', 'pending')
        rows += '<tr>'
        rows += f'<td>#{oid}</td>'
        rows += f'<td>{o.get("shipping_name","Guest")}</td>'
        rows += f'<td>KSh {o["total_amount"]}</td>'
        rows += f'<td><span class="badge bg-{"warning" if status=="pending" else "success"}">{status}</span></td>'
        rows += f'<td>{o["created_at"][:10]}</td>'
        rows += '<td>'
        rows += f'<form method="post" action="/admin/order/{o["id"]}/status" class="d-inline-flex">'
        rows += '<select name="status" class="form-select form-select-sm me-1" style="width:auto;">'
        for s in ['pending','confirmed','shipped','delivered']:
            sel = 'selected' if status == s else ''
            rows += f'<option {sel}>{s}</option>'
        rows += '</select>'
        rows += '<button class="btn btn-sm btn-primary">Update</button>'
        rows += '</form>'
        rows += f'<a href="/admin/order/{o["id"]}/invoice" class="btn btn-sm btn-outline-primary ms-1" target="_blank">Invoice</a>'
        rows += '</td></tr>'
    if not rows:
        rows = '<tr><td colspan="6">No orders yet.</td></tr>'
    content = f"<h2>Orders</h2><table class='table table-striped'><thead class='table-dark'><tr><th>Order ID</th><th>Customer</th><th>Total</th><th>Status</th><th>Date</th><th>Action</th></tr></thead><tbody>{rows}</tbody></table>"
    return admin_layout(content, 'orders')

@app.route('/admin/order/<order_id>/status', methods=['POST'])
@admin_required
def update_order_status(order_id):
    new_status = request.form['status']
    supabase.table('orders').update({'order_status': new_status}).eq('id', order_id).execute()
    return redirect('/admin/orders')

@app.route('/admin/order/<int:order_id>/invoice')
@admin_required
def admin_invoice(order_id):
    order = supabase.table('orders').select('*').eq('id', order_id).single().execute().data
    items = supabase.table('order_items').select('*').eq('order_id', order_id).execute().data or []
    item_rows = ''.join(f'<tr><td>{i["product_name"]}</td><td>{i["quantity"]}</td><td>KSh {i["unit_price"]}</td><td>KSh {i["total_price"]}</td></tr>' for i in items)
    html = f"""<!DOCTYPE html><html><head><title>Invoice #{order_id}</title>
    <style>@media print{{.no-print{{display:none;}}}}body{{padding:2rem;font-family:Arial;}}</style></head><body>
    <button class="no-print" onclick="window.print()">Print</button>
    <h2>{PHARMACY_NAME}</h2><p>Invoice #{order_id}</p>
    <p>Customer: {order.get('shipping_name', order.get('guest_email',''))}</p>
    <table border="1" cellpadding="5" style="width:100%">
    <thead><tr><th>Product</th><th>Qty</th><th>Unit Price</th><th>Total</th></tr></thead><tbody>{item_rows}</tbody></table>
    <h3>Grand Total: KSh {order['total_amount']}</h3>
    </body></html>"""
    return html

@app.route('/admin/products')
@admin_required
def admin_products():
    products = supabase.table('products').select('*').order('name').execute().data or []
    rows = ''
    for p in products:
        rows += '<tr>'
        rows += f'<td>{p["name"]}</td><td>{p["category"]}</td><td>KSh {p["price"]}</td><td>{p["stock"]}</td>'
        rows += f'<td><a href="/admin/edit-product/{p["id"]}" class="btn btn-sm btn-warning">Edit</a> '
        rows += f'<a href="/admin/delete-product/{p["id"]}" class="btn btn-sm btn-danger" onclick="return confirm(\'Delete?\')">Delete</a></td>'
        rows += '</tr>'
    content = f"<h2>Products</h2><a href='/admin/add-product' class='btn btn-success mb-3'>+ Add Product</a><table class='table table-striped'><thead class='table-dark'><tr><th>Name</th><th>Category</th><th>Price</th><th>Stock</th><th>Action</th></tr></thead><tbody>{rows}</tbody></table>"
    return admin_layout(content, 'products')

@app.route('/admin/add-product', methods=['GET', 'POST'])
@admin_required
def add_product():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form.get('description', '')
        category = request.form['category']
        price = float(request.form['price'])
        stock = int(request.form['stock'])
        image = request.files.get('image')
        image_url = None
        if image and image.filename:
            fname = secure_filename(image.filename)
            unique_name = f"{os.urandom(4).hex()}_{fname}"
            supabase.storage.from_("product-images").upload(unique_name, image.read(), {"content-type": image.content_type})
            image_url = f"{SUPABASE_URL}/storage/v1/object/public/product-images/{unique_name}"
        supabase.table('products').insert({
            'name': name, 'description': description, 'category': category,
            'price': price, 'stock': stock, 'image_url': image_url, 'active': True
        }).execute()
        return redirect('/admin/products')
    form_html = """
    <div class="row justify-content-center"><div class="col-md-6">
    <div class="card p-4 shadow-sm border-0 rounded-4">
    <h3>Add Product</h3>
    <form method="post" enctype="multipart/form-data">
        <input class="form-control mb-2" name="name" placeholder="Product Name" required>
        <textarea class="form-control mb-2" name="description" placeholder="Description"></textarea>
        <input class="form-control mb-2" name="category" placeholder="Category" required>
        <div class="row">
            <div class="col"><input class="form-control mb-2" type="number" step="0.01" name="price" placeholder="Price" required></div>
            <div class="col"><input class="form-control mb-2" type="number" name="stock" placeholder="Stock" required></div>
        </div>
        <input class="form-control mb-2" type="file" name="image" accept="image/*">
        <button class="btn btn-primary w-100 rounded-pill">Add Product</button>
    </form>
    </div></div></div>"""
    return admin_layout(form_html, 'products')

@app.route('/admin/edit-product/<product_id>', methods=['GET', 'POST'])
@admin_required
def edit_product(product_id):
    if request.method == 'POST':
        name = request.form['name']
        description = request.form.get('description', '')
        category = request.form['category']
        price = float(request.form['price'])
        stock = int(request.form['stock'])
        image = request.files.get('image')
        upd = {'name': name, 'description': description, 'category': category, 'price': price, 'stock': stock}
        if image and image.filename:
            fname = secure_filename(image.filename)
            unique_name = f"{os.urandom(4).hex()}_{fname}"
            supabase.storage.from_("product-images").upload(unique_name, image.read(), {"content-type": image.content_type})
            upd['image_url'] = f"{SUPABASE_URL}/storage/v1/object/public/product-images/{unique_name}"
        supabase.table('products').update(upd).eq('id', product_id).execute()
        return redirect('/admin/products')
    p = supabase.table('products').select('*').eq('id', product_id).single().execute().data
    form_html = f"""
    <div class="row justify-content-center"><div class="col-md-6">
    <div class="card p-4 shadow-sm border-0 rounded-4">
    <h3>Edit Product</h3>
    <form method="post" enctype="multipart/form-data">
        <input class="form-control mb-2" name="name" value="{p['name']}" required>
        <textarea class="form-control mb-2" name="description">{p.get('description','')}</textarea>
        <input class="form-control mb-2" name="category" value="{p['category']}" required>
        <div class="row">
            <div class="col"><input class="form-control mb-2" type="number" step="0.01" name="price" value="{p['price']}" required></div>
            <div class="col"><input class="form-control mb-2" type="number" name="stock" value="{p['stock']}" required></div>
        </div>
        <input class="form-control mb-2" type="file" name="image" accept="image/*">
        <button class="btn btn-primary w-100 rounded-pill">Update Product</button>
    </form>
    </div></div></div>"""
    return admin_layout(form_html, 'products')

@app.route('/admin/delete-product/<product_id>')
@admin_required
def delete_product(product_id):
    supabase.table('products').delete().eq('id', product_id).execute()
    return redirect('/admin/products')

@app.route('/admin/prescriptions')
@admin_required
def admin_prescriptions():
    rx = supabase.table('prescriptions').select('*').order('created_at', desc=True).execute().data or []
    items = ''.join(f'<div class="card mb-2 p-2"><strong>{r["customer_name"]}</strong> ({r["customer_email"]})<br>Phone: {r["customer_phone"]}<br>Notes: {r.get("notes","")}<br><a href="{r.get("file_url","#")}" class="btn btn-sm btn-primary" target="_blank">View File</a></div>' for r in rx) or '<p>No prescriptions yet.</p>'
    content = f"<h2>Prescriptions</h2>{items}"
    return admin_layout(content, 'prescriptions')

@app.route('/admin/customers')
@admin_required
def admin_customers():
    orders = supabase.table('orders').select('*').order('created_at', desc=True).execute().data or []
    cust = {}
    for o in orders:
        email = o.get('customer_email') or o.get('guest_email')
        if not email: continue
        if email not in cust:
            cust[email] = {"name": o.get('customer_name','') or o.get('shipping_name',''), "phone": o.get('customer_phone','') or o.get('shipping_phone',''), "total_spent": 0, "orders": 0}
        cust[email]["total_spent"] += o['total_amount']
        cust[email]["orders"] += 1
    rows = ''.join(f'<tr><td>{c["name"]}</td><td>{e}</td><td>{c["phone"]}</td><td>{c["orders"]}</td><td>KSh {c["total_spent"]}</td></tr>' for e,c in cust.items()) or '<tr><td colspan="5">No customers yet.</td></tr>'
    content = f"<h2>Customers</h2><table class='table table-striped'><thead class='table-dark'><tr><th>Name</th><th>Email</th><th>Phone</th><th>Orders</th><th>Total Spent</th></tr></thead><tbody>{rows}</tbody></table>"
    return admin_layout(content, 'customers')

@app.route('/admin/users')
@admin_required
def admin_users():
    users = supabase.table('users').select('*').order('created_at', desc=True).execute().data or []
    rows = ''.join(
        f'<tr><td>{u["full_name"]}</td><td>{u["email"]}</td>'
        f'<td><span class="badge bg-{"success" if u.get("approved") else "warning"}">{"Approved" if u.get("approved") else "Pending"}</span></td>'
        f'<td><a href="/admin/approve-user/{u["id"]}" class="btn btn-sm btn-outline-success">Approve</a> '
        f'<a href="/admin/disable-user/{u["id"]}" class="btn btn-sm btn-outline-danger">Disable</a></td></tr>'
        for u in users) or '<tr><td colspan="4">No agents yet.</td></tr>'
    content = f"<h2>Customer Care Team</h2><table class='table table-striped'><thead class='table-dark'><tr><th>Name</th><th>Email</th><th>Status</th><th>Action</th></tr></thead><tbody>{rows}</tbody></table>"
    return admin_layout(content, 'users')

@app.route('/admin/approve-user/<user_id>')
@admin_required
def approve_user(user_id):
    supabase.table('users').update({'approved': True}).eq('id', user_id).execute()
    return redirect('/admin/users')

@app.route('/admin/disable-user/<user_id>')
@admin_required
def disable_user(user_id):
    supabase.table('users').update({'approved': False}).eq('id', user_id).execute()
    return redirect('/admin/users')

@app.route('/admin/create-user', methods=['GET', 'POST'])
@admin_required
def create_user():
    current_user_email = supabase.table('users').select('email').eq('id', session['user_id']).single().execute().data['email']
    if current_user_email != 'rodriguezgeorge089@gmail.com':
        return "Unauthorized", 403
    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        password = request.form['password']
        is_admin = request.form.get('is_admin') == 'on'
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        try:
            supabase.table('users').insert({
                'full_name': full_name, 'email': email, 'password_hash': hashed,
                'is_admin': is_admin, 'approved': True
            }).execute()
        except:
            return admin_layout('<div class="alert alert-danger">Email already exists.</div>', 'create')
        return redirect('/admin/users')
    form_html = """
    <div class="row justify-content-center"><div class="col-md-6">
    <div class="card p-4 shadow-sm border-0 rounded-4">
    <h3>Add Customer Care Agent</h3>
    <form method="post">
        <input class="form-control mb-2" name="full_name" placeholder="Full Name" required>
        <input class="form-control mb-2" name="email" placeholder="Email" required>
        <input class="form-control mb-2" type="password" name="password" placeholder="Password" required>
        <div class="form-check mb-2">
            <input class="form-check-input" type="checkbox" name="is_admin" id="isAdmin">
            <label class="form-check-label" for="isAdmin">Grant Admin Privileges</label>
        </div>
        <button class="btn btn-primary w-100 rounded-pill">Create Agent</button>
    </form>
    </div></div></div>"""
    return admin_layout(form_html, 'create')

@app.route('/admin/settings', methods=['GET', 'POST'])
@admin_required
def admin_settings():
    msg = ''
    if request.method == 'POST':
        new_password = request.form['new_password']
        hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        supabase.table('users').update({'password_hash': hashed}).eq('id', session['user_id']).execute()
        msg = '<div class="alert alert-success">Password updated!</div>'
    form_html = f"""
    <div class="row justify-content-center"><div class="col-md-6">
    <div class="card p-4 shadow-sm border-0 rounded-4">
    <h3>Change Password</h3>
    {msg}
    <form method="post">
        <input class="form-control mb-2" type="password" name="new_password" placeholder="New Password" required>
        <button class="btn btn-primary w-100 rounded-pill">Update Password</button>
    </form>
    </div></div></div>"""
    return admin_layout(form_html, 'settings')

@app.route('/admin/export-orders')
@admin_required
def export_orders():
    orders = supabase.table('orders').select('*').order('created_at', desc=True).execute().data or []
    output = io.StringIO()
    w = csv.writer(output)
    w.writerow(["Order ID","Date","Customer","Email","Phone","Total","Status","Payment"])
    for o in orders:
        w.writerow([str(o['id'])[:8], o['created_at'][:10], o.get('customer_name','') or o.get('shipping_name',''), o.get('customer_email','') or o.get('guest_email',''), o.get('customer_phone','') or o.get('shipping_phone',''), o['total_amount'], o.get('order_status','pending'), o.get('payment_method','')])
    output.seek(0)
    return Response(output.getvalue(), mimetype='text/csv', headers={"Content-Disposition":"attachment;filename=orders.csv"})

# ==================== PWA ROUTES ====================
@app.route('/manifest.json')
def manifest_route():
    manifest = {
        "name": "DawaLink - Online Pharmacy",
        "short_name": "DawaLink",
        "description": "Medicine At Your Convenience",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0A3D62",
        "theme_color": "#0A3D62",
        "icons": [
            {"src":"/static/icon-192.png","sizes":"192x192","type":"image/png","purpose":"any maskable"},
            {"src":"/static/icon-512.png","sizes":"512x512","type":"image/png","purpose":"any maskable"}
        ],
        "categories":["medical","health","shopping"],
        "lang":"en-KE"
    }
    resp = make_response(json.dumps(manifest))
    resp.headers['Content-Type'] = 'application/manifest+json; charset=utf-8'
    return resp

@app.route('/sw.js')
def sw_route():
    sw = "self.addEventListener('install',e=>e.waitUntil(caches.open('v1').then(c=>c.addAll(['/','/shop','/cart'])).then(()=>self.skipWaiting())));self.addEventListener('fetch',e=>e.respondWith(caches.match(e.request).then(r=>r||fetch(e.request))))"
    return Response(sw, mimetype='application/javascript')

def _create_png(width, height, color=(10,61,98)):
    def chunk(t,d):
        c = t+d
        return struct.pack(">I",len(d)) + c + struct.pack(">I", zlib.crc32(c)&0xFFFFFFFF)
    sig = b'\x89PNG\r\n\x1a\n'
    ihdr = chunk(b'IHDR', struct.pack(">IIBBBBB",width,height,8,2,0,0,0))
    raw = b''
    for y in range(height):
        raw += b'\x00'
        for x in range(width):
            raw += bytes(color)
    idat = chunk(b'IDAT', zlib.compress(raw))
    iend = chunk(b'IEND', b'')
    return sig+ihdr+idat+iend

@app.route('/static/icon-192.png')
def icon_192():
    return Response(_create_png(192,192), mimetype='image/png')

@app.route('/static/icon-512.png')
def icon_512():
    return Response(_create_png(512,512), mimetype='image/png')

@app.route('/download')
def download_page():
    return "<h2>Download the APK from the link we provided.</h2>"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',8080)))
