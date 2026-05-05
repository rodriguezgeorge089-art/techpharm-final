import os, json, bcrypt, csv, io, struct, zlib
from flask import Flask, request, redirect, session, Response, make_response
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

# ---------- Public navigation bar ----------
def public_nav(user=None):
    cart_total = 0.0
    if user and session.get('user_id'):
        try:
            uid = session['user_id']
            resp = supabase.table('cart').select('quantity, products(price)').eq('user_id', uid).execute()
            for it in resp.data:
                cart_total += float(it['products']['price']) * it['quantity']
        except: pass
    nav = f'''
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark sticky-top">
      <div class="container">
        <a class="navbar-brand fw-bold" href="/"><i class="fas fa-pills"></i> {PHARMACY_NAME}</a>
        <button class="navbar-toggler" data-bs-toggle="collapse" data-bs-target="#nav"><span class="navbar-toggler-icon"></span></button>
        <div class="collapse navbar-collapse" id="nav">
          <ul class="navbar-nav ms-auto align-items-center">
            <li class="nav-item"><a class="nav-link" href="/">Home</a></li>
            <li class="nav-item"><a class="nav-link" href="/blog">Blog</a></li>
            <li class="nav-item"><a class="nav-link" href="/shop">Shop</a></li>
            <li class="nav-item"><a class="nav-link" href="/cart"><i class="fas fa-shopping-cart"></i> Cart <span class="badge bg-warning">KSh {cart_total:.0f}</span></a></li>'''
    if user:
        nav += '<li class="nav-item"><a class="nav-link" href="/my-account">My Orders</a></li>'
        if user.get('is_admin'):
            nav += '<li class="nav-item"><a class="nav-link" href="/admin" style="color:#F4A261;font-weight:700;">🔧 Admin Panel</a></li>'
        nav += f'<li class="nav-item"><a class="nav-link" href="/logout">{user["full_name"]} (Logout)</a></li>'
    else:
        nav += '<li class="nav-item"><a class="nav-link" href="/login">Login</a></li>'
        nav += '<li class="nav-item"><a class="nav-link" href="/register">Register</a></li>'
    nav += '</ul></div></div></nav>'
    return nav

def public_page(title, body, user=None):
    return f'''<!DOCTYPE html><html><head><title>{title} – {PHARMACY_NAME}</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>body{{font-family:'Segoe UI',sans-serif;background:#f4f6f9;margin:0;}}</style></head>
<body>
{public_nav(user)}
<div class="container mt-4">{body}</div>
<footer class="text-center py-4 mt-5 bg-dark text-white"><small>&copy; 2026 {PHARMACY_NAME}. All rights reserved.</small></footer>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body></html>'''

def admin_page(title, body, active='dashboard'):
    sidebar = ''
    links = {
        'dashboard': '/admin',
        'orders': '/admin/orders',
        'products': '/admin/products',
        'prescriptions': '/admin/prescriptions',
        'customers': '/admin/customers',
        'users': '/admin/users',
        'create-user': '/admin/create-user',
        'settings': '/admin/settings',
        'export': '/admin/export-orders'
    }
    for name, url in links.items():
        active_cls = 'active' if active == name else ''
        sidebar += f'<a href="{url}" class="list-group-item list-group-item-action {active_cls}">{name.replace("-"," ").title()}</a>'
    return f'''<!DOCTYPE html><html><head><title>{title} – Admin Panel</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>body{{display:flex;margin:0;font-family:'Segoe UI',sans-serif;}}
.sidebar{{width:250px;background:#0A3D62;color:white;min-height:100vh;padding:1rem;}}
.sidebar a{{color:#ccc;display:block;padding:0.5rem 1rem;text-decoration:none;border-radius:8px;}}
.sidebar a:hover{{background:#0F4C7A;}}
.sidebar a.active{{background:#F4A261;color:#0A3D62;font-weight:bold;}}
.main{{flex:1;padding:2rem;background:#f4f6f9;}}</style></head>
<body>
<div class="sidebar">
  <h4 style="color:#F4A261;"><i class="fas fa-pills"></i> {PHARMACY_NAME}</h4>
  <div class="list-group">{sidebar}</div>
  <hr><a href="/" class="btn btn-sm btn-outline-light">View Site</a>
  <a href="/logout" class="btn btn-sm btn-outline-danger mt-1">Logout</a>
</div>
<div class="main"><h2>{title}</h2><hr>{body}</div>
</body></html>'''

# ---------- Public routes ----------
@app.route('/')
def home():
    body = '''<div class="text-center py-5" style="background:linear-gradient(135deg,#0A3D62,#1B5A82);color:white;border-radius:20px;">
    <h1>Medicine At Your Convenience</h1><p class="lead">Quality OTC medicines & supplements delivered fast across Kenya.</p>
    <a href="/shop" class="btn btn-light btn-lg me-2">Shop Now</a>
    <a href="/prescription" class="btn btn-outline-light btn-lg">Upload Prescription</a></div>'''
    user = None
    if session.get('user_id'):
        user = {'full_name': session.get('user_name','User'), 'is_admin': session.get('is_admin', False)}
    return public_page("Home", body, user)

@app.route('/blog')
def blog():
    posts = [
        {"title":"Understanding Pain Relief","date":"2026-04-15","snippet":"Learn about OTC pain relievers."},
        {"title":"Essential Baby Care","date":"2026-04-10","snippet":"A guide for new parents."},
        {"title":"Probiotics & Gut Health","date":"2026-04-02","snippet":"How probiotics improve wellness."}
    ]
    html = ''.join(f'<div class="card mb-3"><div class="card-body"><h5>{p["title"]}</h5><small>{p["date"]}</small><p>{p["snippet"]}</p></div></div>' for p in posts)
    return public_page("Blog", html)

@app.route('/shop')
def shop():
    prods = supabase.table('products').select('*').eq('active', True).execute().data or []
    rows = ''
    for p in prods:
        rows += f'''<div class="col-md-4 mb-3"><div class="card"><div class="card-body">
        <h5>{p['name']}</h5><p>{p['category']} – KSh {p['price']}</p>
        <form action="/cart/add" method="POST">
            <input type="hidden" name="productId" value="{p['id']}">
            <input type="number" name="quantity" value="1" min="1" style="width:60px;">
            <button class="btn btn-sm btn-primary">Add to Cart</button>
        </form></div></div></div>'''
    user = None
    if session.get('user_id'):
        user = {'full_name': session.get('user_name','User'), 'is_admin': session.get('is_admin', False)}
    return public_page("Shop", f'<h2>Products</h2><div class="row">{rows}</div>', user)

@app.route('/cart/add', methods=['POST'])
def add_to_cart():
    pid = request.form['productId']
    qty = int(request.form.get('quantity', 1))
    prod = supabase.table('products').select('id,name,price').eq('id', pid).single().execute().data
    if not prod:
        return 'Product not found', 404
    if session.get('user_id'):
        uid = session['user_id']
        ex = supabase.table('cart').select('id,quantity').eq('user_id', uid).eq('product_id', pid).execute()
        if ex.data:
            supabase.table('cart').update({'quantity': ex.data[0]['quantity'] + qty}).eq('id', ex.data[0]['id']).execute()
        else:
            supabase.table('cart').insert({'user_id': uid, 'product_id': pid, 'quantity': qty}).execute()
    else:
        cart = session.get('cart', [])
        found = False
        for it in cart:
            if it['productId'] == pid:
                it['qty'] += qty
                found = True
                break
        if not found:
            cart.append({'productId': pid, 'qty': qty, 'price': float(prod['price']), 'name': prod['name']})
        session['cart'] = cart
    return redirect('/cart')

@app.route('/cart')
def view_cart():
    items = []
    total = 0.0
    if session.get('user_id'):
        uid = session['user_id']
        db = supabase.table('cart').select('quantity,product_id,products(name,price)').eq('user_id', uid).execute()
        for row in db.data:
            p = row['products']
            items.append({'productId': row['product_id'], 'name': p['name'], 'price': float(p['price']), 'qty': row['quantity']})
            total += float(p['price']) * row['quantity']
    else:
        items = session.get('cart', [])
        total = sum(it['price'] * it['qty'] for it in items)
    if not items:
        return public_page("Cart", '<h2>Your Cart</h2><p>Cart is empty.</p><a href="/shop" class="btn btn-primary">Start Shopping</a>')
    rows = ''
    for i in items:
        rows += f'''<div class="card p-3 mb-2 d-flex flex-row justify-content-between align-items-center">
        <div><h5>{i['name']}</h5><small>Qty: {i['qty']} × KSh {i['price']}</small></div>
        <div><h4 class="text-success">KSh {i['price']*i['qty']:.2f}</h4>
        <a href="/cart/remove/{i['productId']}" class="btn btn-sm btn-outline-danger"><i class="fas fa-trash"></i></a></div></div>'''
    body = f'<h2>Your Cart</h2>{rows}<hr><div class="d-flex justify-content-between"><h4>Total</h4><h4>KSh {total:.2f}</h4></div><a href="/checkout" class="btn btn-success w-100 py-3 mt-3">Proceed to Checkout</a>'
    user = None
    if session.get('user_id'):
        user = {'full_name': session.get('user_name','User'), 'is_admin': session.get('is_admin', False)}
    return public_page("Cart", body, user)

@app.route('/cart/remove/<pid>')
def remove_cart(pid):
    if session.get('user_id'):
        try: supabase.table('cart').delete().eq('user_id', session['user_id']).eq('product_id', pid).execute()
        except: pass
    else:
        cart = [i for i in session.get('cart', []) if i['productId'] != pid]
        session['cart'] = cart
    return redirect('/cart')

@app.route('/checkout', methods=['GET','POST'])
def checkout():
    if request.method == 'POST':
        shipping = {
            'shipping_name': request.form['shipping_name'],
            'shipping_address': request.form.get('shipping_address',''),
            'shipping_city': request.form.get('shipping_city',''),
            'shipping_phone': request.form['shipping_phone'],
            'payment_method': request.form.get('payment_method','cod')
        }
        cart_items = []
        if session.get('user_id'):
            uid = session['user_id']
            db = supabase.table('cart').select('quantity,product_id,products(name,price)').eq('user_id', uid).execute()
            if not db.data: return 'Cart is empty.'
            for row in db.data:
                p = row['products']
                cart_items.append({'product_id': row['product_id'], 'product_name': p['name'], 'quantity': row['quantity'], 'unit_price': p['price'], 'total_price': float(p['price'])*row['quantity']})
        else:
            guest_cart = session.get('cart', [])
            if not guest_cart: return 'Cart is empty.'
            cart_items = [{'product_id': i['productId'], 'product_name': i['name'], 'quantity': i['qty'], 'unit_price': i['price'], 'total_price': i['price']*i['qty']} for i in guest_cart]
        total = sum(item['total_price'] for item in cart_items)
        order = {**shipping, 'total_amount': total}
        if session.get('user_id'):
            order['user_id'] = session['user_id']
        else:
            order['guest_email'] = request.form.get('guest_email', 'guest@example.com')
        order_res = supabase.table('orders').insert(order).execute()
        oid = order_res.data[0]['id']
        for item in cart_items:
            supabase.table('order_items').insert({**item, 'order_id': oid}).execute()
        if session.get('user_id'):
            supabase.table('cart').delete().eq('user_id', session['user_id']).execute()
        else:
            session.pop('cart', None)
        return public_page("Order Confirmed", f'<h2 class="text-success">Order #{str(oid)[:8]} Placed!</h2><p>Total: KSh {total:.2f}</p><a href="/" class="btn btn-primary">Home</a>')
    return public_page("Checkout", '''<h2>Checkout</h2>
    <form method="post" style="max-width:500px;">
        <input class="form-control mb-2" name="guest_email" type="email" placeholder="Email (if guest)">
        <input class="form-control mb-2" name="shipping_name" placeholder="Full Name" required>
        <input class="form-control mb-2" name="shipping_address" placeholder="Address">
        <input class="form-control mb-2" name="shipping_city" placeholder="City">
        <input class="form-control mb-2" name="shipping_phone" placeholder="Phone" required>
        <select class="form-select mb-2" name="payment_method"><option value="cod">Cash on Delivery</option><option value="mobile_money">M-Pesa</option></select>
        <button class="btn btn-success w-100">Place Order</button>
    </form>''')

# ---------- Authentication ----------
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']; password = request.form['password']
        user_res = supabase.table('users').select('*').eq('email', email).execute()
        if not user_res.data:
            return public_page("Login", '<div class="alert alert-danger">Invalid credentials</div><a href="/login">Try again</a>')
        user = user_res.data[0]
        if not bcrypt.checkpw(password.encode(), user['password_hash'].encode()):
            return public_page("Login", '<div class="alert alert-danger">Invalid credentials</div><a href="/login">Try again</a>')
        session['user_id'] = user['id']
        session['user_name'] = user['full_name']
        session['is_admin'] = user.get('is_admin', False)
        return redirect('/')
    return public_page("Login", '''<h2>Login</h2>
    <form method="post" style="max-width:400px;">
    <input class="form-control mb-2" name="email" placeholder="Email" required>
    <input class="form-control mb-2" type="password" name="password" placeholder="Password" required>
    <button class="btn btn-primary w-100">Sign In</button></form><p class="mt-2"><a href="/register">Create account</a></p>''')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name = request.form['full_name']; email = request.form['email']; pwd = request.form['password']
        hashed = bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()
        try: supabase.table('users').insert({'full_name': name, 'email': email, 'password_hash': hashed}).execute()
        except: return public_page("Register", '<div class="alert alert-danger">Email already exists.</div><a href="/register">Try again</a>')
        return public_page("Registration Submitted", '<h2>Account Created</h2><p>Please wait for approval.</p><a href="/">Home</a>')
    return public_page("Register", '''<h2>Register</h2><form method="post" style="max-width:400px;">
    <input class="form-control mb-2" name="full_name" placeholder="Full Name" required>
    <input class="form-control mb-2" name="email" type="email" placeholder="Email" required>
    <input class="form-control mb-2" type="password" name="password" placeholder="Password" required>
    <button class="btn btn-primary w-100">Create Account</button></form>''')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/my-account')
def my_account():
    if not session.get('user_id'): return redirect('/login')
    orders = supabase.table('orders').select('*').eq('user_id', session['user_id']).order('created_at', desc=True).execute().data or []
    html = ''
    for o in orders:
        html += f'<div class="card mb-2"><div class="card-body"><strong>Order #{str(o["id"])[:8]}</strong> – {o["created_at"][:10]} – KSh {o["total_amount"]} – {o.get("order_status","")}</div></div>'
    user = {'full_name': session.get('user_name','User'), 'is_admin': session.get('is_admin', False)}
    return public_page("My Orders", f'<h2>My Orders</h2>{html or "<p>No orders yet.</p>"}', user)

# ---------- Admin decorator ----------
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated

# ---------- Admin routes ----------
@app.route('/admin')
@admin_required
def admin_dashboard():
    orders = supabase.table('orders').select('*').order('created_at', desc=True).limit(10).execute().data or []
    total_sales = sum(o['total_amount'] for o in orders) if orders else 0
    total_orders = supabase.table('orders').select('count', count='exact').execute().count
    total_products = supabase.table('products').select('count', count='exact').execute().count
    rows = ''.join(f'<tr><td>#{str(o["id"])[:8]}</td><td>{o.get("shipping_name","Guest")}</td><td>KSh {o["total_amount"]}</td><td><span class="badge bg-{"warning" if o.get("order_status")=="pending" else "success"}">{o.get("order_status","pending")}</span></td></tr>' for o in orders)
    body = f'''<div class="row mb-4">
      <div class="col-md-3"><div class="card bg-success text-white p-3"><h5>Total Sales</h5><h3>KSh {total_sales:,.2f}</h3></div></div>
      <div class="col-md-3"><div class="card bg-warning text-white p-3"><h5>Orders</h5><h3>{total_orders}</h3></div></div>
      <div class="col-md-3"><div class="card bg-primary text-white p-3"><h5>Products</h5><h3>{total_products}</h3></div></div>
      <div class="col-md-3"><div class="card bg-danger text-white p-3"><h5>Customers</h5><h3>-</h3></div></div></div>
      <h4>Recent Orders</h4><table class="table table-striped"><thead class="table-dark"><tr><th>ID</th><th>Customer</th><th>Total</th><th>Status</th></tr></thead><tbody>{rows}</tbody></table>'''
    return admin_page("Dashboard", body)

@app.route('/admin/orders')
@admin_required
def admin_orders():
    orders = supabase.table('orders').select('*').order('created_at', desc=True).execute().data or []
    rows = ''
    for o in orders:
        rows += f'<tr><td>#{str(o["id"])[:8]}</td><td>{o.get("shipping_name","Guest")}</td><td>KSh {o["total_amount"]}</td><td>{o.get("order_status","pending")}</td></tr>'
    return admin_page("Orders", f'<table class="table"><thead class="table-dark"><tr><th>ID</th><th>Customer</th><th>Total</th><th>Status</th></tr></thead><tbody>{rows}</tbody></table>', active='orders')

@app.route('/admin/products')
@admin_required
def admin_products():
    prods = supabase.table('products').select('*').order('name').execute().data or []
    rows = ''.join(f'<tr><td>{p["name"]}</td><td>{p["category"]}</td><td>{p["price"]}</td><td>{p["stock"]}</td></tr>' for p in prods)
    return admin_page("Products", f'<table class="table"><thead class="table-dark"><tr><th>Name</th><th>Category</th><th>Price</th><th>Stock</th></tr></thead><tbody>{rows}</tbody></table>', active='products')

# Other admin pages can be added similarly, but these are the core ones.
# For now, we'll just show a placeholder for the missing ones to avoid errors.

@app.route('/admin/prescriptions')
@admin_required
def admin_prescriptions():
    return admin_page("Prescriptions", "<p>Prescription management coming soon.</p>", active='prescriptions')

@app.route('/admin/customers')
@admin_required
def admin_customers():
    return admin_page("Customers", "<p>Customer management coming soon.</p>", active='customers')

@app.route('/admin/users')
@admin_required
def admin_users():
    return admin_page("Customer Care", "<p>User management coming soon.</p>", active='users')

@app.route('/admin/create-user')
@admin_required
def admin_create_user():
    return admin_page("Add Agent", "<p>User creation coming soon.</p>", active='create-user')

@app.route('/admin/settings')
@admin_required
def admin_settings():
    return admin_page("Settings", "<p>Settings coming soon.</p>", active='settings')

@app.route('/admin/export-orders')
@admin_required
def export_orders():
    orders = supabase.table('orders').select('*').order('created_at', desc=True).execute().data or []
    output = io.StringIO()
    w = csv.writer(output)
    w.writerow(["ID","Date","Customer","Email","Phone","Total","Status","Payment"])
    for o in orders:
        w.writerow([str(o['id'])[:8], o['created_at'][:10], o.get('customer_name','') or o.get('shipping_name',''), o.get('customer_email','') or o.get('guest_email',''), o.get('customer_phone','') or o.get('shipping_phone',''), o['total_amount'], o.get('order_status',''), o.get('payment_method','')])
    output.seek(0)
    return Response(output.getvalue(), mimetype='text/csv', headers={"Content-Disposition":"attachment;filename=orders.csv"})

# ---------- PWA (keep APK working) ----------
@app.route('/manifest.json')
def manifest():
    return make_response(json.dumps({
        "name": f"{PHARMACY_NAME} - Online Pharmacy",
        "short_name": PHARMACY_NAME,
        "start_url": "/",
        "display": "standalone",
        "icons": [{"src":"/static/icon-192.png","sizes":"192x192","type":"image/png"},{"src":"/static/icon-512.png","sizes":"512x512","type":"image/png"}]
    }), {'Content-Type': 'application/manifest+json'})

@app.route('/sw.js')
def sw():
    return Response("self.addEventListener('fetch',e=>e.respondWith(fetch(e.request)))", mimetype='application/javascript')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',8080)))
