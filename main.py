import os, json, bcrypt, io
from flask import Flask, request, redirect, session, Response, make_response
from supabase import create_client, Client
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dawalink-secret')

SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

PHARMACY_NAME = "DawaLink"
PHARMACY_PHONE = "+254792524333"
PHARMACY_EMAIL = "info@dawalink.co.ke"

# ---------- Tiny helper functions ----------
def public_page(title, body):
    return f"""<!DOCTYPE html><html>
<head><title>{title} – {PHARMACY_NAME}</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>body{{font-family:'Segoe UI',sans-serif;background:#f0f2f5;margin:0;padding:2rem;}}</style></head>
<body>
<nav class="navbar navbar-expand-lg navbar-dark bg-dark mb-4">
  <div class="container">
    <a class="navbar-brand" href="/"><i class="fas fa-pills"></i> {PHARMACY_NAME}</a>
    <div class="collapse navbar-collapse">
      <ul class="navbar-nav ms-auto">
        <li class="nav-item"><a class="nav-link" href="/">Home</a></li>
        <li class="nav-item"><a class="nav-link" href="/blog">Blog</a></li>
        <li class="nav-item"><a class="nav-link" href="/shop">Shop</a></li>
        <li class="nav-item"><a class="nav-link" href="/cart"><i class="fas fa-shopping-cart"></i> Cart</a></li>
      </ul>
    </div>
  </div>
</nav>
<div class="container">{body}</div>
</body></html>"""

def admin_page(title, body):
    return f"""<!DOCTYPE html><html>
<head><title>Admin – {PHARMACY_NAME}</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>body{{display:flex;margin:0;font-family:'Segoe UI',sans-serif;}}
.sidebar{{width:220px;background:#0A3D62;color:white;min-height:100vh;padding:1rem;}}
.sidebar a{{color:#ccc;display:block;padding:0.5rem;text-decoration:none;}}
.sidebar a:hover{{background:#0F4C7A;}}
.main{{flex:1;padding:2rem;background:#f4f6f9;}}</style></head>
<body>
<div class="sidebar">
  <h4 style="color:#F4A261;"><i class="fas fa-pills"></i> {PHARMACY_NAME}</h4>
  <a href="/admin">Dashboard</a>
  <a href="/admin/orders">Orders</a>
  <a href="/admin/products">Products</a>
  <a href="/logout">Logout</a>
</div>
<div class="main"><h2>{title}</h2><hr>{body}</div>
</body></html>"""

# ---------- Public routes ----------
@app.route('/')
def home():
    return public_page("Home", "<h1>Welcome to DawaLink</h1><p>Your trusted online pharmacy.</p>")

@app.route('/blog')
def blog():
    posts = [
        {"title":"Pain Relief","date":"2026-04-15","snippet":"Learn about OTC pain relievers."},
        {"title":"Baby Care","date":"2026-04-10","snippet":"A guide for new parents."},
        {"title":"Gut Health","date":"2026-04-02","snippet":"How probiotics improve wellness."}
    ]
    html = ""
    for p in posts:
        html += f"<div class='card mb-2'><div class='card-body'><h5>{p['title']}</h5><small>{p['date']}</small><p>{p['snippet']}</p></div></div>"
    return public_page("Blog", html)

@app.route('/shop')
def shop():
    prods = supabase.table('products').select('*').eq('active', True).execute().data or []
    rows = ""
    for p in prods:
        rows += f"""<div class="col-md-4 mb-3"><div class="card"><div class="card-body">
        <h5>{p['name']}</h5><p>{p['category']} – KSh {p['price']}</p>
        <form action="/cart/add" method="POST">
            <input type="hidden" name="productId" value="{p['id']}">
            <input type="number" name="quantity" value="1" min="1" style="width:60px;">
            <button class="btn btn-sm btn-primary">Add to Cart</button>
        </form></div></div></div>"""
    return public_page("Shop", f"<h2>Products</h2><div class='row'>{rows}</div>")

@app.route('/cart/add', methods=['POST'])
def add_to_cart():
    pid = request.form['productId']
    qty = int(request.form.get('quantity', 1))
    prod = supabase.table('products').select('id,name,price').eq('id', pid).single().execute().data
    if not prod:
        return "Product not found", 404
    if 'user_id' in session:
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
    if 'user_id' in session:
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
        return public_page("Cart", "<h2>Cart is empty</h2><a href='/shop' class='btn btn-primary'>Start Shopping</a>")
    rows = ""
    for i in items:
        rows += f"<div class='d-flex justify-content-between border p-2 mb-2'><span>{i['name']} x {i['qty']}</span><span>KSh {i['price']*i['qty']:.2f}</span></div>"
    body = f"<h2>Your Cart</h2>{rows}<hr><h4>Total: KSh {total:.2f}</h4><a href='/checkout' class='btn btn-success'>Proceed to Checkout</a>"
    return public_page("Cart", body)

@app.route('/checkout', methods=['GET','POST'])
def checkout():
    if request.method == 'POST':
        shipping = {
            'shipping_name': request.form['shipping_name'],
            'shipping_address': request.form.get('shipping_address', ''),
            'shipping_city': request.form.get('shipping_city', ''),
            'shipping_phone': request.form['shipping_phone'],
            'payment_method': request.form.get('payment_method', 'cod')
        }
        # Create order (simplified)
        order = {**shipping, 'total_amount': 0}
        if 'user_id' in session:
            order['user_id'] = session['user_id']
        else:
            order['guest_email'] = request.form.get('guest_email', 'guest@example.com')
        # Calculate total from cart
        total = 0
        cart_items = []
        if 'user_id' in session:
            uid = session['user_id']
            db = supabase.table('cart').select('quantity,product_id,products(name,price)').eq('user_id', uid).execute()
            for row in db.data:
                p = row['products']
                st = float(p['price']) * row['quantity']
                total += st
                cart_items.append({'product_id': row['product_id'], 'product_name': p['name'], 'quantity': row['quantity'], 'unit_price': p['price'], 'total_price': st})
        else:
            for it in session.get('cart', []):
                st = it['price'] * it['qty']
                total += st
                cart_items.append({'product_id': it['productId'], 'product_name': it['name'], 'quantity': it['qty'], 'unit_price': it['price'], 'total_price': st})
        order['total_amount'] = total
        order_res = supabase.table('orders').insert(order).execute()
        oid = order_res.data[0]['id']
        for item in cart_items:
            supabase.table('order_items').insert({**item, 'order_id': oid}).execute()
        # Clear cart
        if 'user_id' in session:
            supabase.table('cart').delete().eq('user_id', session['user_id']).execute()
        else:
            session.pop('cart', None)
        return public_page("Order Confirmed", f"<h2>Order #{str(oid)[:8]} placed!</h2><p>Total: KSh {total:.2f}</p><a href='/'>Home</a>")
    return public_page("Checkout", """<h2>Checkout</h2>
    <form method="post">
        <input class="form-control mb-2" name="shipping_name" placeholder="Full Name" required>
        <input class="form-control mb-2" name="shipping_address" placeholder="Address">
        <input class="form-control mb-2" name="shipping_city" placeholder="City">
        <input class="form-control mb-2" name="shipping_phone" placeholder="Phone" required>
        <select class="form-select mb-2" name="payment_method"><option value="cod">Cash on Delivery</option><option value="mobile_money">M-Pesa</option></select>
        <button class="btn btn-success w-100">Place Order</button>
    </form>""")

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user_res = supabase.table('users').select('*').eq('email', email).execute()
        if not user_res.data:
            return public_page("Login", "<div class='alert alert-danger'>Invalid credentials</div><a href='/login'>Try again</a>")
        user = user_res.data[0]
        if not bcrypt.checkpw(password.encode(), user['password_hash'].encode()):
            return public_page("Login", "<div class='alert alert-danger'>Invalid credentials</div><a href='/login'>Try again</a>")
        session['user_id'] = user['id']
        session['user_name'] = user['full_name']
        session['is_admin'] = user.get('is_admin', False)
        return redirect('/')
    return public_page("Login", """<h2>Login</h2><form method="post">
    <input class="form-control mb-2" name="email" placeholder="Email" required>
    <input class="form-control mb-2" type="password" name="password" placeholder="Password" required>
    <button class="btn btn-primary w-100">Sign In</button></form>""")

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ---------- Admin (protected) ----------
def admin_required(f):
    def decorated(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect('/login')
        return f(*args, **kwargs)
    decorated.__name__ = f.__name__
    return decorated

@app.route('/admin')
@admin_required
def admin_dashboard():
    orders = supabase.table('orders').select('*').order('created_at', desc=True).limit(10).execute().data or []
    rows = ""
    for o in orders:
        rows += f"<tr><td>#{str(o['id'])[:8]}</td><td>{o.get('shipping_name','Guest')}</td><td>KSh {o['total_amount']}</td><td>{o.get('order_status','pending')}</td></tr>"
    body = f"<h4>Recent Orders</h4><table class='table table-striped'><thead class='table-dark'><tr><th>ID</th><th>Customer</th><th>Total</th><th>Status</th></tr></thead><tbody>{rows}</tbody></table>"
    return admin_page("Dashboard", body)

@app.route('/admin/orders')
@admin_required
def admin_orders():
    return admin_page("Orders", "<p>Orders list will be here.</p>")

@app.route('/admin/products')
@admin_required
def admin_products():
    return admin_page("Products", "<p>Product management will be here.</p>")

# Dummy PWA routes (keep APK functional)
@app.route('/manifest.json')
def manifest():
    return make_response(json.dumps({"name": f"{PHARMACY_NAME} - Online Pharmacy","short_name": PHARMACY_NAME,"start_url":"/","display":"standalone","icons":[{"src":"/static/icon-192.png","sizes":"192x192","type":"image/png"},{"src":"/static/icon-512.png","sizes":"512x512","type":"image/png"}]}), {'Content-Type':'application/manifest+json'})

@app.route('/sw.js')
def sw():
    return Response("self.addEventListener('fetch',e=>e.respondWith(fetch(e.request)))", mimetype='application/javascript')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',8080)))
