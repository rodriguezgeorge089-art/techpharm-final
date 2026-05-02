import os, json, bcrypt, csv, io
from flask import Flask, render_template, request, redirect, session, Response
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

# ---------- Context processor ----------
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

    return dict(user=user, cart_total=cart_total,
                wishlist_count=wishlist_count, compare_count=compare_count,
                pharmacy_name=PHARMACY_NAME, phone=PHARMACY_PHONE, email=PHARMACY_EMAIL)

# ---------- Public pages ----------
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

# ---------- Shop ----------
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

# ---------- Prescription upload ----------
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

# ---------- Cart ----------
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

@app.route('/wishlist/toggle', methods=['POST'])
def wishlist_toggle():
    if 'user_id' not in session:
        return 'Login required', 401
    user_id = session['user_id']
    product_id = request.form['productId']
    existing = supabase.table('wishlist').select('id').eq('user_id', user_id).eq('product_id', product_id).execute()
    if existing.data:
        supabase.table('wishlist').delete().eq('user_id', user_id).eq('product_id', product_id).execute()
    else:
        supabase.table('wishlist').insert({'user_id': user_id, 'product_id': product_id}).execute()
    return redirect(request.referrer or '/')

@app.route('/compare/toggle/<product_id>')
def compare_toggle(product_id):
    compare = json.loads(request.cookies.get('compare', '[]'))
    if product_id in compare:
        compare.remove(product_id)
    else:
        if len(compare) < 4:
            compare.append(product_id)
    resp = redirect(request.referrer or '/')
    resp.set_cookie('compare', json.dumps(compare), max_age=86400)
    return resp

@app.route('/compare')
def compare_page():
    ids = json.loads(request.cookies.get('compare', '[]'))
    if not ids:
        return 'No products to compare.'
    products = supabase.table('products').select('*').in_('id', ids).execute().data
    return render_template('compare.html', products=products)

# ---------- Checkout with discount codes ----------
@app.route('/checkout')
def checkout_form():
    return render_template('checkout.html')

@app.route('/checkout', methods=['POST'])
def place_order():
    shipping = {
        'shipping_name': request.form['shipping_name'],
        'shipping_address': request.form['shipping_address'],
        'shipping_city': request.form['shipping_city'],
        'shipping_phone': request.form['shipping_phone'],
        'payment_method': request.form['payment_method']
    }
    guest_email = request.form.get('guest_email')
    user_id = session.get('user_id')

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

    order_res = supabase.table('orders').insert(order_data).execute()
    order_id = order_res.data[0]['id']

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

@app.route('/order-confirmation')
def order_confirmation():
    order_id = session.pop('last_order_id', None)
    discount = session.pop('discount_applied', 0)
    if not order_id:
        return redirect('/')
    order = supabase.table('orders').select('*').eq('id', order_id).single().execute().data
    items = supabase.table('order_items').select('*').eq('order_id', order_id).execute().data
    return render_template('order_confirmation.html', order=order, items=items, discount=discount)

# ---------- Authentication ----------
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

        # Super admin always approved
        if email == 'rodriguezgeorge089@gmail.com':
            approved = True
            if not user.get('approved'):
                supabase.table('users').update({'approved': True}).eq('id', user['id']).execute()

        if not is_admin and not approved:
            return render_template('login.html', error='Your account is pending approval. Please try again later or contact support.')

        if is_admin and not approved:
            supabase.table('users').update({'approved': True}).eq('id', user['id']).execute()
            user['approved'] = True

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
            supabase.table('users').insert({
                'full_name': full_name,
                'email': email,
                'password_hash': hashed
            }).execute()
        except:
            return render_template('register.html', error='Email already exists.')
        return render_template('register_success.html')
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ---------- Customer Orders ----------
@app.route('/my-account')
def my_account():
    if not session.get('user_id'):
        return redirect('/login')
    user_id = session['user_id']
    orders = supabase.table('orders').select('*').eq('user_id', user_id).order('created_at', desc=True).execute().data or []
    for order in orders:
        order['items'] = supabase.table('order_items').select('*').eq('order_id', order['id']).execute().data or []
    return render_template('my_orders.html', orders=orders)

# ---------- Admin Decorator ----------
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated

# ==================== ALL ADMIN PAGES AS INLINE HTML ====================
NAV = """
<a href="/admin">Dashboard</a> | 
<a href="/admin/orders">Orders</a> | 
<a href="/admin/products">Products</a> | 
<a href="/admin/prescriptions">Prescriptions</a> | 
<a href="/admin/customers">Customers</a> | 
<a href="/admin/users">Users</a> | 
<a href="/admin/create-user">Create User</a> | 
<a href="/admin/settings">Settings</a> | 
<a href="/admin/export-orders">Export CSV</a> | 
<a href="/logout">Logout</a>
"""

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
        rows += f'<tr><td>#{oid}</td><td>{o.get("shipping_name", "Guest")}</td><td>KSh {o["total_amount"]}</td><td>{status}</td></tr>'

    return f"""<!DOCTYPE html><html><head><title>Admin</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>body{{padding:2rem;background:#f4f6f9;}}</style></head><body><div class="container">
    <h1>Admin Dashboard</h1><nav>{NAV}</nav><hr>
    <div class="row">
        <div class="col-md-3"><div class="card text-white bg-success mb-3"><div class="card-body"><h5>Total Sales</h5><h2>KSh {total_sales:,.2f}</h2></div></div></div>
        <div class="col-md-3"><div class="card text-white bg-warning mb-3"><div class="card-body"><h5>Orders</h5><h2>{total_orders}</h2></div></div></div>
        <div class="col-md-3"><div class="card text-white bg-primary mb-3"><div class="card-body"><h5>Products</h5><h2>{total_products}</h2></div></div></div>
        <div class="col-md-3"><div class="card text-white bg-danger mb-3"><div class="card-body"><h5>Customers</h5><h2>{total_customers}</h2></div></div></div>
    </div>
    <h3>Recent Orders</h3>
    <table class="table table-striped"><thead><tr><th>Order ID</th><th>Customer</th><th>Total</th><th>Status</th></tr></thead><tbody>{rows}</tbody></table>
    </div></body></html>"""

@app.route('/admin/orders')
@admin_required
def admin_orders():
    orders = supabase.table('orders').select('*').order('created_at', desc=True).execute().data or []
    rows = ''
    for o in orders:
        oid = str(o['id'])[:8]
        status = o.get('order_status', 'pending')
        rows += f'<tr><td>#{oid}</td><td>{o.get("shipping_name", "Guest")}</td><td>KSh {o["total_amount"]}</td><td>{status}</td><td><a href="/admin/order/{o["id"]}/invoice">Invoice</a></td></tr>'
    return f"""<!DOCTYPE html><html><head><title>Orders</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>body{{padding:2rem;background:#f4f6f9;}}</style></head><body><div class="container">
    <h1>Orders</h1><nav>{NAV}</nav><hr>
    <table class="table"><thead><tr><th>Order ID</th><th>Customer</th><th>Total</th><th>Status</th><th>Invoice</th></tr></thead><tbody>{rows}</tbody></table>
    </div></body></html>"""

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
    item_rows = ''
    for i in items:
        item_rows += f'<tr><td>{i["product_name"]}</td><td>{i["quantity"]}</td><td>KSh {i["unit_price"]}</td><td>KSh {i["total_price"]}</td></tr>'
    return f"""<!DOCTYPE html><html><head><title>Invoice #{order_id}</title>
    <style>@media print{{.no-print{{display:none;}}}}body{{font-family:Arial;padding:2rem;}}</style></head><body>
    <button class="no-print" onclick="window.print()">Print</button>
    <h2>{PHARMACY_NAME}</h2><p>Invoice #{order_id}</p>
    <p>Customer: {order.get('shipping_name', order.get('guest_email',''))}</p>
    <table border="1" cellpadding="5" style="width:100%">
    <thead><tr><th>Product</th><th>Qty</th><th>Unit Price</th><th>Total</th></tr></thead><tbody>{item_rows}</tbody></table>
    <h3>Grand Total: KSh {order['total_amount']}</h3>
    </body></html>"""

@app.route('/admin/products')
@admin_required
def admin_products():
    products = supabase.table('products').select('*').order('name').execute().data or []
    rows = ''
    for p in products:
        rows += f'<tr><td>{p["name"]}</td><td>{p["category"]}</td><td>KSh {p["price"]}</td><td>{p["stock"]}</td><td><a href="/admin/edit-product/{p["id"]}">Edit</a> | <a href="/admin/delete-product/{p["id"]}">Delete</a></td></tr>'
    return f"""<!DOCTYPE html><html><head><title>Products</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>body{{padding:2rem;background:#f4f6f9;}}</style></head><body><div class="container">
    <h1>Products</h1><nav>{NAV}</nav><hr>
    <a href="/admin/add-product" class="btn btn-success mb-3">+ Add Product</a>
    <table class="table"><thead><tr><th>Name</th><th>Category</th><th>Price</th><th>Stock</th><th>Action</th></tr></thead><tbody>{rows}</tbody></table>
    </div></body></html>"""

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
    return """<!DOCTYPE html><html><head><title>Add Product</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>body{padding:2rem;}</style></head><body><div class="container" style="max-width:500px">
    <h2>Add Product</h2>
    <form method="post" enctype="multipart/form-data">
    <input class="form-control mb-2" name="name" placeholder="Name" required>
    <textarea class="form-control mb-2" name="description" placeholder="Description"></textarea>
    <input class="form-control mb-2" name="category" placeholder="Category" required>
    <input class="form-control mb-2" type="number" step="0.01" name="price" placeholder="Price" required>
    <input class="form-control mb-2" type="number" name="stock" placeholder="Stock" required>
    <input class="form-control mb-2" type="file" name="image" accept="image/*">
    <button class="btn btn-primary">Add</button></form></div></body></html>"""

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
    return f"""<!DOCTYPE html><html><head><title>Edit Product</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>body{{padding:2rem;}}</style></head><body><div class="container" style="max-width:500px">
    <h2>Edit Product</h2>
    <form method="post" enctype="multipart/form-data">
    <input class="form-control mb-2" name="name" value="{p['name']}" required>
    <textarea class="form-control mb-2" name="description">{p.get('description','')}</textarea>
    <input class="form-control mb-2" name="category" value="{p['category']}" required>
    <input class="form-control mb-2" type="number" step="0.01" name="price" value="{p['price']}" required>
    <input class="form-control mb-2" type="number" name="stock" value="{p['stock']}" required>
    <input class="form-control mb-2" type="file" name="image" accept="image/*">
    <button class="btn btn-primary">Update</button></form></div></body></html>"""

@app.route('/admin/delete-product/<product_id>')
@admin_required
def delete_product(product_id):
    supabase.table('products').delete().eq('id', product_id).execute()
    return redirect('/admin/products')

@app.route('/admin/prescriptions')
@admin_required
def admin_prescriptions():
    rx = supabase.table('prescriptions').select('*').order('created_at', desc=True).execute().data or []
    rows = ''
    for r in rx:
        rows += f'<tr><td>{r["customer_name"]}</td><td>{r["customer_email"]}</td><td>{r["customer_phone"]}</td><td>{r.get("notes","")}</td><td><a href="{r.get("file_url","#")}">View</a></td></tr>'
    return f"""<!DOCTYPE html><html><head><title>Prescriptions</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>body{{padding:2rem;background:#f4f6f9;}}</style></head><body><div class="container">
    <h1>Prescriptions</h1><nav>{NAV}</nav><hr>
    <table class="table"><thead><tr><th>Name</th><th>Email</th><th>Phone</th><th>Notes</th><th>File</th></tr></thead><tbody>{rows}</tbody></table>
    </div></body></html>"""

@app.route('/admin/customers')
@admin_required
def admin_customers():
    orders = supabase.table('orders').select('*').order('created_at', desc=True).execute().data or []
    customers = {}
    for o in orders:
        email = o.get('customer_email') or o.get('guest_email')
        if not email: continue
        if email not in customers:
            customers[email] = {"name": o.get('customer_name','') or o.get('shipping_name',''), "phone": o.get('customer_phone','') or o.get('shipping_phone',''), "total_spent": 0, "orders": 0}
        customers[email]["total_spent"] += o['total_amount']
        customers[email]["orders"] += 1
    rows = ''
    for e, c in customers.items():
        rows += f'<tr><td>{c["name"]}</td><td>{e}</td><td>{c["phone"]}</td><td>{c["orders"]}</td><td>KSh {c["total_spent"]}</td></tr>'
    return f"""<!DOCTYPE html><html><head><title>Customers</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>body{{padding:2rem;background:#f4f6f9;}}</style></head><body><div class="container">
    <h1>Customers</h1><nav>{NAV}</nav><hr>
    <table class="table"><thead><tr><th>Name</th><th>Email</th><th>Phone</th><th>Orders</th><th>Total Spent</th></tr></thead><tbody>{rows}</tbody></table>
    </div></body></html>"""

@app.route('/admin/users')
@admin_required
def admin_users():
    users = supabase.table('users').select('*').order('created_at', desc=True).execute().data or []
    rows = ''
    for u in users:
        approved = 'Yes' if u.get('approved') else 'No'
        rows += f'<tr><td>{u["full_name"]}</td><td>{u["email"]}</td><td>{approved}</td><td><a href="/admin/approve-user/{u["id"]}">Approve</a> | <a href="/admin/disable-user/{u["id"]}">Disable</a></td></tr>'
    return f"""<!DOCTYPE html><html><head><title>Users</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>body{{padding:2rem;background:#f4f6f9;}}</style></head><body><div class="container">
    <h1>User Management</h1><nav>{NAV}</nav><hr>
    <table class="table"><thead><tr><th>Name</th><th>Email</th><th>Approved</th><th>Action</th></tr></thead><tbody>{rows}</tbody></table>
    </div></body></html>"""

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
            return render_template('admin_create_user.html', error='Email already exists.')
        return redirect('/admin/users')
    return """<!DOCTYPE html><html><head><title>Create User</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>body{padding:2rem;}</style></head><body><div class="container" style="max-width:500px">
    <h2>Create User</h2><form method="post">
    <input class="form-control mb-2" name="full_name" placeholder="Full Name" required>
    <input class="form-control mb-2" name="email" placeholder="Email" required>
    <input class="form-control mb-2" type="password" name="password" placeholder="Password" required>
    <label class="form-check-label"><input type="checkbox" name="is_admin"> Admin</label>
    <button class="btn btn-primary mt-2">Create</button></form></div></body></html>"""

@app.route('/admin/settings', methods=['GET', 'POST'])
@admin_required
def admin_settings():
    if request.method == 'POST':
        new_password = request.form['new_password']
        hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        supabase.table('users').update({'password_hash': hashed}).eq('id', session['user_id']).execute()
        return redirect('/admin/settings?success=1')
    msg = request.args.get('success') and "Password updated!" or ""
    return f"""<!DOCTYPE html><html><head><title>Settings</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>body{{padding:2rem;background:#f4f6f9;}}</style></head><body><div class="container">
    <h1>Settings</h1><nav>{NAV}</nav><hr>
    {f'<div class="alert alert-success">{msg}</div>' if msg else ''}
    <form method="post" style="max-width:400px">
    <input class="form-control mb-2" type="password" name="new_password" placeholder="New Password" required>
    <button class="btn btn-primary">Update Password</button></form></div></body></html>"""

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
