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

# ---------- Helper to build public HTML ----------
def public_html(title, body, user=None):
    cart_total = 0.0
    if user:
        try:
            uid = session['user_id']
            resp = supabase.table('cart').select('quantity, products(price)').eq('user_id', uid).execute()
            for item in resp.data:
                cart_total += float(item['products']['price']) * item['quantity']
        except: pass
    user_menu = ''
    if user:
        user_menu += '<li class="nav-item"><a class="nav-link" href="/my-account">My Orders</a></li>'
        if user.get('is_admin'):
            user_menu += '<li class="nav-item"><a class="nav-link" href="/admin" style="color:#F4A261;font-weight:700;">🔧 Admin Panel</a></li>'
        user_menu += f'<li class="nav-item"><a class="nav-link" href="/logout">{user["full_name"]} (Logout)</a></li>'
    else:
        user_menu += '<li class="nav-item"><a class="nav-link" href="/login">Login</a></li>'
    return f'''<!DOCTYPE html><html lang="en"><head><title>{title} – {PHARMACY_NAME}</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>body{{font-family:'Inter',sans-serif;background:#F9F6F1;margin:0;}}.navbar{{background:#fff;box-shadow:0 2px 10px rgba(0,0,0,0.05);padding:0.8rem 0;}}.navbar-brand{{font-weight:800;font-size:1.8rem;color:#0A3D62;}}.btn-primary{{background:#0A3D62;border:none;border-radius:40px;padding:0.6rem 2rem;font-weight:600;}}.btn-primary:hover{{background:#F4A261;}}.whatsapp{{position:fixed;bottom:30px;right:30px;background:#25D366;color:white;border-radius:50%;width:55px;height:55px;display:flex;align-items:center;justify-content:center;font-size:1.8rem;box-shadow:0 5px 15px rgba(37,211,102,0.3);z-index:1000;}}</style></head>
<body><nav class="navbar navbar-expand-lg"><div class="container"><a class="navbar-brand" href="/"><i class="fas fa-pills"></i> {PHARMACY_NAME}</a>
<button class="navbar-toggler" data-bs-toggle="collapse" data-bs-target="#nav"><span class="navbar-toggler-icon"></span></button>
<div class="collapse navbar-collapse" id="nav"><ul class="navbar-nav ms-auto">
<li class="nav-item"><a class="nav-link" href="/">Home</a></li>
<li class="nav-item"><a class="nav-link" href="/about">About</a></li>
<li class="nav-item"><a class="nav-link" href="/contact">Contact</a></li>
<li class="nav-item dropdown"><a class="nav-link dropdown-toggle" href="#" data-bs-toggle="dropdown">Shop</a><ul class="dropdown-menu"><li><a class="dropdown-item" href="/shop">All Products</a></li><li><a class="dropdown-item" href="/shop?category=Supplements">Supplements</a></li><li><a class="dropdown-item" href="/shop?category=Pain+Relief">Pain Relief</a></li><li><a class="dropdown-item" href="/shop?category=Baby+Care">Baby Care</a></li><li><a class="dropdown-item" href="/shop?category=Women+Health">Women Health</a></li></ul></li>
<li class="nav-item"><a class="nav-link" href="/prescription">Upload Rx</a></li>
<li class="nav-item"><a class="nav-link" href="/blog">Blog</a></li>
<li class="nav-item"><a class="nav-link" href="/cart"><i class="fas fa-shopping-cart"></i> Cart <span class="badge bg-warning">KSh {cart_total:.0f}</span></a></li>
{user_menu}</ul></div></div></nav>
<div class="container mt-4">{body}</div>
<footer class="text-center py-4" style="background:#0A3D62;color:white;margin-top:3rem;"><p>&copy; 2026 {PHARMACY_NAME}.</p></footer>
<a href="https://wa.me/254792524333?text=Hello%20DawaLink" class="whatsapp" target="_blank"><i class="fab fa-whatsapp"></i></a>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script></body></html>'''

# ---------- Public routes ----------
@app.route('/')
def home():
    body = '''<div class="text-center py-5" style="background:linear-gradient(135deg,#0A3D62,#1B5A82);color:white;"><h1>Medicine At Your Convenience</h1><p class="lead">Quality OTC medicines & supplements delivered across Kenya.</p><a href="/shop" class="btn btn-light btn-lg me-2">Shop Now</a><a href="/prescription" class="btn btn-outline-light btn-lg">Upload Prescription</a></div>'''
    return public_html("Home", body)

@app.route('/about')
def about():
    return public_html("About", f"<h2>About {PHARMACY_NAME}</h2><p>Your trusted online pharmacy…</p>")

@app.route('/contact', methods=['GET','POST'])
def contact():
    if request.method == 'POST':
        try: supabase.table('inquiries').insert({k: request.form[k] for k in ['name','email','message']}).execute()
        except: pass
        return redirect('/contact?sent=1')
    sent = 'Message sent!' if request.args.get('sent') else ''
    body = f'''<h2>Contact Us</h2><form method="post"><input class="form-control mb-2" name="name" placeholder="Name" required><input class="form-control mb-2" name="email" type="email" placeholder="Email" required><textarea class="form-control mb-2" name="message" rows="4" placeholder="Message"></textarea><button class="btn btn-primary">Send</button></form>{sent}'''
    return public_html("Contact", body)

@app.route('/blog')
def blog():
    posts = [{"title":"Pain Relief","date":"2026-04-15","snippet":"Learn about OTC pain relievers."},
             {"title":"Baby Care","date":"2026-04-10","snippet":"A guide for new parents."},
             {"title":"Gut Health","date":"2026-04-02","snippet":"How probiotics improve wellness."}]
    html = ''.join(f'<div class="card mb-3 p-3"><h5>{p["title"]}</h5><small>{p["date"]}</small><p>{p["snippet"]}</p></div>' for p in posts)
    return public_html("Blog", html)

@app.route('/shop')
def shop():
    search = request.args.get('search','')
    category = request.args.get('category','')
    page = int(request.args.get('page',1))
    per_page = 6
    query = supabase.table('products').select('*', count='exact').eq('active', True)
    if search: query = query.or_(f"name.ilike.%{search}%,category.ilike.%{search}%")
    if category: query = query.or_(f"category.ilike.%{category}%")
    total_res = query.execute()
    total = total_res.count if total_res.count else 0
    data = supabase.table('products').select('*').eq('active', True)
    if search: data = data.or_(f"name.ilike.%{search}%,category.ilike.%{search}%")
    if category: data = data.or_(f"category.ilike.%{category}%")
    prods = data.range((page-1)*per_page, page*per_page-1).execute().data or []
    rows = ''
    for p in prods:
        img = f'<img src="{p.get("image_url")}" style="height:150px;object-fit:cover;">' if p.get("image_url") else '<div style="height:150px;background:#eee;display:flex;align-items:center;justify-content:center;"><i class="fas fa-pills fa-2x text-muted"></i></div>'
        rows += f'''<div class="col-6 col-md-4 col-lg-3 mb-4"><div class="card h-100 shadow-sm border-0 rounded-4 overflow-hidden">
        {img}<div class="card-body p-2"><h6 class="fw-bold mb-1">{p['name']}</h6><p class="text-muted small mb-1">{p['category']}</p>
        <div class="d-flex justify-content-between align-items-center"><span class="fw-bold text-primary">KSh {p['price']}</span>
        <form action="/cart/add" method="POST"><input type="hidden" name="productId" value="{p['id']}">
        <input type="number" name="quantity" value="1" min="1" max="10" class="form-control form-control-sm d-inline-block" style="width:50px;">
        <button type="submit" class="btn btn-primary btn-sm rounded-pill"><i class="fas fa-cart-plus"></i></button></form></div></div></div></div>'''
    pagination = ''
    if (total_pages := max(1, (total+per_page-1)//per_page)) > 1:
        pagination = '<nav><ul class="pagination justify-content-center">'
        for p in range(1, total_pages+1):
            active = 'active' if p == page else ''
            pagination += f'<li class="page-item {active}"><a class="page-link" href="/shop?page={p}&search={search}&category={category}">{p}</a></li>'
        pagination += '</ul></nav>'
    body = f'''<h2>Our Products</h2>
    <form class="row g-3 mb-4" method="get"><div class="col-md-7"><input class="form-control" name="search" value="{search}" placeholder="Search..."></div>
    <div class="col-md-3"><select class="form-select" name="category"><option value="">All</option><option value="Supplements" {'selected' if category=='Supplements' else ''}>Supplements</option><option value="Pain Relief" {'selected' if category=='Pain Relief' else ''}>Pain Relief</option><option value="Baby Care" {'selected' if category=='Baby Care' else ''}>Baby Care</option><option value="Women Health" {'selected' if category=='Women Health' else ''}>Women Health</option></select></div>
    <div class="col-md-2"><button class="btn btn-primary w-100">Filter</button></div></form>
    <div class="row">{rows}</div>{pagination}'''
    return public_html("Shop", body)

@app.route('/prescription', methods=['GET','POST'])
def prescription_upload():
    if request.method == 'POST':
        name = request.form['customer_name']
        email = request.form['customer_email']
        phone = request.form['customer_phone']
        notes = request.form.get('notes','')
        file = request.files.get('prescription_file')
        file_url = None
        if file and file.filename:
            fname = secure_filename(file.filename)
            unique_name = f"rx_{os.urandom(4).hex()}_{fname}"
            supabase.storage.from_("product-images").upload(unique_name, file.read(), {"content-type": file.content_type})
            file_url = f"{SUPABASE_URL}/storage/v1/object/public/product-images/{unique_name}"
        try: supabase.table('prescriptions').insert({'customer_name':name,'customer_email':email,'customer_phone':phone,'notes':notes,'file_url':file_url,'status':'pending'}).execute()
        except: pass
        return public_html("Rx Received", '<h2 class="text-success">Thank You!</h2><p>Your prescription has been submitted.</p><a href="/" class="btn btn-primary">Home</a>')
    return public_html("Upload Prescription", '''<h2>Upload Prescription</h2>
    <form method="post" enctype="multipart/form-data" style="max-width:500px;">
    <input class="form-control mb-2" name="customer_name" placeholder="Your Name" required>
    <input class="form-control mb-2" name="customer_email" type="email" placeholder="Your Email" required>
    <input class="form-control mb-2" name="customer_phone" placeholder="Phone" required>
    <textarea class="form-control mb-2" name="notes" placeholder="Notes"></textarea>
    <input class="form-control mb-2" type="file" name="prescription_file" accept="image/*,.pdf" required>
    <button class="btn btn-primary w-100">Submit</button></form>''')

# Cart routes
@app.route('/cart/add', methods=['POST'])
def add_to_cart():
    pid = request.form['productId']
    qty = int(request.form.get('quantity',1))
    prod = supabase.table('products').select('id,name,price').eq('id',pid).single().execute().data
    if not prod: return 'Product not found',404
    if 'user_id' in session:
        uid = session['user_id']
        ex = supabase.table('cart').select('id,quantity').eq('user_id',uid).eq('product_id',pid).execute()
        if ex.data:
            supabase.table('cart').update({'quantity': ex.data[0]['quantity'] + qty}).eq('id', ex.data[0]['id']).execute()
        else:
            supabase.table('cart').insert({'user_id':uid,'product_id':pid,'quantity':qty}).execute()
    else:
        cart = session.get('cart',[])
        found = False
        for it in cart:
            if it['productId'] == pid:
                it['qty'] += qty; found = True; break
        if not found:
            cart.append({'productId':pid,'qty':qty,'price':float(prod['price']),'name':prod['name']})
        session['cart'] = cart
    return redirect('/cart')

@app.route('/cart')
def view_cart():
    items = []; total = 0.0
    if 'user_id' in session:
        uid = session['user_id']
        db = supabase.table('cart').select('quantity,product_id,products(name,price)').eq('user_id',uid).execute()
        for row in db.data:
            p = row['products']
            items.append({'productId':row['product_id'],'name':p['name'],'price':float(p['price']),'qty':row['quantity']})
            total += float(p['price']) * row['quantity']
    else:
        items = session.get('cart',[])
        total = sum(it['price']*it['qty'] for it in items)
    if not items:
        return public_html("Cart", '<h2>Your Cart</h2><p>Cart is empty.</p><a href="/shop" class="btn btn-primary">Shop</a>')
    rows = ''.join(f'<div class="card p-3 mb-2 d-flex flex-row justify-content-between"><div><h5>{i["name"]}</h5><small>Qty: {i["qty"]} × KSh {i["price"]}</small></div><div><h4 class="text-success">KSh {i["price"]*i["qty"]:.2f}</h4><a href="/cart/remove/{i["productId"]}" class="btn btn-sm btn-outline-danger"><i class="fas fa-trash"></i></a></div></div>' for i in items)
    body = f'<h2>Your Cart</h2>{rows}<hr><div class="d-flex justify-content-between"><h4>Total</h4><h4>KSh {total:.2f}</h4></div><a href="/checkout" class="btn btn-success w-100 py-3 mt-3 rounded-pill">Proceed to Checkout</a>'
    return public_html("Cart", body, user={'cart':items})

@app.route('/cart/remove/<pid>')
def remove_cart(pid):
    if 'user_id' in session:
        try: supabase.table('cart').delete().eq('user_id',session['user_id']).eq('product_id',pid).execute()
        except: pass
    else:
        cart = [i for i in session.get('cart',[]) if i['productId'] != pid]
        session['cart'] = cart
    return redirect('/cart')

@app.route('/checkout', methods=['GET','POST'])
def checkout():
    if request.method == 'POST':
        guest_email = request.form.get('guest_email')
        shipping = {k: request.form[k] for k in ['shipping_name','shipping_address','shipping_city','shipping_phone','payment_method']}
        cart_items = []
        if 'user_id' in session:
            uid = session['user_id']
            db = supabase.table('cart').select('quantity,product_id,products(name,price)').eq('user_id',uid).execute()
            if not db.data: return 'Cart empty.'
            for row in db.data:
                p = row['products']
                cart_items.append({'productId':row['product_id'],'name':p['name'],'price':float(p['price']),'qty':row['quantity']})
        else:
            guest_cart = session.get('cart',[])
            if not guest_cart: return 'Cart empty.'
            if not guest_email: return 'Guest email required.'
            cart_items = guest_cart
        total = sum(it['price']*it['qty'] for it in cart_items)
        discount_code = request.form.get('discount_code','').strip().upper()
        if discount_code:
            code = supabase.table('discount_codes').select('*').eq('code',discount_code).single().execute()
            if code.data and code.data.get('active'):
                c = code.data
                if c.get('discount_percent'): total *= (1 - c['discount_percent']/100)
                elif c.get('discount_amount'): total -= c['discount_amount']
                supabase.table('discount_codes').update({'used_count': c['used_count']+1}).eq('id',c['id']).execute()
        order = {**shipping, 'total_amount': total}
        if 'user_id' in session: order['user_id'] = session['user_id']
        else: order['guest_email'] = guest_email
        order_res = supabase.table('orders').insert(order).execute()
        oid = order_res.data[0]['id']
        for item in cart_items:
            supabase.table('order_items').insert({'order_id':oid,'product_id':item['productId'],'product_name':item['name'],'quantity':item['qty'],'unit_price':item['price'],'total_price':item['price']*item['qty']}).execute()
        if 'user_id' in session: supabase.table('cart').delete().eq('user_id',session['user_id']).execute()
        else: session.pop('cart',None)
        ord = supabase.table('orders').select('*').eq('id',oid).single().execute().data
        items_html = ''.join(f'<tr><td>{i["product_name"]}</td><td>{i["quantity"]}</td><td>KSh {i["unit_price"]}</td><td>KSh {i["total_price"]}</td></tr>' for i in supabase.table('order_items').select('*').eq('order_id',oid).execute().data)
        body = f'''<h2 class="text-success">Order Confirmed</h2><p>Order #{oid[:8]} placed. Total: KSh {ord['total_amount']}</p>
        <table class="table"><thead><tr><th>Product</th><th>Qty</th><th>Unit</th><th>Subtotal</th></tr></thead><tbody>{items_html}</tbody></table>
        <a href="/shop" class="btn btn-primary">Continue Shopping</a>'''
        return public_html("Order Confirmed", body)
    return public_html("Checkout", '''<h2>Checkout</h2>
    <form method="post" style="max-width:500px;">
    <input class="form-control mb-2" name="guest_email" type="email" placeholder="Email (if guest)">
    <input class="form-control mb-2" name="shipping_name" placeholder="Full Name" required>
    <input class="form-control mb-2" name="shipping_address" placeholder="Address">
    <input class="form-control mb-2" name="shipping_city" placeholder="City">
    <input class="form-control mb-2" name="shipping_phone" placeholder="Phone" required>
    <select class="form-select mb-2" name="payment_method"><option value="cod">Cash on Delivery</option><option value="mobile_money">M-Pesa</option></select>
    <input class="form-control mb-2" name="discount_code" placeholder="Discount code">
    <button class="btn btn-success w-100 py-3 rounded-pill">Place Order</button></form>''')

# Authentication
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']; password = request.form['password']
        user_res = supabase.table('users').select('*').eq('email',email).execute()
        if not user_res.data: return public_html("Login", '<div class="alert alert-danger">Invalid credentials</div><a href="/login">Try again</a>')
        user = user_res.data[0]
        if not bcrypt.checkpw(password.encode(), user['password_hash'].encode()): return public_html("Login", '<div class="alert alert-danger">Invalid credentials</div><a href="/login">Try again</a>')
        is_admin = user.get('is_admin', False)
        approved = user.get('approved', False)
        if email == 'rodriguezgeorge089@gmail.com':
            approved = True
            if not user.get('approved'): supabase.table('users').update({'approved':True}).eq('id',user['id']).execute()
        if not is_admin and not approved: return public_html("Login", '<div class="alert alert-danger">Account pending approval.</div>')
        if is_admin and not approved: supabase.table('users').update({'approved':True}).eq('id',user['id']).execute()
        session['user_id'] = user['id']; session['user_name'] = user['full_name']; session['is_admin'] = is_admin
        if 'cart' in session:
            for item in session['cart']:
                ex = supabase.table('cart').select('id').eq('user_id',user['id']).eq('product_id',item['productId']).execute()
                if ex.data: supabase.table('cart').update({'quantity': ex.data[0]['quantity'] + item['qty']}).eq('id', ex.data[0]['id']).execute()
                else: supabase.table('cart').insert({'user_id':user['id'],'product_id':item['productId'],'quantity':item['qty']}).execute()
            session.pop('cart', None)
        return redirect('/')
    return public_html("Login", '''<h2>Login</h2><form method="post" style="max-width:400px;">
    <input class="form-control mb-2" name="email" placeholder="Email" required>
    <input class="form-control mb-2" type="password" name="password" placeholder="Password" required>
    <button class="btn btn-primary w-100">Sign In</button></form><p class="mt-3"><a href="/register">Create account</a> · <a href="/">Home</a></p>''')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['full_name']; email = request.form['email']; password = request.form['password']
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        try: supabase.table('users').insert({'full_name':full_name,'email':email,'password_hash':hashed}).execute()
        except: return public_html("Register", '<div class="alert alert-danger">Email already exists.</div><a href="/register">Try again</a>')
        return public_html("Registration Submitted", '<h2>Registration Submitted</h2><p>Your account will be reviewed.</p><a href="/">Home</a>')
    return public_html("Register", '''<h2>Register</h2><form method="post" style="max-width:400px;">
    <input class="form-control mb-2" name="full_name" placeholder="Full Name" required>
    <input class="form-control mb-2" name="email" type="email" placeholder="Email" required>
    <input class="form-control mb-2" type="password" name="password" placeholder="Password" required>
    <button class="btn btn-primary w-100">Register</button></form><p class="mt-3"><a href="/login">Already have an account?</a></p>''')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/my-account')
def my_account():
    if not session.get('user_id'): return redirect('/login')
    orders = supabase.table('orders').select('*').eq('user_id',session['user_id']).order('created_at', desc=True).execute().data or []
    html = ''.join(f'<div class="card mb-3"><div class="card-header">Order #{str(o["id"])[:8]} – {o["created_at"][:10]} – KSh {o["total_amount"]} – {o.get("order_status","")}</div></div>' for o in orders)
    return public_html("My Orders", f'<h2>My Orders</h2>{html or "<p>No orders yet.</p>"}', user={'full_name':session.get('user_name',''),'is_admin':False})

# ---------- Admin decorator ----------
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('is_admin'): return redirect('/login')
        return f(*args, **kwargs)
    return decorated

# Admin layout helper
def admin_page(title, body, active='dashboard'):
    sidebar = ''
    links = {'dashboard':'/admin','orders':'/admin/orders','products':'/admin/products','prescriptions':'/admin/prescriptions','customers':'/admin/customers','users':'/admin/users','create-user':'/admin/create-user','settings':'/admin/settings','export':'/admin/export-orders'}
    for name,url in links.items():
        active_cls = 'active' if active == name else ''
        sidebar += f'<a href="{url}" class="list-group-item list-group-item-action {active_cls}">{name.replace("-"," ").title()}</a>'
    return f'''<!DOCTYPE html><html><head><title>{title} – Admin</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>body{{display:flex;margin:0;}}.sidebar{{width:250px;background:#0A3D62;color:white;min-height:100vh;padding:1rem;}}.sidebar a{{color:#ccc;}}.sidebar a:hover{{background:#0F4C7A;}}.main-content{{flex:1;padding:2rem;background:#f4f6f9;}}</style></head>
<body><div class="sidebar"><h4 class="text-warning"><i class="fas fa-pills"></i> {PHARMACY_NAME}</h4><div class="list-group">{sidebar}</div></div>
<div class="main-content"><h2>{title}</h2><hr>{body}</div></body></html>'''

@app.route('/admin')
@admin_required
def admin_dashboard():
    orders = supabase.table('orders').select('*').order('created_at', desc=True).limit(10).execute().data or []
    total_sales = sum(o['total_amount'] for o in orders)
    total_orders = supabase.table('orders').select('count', count='exact').execute().count
    total_products = supabase.table('products').select('count', count='exact').execute().count
    cust_set = {o.get('customer_email') or o.get('guest_email') for o in orders if o.get('customer_email') or o.get('guest_email')}
    rows = ''.join(f'<tr><td>#{str(o["id"])[:8]}</td><td>{o.get("shipping_name","Guest")}</td><td>KSh {o["total_amount"]}</td><td><span class="badge bg-{"warning" if o.get("order_status")=="pending" else "success"}">{o.get("order_status","pending")}</span></td><td>{o["created_at"][:10]}</td></tr>' for o in orders)
    body = f'''<div class="row"><div class="col-md-3"><div class="card text-white bg-success mb-3"><div class="card-body"><h5>Sales</h5><h3>KSh {total_sales:,.2f}</h3></div></div></div>
    <div class="col-md-3"><div class="card text-white bg-warning mb-3"><div class="card-body"><h5>Orders</h5><h3>{total_orders}</h3></div></div></div>
    <div class="col-md-3"><div class="card text-white bg-primary mb-3"><div class="card-body"><h5>Products</h5><h3>{total_products}</h3></div></div></div>
    <div class="col-md-3"><div class="card text-white bg-danger mb-3"><div class="card-body"><h5>Customers</h5><h3>{len(cust_set)}</h3></div></div></div></div>
    <h4>Recent Orders</h4><table class="table table-striped"><thead class="table-dark"><tr><th>ID</th><th>Customer</th><th>Total</th><th>Status</th><th>Date</th></tr></thead><tbody>{rows}</tbody></table>'''
    return admin_page("Dashboard", body)

@app.route('/admin/orders')
@admin_required
def admin_orders():
    orders = supabase.table('orders').select('*').order('created_at', desc=True).execute().data or []
    rows = ''
    for o in orders:
        rows += '<tr><td>#{}</td><td>{}</td><td>KSh {}</td><td>{}</td><td>{}</td><td><form method="post" action="/admin/order/{}/status" class="d-inline"><select name="status" class="form-select form-select-sm" style="width:auto;"><option>pending</option><option>confirmed</option><option>shipped</option><option>delivered</option></select> <button class="btn btn-sm btn-primary">Update</button></form></td></tr>'.format(str(o['id'])[:8], o.get('shipping_name','Guest'), o['total_amount'], o.get('order_status','pending'), o['created_at'][:10], o['id'])
    return admin_page("Orders", f'<table class="table"><thead class="table-dark"><tr><th>ID</th><th>Customer</th><th>Total</th><th>Status</th><th>Date</th><th>Action</th></tr></thead><tbody>{rows}</tbody></table>', active='orders')

@app.route('/admin/order/<oid>/status', methods=['POST'])
@admin_required
def update_status(oid):
    supabase.table('orders').update({'order_status': request.form['status']}).eq('id', oid).execute()
    return redirect('/admin/orders')

@app.route('/admin/order/<int:oid>/invoice')
@admin_required
def admin_invoice(oid):
    order = supabase.table('orders').select('*').eq('id',oid).single().execute().data
    items = supabase.table('order_items').select('*').eq('order_id',oid).execute().data or []
    item_rows = ''.join(f'<tr><td>{i["product_name"]}</td><td>{i["quantity"]}</td><td>KSh {i["unit_price"]}</td><td>KSh {i["total_price"]}</td></tr>' for i in items)
    return f'<html><body onload="window.print()"><h2>{PHARMACY_NAME} Invoice #{oid}</h2><table border="1">{item_rows}</table><h3>Total: KSh {order["total_amount"]}</h3></body></html>'

@app.route('/admin/products')
@admin_required
def admin_products():
    prods = supabase.table('products').select('*').order('name').execute().data or []
    rows = ''.join(f'<tr><td>{p["name"]}</td><td>{p["category"]}</td><td>{p["price"]}</td><td>{p["stock"]}</td><td><a href="/admin/edit-product/{p["id"]}" class="btn btn-sm btn-warning">Edit</a> <a href="/admin/delete-product/{p["id"]}" class="btn btn-sm btn-danger">Delete</a></td></tr>' for p in prods)
    return admin_page("Products", f'<a href="/admin/add-product" class="btn btn-success mb-3">+ Add Product</a><table class="table"><thead class="table-dark"><tr><th>Name</th><th>Category</th><th>Price</th><th>Stock</th><th></th></tr></thead><tbody>{rows}</tbody></table>', active='products')

@app.route('/admin/add-product', methods=['GET','POST'])
@admin_required
def add_product():
    if request.method == 'POST':
        name = request.form['name']; desc = request.form.get('description',''); cat = request.form['category']; price = float(request.form['price']); stock = int(request.form['stock'])
        img = request.files.get('image')
        url = None
        if img and img.filename:
            fname = secure_filename(img.filename)
            uname = f"{os.urandom(4).hex()}_{fname}"
            supabase.storage.from_("product-images").upload(uname, img.read(), {"content-type": img.content_type})
            url = f"{SUPABASE_URL}/storage/v1/object/public/product-images/{uname}"
        supabase.table('products').insert({'name':name,'description':desc,'category':cat,'price':price,'stock':stock,'image_url':url,'active':True}).execute()
        return redirect('/admin/products')
    return admin_page("Add Product", '''<form method="post" enctype="multipart/form-data" style="max-width:500px;">
    <input class="form-control mb-2" name="name" placeholder="Name" required>
    <textarea class="form-control mb-2" name="description" placeholder="Description"></textarea>
    <input class="form-control mb-2" name="category" placeholder="Category" required>
    <div class="row"><div class="col"><input class="form-control mb-2" type="number" step="0.01" name="price" placeholder="Price" required></div>
    <div class="col"><input class="form-control mb-2" type="number" name="stock" placeholder="Stock" required></div></div>
    <input class="form-control mb-2" type="file" name="image" accept="image/*">
    <button class="btn btn-primary w-100">Add Product</button></form>''', active='products')

@app.route('/admin/edit-product/<pid>', methods=['GET','POST'])
@admin_required
def edit_product(pid):
    if request.method == 'POST':
        upd = {'name':request.form['name'],'description':request.form.get('description',''),'category':request.form['category'],'price':float(request.form['price']),'stock':int(request.form['stock'])}
        img = request.files.get('image')
        if img and img.filename:
            fname = secure_filename(img.filename)
            uname = f"{os.urandom(4).hex()}_{fname}"
            supabase.storage.from_("product-images").upload(uname, img.read(), {"content-type": img.content_type})
            upd['image_url'] = f"{SUPABASE_URL}/storage/v1/object/public/product-images/{uname}"
        supabase.table('products').update(upd).eq('id',pid).execute()
        return redirect('/admin/products')
    p = supabase.table('products').select('*').eq('id',pid).single().execute().data
    return admin_page("Edit Product", f'''<form method="post" enctype="multipart/form-data" style="max-width:500px;">
    <input class="form-control mb-2" name="name" value="{p['name']}" required>
    <textarea class="form-control mb-2" name="description">{p.get('description','')}</textarea>
    <input class="form-control mb-2" name="category" value="{p['category']}" required>
    <div class="row"><div class="col"><input class="form-control mb-2" type="number" step="0.01" name="price" value="{p['price']}" required></div>
    <div class="col"><input class="form-control mb-2" type="number" name="stock" value="{p['stock']}" required></div></div>
    <input class="form-control mb-2" type="file" name="image" accept="image/*">
    <button class="btn btn-primary w-100">Update Product</button></form>''', active='products')

@app.route('/admin/delete-product/<pid>')
@admin_required
def delete_product(pid):
    supabase.table('products').delete().eq('id',pid).execute()
    return redirect('/admin/products')

@app.route('/admin/prescriptions')
@admin_required
def admin_prescriptions():
    rx = supabase.table('prescriptions').select('*').order('created_at', desc=True).execute().data or []
    items = ''.join(f'<div class="card p-2 mb-2"><strong>{r["customer_name"]}</strong> – {r["customer_email"]}<br>{r["customer_phone"]}<br><a href="{r.get("file_url","#")}" target="_blank">View File</a></div>' for r in rx)
    return admin_page("Prescriptions", items, active='prescriptions')

@app.route('/admin/customers')
@admin_required
def admin_customers():
    orders = supabase.table('orders').select('*').execute().data or []
    cust = {}
    for o in orders:
        e = o.get('customer_email') or o.get('guest_email')
        if not e: continue
        if e not in cust: cust[e] = {'name': o.get('customer_name','') or o.get('shipping_name',''), 'phone': o.get('customer_phone','') or o.get('shipping_phone',''), 'spent':0, 'orders':0}
        cust[e]['spent'] += o['total_amount']; cust[e]['orders'] += 1
    rows = ''.join(f'<tr><td>{c["name"]}</td><td>{e}</td><td>{c["phone"]}</td><td>{c["orders"]}</td><td>KSh {c["spent"]}</td></tr>' for e,c in cust.items())
    return admin_page("Customers", f'<table class="table"><thead class="table-dark"><tr><th>Name</th><th>Email</th><th>Phone</th><th>Orders</th><th>Total</th></tr></thead><tbody>{rows}</tbody></table>', active='customers')

@app.route('/admin/users')
@admin_required
def admin_users():
    users = supabase.table('users').select('*').execute().data or []
    rows = ''.join(f'<tr><td>{u["full_name"]}</td><td>{u["email"]}</td><td>{"Approved" if u.get("approved") else "Pending"}</td><td><a href="/admin/approve-user/{u["id"]}" class="btn btn-sm btn-success">Approve</a> <a href="/admin/disable-user/{u["id"]}" class="btn btn-sm btn-danger">Disable</a></td></tr>' for u in users)
    return admin_page("Customer Care", f'<table class="table"><thead class="table-dark"><tr><th>Name</th><th>Email</th><th>Status</th><th></th></tr></thead><tbody>{rows}</tbody></table>', active='users')

@app.route('/admin/approve-user/<uid>')
@admin_required
def approve_user(uid):
    supabase.table('users').update({'approved':True}).eq('id',uid).execute()
    return redirect('/admin/users')

@app.route('/admin/disable-user/<uid>')
@admin_required
def disable_user(uid):
    supabase.table('users').update({'approved':False}).eq('id',uid).execute()
    return redirect('/admin/users')

@app.route('/admin/create-user', methods=['GET','POST'])
@admin_required
def create_user():
    if request.method == 'POST':
        name = request.form['full_name']; email = request.form['email']; pwd = request.form['password']; is_admin = request.form.get('is_admin') == 'on'
        hashed = bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()
        try: supabase.table('users').insert({'full_name':name,'email':email,'password_hash':hashed,'is_admin':is_admin,'approved':True}).execute()
        except: return admin_page("Add Agent", '<div class="alert alert-danger">Email exists.</div><a href="/admin/create-user">Try again</a>', active='create-user')
        return redirect('/admin/users')
    return admin_page("Add Agent", '''<form method="post" style="max-width:500px;">
    <input class="form-control mb-2" name="full_name" placeholder="Full Name" required>
    <input class="form-control mb-2" name="email" type="email" placeholder="Email" required>
    <input class="form-control mb-2" type="password" name="password" placeholder="Password" required>
    <div class="form-check mb-2"><input class="form-check-input" type="checkbox" name="is_admin"> Grant Admin</div>
    <button class="btn btn-primary w-100">Create</button></form>''', active='create-user')

@app.route('/admin/settings', methods=['GET','POST'])
@admin_required
def admin_settings():
    if request.method == 'POST':
        new_pwd = request.form['new_password']
        hashed = bcrypt.hashpw(new_pwd.encode(), bcrypt.gensalt()).decode()
        supabase.table('users').update({'password_hash':hashed}).eq('id', session['user_id']).execute()
        return redirect('/admin/settings?success=1')
    msg = '<div class="alert alert-success">Password updated!</div>' if request.args.get('success') else ''
    return admin_page("Settings", f'{msg}<form method="post" style="max-width:400px;"><input class="form-control mb-2" type="password" name="new_password" placeholder="New Password"><button class="btn btn-primary">Update</button></form>', active='settings')

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

# PWA
@app.route('/manifest.json')
def manifest():
    return make_response(json.dumps({
        "name": f"{PHARMACY_NAME} - Online Pharmacy",
        "short_name": PHARMACY_NAME,
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0A3D62",
        "theme_color": "#0A3D62",
        "icons": [{"src":"/static/icon-192.png","sizes":"192x192","type":"image/png"},{"src":"/static/icon-512.png","sizes":"512x512","type":"image/png"}]
    }), {'Content-Type': 'application/manifest+json'})

@app.route('/sw.js')
def sw():
    return Response("self.addEventListener('fetch',e=>e.respondWith(fetch(e.request)))", mimetype='application/javascript')

def _create_png(w,h,color=(10,61,98)):
    def chunk(t,d): c=t+d; return struct.pack(">I",len(d)) + c + struct.pack(">I",zlib.crc32(c)&0xFFFFFFFF)
    sig = b'\x89PNG\r\n\x1a\n'
    ihdr = struct.pack(">IIBBBBB",w,h,8,2,0,0,0)
    raw = b''.join(b'\x00' + bytes(color)*w for _ in range(h))
    return sig + chunk(b'IHDR',ihdr) + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND',b'')

@app.route('/static/icon-192.png')
def icon192(): return Response(_create_png(192,192), mimetype='image/png')
@app.route('/static/icon-512.png')
def icon512(): return Response(_create_png(512,512), mimetype='image/png')

@app.route('/download')
def download(): return public_html("Download App", '<h2>Download our APK</h2><p>Install directly from <a href="#">link</a>.</p>')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',8080)))
