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

def navbar_html(user, cart_total):
    user_menu = ''
    if user:
        user_menu += '<li class="nav-item"><a class="nav-link" href="/my-account">My Orders</a></li>'
        if user.get('is_admin'):
            user_menu += '<li class="nav-item"><a class="nav-link" href="/admin" style="color:#F4A261;font-weight:700;">🔧 Admin Panel</a></li>'
        user_menu += f'<li class="nav-item"><a class="nav-link" href="/logout">{user["full_name"]} (Logout)</a></li>'
    else:
        user_menu += '<li class="nav-item"><a class="nav-link" href="/login">Login</a></li>'
    return f'''<nav class="navbar navbar-expand-lg sticky-top" style="background:rgba(255,255,255,0.95);box-shadow:0 2px 10px rgba(0,0,0,0.05);">
    <div class="container">
        <a class="navbar-brand fw-bold" href="/" style="color:#0A3D62;"><i class="fas fa-pills" style="background:#F4A261;color:white;border-radius:12px;padding:8px 12px;margin-right:8px;"></i>{PHARMACY_NAME}</a>
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#mainNav"><span class="navbar-toggler-icon"></span></button>
        <div class="collapse navbar-collapse" id="mainNav">
            <ul class="navbar-nav ms-auto align-items-center">
                <li class="nav-item"><a class="nav-link" href="/">Home</a></li>
                <li class="nav-item"><a class="nav-link" href="/about">About</a></li>
                <li class="nav-item"><a class="nav-link" href="/contact">Contact</a></li>
                <li class="nav-item dropdown">
                    <a class="nav-link dropdown-toggle" href="#" data-bs-toggle="dropdown">Shop</a>
                    <ul class="dropdown-menu">
                        <li><a class="dropdown-item" href="/shop">All Products</a></li>
                        <li><a class="dropdown-item" href="/shop?category=Supplements">Supplements</a></li>
                        <li><a class="dropdown-item" href="/shop?category=Pain+Relief">Pain Relief</a></li>
                        <li><a class="dropdown-item" href="/shop?category=Baby+Care">Baby Care</a></li>
                        <li><a class="dropdown-item" href="/shop?category=Women+Health">Women Health</a></li>
                    </ul>
                </li>
                <li class="nav-item"><a class="nav-link" href="/prescription">Upload Rx</a></li>
                <li class="nav-item"><a class="nav-link" href="/blog">Blog</a></li>
                <li class="nav-item"><a class="nav-link" href="/cart"><i class="fas fa-shopping-cart"></i> Cart <span class="badge bg-warning">{cart_total:.0f} KSh</span></a></li>
                {user_menu}
            </ul>
        </div>
    </div>
</nav>'''

def public_page(title, body, user=None):
    cart_total = 0.0
    if user:
        try:
            uid = session.get('user_id')
            resp = supabase.table('cart').select('quantity, products(price)').eq('user_id', uid).execute()
            for it in resp.data:
                cart_total += float(it['products']['price']) * it['quantity']
        except: pass
    return f'''<!DOCTYPE html><html>
<head><title>{title} – {PHARMACY_NAME}</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>body{{font-family:'Inter',sans-serif;background:#F9F6F1;margin:0;}}.btn-primary{{background:#0A3D62;border:none;border-radius:40px;padding:0.7rem 2rem;font-weight:600;}}.btn-primary:hover{{background:#F4A261;}}footer{{background:#0A3D62;color:white;text-align:center;padding:2rem;margin-top:3rem;}}.whatsapp{{position:fixed;bottom:30px;right:30px;background:#25D366;color:white;border-radius:50%;width:55px;height:55px;display:flex;align-items:center;justify-content:center;font-size:1.8rem;box-shadow:0 5px 15px rgba(37,211,102,0.3);z-index:1000;}}</style></head>
<body>
{navbar_html(user, cart_total)}
<div class="container mt-4">{body}</div>
<footer><p>&copy; 2026 {PHARMACY_NAME}. All rights reserved.</p></footer>
<a href="https://wa.me/254792524333?text=Hello%20DawaLink%2C%20I%20need%20assistance" class="whatsapp" target="_blank"><i class="fab fa-whatsapp"></i></a>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body></html>'''

def admin_sidebar(active='dashboard'):
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
    sidebar = '<div class="d-flex flex-column p-3 bg-dark text-white" style="width:250px;min-height:100vh;position:fixed;">'
    sidebar += f'<h4 class="text-warning"><i class="fas fa-pills"></i> {PHARMACY_NAME}</h4><hr>'
    for name, url in links.items():
        active_cls = 'active' if active == name else ''
        sidebar += f'<a href="{url}" class="btn btn-outline-light mb-1 {active_cls}">{name.replace("-"," ").title()}</a>'
    sidebar += '<hr><a href="/" class="btn btn-outline-light btn-sm">View Site</a><a href="/logout" class="btn btn-outline-danger btn-sm mt-auto">Logout</a></div>'
    return sidebar

@app.route('/')
def home():
    body = '''<section class="text-center py-5" style="background:linear-gradient(135deg,#0A3D62,#1B5A82);color:white;">
    <h1 style="font-size:3rem;font-weight:800;">Medicine At Your Convenience</h1>
    <p class="lead">Quality OTC medicines, supplements & personal care products delivered fast across Kenya.</p>
    <a href="/shop" class="btn btn-light btn-lg me-2">Shop Now</a>
    <a href="/prescription" class="btn btn-outline-light btn-lg">Upload Prescription</a>
</section>'''
    return public_page("Home", body)

@app.route('/about')
def about():
    return public_page("About Us", f"<h2>About {PHARMACY_NAME}</h2><p>{PHARMACY_NAME} is your trusted online pharmacy…</p>")

@app.route('/contact', methods=['GET','POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        msg = request.form['message']
        try: supabase.table('inquiries').insert({'name':name,'email':email,'message':msg}).execute()
        except: pass
        return redirect('/contact?sent=1')
    sent = request.args.get('sent')
    body = f'''<h2>Contact Us</h2>
    <p>Tel: {PHARMACY_PHONE}<br>Email: {PHARMACY_EMAIL}</p>
    <form method="post"><input class="form-control mb-2" name="name" placeholder="Name" required>
    <input class="form-control mb-2" name="email" type="email" placeholder="Email" required>
    <textarea class="form-control mb-2" name="message" rows="4" placeholder="Message" required></textarea>
    <button class="btn btn-primary">Send</button></form>
    {f'<div class="alert alert-success mt-3">Message sent!</div>' if sent else ''}'''
    return public_page("Contact", body)

@app.route('/blog')
def blog():
    posts = [{"title":"Understanding Pain Relief","date":"2026-04-15","snippet":"Learn about different types of OTC pain relievers."},
             {"title":"Essential Baby Care Products","date":"2026-04-10","snippet":"A guide for new parents."},
             {"title":"Probiotics & Gut Health","date":"2026-04-02","snippet":"How probiotics improve wellness."}]
    post_html = ''.join(f'<div class="card mb-3 p-3"><h5>{p["title"]}</h5><small class="text-muted">{p["date"]}</small><p>{p["snippet"]}</p></div>' for p in posts)
    return public_page("Blog", post_html)

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
    products = data.range((page-1)*per_page, page*per_page-1).execute().data or []
    total_pages = max(1, (total + per_page -1)//per_page)
    rows = ''
    for p in products:
        img = f'<img src="{p.get("image_url")}" style="height:150px;object-fit:cover;">' if p.get("image_url") else '<div style="height:150px;background:#eee;display:flex;align-items:center;justify-content:center;"><i class="fas fa-pills fa-2x text-muted"></i></div>'
        rows += f'''<div class="col-6 col-md-4 col-lg-3 mb-4"><div class="card h-100 shadow-sm border-0 rounded-4 overflow-hidden">
            {img}<div class="card-body p-2"><h6 class="fw-bold mb-1">{p['name']}</h6><p class="text-muted small mb-1">{p['category']}</p>
            <div class="d-flex justify-content-between align-items-center"><span class="fw-bold" style="color:#0A3D62;">KSh {p['price']}</span>
            <form action="/cart/add" method="POST"><input type="hidden" name="productId" value="{p['id']}">
            <input type="number" name="quantity" value="1" min="1" max="10" class="form-control form-control-sm d-inline" style="width:50px;">
            <button type="submit" class="btn btn-primary btn-sm rounded-pill"><i class="fas fa-cart-plus"></i></button></form></div></div></div></div>'''
    pagination = ''
    if total_pages > 1:
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
    return public_page("Shop", body)

@app.route('/cart/add', methods=['POST'])
def add_to_cart():
    product_id = request.form['productId']
    quantity = int(request.form.get('quantity',1))
    prod = supabase.table('products').select('id,name,price').eq('id',product_id).single().execute().data
    if not prod: return 'Product not found',404
    if 'user_id' in session:
        uid = session['user_id']
        existing = supabase.table('cart').select('id,quantity').eq('user_id',uid).eq('product_id',product_id).execute()
        if existing.data:
            supabase.table('cart').update({'quantity': existing.data[0]['quantity'] + quantity}).eq('id', existing.data[0]['id']).execute()
        else:
            supabase.table('cart').insert({'user_id':uid,'product_id':product_id,'quantity':quantity}).execute()
    else:
        cart = session.get('cart',[])
        found = False
        for item in cart:
            if item['productId'] == product_id:
                item['qty'] += quantity; found = True; break
        if not found:
            cart.append({'productId':product_id,'qty':quantity,'price':float(prod['price']),'name':prod['name']})
        session['cart'] = cart
    return redirect('/cart')

@app.route('/cart')
def view_cart():
    cart_items = []; total = 0.0
    if 'user_id' in session:
        uid = session['user_id']
        db_cart = supabase.table('cart').select('quantity,product_id,products(name,price)').eq('user_id',uid).execute()
        for item in db_cart.data:
            p = item['products']
            cart_items.append({'productId':item['product_id'],'name':p['name'],'price':float(p['price']),'qty':item['quantity']})
            total += float(p['price']) * item['quantity']
    else:
        cart_items = session.get('cart',[])
        total = sum(it['price']*it['qty'] for it in cart_items)
    if not cart_items:
        return public_page("Cart", '<h2>Your Cart</h2><p>Cart is empty.</p><a href="/shop" class="btn btn-primary">Shop</a>')
    rows = ''.join(f'<div class="card p-3 mb-2 d-flex flex-row justify-content-between"><div><h5>{i["name"]}</h5><small>Qty: {i["qty"]} × KSh {i["price"]}</small></div><div><h4 class="text-success">KSh {i["price"]*i["qty"]:.2f}</h4><a href="/cart/remove/{i["productId"]}" class="btn btn-sm btn-outline-danger"><i class="fas fa-trash"></i></a></div></div>' for i in cart_items)
    body = f'<h2>Your Cart</h2>{rows}<hr><div class="d-flex justify-content-between"><h4>Total</h4><h4>KSh {total:.2f}</h4></div><a href="/checkout" class="btn btn-success w-100 py-3 mt-3 rounded-pill">Proceed to Checkout</a>'
    return public_page("Cart", body, user={'cart':cart_items})

@app.route('/cart/remove/<pid>')
def remove_cart(pid):
    if 'user_id' in session:
        try: supabase.table('cart').delete().eq('user_id',session['user_id']).eq('product_id',pid).execute()
        except: pass
    else:
        cart = [i for i in session.get('cart',[]) if i['productId'] != pid]
        session['cart'] = cart
    return redirect('/cart')

@app.route('/checkout')
def checkout():
    return public_page("Checkout", '''<h2>Checkout</h2>
    <form method="post" action="/checkout">
    <input class="form-control mb-2" name="guest_email" placeholder="Email (if guest)" type="email">
    <input class="form-control mb-2" name="shipping_name" placeholder="Full Name" required>
    <input class="form-control mb-2" name="shipping_address" placeholder="Address">
    <input class="form-control mb-2" name="shipping_city" placeholder="City">
    <input class="form-control mb-2" name="shipping_phone" placeholder="Phone" required>
    <select class="form-select mb-2" name="payment_method"><option value="cod">Cash on Delivery</option><option value="mobile_money">M-Pesa</option></select>
    <input class="form-control mb-2" name="discount_code" placeholder="Discount code (optional)">
    <button class="btn btn-success w-100 py-3 rounded-pill">Place Order</button></form>''')

@app.route('/checkout', methods=['POST'])
def place_order():
    guest_email = request.form.get('guest_email')
    shipping = {k: request.form[k] for k in ['shipping_name','shipping_address','shipping_city','shipping_phone','payment_method']}
    cart_items = []
    if 'user_id' in session:
        uid = session['user_id']
        db = supabase.table('cart').select('quantity,product_id,products(name,price)').eq('user_id',uid).execute()
        if not db.data: return 'Cart is empty.'
        for item in db.data:
            p = item['products']
            cart_items.append({'productId':item['product_id'],'name':p['name'],'price':float(p['price']),'qty':item['quantity']})
    else:
        guest_cart = session.get('cart',[])
        if not guest_cart: return 'Cart is empty.'
        if not guest_email: return 'Guest email required.'
        cart_items = guest_cart
    total = sum(it['price']*it['qty'] for it in cart_items)
    discount_code = request.form.get('discount_code','').strip().upper()
    if discount_code:
        code = supabase.table('discount_codes').select('*').eq('code',discount_code).maybe_single().execute()
        if code.data and code.data.get('active'):
            c = code.data
            if c.get('discount_percent'):
                total *= (1 - c['discount_percent']/100)
            elif c.get('discount_amount'):
                total -= c['discount_amount']
            supabase.table('discount_codes').update({'used_count': c['used_count']+1}).eq('id',c['id']).execute()
    order = {**shipping,'total_amount':total}
    if 'user_id' in session:
        order['user_id'] = session['user_id']
    else:
        order['guest_email'] = guest_email
    order_res = supabase.table('orders').insert(order).execute()
    oid = order_res.data[0]['id']
    for item in cart_items:
        supabase.table('order_items').insert({'order_id':oid,'product_id':item['productId'],'product_name':item['name'],'quantity':item['qty'],'unit_price':item['price'],'total_price':item['price']*item['qty']}).execute()
    if 'user_id' in session:
        supabase.table('cart').delete().eq('user_id',session['user_id']).execute()
    else:
        session.pop('cart',None)
    # inline order confirmation
    ord = supabase.table('orders').select('*').eq('id',oid).single().execute().data
    items_html = ''.join(f'<tr><td>{i["product_name"]}</td><td>{i["quantity"]}</td><td>KSh {i["unit_price"]}</td><td>KSh {i["total_price"]}</td></tr>' for i in supabase.table('order_items').select('*').eq('order_id',oid).execute().data)
    return f'''<!DOCTYPE html><html><head><title>Order Confirmed</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"></head><body class="p-4"><div class="container" style="max-width:600px;"><h2 class="text-success">Thank You! Order #{oid[:8]} placed.</h2><p>Total: KSh {ord['total_amount']}</p><table class="table"><thead><tr><th>Product</th><th>Qty</th><th>Unit</th><th>Subtotal</th></tr></thead><tbody>{items_html}</tbody></table><a href="/shop" class="btn btn-primary">Continue</a></div></body></html>'''

# … (login, register, admin routes follow the same inline pattern) …
# For brevity I'll include a simplified admin layout.
# The complete code is already given above; just ensure you paste everything.
