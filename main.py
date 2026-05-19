import os, json, bcrypt, csv, io, struct, zlib, html
from datetime import datetime, timedelta
from functools import wraps
from flask import (
    Flask,
    request,
    redirect,
    session,
    Response,
    make_response,
)
from supabase import create_client, Client
from werkzeug.utils import secure_filename
from flask_wtf.csrf import CSRFProtect, generate_csrf
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# ---------- XSS helper ----------
def e(value):
    """Escape HTML special characters to prevent XSS."""
    return html.escape(str(value)) if value is not None else ''

# ---------- App initialisation ----------
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'mediocare-secret')
app.config['WTF_CSRF_ENABLED'] = True
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5 MB max upload

csrf = CSRFProtect(app)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
)

SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    print("\n❌ ERROR: Environment variables SUPABASE_URL and SUPABASE_KEY must be set!\n")
    print("   export SUPABASE_URL=https://your-project.supabase.co")
    print("   export SUPABASE_KEY=your-anon-key\n")
    raise RuntimeError("Supabase credentials missing.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

PHARMACY_NAME = "Mediocare"
PHARMACY_PHONE = "+254792524333"
PHARMACY_EMAIL = "info@mediocare.co.ke"

# ---------- Public Page Template (CSS is now external) ----------
def public_page(title, body, user=None):
    cart_total = 0.0
    if user and session.get('user_id'):
        try:
            uid = session['user_id']
            resp = supabase.table('cart').select('quantity, products(price)').eq('user_id', uid).execute()
            for it in resp.data:
                cart_total += float(it['products']['price']) * it['quantity']
        except: pass
    else:
        guest_cart = session.get('cart', [])
        cart_total = sum(it['price'] * it['qty'] for it in guest_cart)

    links = [
        ('/', 'Home', 'fa-home'),
        ('/shop', 'Shop', 'fa-store'),
        ('/prescription', 'Rx', 'fa-file-prescription'),
        ('/branches', 'Branches', 'fa-map-marker-alt'),
        ('/wishlist', 'Wishlist', 'fa-heart'),
        ('/cart', f'Cart {int(cart_total)}', 'fa-shopping-cart'),
        ('/reminders', 'Reminders', 'fa-bell'),
        ('/symptom-checker', 'Symptom', 'fa-stethoscope')
    ]
    if user:
        links.append(('/my-account', 'Orders', 'fa-box'))
        if user.get('is_admin'): links.append(('/admin', 'Admin', 'fa-tachometer-alt'))
        links.append(('/logout', 'Logout', 'fa-sign-out-alt'))
    else:
        links.append(('/login', 'Login', 'fa-sign-in-alt'))
        links.append(('/register', 'Register', 'fa-user-plus'))

    nav_links_html = ''.join(f'<a class="nav-link" href="{e(url)}"><i class="fas {e(icon)}"></i>{e(label)}</a>' for url, label, icon in links)
    nav = f'''<nav class="navbar navbar-public sticky-top"><div class="container d-flex align-items-center">
        <a class="navbar-brand d-flex align-items-center" href="/" style="text-decoration:none;">
            <span class="brand-logo"><i class="fas fa-plus"></i></span>
            <div class="brand-text">
                <span class="brand-name">{e(PHARMACY_NAME)}</span>
                <span class="brand-sub">PHARMACY LTD</span>
            </div>
        </a>
        <div class="public-nav-links ms-auto">{nav_links_html}</div>
    </div></nav>'''

    # Toast message via meta tag (safer)
    toast_meta = ""
    if request.args.get('toast'):
        toast_meta = f'<meta name="toast-message" content="{e(request.args.get("toast"))}">'

    return f"""<!DOCTYPE html><html><head><title>{e(title)} – {e(PHARMACY_NAME)}</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<link rel="stylesheet" href="/static/style.css">
{toast_meta}
</head><body>
{nav}
{body}
<a href="https://wa.me/{e(PHARMACY_PHONE)}?text=Hello%20Mediocare" class="whatsapp-float" target="_blank"><i class="fab fa-whatsapp"></i></a>
<div class="toast-container" id="toastContainer"></div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script src="/static/app.js"></script>
</body></html>"""

# ---------- Admin Page Template (CSS is now external) ----------
def admin_page(title, body, active='dashboard'):
    links = [
        ('dashboard','fa-tachometer-alt','/admin'),
        ('orders','fa-shopping-cart','/admin/orders'),
        ('products','fa-pills','/admin/products'),
        ('prescriptions','fa-file-prescription','/admin/prescriptions'),
        ('customers','fa-users','/admin/customers'),
        ('users','fa-headset','/admin/users'),
        ('create-user','fa-user-plus','/admin/create-user'),
        ('discounts','fa-tags','/admin/discounts'),
        ('bundles','fa-boxes','/admin/bundles'),
        ('analytics','fa-chart-bar','/admin/analytics'),
        ('settings','fa-cog','/admin/settings'),
        ('branches','fa-map-marker-alt','/admin/branches'),
        ('symptoms','fa-heartbeat','/admin/symptoms'),
        ('export','fa-download','/admin/export-orders')
    ]

    sidebar_html = '<div class="admin-sidebar d-none d-md-flex flex-column">'
    sidebar_html += f'''
    <div class="admin-brand" style="display:flex; align-items:center; margin-bottom:2rem;">
        <span class="admin-brand-logo" style="display:flex; align-items:center; justify-content:center; width:44px; height:44px; background:white; border-radius:50%; margin-right:12px; color:#0A3D62; font-size:1.6rem; font-weight:bold; box-shadow:0 2px 8px rgba(0,0,0,0.1);"><i class="fas fa-plus"></i></span>
        <div style="display:flex; flex-direction:column; line-height:1.2;">
            <span style="font-weight:800; font-size:1.5rem; color:white;">{e(PHARMACY_NAME)}</span>
            <span style="font-size:0.65rem; font-weight:700; letter-spacing:2px; color:rgba(255,255,255,0.85); text-transform:uppercase;">PHARMACY LTD</span>
        </div>
    </div>'''
    for name, icon, url in links:
        active_class = 'active' if name == active else ''
        sidebar_html += f'<a href="{e(url)}" class="{e(active_class)}"><i class="fas {e(icon)}"></i> {e(name.replace("-"," ").title())}</a>'
    sidebar_html += '<hr style="border-color:rgba(255,255,255,0.2); margin-top:auto;">'
    sidebar_html += '<a href="/" class="btn-view">🏠 View Site</a>'
    sidebar_html += '<a href="/logout" class="btn-logout">🚪 Logout</a>'
    sidebar_html += '</div>'

    mobile_links = ''
    for name, icon, url in links:
        active_class = 'active' if name == active else ''
        mobile_links += f'<a href="{e(url)}" class="{e(active_class)}"><i class="fas {e(icon)}"></i> {e(name.replace("-"," ").title())}</a>'
    mobile_bar = f'<div class="admin-mobile-nav d-md-none">{mobile_links}</div>'

    return f"""<!DOCTYPE html>
<html>
<head>
    <title>{e(title)} – Admin</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link rel="stylesheet" href="/static/style.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
</head>
<body style="display:flex; flex-direction:column;">
    {sidebar_html}
    {mobile_bar}
    <div class="main-admin">
        <h2>{e(title)}</h2>
        <hr>{body}
    </div>
</body>
</html>"""

# ---------- CSRF Helper ----------
def csrf_field():
    return f'<input type="hidden" name="csrf_token" value="{generate_csrf()}">'

# ---------- Password Strength ----------
def is_password_strong(password):
    if len(password) < 8: return False
    if not any(c.isupper() for c in password): return False
    if not any(c.islower() for c in password): return False
    if not any(c.isdigit() for c in password): return False
    return True

# ---------- Frequently Bought Together ----------
def get_frequently_bought_together(product_id, limit=4):
    orders_with_product = supabase.table('order_items').select('order_id').eq('product_id', product_id).execute().data
    if not orders_with_product:
        return []
    order_ids = list(set([o['order_id'] for o in orders_with_product]))
    if not order_ids:
        return []
    all_items = supabase.table('order_items').select('product_id').in_('order_id', order_ids).execute().data
    product_counts = {}
    for item in all_items:
        pid = item['product_id']
        if pid == product_id:
            continue
        product_counts[pid] = product_counts.get(pid, 0) + 1
    sorted_pids = sorted(product_counts, key=product_counts.get, reverse=True)[:limit]
    if not sorted_pids:
        return []
    return supabase.table('products').select('id,name,price,image_url').in_('id', sorted_pids).execute().data

# ---------- ROUTES ----------

@app.route('/login', methods=['GET','POST'])
@limiter.limit("5 per minute")
def login():
    if request.method=='POST':
        email=request.form['email']; pwd=request.form['password']
        user_res=supabase.table('users').select('*').eq('email',email).execute()
        if not user_res.data:
            return public_page("Login",'<div class="alert alert-danger">Invalid credentials</div><a href="/login">Try again</a>')
        user=user_res.data[0]
        if not bcrypt.checkpw(pwd.encode(),user['password_hash'].encode()):
            return public_page("Login",'<div class="alert alert-danger">Invalid credentials</div><a href="/login">Try again</a>')
        session['user_id']=user['id']; session['user_name']=user['full_name']; session['is_admin']=user.get('is_admin',False)
        return redirect('/?toast=Login successful')
    form = f"""<div class="row justify-content-center mt-5"><div class="col-md-5 col-lg-4"><div class="card shadow-lg rounded-4 p-4"><div class="text-center mb-4"><i class="fas fa-pills fa-3x text-primary"></i><h3 class="fw-bold mt-2">Welcome Back</h3><p class="text-muted">Sign in to your account</p></div>
    <form method="post">{csrf_field()}<div class="mb-3"><input class="form-control" name="email" type="email" placeholder="Email" required></div>
    <div class="mb-3"><div class="input-group"><input class="form-control" name="password" type="password" id="loginPassword" placeholder="Password" required><span class="input-group-text toggle-password" data-target="loginPassword"><i class="far fa-eye"></i></span></div></div>
    <button class="btn btn-primary w-100 py-2 rounded-pill">Sign In</button></form><p class="mt-3 text-center"><a href="/register">Create an account</a> · <a href="/">Home</a></p></div></div></div>"""
    return public_page("Login", form)

@app.route('/register', methods=['GET','POST'])
@limiter.limit("3 per minute")
def register():
    if request.method=='POST':
        name=request.form['full_name']; email=request.form['email']; pwd=request.form['password']
        if not is_password_strong(pwd):
            return public_page("Register",'<div class="alert alert-danger">Password must be at least 8 characters with uppercase, lowercase and a number.</div><a href="/register">Try again</a>')
        hashed=bcrypt.hashpw(pwd.encode(),bcrypt.gensalt()).decode()
        try:
            supabase.table('users').insert({'full_name':name,'email':email,'password_hash':hashed}).execute()
        except:
            return public_page("Register",'<div class="alert alert-danger">Email already exists.</div><a href="/register">Try again</a>')
        return public_page("Registration Submitted",'<div class="text-center mt-5"><i class="fas fa-check-circle fa-5x text-success mb-3"></i><h2>Account Created</h2><p>Your account is pending approval.</p><a href="/" class="btn btn-primary rounded-pill mt-3">Home</a></div>')
    form = f"""<div class="row justify-content-center mt-5"><div class="col-md-5 col-lg-4"><div class="card shadow-lg rounded-4 p-4"><div class="text-center mb-4"><i class="fas fa-user-plus fa-3x text-primary"></i><h3 class="fw-bold mt-2">Create Account</h3></div>
    <form method="post">{csrf_field()}<div class="mb-3"><input class="form-control" name="full_name" placeholder="Full Name" required></div>
    <div class="mb-3"><input class="form-control" name="email" type="email" placeholder="Email" required></div>
    <div class="mb-3"><div class="input-group"><input class="form-control" name="password" type="password" id="registerPassword" placeholder="Password (min. 8 chars, A-z, 0-9)" required><span class="input-group-text toggle-password" data-target="registerPassword"><i class="far fa-eye"></i></span></div></div>
    <button class="btn btn-primary w-100 py-2 rounded-pill">Register</button></form><p class="mt-3 text-center"><a href="/login">Already have an account?</a></p></div></div></div>"""
    return public_page("Register", form)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/?toast=Logged out')

# ---------- Home Page ----------
@app.route('/')
def home():
    try:
        featured = supabase.table('products').select('id,name,price,image_url').eq('active',True).limit(4).execute().data or []
    except:
        featured = []
    try: total_orders = supabase.table('orders').select('count', count='exact').execute().count
    except: total_orders = 0
    try: total_products = supabase.table('products').select('count', count='exact').execute().count
    except: total_products = 0
    try: total_branches = supabase.table('branches').select('count', count='exact').execute().count
    except: total_branches = 0

    featured_html = ''
    if featured:
        for p in featured:
            img = f'<img src="{e(p.get("image_url"))}" class="card-img-top" style="height:160px; object-fit:cover; border-radius:15px 15px 0 0;">' if p.get('image_url') else '<div class="bg-light d-flex align-items-center justify-content-center" style="height:160px; border-radius:15px 15px 0 0;"><i class="fas fa-pills fa-3x text-muted"></i></div>'
            featured_html += f'''<div class="col-md-3 mb-4"><div class="card h-100 border-0 shadow-sm rounded-4 overflow-hidden">{img}<div class="card-body text-center"><h5 class="fw-bold">{e(p['name'])}</h5><p class="text-success fw-bold mb-2">KSh {e(p['price'])}</p><a href="/shop" class="btn btn-outline-primary btn-sm rounded-pill">View</a></div></div></div>'''
    else:
        featured_html = '<div class="col-12 text-center"><p class="text-muted">No products yet. <a href="/shop">Start shopping</a></p></div>'

    if session.get('user_id'):
        quick_links = '''
        <div class="d-md-none mt-4">
            <h5 class="text-center mb-3 fw-bold">Quick Links</h5>
            <div class="row g-3 text-center">
                <div class="col-4"><a href="/shop" class="card p-3 text-decoration-none h-100 shadow-sm rounded-4"><i class="fas fa-store fa-2x text-primary"></i><div class="mt-2 fw-bold small">Shop</div></a></div>
                <div class="col-4"><a href="/prescription" class="card p-3 text-decoration-none h-100 shadow-sm rounded-4"><i class="fas fa-file-prescription fa-2x text-primary"></i><div class="mt-2 fw-bold small">Rx</div></a></div>
                <div class="col-4"><a href="/branches" class="card p-3 text-decoration-none h-100 shadow-sm rounded-4"><i class="fas fa-map-marker-alt fa-2x text-primary"></i><div class="mt-2 fw-bold small">Branches</div></a></div>
                <div class="col-4"><a href="/cart" class="card p-3 text-decoration-none h-100 shadow-sm rounded-4"><i class="fas fa-shopping-cart fa-2x text-primary"></i><div class="mt-2 fw-bold small">Cart</div></a></div>
                <div class="col-4"><a href="/my-account" class="card p-3 text-decoration-none h-100 shadow-sm rounded-4"><i class="fas fa-box fa-2x text-primary"></i><div class="mt-2 fw-bold small">Orders</div></a></div>
                <div class="col-4"><a href="/logout" class="card p-3 text-decoration-none h-100 shadow-sm rounded-4"><i class="fas fa-sign-out-alt fa-2x text-danger"></i><div class="mt-2 fw-bold small">Logout</div></a></div>
            </div>
        </div>'''
    else:
        quick_links = '''
        <div class="d-md-none mt-4">
            <h5 class="text-center mb-3 fw-bold">Quick Links</h5>
            <div class="row g-3 text-center">
                <div class="col-4"><a href="/shop" class="card p-3 text-decoration-none h-100 shadow-sm rounded-4"><i class="fas fa-store fa-2x text-primary"></i><div class="mt-2 fw-bold small">Shop</div></a></div>
                <div class="col-4"><a href="/prescription" class="card p-3 text-decoration-none h-100 shadow-sm rounded-4"><i class="fas fa-file-prescription fa-2x text-primary"></i><div class="mt-2 fw-bold small">Rx</div></a></div>
                <div class="col-4"><a href="/branches" class="card p-3 text-decoration-none h-100 shadow-sm rounded-4"><i class="fas fa-map-marker-alt fa-2x text-primary"></i><div class="mt-2 fw-bold small">Branches</div></a></div>
                <div class="col-4"><a href="/cart" class="card p-3 text-decoration-none h-100 shadow-sm rounded-4"><i class="fas fa-shopping-cart fa-2x text-primary"></i><div class="mt-2 fw-bold small">Cart</div></a></div>
                <div class="col-4"><a href="/login" class="card p-3 text-decoration-none h-100 shadow-sm rounded-4"><i class="fas fa-sign-in-alt fa-2x text-primary"></i><div class="mt-2 fw-bold small">Login</div></a></div>
                <div class="col-4"><a href="/register" class="card p-3 text-decoration-none h-100 shadow-sm rounded-4"><i class="fas fa-user-plus fa-2x text-primary"></i><div class="mt-2 fw-bold small">Register</div></a></div>
            </div>
        </div>'''

    body = f"""
    <div class="hero">
        <div class="hero-bg-animation">
            <div class="circle"></div><div class="circle"></div><div class="circle"></div>
        </div>
        <div class="position-relative" style="z-index:1;">
            <h1 class="fw-bold mb-3">Your Health,<br>Delivered with Care.</h1>
            <p class="lead mb-4">Genuine human & veterinary medicines, supplements, and personal care products – delivered quickly to your doorstep anywhere in Kenya.</p>
            <div class="btn-group">
                <a href="/shop" class="btn btn-white btn-lg">Explore Products</a>
                <a href="/prescription" class="btn btn-outline-white btn-lg">Upload Prescription</a>
            </div>
        </div>
    </div>

    <div class="container py-5">
        <div class="row g-4">
            <div class="col-6 col-md-3 counter-item"><div class="number">{total_orders}</div><div class="label">Orders Delivered</div></div>
            <div class="col-6 col-md-3 counter-item"><div class="number">{total_products}</div><div class="label">Quality Products</div></div>
            <div class="col-6 col-md-3 counter-item"><div class="number">{total_branches}</div><div class="label">Branches Nationwide</div></div>
            <div class="col-6 col-md-3 counter-item"><div class="number">24/7</div><div class="label">Expert Support</div></div>
        </div>
    </div>

    <div class="container py-5 text-center">
        <h2 class="fw-bold mb-2" style="color: var(--blue);">How Mediocare Works</h2>
        <p class="text-muted mb-5">Three simple steps to better health.</p>
        <div class="row g-4">
            <div class="col-md-4"><div class="step-card"><div class="step-icon"><i class="fas fa-search"></i></div><h5>1. Find Your Medicine</h5><p class="text-muted">Browse our wide catalog or use the search to locate exactly what you need.</p></div></div>
            <div class="col-md-4"><div class="step-card"><div class="step-icon"><i class="fas fa-clipboard-check"></i></div><h5>2. Verified & Approved</h5><p class="text-muted">Our pharmacists review every order and prescription for safety and accuracy.</p></div></div>
            <div class="col-md-4"><div class="step-card"><div class="step-icon"><i class="fas fa-truck"></i></div><h5>3. Fast, Discreet Delivery</h5><p class="text-muted">Receive your order at home or pick it up at your nearest branch.</p></div></div>
        </div>
    </div>

    <div class="container py-5 text-center">
        <h2 class="fw-bold mb-2" style="color: var(--blue);">Our Services</h2>
        <p class="text-muted mb-5">Comprehensive pharmaceutical solutions tailored to your needs.</p>
        <div class="row g-4">
            <div class="col-md-4"><div class="service-card"><div class="service-icon"><i class="fas fa-stethoscope"></i></div><h5>Medical Equipment</h5><p>High‑quality hospital and clinic devices from trusted manufacturers.</p></div></div>
            <div class="col-md-4"><div class="service-card"><div class="service-icon"><i class="fas fa-user-md"></i></div><h5>Human Medicine</h5><p>A complete range of pharmaceutical products for everyday health.</p></div></div>
            <div class="col-md-4"><div class="service-card"><div class="service-icon"><i class="fas fa-dog"></i></div><h5>Veterinary Medicine</h5><p>Effective treatments to keep your animals healthy and thriving.</p></div></div>
            <div class="col-md-4"><div class="service-card"><div class="service-icon"><i class="fas fa-flask"></i></div><h5>Laboratory Chemicals</h5><p>Premium reagents and chemicals for reliable diagnostic work.</p></div></div>
            <div class="col-md-4"><div class="service-card"><div class="service-icon"><i class="fas fa-ship"></i></div><h5>Medicine Importation</h5><p>International sourcing of authentic medicines at competitive prices.</p></div></div>
            <div class="col-md-4"><div class="service-card"><div class="service-icon"><i class="fas fa-tractor"></i></div><h5>Farm Inputs</h5><p>Agro‑chemicals and farming essentials to boost your agricultural yield.</p></div></div>
        </div>
    </div>

    <div class="container py-5 text-center">
        <h2 class="fw-bold mb-2" style="color: var(--blue);">Featured Products</h2>
        <p class="text-muted mb-5">Our top‑rated health essentials handpicked for you.</p>
        <div class="row">{featured_html}</div>
    </div>

    <div class="container py-5 text-center">
        <h2 class="fw-bold mb-2" style="color: var(--blue);">Loved by Thousands</h2>
        <p class="text-muted mb-5">Real feedback from our happy customers.</p>
        <div class="row g-4">
            <div class="col-md-4"><div class="testimonial-card"><p class="quote">"Mediocare saved me a trip to the clinic. My prescription was verified and delivered within hours. Truly reliable!"</p><div class="stars"><i class="fas fa-star"></i><i class="fas fa-star"></i><i class="fas fa-star"></i><i class="fas fa-star"></i><i class="fas fa-star"></i></div><strong class="d-block mt-2">– Grace A.</strong></div></div>
            <div class="col-md-4"><div class="testimonial-card"><p class="quote">"I regularly order supplements for my family. The pricing is great and customer service is always helpful."</p><div class="stars"><i class="fas fa-star"></i><i class="fas fa-star"></i><i class="fas fa-star"></i><i class="fas fa-star"></i><i class="fas fa-star-half-alt"></i></div><strong class="d-block mt-2">– Brian O.</strong></div></div>
            <div class="col-md-4"><div class="testimonial-card"><p class="quote">"Very professional. I love how discreet the packaging is. Highly recommended for anyone valuing privacy."</p><div class="stars"><i class="fas fa-star"></i><i class="fas fa-star"></i><i class="fas fa-star"></i><i class="fas fa-star"></i><i class="fas fa-star"></i></div><strong class="d-block mt-2">– Wanjiku M.</strong></div></div>
        </div>
    </div>

    <div class="container py-5">
        <div class="newsletter-box">
            <h2 class="fw-bold mb-3">Stay Healthy with Mediocare</h2>
            <p class="mb-4">Subscribe for exclusive offers, health tips, and new product alerts.</p>
            <form action="/contact" method="POST" class="d-flex justify-content-center flex-wrap">
                {csrf_field()}
                <input type="email" name="email" placeholder="Enter your email" class="mb-2 mb-md-0 me-md-2" required>
                <button type="submit" class="btn">Subscribe</button>
            </form>
        </div>
    </div>

    <footer class="text-center py-4 mt-5" style="background: var(--blue); color: white;">
        <p class="mb-0">&copy; 2026 {e(PHARMACY_NAME)}. All rights reserved. | <i class="fas fa-phone"></i> {e(PHARMACY_PHONE)}</p>
    </footer>

    {quick_links}
    """
    user = None
    if session.get('user_id'):
        user = {'full_name': session.get('user_name', 'User'), 'is_admin': session.get('is_admin', False)}
    return public_page("Home", body, user)

# ---------- Shop ----------
@app.route('/shop')
def shop():
    search = request.args.get('search',''); category = request.args.get('category',''); page = int(request.args.get('page',1))
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
        img = f'<img src="{e(p.get("image_url"))}" class="card-img-top" style="height:180px;object-fit:cover;">' if p.get("image_url") else '<div class="bg-light d-flex align-items-center justify-content-center" style="height:180px;"><i class="fas fa-pills fa-3x text-muted"></i></div>'
        rows += f'''<div class="col-6 col-md-4 mb-4"><div class="card h-100">{img}<div class="card-body"><h5 class="fw-bold">{e(p['name'])}</h5><p class="text-muted small">{e(p['category'])}</p>
        <div class="d-flex justify-content-between align-items-center"><span class="h5" style="color:var(--blue);">KSh {e(p['price'])}</span>
        <div>
            <form action="/cart/add" method="POST" class="d-inline">{csrf_field()}<input type="hidden" name="productId" value="{p['id']}">
            <input type="number" name="quantity" value="1" min="1" class="form-control form-control-sm d-inline-block" style="width:60px;">
            <button class="btn btn-primary btn-sm rounded-pill ms-1"><i class="fas fa-cart-plus"></i></button></form>
            <a href="/product/{p['id']}" class="btn btn-sm btn-outline-primary ms-1"><i class="fas fa-eye"></i></a>
            <form action="/wishlist/add/{p['id']}" method="POST" class="d-inline">
                {csrf_field()}
                <button class="btn btn-sm btn-outline-danger ms-1"><i class="far fa-heart"></i></button>
            </form>
        </div></div></div></div></div>'''

    voice_button = '''<button type="button" class="btn btn-outline-secondary" onclick="startVoiceSearch()" title="Search by voice"><i class="fas fa-microphone"></i></button>'''
    voice_js = '''<script>
    function startVoiceSearch() {
        if (!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
            alert('Voice search not supported in your browser. Please type to search.');
            return;
        }
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        const recognition = new SpeechRecognition();
        recognition.lang = 'en-US';
        recognition.onresult = function(event) {
            document.querySelector('input[name="search"]').value = event.results[0][0].transcript;
            document.querySelector('form.row').submit();
        };
        recognition.start();
    }
    </script>'''

    pagination = ''
    total_pages = max(1, (total+per_page-1)//per_page)
    if total_pages > 1:
        pagination = '<nav><ul class="pagination justify-content-center">'
        for p in range(1, total_pages+1):
            active = 'active' if p == page else ''
            pagination += f'<li class="page-item {active}"><a class="page-link" href="/shop?page={p}&search={e(search)}&category={e(category)}">{p}</a></li>'
        pagination += '</ul></nav>'

    body = f'''<h2 class="fw-bold mb-4" style="color:var(--blue);">Our Products</h2>
    <form class="row g-3 mb-4">
        <div class="col-md-7">
            <div class="input-group">
                <input class="form-control" name="search" value="{e(search)}" placeholder="Search...">
                {voice_button}
            </div>
        </div>
        <div class="col-md-3"><select class="form-select" name="category"><option value="">All</option><option value="Supplements" {'selected' if category=='Supplements' else ''}>Supplements</option><option value="Pain Relief" {'selected' if category=='Pain Relief' else ''}>Pain Relief</option><option value="Baby Care" {'selected' if category=='Baby Care' else ''}>Baby Care</option><option value="Women Health" {'selected' if category=='Women Health' else ''}>Women Health</option></select></div>
        <div class="col-md-2"><button class="btn btn-primary w-100">Filter</button></div>
    </form>
    {voice_js}
    <div class="row">{rows}</div>{pagination}'''
    user = None
    if session.get('user_id'): user = {'full_name': session.get('user_name','User'), 'is_admin': session.get('is_admin', False)}
    return public_page("Shop", body, user)

# ---------- Product Detail & Reviews ----------
@app.route('/product/<int:pid>', methods=['GET','POST'])
def product_detail(pid):
    prod = supabase.table('products').select('*').eq('id',pid).single().execute().data
    if not prod: return "Product not found", 404
    reviews = supabase.table('reviews').select('*, users(full_name)').eq('product_id',pid).order('created_at',desc=True).execute().data or []
    avg_rating = round(sum([r['rating'] for r in reviews]) / len(reviews), 1) if reviews else 0
    if request.method=='POST' and session.get('user_id'):
        rating = int(request.form['rating'])
        comment = request.form.get('comment','')
        supabase.table('reviews').insert({'user_id':session['user_id'],'product_id':pid,'rating':rating,'comment':comment}).execute()
        return redirect(f'/product/{pid}?toast=Review submitted')

    review_html = ''.join(f'''<div class="mb-3"><strong>{e(r.get("users",{}).get("full_name","Anonymous"))}</strong>
    <div class="stars">{''.join('<i class="fas fa-star"></i>' for _ in range(r['rating']))}</div>
    <p>{e(r.get("comment",""))}</p></div>''' for r in reviews)

    fbt_products = get_frequently_bought_together(pid)
    fbt_html = ''
    if fbt_products:
        fbt_items = ''.join(f'''<div class="col-md-6 mb-3">
            <div class="card h-100">
                <div class="card-body text-center">
                    <h5 class="fw-bold">{e(p['name'])}</h5>
                    <p class="text-success">KSh {e(p['price'])}</p>
                    <a href="/product/{p['id']}" class="btn btn-outline-primary btn-sm">View</a>
                </div>
            </div>
        </div>''' for p in fbt_products)
        fbt_html = f'''
        <div class="mt-4">
            <h4 class="fw-bold">Frequently Bought Together</h4>
            <div class="row">{fbt_items}</div>
        </div>'''

    body = f'''
    <h2>{e(prod['name'])}</h2>
    <p>{e(prod.get('description',''))}</p>
    <h4>KSh {e(prod['price'])}</h4>
    <div class="mb-3">Average rating: {avg_rating} ({len(reviews)} reviews)</div>
    {review_html}
    {fbt_html}
    {'<h5>Write a review:</h5><form method="post">'+csrf_field()+'<select name="rating" class="form-select mb-2"><option>5</option><option>4</option><option>3</option><option>2</option><option>1</option></select><textarea name="comment" class="form-control mb-2" placeholder="Comment"></textarea><button class="btn btn-primary">Submit</button></form>' if session.get('user_id') else '<p><a href="/login">Log in</a> to review</p>'}
    <a href="/shop" class="btn btn-outline-primary mt-3">Back to Shop</a>
    '''
    return public_page(prod['name'], body)

# ---------- Wishlist (POST only) ----------
@app.route('/wishlist/add/<int:pid>', methods=['POST'])
def wishlist_add(pid):
    if not session.get('user_id'): return redirect('/login')
    supabase.table('wishlist').upsert({'user_id':session['user_id'],'product_id':pid}).execute()
    return redirect(request.referrer + ('&wishlist_added=1' if '?' in request.referrer else '?wishlist_added=1'))

@app.route('/wishlist/remove/<int:pid>', methods=['POST'])
def wishlist_remove(pid):
    if not session.get('user_id'): return redirect('/login')
    supabase.table('wishlist').delete().eq('user_id',session['user_id']).eq('product_id',pid).execute()
    return redirect(request.referrer or '/wishlist')

@app.route('/wishlist')
def view_wishlist():
    if not session.get('user_id'): return redirect('/login')
    w = supabase.table('wishlist').select('product_id').eq('user_id',session['user_id']).execute().data or []
    if not w: return public_page("Wishlist","<h2>Your Wishlist</h2><p>Wishlist is empty.</p>")
    pids = [x['product_id'] for x in w]
    prods = supabase.table('products').select('*').in_('id',pids).execute().data
    rows = ''.join(f'''<div class="col-md-4 mb-4"><div class="card h-100"><div class="card-body"><h5>{e(p['name'])}</h5><p>KSh {e(p['price'])}</p>
    <form action="/wishlist/remove/{p['id']}" method="POST" class="d-inline">
        {csrf_field()}
        <button class="btn btn-sm btn-outline-danger">Remove</button>
    </form></div></div></div>''' for p in prods)
    return public_page("Wishlist",f'<h2>Your Wishlist</h2><div class="row">{rows}</div>')

# ---------- Cart (POST for remove) ----------
@app.route('/cart/add', methods=['POST'])
def add_to_cart():
    pid = request.form['productId']; qty = int(request.form.get('quantity',1))
    prod = supabase.table('products').select('id,name,price').eq('id',pid).single().execute().data
    if not prod: return "Product not found", 404
    if session.get('user_id'):
        uid = session['user_id']
        ex = supabase.table('cart').select('id,quantity').eq('user_id',uid).eq('product_id',pid).execute()
        if ex.data: supabase.table('cart').update({'quantity':ex.data[0]['quantity']+qty}).eq('id',ex.data[0]['id']).execute()
        else: supabase.table('cart').insert({'user_id':uid,'product_id':pid,'quantity':qty}).execute()
    else:
        cart = session.get('cart',[])
        found = False
        for it in cart:
            if it['productId']==pid: it['qty']+=qty; found=True; break
        if not found: cart.append({'productId':pid,'qty':qty,'price':float(prod['price']),'name':prod['name']})
        session['cart'] = cart
    return redirect(request.referrer + ('&added=1' if '?' in request.referrer else '?added=1'))

@app.route('/cart')
def view_cart():
    items=[]; total=0.0
    if session.get('user_id'):
        uid=session['user_id']
        db=supabase.table('cart').select('quantity,product_id,products(name,price)').eq('user_id',uid).execute()
        for row in db.data:
            p=row['products']
            items.append({'productId':row['product_id'],'name':p['name'],'price':float(p['price']),'qty':row['quantity']})
            total+=float(p['price'])*row['quantity']
    else:
        items=session.get('cart',[])
        total=sum(it['price']*it['qty'] for it in items)
    if not items: return public_page("Cart",'<div class="text-center mt-5"><i class="fas fa-shopping-cart fa-5x text-muted mb-4"></i><h2>Your Cart is Empty</h2><p class="text-muted">Looks like you haven\'t added anything yet.</p><a href="/shop" class="btn btn-primary rounded-pill mt-3">Start Shopping</a></div>')
    rows=''.join(f'''<div class="card p-3 mb-2 d-flex flex-row justify-content-between align-items-center"><div><h5>{e(i["name"])}</h5><small>Qty: {i["qty"]} × KSh {e(i["price"])}</small></div><div><h4 class="text-success">KSh {i["price"]*i["qty"]:.2f}</h4>
    <form action="/cart/remove/{i["productId"]}" method="POST" class="d-inline">
        {csrf_field()}
        <button class="btn btn-sm btn-outline-danger"><i class="fas fa-trash"></i></button>
    </form></div></div>''' for i in items)
    body=f'<h2>Your Cart</h2>{rows}<hr><div class="d-flex justify-content-between"><h4>Total</h4><h4>KSh {total:.2f}</h4></div><a href="/checkout" class="btn btn-success w-100 py-3 mt-3">Proceed to Checkout</a>'
    user = None
    if session.get('user_id'): user = {'full_name':session.get('user_name','User'),'is_admin':session.get('is_admin',False)}
    return public_page("Cart", body, user)

@app.route('/cart/remove/<pid>', methods=['POST'])
def remove_cart(pid):
    if session.get('user_id'):
        supabase.table('cart').delete().eq('user_id',session['user_id']).eq('product_id',pid).execute()
    else:
        cart = [i for i in session.get('cart',[]) if i['productId']!=pid]
        session['cart']=cart
    return redirect('/cart')

# ---------- Checkout ----------
@app.route('/checkout', methods=['GET','POST'])
@limiter.limit("3 per minute")
def checkout():
    if request.method=='POST':
        shipping = {k:request.form[k] for k in ['shipping_name','shipping_address','shipping_city','shipping_phone','payment_method']}
        cart_items = []
        if session.get('user_id'):
            uid=session['user_id']
            db=supabase.table('cart').select('quantity,product_id,products(name,price)').eq('user_id',uid).execute()
            if not db.data: return 'Cart empty.'
            for row in db.data:
                p=row['products']
                cart_items.append({'product_id':row['product_id'],'product_name':p['name'],'quantity':row['quantity'],'unit_price':p['price'],'total_price':float(p['price'])*row['quantity']})
        else:
            guest_cart=session.get('cart',[])
            if not guest_cart: return 'Cart empty.'
            cart_items = [{'product_id':i['productId'],'product_name':i['name'],'quantity':i['qty'],'unit_price':i['price'],'total_price':i['price']*i['qty']} for i in guest_cart]
        total = sum(item['total_price'] for item in cart_items)
        discount_code = request.form.get('discount_code','').strip().upper()
        if discount_code:
            code = supabase.table('discount_codes').select('*').eq('code',discount_code).single().execute()
            if code.data and code.data.get('active'):
                c = code.data
                if c.get('discount_percent'): total *= (1 - c['discount_percent']/100)
                elif c.get('discount_amount'): total -= c['discount_amount']
                supabase.table('discount_codes').update({'used_count':c.get('used_count',0)+1}).eq('id',c['id']).execute()
        order = {**shipping, 'total_amount': total}
        if session.get('user_id'): order['user_id'] = session['user_id']
        else: order['guest_email'] = request.form.get('guest_email','guest@example.com')
        order_res = supabase.table('orders').insert(order).execute()
        oid = order_res.data[0]['id']
        for item in cart_items: supabase.table('order_items').insert({**item,'order_id':oid}).execute()
        if session.get('user_id'): supabase.table('cart').delete().eq('user_id',session['user_id']).execute()
        else: session.pop('cart',None)

        order_data = supabase.table('orders').select('*').eq('id',oid).single().execute().data
        items_data = supabase.table('order_items').select('*').eq('order_id',oid).execute().data
        receipt = f"""<div class="card shadow-lg rounded-4 overflow-hidden mt-4">
            <div class="card-header bg-success text-white text-center py-4" style="background: var(--grad) !important;">
                <h2 class="fw-bold mb-0"><i class="fas fa-check-circle me-2"></i>Order Confirmed</h2>
                <p class="mb-0">Thank you for your purchase!</p>
            </div>
            <div class="card-body p-4">
                <div class="row mb-4">
                    <div class="col-sm-6"><h5>Invoice</h5><p><strong>Order #:</strong> {str(oid)[:8]}<br><strong>Date:</strong> {order_data['created_at'][:10]}<br><strong>Status:</strong> <span class="badge bg-warning text-dark">{e(order_data['order_status'])}</span></p></div>
                    <div class="col-sm-6 text-sm-end"><h5>Customer</h5><p>{e(order_data.get('shipping_name',''))}<br>{e(order_data.get('shipping_phone',''))}<br>{e(order_data.get('shipping_address',''))}, {e(order_data.get('shipping_city',''))}</p></div>
                </div>
                <table class="table table-bordered">
                    <thead class="table-light"><tr><th>Product</th><th>Qty</th><th>Unit Price</th><th>Total</th></tr></thead>
                    <tbody>{"".join(f'<tr><td>{e(i["product_name"])}</td><td>{i["quantity"]}</td><td>KSh {e(i["unit_price"])}</td><td>KSh {i["total_price"]}</td></tr>' for i in items_data)}</tbody>
                    <tfoot><tr class="fw-bold"><td colspan="3" class="text-end">Grand Total</td><td>KSh {order_data['total_amount']}</td></tr></tfoot>
                </table>
                <div class="text-center mt-3 no-print">
                    <button onclick="window.print()" class="btn btn-primary rounded-pill px-4"><i class="fas fa-print me-2"></i> Print Receipt</button>
                    <a href="/download-receipt/{oid}" class="btn btn-outline-primary rounded-pill px-4 ms-2"><i class="fas fa-download me-2"></i> Download Receipt</a>
                    <a href="/shop" class="btn btn-outline-primary rounded-pill px-4 ms-2">Continue Shopping</a>
                </div>
            </div>
        </div>"""
        return public_page("Order Confirmed", receipt)
    return public_page("Checkout",f'''<h2>Checkout</h2><form method="post" style="max-width:500px;">
    {csrf_field()}
    <input class="form-control mb-2" name="guest_email" type="email" placeholder="Email (if guest)">
    <input class="form-control mb-2" name="shipping_name" placeholder="Full Name" required>
    <input class="form-control mb-2" name="shipping_address" placeholder="Address">
    <input class="form-control mb-2" name="shipping_city" placeholder="City">
    <input class="form-control mb-2" name="shipping_phone" placeholder="Phone" required>
    <select class="form-select mb-2" name="payment_method"><option value="cod">Cash on Delivery</option><option value="mobile_money">M-Pesa</option></select>
    <input class="form-control mb-2" name="discount_code" placeholder="Discount Code">
    <button class="btn btn-success w-100 py-3">Place Order</button></form>''')

@app.route('/download-receipt/<int:oid>')
def download_receipt(oid):
    order = supabase.table('orders').select('*').eq('id',oid).single().execute().data
    items = supabase.table('order_items').select('*').eq('order_id',oid).execute().data or []
    if not order: return "Order not found", 404
    item_rows = ''.join(f'<tr><td>{e(i["product_name"])}</td><td>{i["quantity"]}</td><td>KSh {e(i["unit_price"])}</td><td>KSh {i["total_price"]}</td></tr>' for i in items)
    html = f"""<!DOCTYPE html><html><head><title>Receipt #{oid}</title>
    <style>body{{font-family:'Segoe UI',sans-serif;padding:2rem;}} table{{width:100%;border-collapse:collapse;}} th,td{{padding:10px;border:1px solid #ddd;}} th{{background:#0A3D62;color:white;}} .total-row td{{font-weight:bold;}}</style></head><body>
    <h2>{e(PHARMACY_NAME)} - Receipt #{oid}</h2>
    <p><strong>Date:</strong> {order['created_at'][:10]}<br><strong>Customer:</strong> {e(order.get('shipping_name',''))}</p>
    <table><thead><tr><th>Product</th><th>Qty</th><th>Unit Price</th><th>Total</th></tr></thead><tbody>{item_rows}</tbody><tfoot><tr class="total-row"><td colspan="3" class="text-end">Grand Total</td><td>KSh {order['total_amount']}</td></tr></tfoot></table>
    </body></html>"""
    resp = make_response(html)
    resp.headers['Content-Disposition'] = f'attachment; filename="receipt_{oid}.html"'
    resp.headers['Content-Type'] = 'text/html'
    return resp

# ---------- Prescription upload ----------
@app.route('/prescription', methods=['GET','POST'])
def prescription_upload():
    if request.method == 'POST':
        file = request.files.get('prescription_file')
        if file and file.filename:
            if file.content_length and file.content_length > 5*1024*1024:
                return "File too large. Max 5MB.", 413
            allowed_mime = ['image/jpeg','image/png','application/pdf']
            if file.content_type not in allowed_mime:
                return "Only JPEG, PNG, PDF allowed.", 400
        try:
            name = request.form['customer_name']
            phone = request.form['customer_phone']
            notes = request.form.get('notes', '')
            file = request.files.get('prescription_file')
            file_url = None
            if file and file.filename:
                fname = secure_filename(file.filename)
                uname = f"rx_{os.urandom(4).hex()}_{fname}"
                supabase.storage.from_("product-images").upload(uname, file.read(), {"content-type": file.content_type})
                file_url = f"{SUPABASE_URL}/storage/v1/object/public/product-images/{uname}"
            supabase.table('prescriptions').insert({
                'customer_name': name,
                'customer_phone': phone,
                'notes': notes,
                'file_url': file_url,
                'status': 'pending'
            }).execute()
            return public_page("Prescription Received",
                '<div class="text-center mt-5"><i class="fas fa-check-circle fa-5x text-success mb-3"></i><h2>Thank You!</h2><p>Your prescription has been submitted.</p><a href="/" class="btn btn-primary rounded-pill mt-3">Back to Home</a></div>')
        except Exception as ex:
            return public_page("Upload Error",
                f'<div class="alert alert-danger mt-5"><h4>Upload Failed</h4><p>{e(str(ex))}</p></div><a href="/prescription">Try again</a>')
    return public_page("Upload Prescription", f'''<div class="row justify-content-center mt-5"><div class="col-md-6 col-lg-5"><div class="card shadow-lg rounded-4 p-4"><div class="text-center mb-4"><i class="fas fa-file-prescription fa-3x text-primary"></i><h3 class="fw-bold mt-2">Upload Prescription</h3></div>
    <form method="post" enctype="multipart/form-data">
    {csrf_field()}
    <div class="mb-3"><input class="form-control" name="customer_name" placeholder="Your Name" required></div>
    <div class="mb-3"><input class="form-control" name="customer_phone" placeholder="Phone Number" required></div>
    <div class="mb-3"><textarea class="form-control" name="notes" rows="3" placeholder="Additional notes (optional)"></textarea></div>
    <div class="mb-3"><input class="form-control" type="file" name="prescription_file" accept="image/*,.pdf" required></div>
    <button class="btn btn-primary w-100 py-2 rounded-pill">Submit Prescription</button></form></div></div></div>''')

# ---------- Public Branches page with Map ----------
@app.route('/branches')
def branches():
    branches = supabase.table('branches').select('*').order('name').execute().data or []
    map_lat = -1.2921
    map_lng = 36.8219
    if branches and branches[0].get('latitude') and branches[0].get('longitude'):
        map_lat = float(branches[0]['latitude'])
        map_lng = float(branches[0]['longitude'])

    markers_js = ''
    for b in branches:
        if b.get('latitude') is not None and b.get('longitude') is not None:
            popup = f"<b>{e(b['name'])}</b><br>{e(b.get('address',''))}<br>{e(b.get('phone',''))}"
            markers_js += f"L.marker([{b['latitude']}, {b['longitude']}]).addTo(map).bindPopup({json.dumps(popup)});\n"

    branch_cards = ''.join(f'''<div class="col-md-6 col-lg-4 mb-4">
            <div class="card h-100 shadow-sm border-0 rounded-4">
                <div class="card-body">
                    <h5 class="fw-bold"><i class="fas fa-map-marker-alt text-danger me-2"></i>{e(b['name'])}</h5>
                    <p class="mb-1"><i class="fas fa-map-pin me-2 text-muted"></i>{e(b.get('address',''))}</p>
                    <p class="mb-0"><i class="fas fa-phone me-2 text-muted"></i>{e(b.get('phone',''))}</p>
                </div>
            </div>
        </div>''' for b in branches)

    body = f'''
    <h2 class="mb-4 fw-bold" style="color:var(--blue);"><i class="fas fa-map-marked-alt me-2"></i>Find Us – Our Branches</h2>
    <div id="map" style="height:400px; border-radius:16px; margin-bottom:2rem;"></div>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        var map = L.map('map').setView([{map_lat}, {map_lng}], 13);
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            maxZoom: 19,
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        }}).addTo(map);
        {markers_js}
    </script>
    <div class="row">{branch_cards}</div>
    '''
    return public_page("Branches", body)

# ---------- About, Contact ----------
@app.route('/about')
def about(): return public_page("About",f'<h2>About {e(PHARMACY_NAME)}</h2><p>Your trusted online pharmacy since 2026.</p>')

@app.route('/contact', methods=['GET','POST'])
def contact():
    if request.method=='POST':
        try: supabase.table('inquiries').insert({k:request.form[k] for k in ['name','email','message']}).execute()
        except: pass
        return redirect('/contact?sent=1')
    sent = 'Message sent!' if request.args.get('sent') else ''
    return public_page("Contact",f'<h2>Contact</h2><form method="post">{csrf_field()}<input class="form-control mb-2" name="name" placeholder="Name"><input class="form-control mb-2" name="email" type="email" placeholder="Email"><textarea class="form-control mb-2" name="message" rows="4" placeholder="Message"></textarea><button class="btn btn-primary">Send</button></form>{e(sent)}')

# ---------- My Account (with POST refill) ----------
@app.route('/my-account')
def my_account():
    if not session.get('user_id'): return redirect('/login')
    orders = supabase.table('orders').select('*').eq('user_id',session['user_id']).order('created_at',desc=True).execute().data or []
    html=''.join(f'''<div class="card mb-3 shadow-sm"><div class="card-body"><strong><a href="/order/{o["id"]}">Order #{str(o["id"])[:8]}</a></strong><br><small>{o["created_at"][:10]}</small><br>Total: KSh {o["total_amount"]}<br><span class="badge bg-info">{e(o.get("order_status",""))}</span>
    <form action="/refill/{o['id']}" method="POST" class="d-inline">
        {csrf_field()}
        <button class="btn btn-sm btn-outline-primary">Refill</button>
    </form></div></div>''' for o in orders)
    user={'full_name':session.get('user_name','User'),'is_admin':session.get('is_admin',False)}
    return public_page("My Orders",f'<h2 class="mb-4">My Orders</h2>{html or "<p>No orders yet.</p>"}',user)

# ---------- Order Tracking (Customer) ----------
@app.route('/order/<int:oid>')
def customer_order_detail(oid):
    if not session.get('user_id'): return redirect('/login')
    order = supabase.table('orders').select('*').eq('id', oid).single().execute().data
    if not order or order.get('user_id') != session['user_id']: return "Order not found", 404
    items = supabase.table('order_items').select('*').eq('order_id', oid).execute().data or []

    status_steps = [
        {'key': 'pending', 'label': 'Order Received', 'icon': 'fas fa-receipt'},
        {'key': 'confirmed', 'label': 'Confirmed', 'icon': 'fas fa-check-circle'},
        {'key': 'shipped', 'label': 'Shipped', 'icon': 'fas fa-truck'},
        {'key': 'delivered', 'label': 'Delivered', 'icon': 'fas fa-box'},
    ]
    current_status = order.get('order_status', 'pending')
    timeline_html = ''
    for step in status_steps:
        if step['key'] == current_status or status_steps.index(step) < status_steps.index(next(s for s in status_steps if s['key'] == current_status)):
            state = 'completed' if step['key'] == current_status else 'active'
        else:
            state = 'upcoming'
        timeline_html += f'''<div class="d-flex align-items-center mb-3">
            <span class="badge rounded-pill p-2 me-2 {'bg-success' if state == 'completed' else 'bg-primary' if state == 'active' else 'bg-light text-muted'}">
                <i class="{step['icon']}"></i>
            </span>
            <span class="{'fw-bold' if state == 'active' else ''}">{step['label']}</span>
        </div>'''
    items_html = ''.join(f'<tr><td>{e(i["product_name"])}</td><td>{i["quantity"]}</td><td>KSh {e(i["unit_price"])}</td><td>KSh {i["total_price"]}</td></tr>' for i in items)

    body = f'''
    <h2>Order #{str(oid)[:8]}</h2>
    <div class="row mt-4">
        <div class="col-md-4"><div class="card p-4 shadow-sm rounded-4"><h5 class="fw-bold">Status Timeline</h5>{timeline_html}</div></div>
        <div class="col-md-8">
            <div class="card p-4 shadow-sm rounded-4">
                <h5 class="fw-bold">Order Details</h5>
                <p><strong>Date:</strong> {order['created_at'][:10]}<br>
                <strong>Shipping Address:</strong> {e(order.get('shipping_address',''))}, {e(order.get('shipping_city',''))}<br>
                <strong>Phone:</strong> {e(order.get('shipping_phone',''))}<br>
                <strong>Payment:</strong> {e(order.get('payment_method',''))}</p>
                <div class="table-responsive"><table class="table"><thead><tr><th>Product</th><th>Qty</th><th>Unit Price</th><th>Total</th></tr></thead><tbody>{items_html}</tbody></table></div>
                <div class="text-end fw-bold">Total: KSh {order['total_amount']}</div>
                <a href="/invoice/{oid}" target="_blank" class="btn btn-outline-primary mt-3"><i class="fas fa-print me-2"></i>Download Invoice</a>
            </div>
        </div>
    </div>'''
    return public_page("Order Details", body)

# ---------- Printable Invoice (Customer) ----------
@app.route('/invoice/<int:oid>')
def customer_invoice(oid):
    if not session.get('user_id'): return redirect('/login')
    order = supabase.table('orders').select('*').eq('id', oid).single().execute().data
    if not order or order.get('user_id') != session['user_id']: return "Order not found", 404
    items = supabase.table('order_items').select('*').eq('order_id', oid).execute().data or []
    item_rows = ''.join(f'<tr><td>{e(i["product_name"])}</td><td>{i["quantity"]}</td><td>KSh {e(i["unit_price"])}</td><td>KSh {i["total_price"]}</td></tr>' for i in items)
    html = f"""<!DOCTYPE html><html><head><title>Invoice #{oid}</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>body{{font-family:'Segoe UI',sans-serif;padding:2rem;}} .invoice-box{{max-width:800px;margin:auto;border:1px solid #eee;box-shadow:0 0 10px rgba(0,0,0,0.05);padding:2rem;}} .logo{{font-weight:800;font-size:1.8rem;color:#0A3D62;}} .logo span{{color:#F4A261}} table{{width:100%;border-collapse:collapse;}} th{{background:#0A3D62;color:white;padding:10px;}} td{{padding:10px;border-bottom:1px solid #ddd;}} .total-row td{{font-weight:bold;border-top:2px solid #0A3D62;}}</style></head><body>
<div class="invoice-box">
    <div class="d-flex justify-content-between"><div class="logo">{e(PHARMACY_NAME)} <span>Pharmacy</span></div><div><h5>INVOICE</h5><p>#{oid}<br>{order['created_at'][:10]}</p></div></div>
    <div class="row"><div class="col-6"><strong>From:</strong><br>{e(PHARMACY_NAME)} Pharmacy Ltd<br>Mombasa Road, Taji Mall, Nairobi<br>Tel: {e(PHARMACY_PHONE)}</div><div class="col-6 text-end"><strong>Bill To:</strong><br>{e(order.get('shipping_name',''))}<br>{e(order.get('shipping_phone',''))}<br>{e(order.get('shipping_address',''))}, {e(order.get('shipping_city',''))}</div></div>
    <table class="mt-3"><thead><tr><th>Product</th><th>Qty</th><th>Unit Price</th><th>Total</th></tr></thead><tbody>{item_rows}</tbody><tfoot><tr class="total-row"><td colspan="3" class="text-end">Grand Total</td><td>KSh {order['total_amount']}</td></tr></tfoot></table>
    <p class="mt-3">Thank you for choosing {e(PHARMACY_NAME)}!</p>
</div><script>window.print();</script></body></html>"""
    return html

# ---------- Refill Order (POST only) ----------
@app.route('/refill/<int:oid>', methods=['POST'])
def refill_order(oid):
    if not session.get('user_id'):
        return redirect('/login')
    order = supabase.table('orders').select('*').eq('id', oid).single().execute().data
    if not order or order.get('user_id') != session['user_id']:
        return "Order not found", 404
    items = supabase.table('order_items').select('*').eq('order_id', oid).execute().data or []
    for item in items:
        pid = item['product_id']
        qty = item['quantity']
        ex = supabase.table('cart').select('id,quantity').eq('user_id', session['user_id']).eq('product_id', pid).execute()
        if ex.data:
            supabase.table('cart').update({'quantity': ex.data[0]['quantity'] + qty}).eq('id', ex.data[0]['id']).execute()
        else:
            supabase.table('cart').insert({'user_id': session['user_id'], 'product_id': pid, 'quantity': qty}).execute()
    return redirect('/cart?toast=Order refilled')

# ---------- Medicine Reminders ----------
@app.route('/reminders', methods=['GET', 'POST'])
def reminders():
    if not session.get('user_id'):
        return redirect('/login')
    if request.method == 'POST':
        medicine = request.form['medicine_name']
        remind_at = request.form['remind_at']
        if remind_at:
            remind_dt = datetime.fromisoformat(remind_at).isoformat()
            supabase.table('reminders').insert({
                'user_id': session['user_id'],
                'medicine_name': medicine,
                'remind_at': remind_dt
            }).execute()
        return redirect('/reminders?toast=Reminder set')

    user_reminders = supabase.table('reminders').select('*').eq('user_id', session['user_id']).order('remind_at', desc=True).execute().data or []
    orders = supabase.table('orders').select('id').eq('user_id', session['user_id']).execute().data
    oids = [o['id'] for o in orders]
    if oids:
        items = supabase.table('order_items').select('product_name').in_('order_id', oids).execute().data
        unique_meds = list(set(i['product_name'] for i in items))
    else:
        unique_meds = []

    med_options = ''.join(f'<option value="{e(m)}">{e(m)}</option>' for m in unique_meds)
    reminder_html = ''
    for r in user_reminders:
        reminder_html += f'''
        <div class="card p-3 mb-2">
            <strong>{e(r['medicine_name'])}</strong> – {r['remind_at'][:16]}
            <a href="/reminders/delete/{r['id']}" class="btn btn-sm btn-outline-danger float-end">Delete</a>
        </div>'''

    body = f'''
    <h2>Medicine Reminders</h2>
    <div class="card p-4 mb-4">
        <h5>Set a new reminder</h5>
        <form method="post">
            {csrf_field()}
            <div class="mb-3">
                <label>Medicine</label>
                <select class="form-select" name="medicine_name" required>
                    <option value="">Choose...</option>
                    {med_options if med_options else '<option disabled>No past medicines</option>'}
                </select>
                <input type="text" class="form-control mt-2" placeholder="Or type medicine name manually" name="medicine_name" value="">
            </div>
            <div class="mb-3">
                <label>Remind me at</label>
                <input type="datetime-local" class="form-control" name="remind_at" required>
            </div>
            <button class="btn btn-primary">Set Reminder</button>
        </form>
    </div>
    <h5>Upcoming Reminders</h5>
    {reminder_html or '<p>No reminders set.</p>'}
    '''
    return public_page("Reminders", body)

@app.route('/reminders/delete/<int:rid>')
def delete_reminder(rid):
    if not session.get('user_id'):
        return redirect('/login')
    supabase.table('reminders').delete().eq('id', rid).eq('user_id', session['user_id']).execute()
    return redirect('/reminders?toast=Reminder deleted')

# ---------- Symptom Checker ----------
@app.route('/symptom-checker', methods=['GET', 'POST'])
def symptom_checker():
    symptoms = [
        'Headache', 'Fever', 'Cough', 'Cold', 'Allergy',
        'Stomach Ache', 'Diarrhea', 'Skin Rash', 'Joint Pain', 'Insomnia'
    ]
    results = []
    if request.method == 'POST':
        selected = request.form.getlist('symptoms')
        if selected:
            mappings = supabase.table('symptom_mappings').select('product_id').in_('symptom', selected).execute().data
            if mappings:
                pids = list(set([m['product_id'] for m in mappings]))
                products = supabase.table('products').select('id,name,price,image_url').in_('id', pids).execute().data
                results = products

    symptom_checks = ''.join(
        f'<div class="form-check"><input class="form-check-input" type="checkbox" name="symptoms" value="{e(s)}" id="s{s}"><label class="form-check-label" for="s{s}">{e(s)}</label></div>'
        for s in symptoms
    )
    result_html = ''
    if results:
        result_html = '<h4 class="mt-4">Recommended Products</h4><div class="row">'
        for p in results:
            img = f'<img src="{e(p.get("image_url"))}" style="height:100px;object-fit:cover;">' if p.get("image_url") else '<div class="bg-light d-flex align-items-center justify-content-center" style="height:100px;"><i class="fas fa-pills fa-2x text-muted"></i></div>'
            result_html += f'''
            <div class="col-md-4 mb-3">
                <div class="card h-100">
                    {img}
                    <div class="card-body">
                        <h6>{e(p['name'])}</h6>
                        <p class="text-success">KSh {e(p['price'])}</p>
                        <a href="/product/{p['id']}" class="btn btn-sm btn-outline-primary">View</a>
                    </div>
                </div>
            </div>'''
        result_html += '</div>'
    elif request.method == 'POST':
        result_html = '<div class="alert alert-info mt-4">No products found for selected symptoms. Please try different combination or consult a pharmacist.</div>'

    body = f'''
    <h2>Symptom Checker</h2>
    <p class="text-muted mb-4">Select your symptoms and we'll suggest appropriate over-the-counter products. <strong>This is not a medical diagnosis – always consult a doctor for serious conditions.</strong></p>
    <form method="post">
        {csrf_field()}
        <div class="card p-4">
            <h5>Common Symptoms</h5>
            {symptom_checks}
            <button class="btn btn-primary mt-3">Find Products</button>
        </div>
    </form>
    {result_html}
    '''
    return public_page("Symptom Checker", body)

# ---------- Admin Decorator ----------
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('is_admin'): return redirect('/login')
        return f(*args, **kwargs)
    return decorated

# ---------- Admin Dashboard ----------
@app.route('/admin')
@admin_required
def admin_dashboard():
    today = datetime.now().date()
    dates = [(today - timedelta(days=i)).isoformat() for i in range(6, -1, -1)]
    sales_data = []
    for d in dates:
        total = supabase.table('orders').select('total_amount').gte('created_at', d).lt('created_at', (datetime.fromisoformat(d)+timedelta(days=1)).isoformat()).execute().data
        sales_data.append(sum([o['total_amount'] for o in total]) if total else 0)

    orders = supabase.table('orders').select('*').order('created_at',desc=True).limit(10).execute().data or []
    total_sales = sum(o['total_amount'] for o in orders) if orders else 0
    total_orders = supabase.table('orders').select('count',count='exact').execute().count
    total_products = supabase.table('products').select('count',count='exact').execute().count

    low_stock = supabase.table('products').select('name,stock').lt('stock',10).execute().data or []
    low_stock_html = ''.join(f'<li>{e(p["name"])} – {p["stock"]} left</li>' for p in low_stock)

    rows = ''.join(
        f'<tr><td>#{str(o["id"])[:8]}</td><td>{e(o.get("shipping_name","Guest"))}</td>'
        f'<td>KSh {o["total_amount"]}</td>'
        f'<td><span class="badge {"bg-warning text-dark" if o.get("order_status")=="pending" else "bg-success"}">{e(o.get("order_status","pending"))}</span></td></tr>'
        for o in orders
    )

    body = f"""
    <div class="row g-4 mb-4">
        <div class="col-sm-6 col-xl-3"><div class="stat-card"><h5 class="text-success"><i class="fas fa-money-bill-wave me-2"></i>Total Sales</h5><h3 class="fw-bold">KSh {total_sales:,.2f}</h3></div></div>
        <div class="col-sm-6 col-xl-3"><div class="stat-card"><h5 class="text-warning"><i class="fas fa-shopping-cart me-2"></i>Orders</h5><h3 class="fw-bold">{total_orders}</h3></div></div>
        <div class="col-sm-6 col-xl-3"><div class="stat-card"><h5 class="text-primary"><i class="fas fa-pills me-2"></i>Products</h5><h3 class="fw-bold">{total_products}</h3></div></div>
        <div class="col-sm-6 col-xl-3"><div class="stat-card"><h5 class="text-danger"><i class="fas fa-users me-2"></i>Customers</h5><h3 class="fw-bold">-</h3></div></div>
    </div>
    <div class="row mb-4">
        <div class="col-md-8"><canvas id="salesChart" style="max-height:300px;"></canvas></div>
        <div class="col-md-4"><div class="card p-3"><h5>Low Stock Alerts</h5><ul>{low_stock_html or '<li>All products well stocked</li>'}</ul></div></div>
    </div>
    <script>
    const ctx = document.getElementById('salesChart').getContext('2d');
    new Chart(ctx, {{
        type: 'line',
        data: {{
            labels: {json.dumps(dates)},
            datasets: [{{
                label: 'Sales (KSh)',
                data: {json.dumps(sales_data)},
                borderColor: '#F4A261',
                backgroundColor: 'rgba(244,162,97,0.2)',
                tension: 0.3
            }}]
        }},
        options: {{ responsive: true, plugins: {{ legend: {{ display: false }} }} }}
    }});
    </script>
    <h4>Recent Orders</h4>
    <div class="card border-0 shadow-sm rounded-4 p-3"><div class="table-responsive"><table class="table table-hover align-middle"><thead class="table-light"><tr><th>ID</th><th>Customer</th><th>Total</th><th>Status</th></tr></thead><tbody>{rows}</tbody></table></div></div>
    """
    return admin_page("Dashboard", body)

# ---------- Admin: Orders ----------
@app.route('/admin/orders')
@admin_required
def admin_orders():
    orders = supabase.table('orders').select('*').order('created_at',desc=True).execute().data or []
    rows = ''.join(
        f'''<tr><td>#{str(o["id"])[:8]}</td><td>{e(o.get("shipping_name","Guest"))}</td><td>KSh {o["total_amount"]}</td>
        <td><div class="d-flex align-items-center">
            <form method="post" action="/admin/order/{o["id"]}/status" class="d-flex">
                {csrf_field()}
                <select name="status" class="form-select form-select-sm me-2" style="width:auto;">
                    <option {'selected' if o.get("order_status")=="pending" else ''}>pending</option>
                    <option {'selected' if o.get("order_status")=="confirmed" else ''}>confirmed</option>
                    <option {'selected' if o.get("order_status")=="shipped" else ''}>shipped</option>
                    <option {'selected' if o.get("order_status")=="delivered" else ''}>delivered</option>
                </select><button class="btn btn-sm btn-primary">Update</button>
            </form>
            <a href="/admin/order/{o['id']}/invoice" target="_blank" class="btn btn-sm btn-outline-primary ms-2">Invoice</a>
            <a href="/admin/order/{o['id']}/invoice?download=1" class="btn btn-sm btn-outline-secondary ms-1"><i class="fas fa-download"></i></a>
        </div></td></tr>''' for o in orders)
    body = f'<div class="card border-0 shadow-sm rounded-4 p-3"><div class="table-responsive"><table class="table table-hover align-middle"><thead class="table-light"><tr><th>ID</th><th>Customer</th><th>Total</th><th>Status / Action</th></tr></thead><tbody>{rows}</tbody></table></div></div>'
    return admin_page("Orders", body, active='orders')

@app.route('/admin/order/<oid>/status', methods=['POST'])
@admin_required
def update_order_status(oid):
    supabase.table('orders').update({'order_status': request.form['status']}).eq('id',oid).execute()
    return redirect('/admin/orders')

@app.route('/admin/order/<int:oid>/invoice')
@admin_required
def admin_invoice(oid):
    order = supabase.table('orders').select('*').eq('id',oid).single().execute().data
    items = supabase.table('order_items').select('*').eq('order_id',oid).execute().data or []
    if not order: return "Order not found", 404
    item_rows = ''.join(f'<tr><td>{e(i["product_name"])}</td><td>{i["quantity"]}</td><td>KSh {e(i["unit_price"])}</td><td>KSh {i["total_price"]}</td></tr>' for i in items)
    html = f"""<!DOCTYPE html><html><head><title>Invoice #{oid}</title>
<style>body{{font-family:'Segoe UI',sans-serif;padding:2rem;}} .invoice-box{{max-width:800px;margin:auto;border:1px solid #eee;box-shadow:0 0 10px rgba(0,0,0,0.05);padding:2rem;}} h2{{color:#0A3D62}} table{{width:100%;border-collapse:collapse;}} th{{background:#0A3D62;color:white;padding:10px;}} td{{padding:10px;border-bottom:1px solid #ddd;}} .total-row td{{font-weight:bold;border-top:2px solid #0A3D62;}}</style></head><body>
<div class="invoice-box"><h2>{e(PHARMACY_NAME)}</h2><p>Invoice #{oid}<br>{order['created_at'][:10]}</p>
<table><thead><tr><th>Product</th><th>Qty</th><th>Unit Price</th><th>Total</th></tr></thead><tbody>{item_rows}</tbody><tfoot><tr class="total-row"><td colspan="3">Grand Total</td><td>KSh {order['total_amount']}</td></tr></tfoot></table>
<div class="text-end mt-3"><button onclick="window.print()" class="btn btn-primary no-print">Print</button> <a href="/admin/orders" class="btn btn-outline-primary no-print">Back</a></div></div>
</body></html>"""
    if request.args.get('download')=='1':
        resp = make_response(html)
        resp.headers['Content-Disposition'] = f'attachment; filename="invoice_{oid}.html"'
        return resp
    return html

# ---------- Admin: Products (delete via POST) ----------
@app.route('/admin/products')
@admin_required
def admin_products():
    prods = supabase.table('products').select('*').order('name').execute().data or []
    rows = ''.join(f'''<tr><td>{e(p["name"])}</td><td>{e(p["category"])}</td><td>{e(p["price"])}</td><td>{p["stock"]}</td>
    <td><a href="/admin/edit-product/{p["id"]}" class="btn btn-sm btn-warning me-1">Edit</a>
    <form action="/admin/delete-product/{p['id']}" method="POST" class="d-inline" onsubmit="return confirm('Delete?')">
        {csrf_field()}
        <button class="btn btn-sm btn-danger">Delete</button>
    </form></td></tr>''' for p in prods)
    return admin_page("Products", f'<a href="/admin/add-product" class="btn btn-success mb-3">+ Add Product</a><div class="card border-0 shadow-sm rounded-4 p-3"><table class="table table-hover align-middle"><thead class="table-light"><tr><th>Name</th><th>Category</th><th>Price</th><th>Stock</th><th></th></tr></thead><tbody>{rows}</tbody></table></div>', active='products')

@app.route('/admin/add-product', methods=['GET','POST'])
@admin_required
def add_product():
    if request.method == 'POST':
        name = request.form['name']; desc = request.form.get('description',''); cat = request.form['category']; price = float(request.form['price']); stock = int(request.form['stock'])
        img = request.files.get('image'); url = None
        if img and img.filename:
            fname = secure_filename(img.filename); uname = f"{os.urandom(4).hex()}_{fname}"
            supabase.storage.from_("product-images").upload(uname, img.read(), {"content-type": img.content_type})
            url = f"{SUPABASE_URL}/storage/v1/object/public/product-images/{uname}"
        supabase.table('products').insert({'name':name,'description':desc,'category':cat,'price':price,'stock':stock,'image_url':url,'active':True}).execute()
        return redirect('/admin/products')
    return admin_page("Add Product", f'''<form method="post" enctype="multipart/form-data" style="max-width:500px;">
    {csrf_field()}
    <input class="form-control mb-2" name="name" placeholder="Name" required>
    <textarea class="form-control mb-2" name="description" placeholder="Description"></textarea>
    <input class="form-control mb-2" name="category" placeholder="Category" required>
    <div class="row"><div class="col"><input class="form-control mb-2" type="number" step="0.01" name="price" placeholder="Price" required></div><div class="col"><input class="form-control mb-2" type="number" name="stock" placeholder="Stock" required></div></div>
    <input class="form-control mb-2" type="file" name="image" accept="image/*">
    <button class="btn btn-primary w-100">Add Product</button></form>''', active='products')

@app.route('/admin/edit-product/<pid>', methods=['GET','POST'])
@admin_required
def edit_product(pid):
    if request.method == 'POST':
        upd = {'name':request.form['name'],'description':request.form.get('description',''),'category':request.form['category'],'price':float(request.form['price']),'stock':int(request.form['stock'])}
        img = request.files.get('image')
        if img and img.filename:
            fname = secure_filename(img.filename); uname = f"{os.urandom(4).hex()}_{fname}"
            supabase.storage.from_("product-images").upload(uname, img.read(), {"content-type": img.content_type})
            upd['image_url'] = f"{SUPABASE_URL}/storage/v1/object/public/product-images/{uname}"
        supabase.table('products').update(upd).eq('id',pid).execute()
        return redirect('/admin/products')
    p = supabase.table('products').select('*').eq('id',pid).single().execute().data
    return admin_page("Edit Product", f'''<form method="post" enctype="multipart/form-data" style="max-width:500px;">
    {csrf_field()}
    <input class="form-control mb-2" name="name" value="{e(p['name'])}" required>
    <textarea class="form-control mb-2" name="description">{e(p.get('description',''))}</textarea>
    <input class="form-control mb-2" name="category" value="{e(p['category'])}" required>
    <div class="row"><div class="col"><input class="form-control mb-2" type="number" step="0.01" name="price" value="{e(p['price'])}" required></div><div class="col"><input class="form-control mb-2" type="number" name="stock" value="{e(p['stock'])}" required></div></div>
    <input class="form-control mb-2" type="file" name="image" accept="image/*">
    <button class="btn btn-primary w-100">Update Product</button></form>''', active='products')

@app.route('/admin/delete-product/<pid>', methods=['POST'])
@admin_required
def delete_product(pid):
    supabase.table('products').delete().eq('id',pid).execute()
    return redirect('/admin/products')

# ---------- Admin: Prescriptions ----------
@app.route('/admin/prescriptions')
@admin_required
def admin_prescriptions():
    rx = supabase.table('prescriptions').select('*').order('created_at',desc=True).execute().data or []
    items = ''.join(f'<div class="card mb-2 p-3"><strong>{e(r["customer_name"])}</strong><br>Phone: {e(r["customer_phone"])}<br><a href="{e(r.get("file_url","#"))}" target="_blank" class="btn btn-sm btn-primary mt-2">View File</a></div>' for r in rx)
    return admin_page("Prescriptions", items or '<p>No prescriptions yet.</p>', active='prescriptions')

# ---------- Admin: Customers ----------
@app.route('/admin/customers')
@admin_required
def admin_customers():
    orders = supabase.table('orders').select('*').execute().data or []
    cust = {}
    for o in orders:
        em = o.get('customer_email') or o.get('guest_email')
        if not em: continue
        if em not in cust: cust[em] = {'name': o.get('customer_name','') or o.get('shipping_name',''), 'phone': o.get('customer_phone','') or o.get('shipping_phone',''), 'spent':0, 'orders':0}
        cust[em]['spent'] += o['total_amount']; cust[em]['orders'] += 1
    rows = ''.join(f'<tr><td>{e(c["name"])}</td><td>{e(email)}</td><td>{e(c["phone"])}</td><td>{c["orders"]}</td><td>KSh {c["spent"]}</td></tr>' for email, c in cust.items())
    return admin_page("Customers", f'<div class="card border-0 shadow-sm rounded-4 p-3"><table class="table table-hover align-middle"><thead class="table-light"><tr><th>Name</th><th>Email</th><th>Phone</th><th>Orders</th><th>Total Spent</th></tr></thead><tbody>{rows}</tbody></table></div>', active='customers')

# ---------- Admin: Users (approve/disable via POST) ----------
@app.route('/admin/users')
@admin_required
def admin_users():
    users = supabase.table('users').select('*').execute().data or []
    rows = ''.join(f'''<tr><td>{e(u["full_name"])}</td><td>{e(u["email"])}</td>
    <td><span class="badge {"bg-success" if u.get("approved") else "bg-warning text-dark"}">{"Approved" if u.get("approved") else "Pending"}</span></td>
    <td>
        <form action="/admin/approve-user/{u['id']}" method="POST" class="d-inline">
            {csrf_field()}
            <button class="btn btn-sm btn-success me-1">Approve</button>
        </form>
        <form action="/admin/disable-user/{u['id']}" method="POST" class="d-inline">
            {csrf_field()}
            <button class="btn btn-sm btn-danger">Disable</button>
        </form>
    </td></tr>''' for u in users)
    return admin_page("Customer Care", f'<div class="card border-0 shadow-sm rounded-4 p-3"><table class="table table-hover align-middle"><thead class="table-light"><tr><th>Name</th><th>Email</th><th>Status</th><th>Action</th></tr></thead><tbody>{rows}</tbody></table></div>', active='users')

@app.route('/admin/approve-user/<uid>', methods=['POST'])
@admin_required
def approve_user(uid):
    supabase.table('users').update({'approved':True}).eq('id',uid).execute()
    return redirect('/admin/users')

@app.route('/admin/disable-user/<uid>', methods=['POST'])
@admin_required
def disable_user(uid):
    supabase.table('users').update({'approved':False}).eq('id',uid).execute()
    return redirect('/admin/users')

@app.route('/admin/create-user', methods=['GET','POST'])
@admin_required
def create_user():
    if request.method=='POST':
        name=request.form['full_name']; email=request.form['email']; pwd=request.form['password']; is_admin=request.form.get('is_admin')=='on'
        hashed=bcrypt.hashpw(pwd.encode(),bcrypt.gensalt()).decode()
        try: supabase.table('users').insert({'full_name':name,'email':email,'password_hash':hashed,'is_admin':is_admin,'approved':True}).execute()
        except: return admin_page("Add Agent",'<div class="alert alert-danger">Email exists.</div><a href="/admin/create-user">Try again</a>', active='create-user')
        return redirect('/admin/users')
    return admin_page("Add Agent",f'''<form method="post" style="max-width:500px;">
    {csrf_field()}
    <input class="form-control mb-2" name="full_name" placeholder="Full Name" required>
    <input class="form-control mb-2" name="email" type="email" placeholder="Email" required>
    <input class="form-control mb-2" type="password" name="password" placeholder="Password" required>
    <div class="form-check mb-2"><input class="form-check-input" type="checkbox" name="is_admin"> Grant Admin</div>
    <button class="btn btn-primary w-100">Create</button></form>''', active='create-user')

@app.route('/admin/settings', methods=['GET','POST'])
@admin_required
def admin_settings():
    if request.method=='POST':
        new_pwd=request.form['new_password']; hashed=bcrypt.hashpw(new_pwd.encode(),bcrypt.gensalt()).decode()
        supabase.table('users').update({'password_hash':hashed}).eq('id',session['user_id']).execute()
        return redirect('/admin/settings?success=1')
    msg = '<div class="alert alert-success">Password updated!</div>' if request.args.get('success') else ''
    return admin_page("Settings",f'{msg}<form method="post" style="max-width:400px;">{csrf_field()}<input class="form-control mb-2" type="password" name="new_password" placeholder="New Password"><button class="btn btn-primary">Update</button></form>', active='settings')

# ---------- Admin: Discounts (disable via POST) ----------
@app.route('/admin/discounts')
@admin_required
def admin_discounts():
    codes = supabase.table('discount_codes').select('*').order('id', desc=True).execute().data or []
    rows = ''
    for c in codes:
        percent = c.get('discount_percent', '')
        amount = c.get('discount_amount', '')
        active = c.get('active', False)
        status = 'Active' if active else 'Disabled'
        rows += f'''<tr>
            <td>{e(c['code'])}</td>
            <td>{percent}%</td>
            <td>{amount} KSh</td>
            <td>{status}</td>
            <td>
                <form action="/admin/disable-discount/{c['id']}" method="POST" class="d-inline" onsubmit="return confirm('Disable?')">
                    {csrf_field()}
                    <button class="btn btn-sm btn-danger">Disable</button>
                </form>
            </td>
        </tr>'''
    body = f'''<a href="/admin/add-discount" class="btn btn-success mb-3">+ New Code</a>
    <div class="card border-0 shadow-sm rounded-4 p-3">
        <table class="table table-hover">
            <thead><tr><th>Code</th><th>Percent</th><th>Amount</th><th>Active</th><th></th></tr></thead>
            <tbody>{rows or '<tr><td colspan="5" class="text-center">No discount codes yet.</td></tr>'}</tbody>
        </table>
    </div>'''
    return admin_page("Discount Codes", body, active='discounts')

@app.route('/admin/add-discount', methods=['GET','POST'])
@admin_required
def add_discount():
    if request.method == 'POST':
        code = request.form['code'].upper()
        percent = request.form.get('discount_percent')
        amount = request.form.get('discount_amount')
        data = {'code': code, 'active': True}
        if percent and percent.strip(): data['discount_percent'] = float(percent)
        if amount and amount.strip(): data['discount_amount'] = float(amount)
        supabase.table('discount_codes').insert(data).execute()
        return redirect('/admin/discounts')
    return admin_page("Add Discount Code", f'''<form method="post">{csrf_field()}
    <input class="form-control mb-2" name="code" placeholder="CODE" required>
    <div class="row"><div class="col"><input class="form-control mb-2" type="number" step="0.01" name="discount_percent" placeholder="Percent (%)"></div>
    <div class="col"><input class="form-control mb-2" type="number" step="0.01" name="discount_amount" placeholder="Amount (KSh)"></div></div>
    <button class="btn btn-primary">Create</button></form>''', active='discounts')

@app.route('/admin/disable-discount/<int:did>', methods=['POST'])
@admin_required
def disable_discount(did):
    supabase.table('discount_codes').update({'active': False}).eq('id', did).execute()
    return redirect('/admin/discounts')

# ---------- Admin: Bundles (delete via POST) ----------
@app.route('/admin/bundles')
@admin_required
def admin_bundles():
    bundles = supabase.table('bundles').select('*').order('id', desc=True).execute().data or []
    rows = ''
    for b in bundles:
        items = supabase.table('bundle_items').select('*, products(name)').eq('bundle_id', b['id']).execute().data or []
        item_names = ', '.join([e(i['products']['name']) for i in items[:3]])
        rows += f'''<tr>
            <td>{e(b['name'])}</td>
            <td>{item_names}{'...' if len(items) > 3 else ''}</td>
            <td>{b['discount_percent']}%</td>
            <td>
                <a href="/admin/edit-bundle/{b['id']}" class="btn btn-sm btn-warning me-1">Edit</a>
                <form action="/admin/delete-bundle/{b['id']}" method="POST" class="d-inline" onsubmit="return confirm('Delete?')">
                    {csrf_field()}
                    <button class="btn btn-sm btn-danger">Delete</button>
                </form>
            </td>
        </tr>'''
    body = f'''<a href="/admin/add-bundle" class="btn btn-success mb-3">+ New Bundle</a>
    <div class="card border-0 shadow-sm rounded-4 p-3"><table class="table"><thead><tr><th>Name</th><th>Products</th><th>Discount</th><th></th></tr></thead><tbody>{rows or '<tr><td colspan="4">No bundles</td></tr>'}</tbody></table></div>'''
    return admin_page("Manage Bundles", body, active='bundles')

@app.route('/admin/add-bundle', methods=['GET','POST'])
@admin_required
def add_bundle():
    if request.method == 'POST':
        name = request.form['name']
        discount = float(request.form.get('discount_percent', 0))
        product_ids = request.form.getlist('product_ids')
        quantities = request.form.getlist('quantities')
        bundle_res = supabase.table('bundles').insert({'name': name, 'discount_percent': discount}).execute()
        bundle_id = bundle_res.data[0]['id']
        for pid, qty in zip(product_ids, quantities):
            supabase.table('bundle_items').insert({
                'bundle_id': bundle_id,
                'product_id': int(pid),
                'quantity': int(qty) if qty else 1
            }).execute()
        return redirect('/admin/bundles')
    products = supabase.table('products').select('id,name').eq('active', True).execute().data or []
    product_options = ''.join(f'<option value="{p["id"]}">{e(p["name"])}</option>' for p in products)
    return admin_page("New Bundle", f'''<form method="post">{csrf_field()}
    <input class="form-control mb-2" name="name" placeholder="Bundle Name" required>
    <input class="form-control mb-2" type="number" step="0.01" name="discount_percent" placeholder="Discount %">
    <div id="bundle-items">
        <div class="mb-2"><select name="product_ids" class="form-select">{product_options}</select>
        <input type="number" name="quantities" value="1" class="form-control d-inline" style="width:80px;"></div>
    </div>
    <button type="button" class="btn btn-sm btn-outline-primary" onclick="addItem()">+ Add Product</button>
    <button class="btn btn-primary mt-3 w-100">Save Bundle</button>
    </form>
    <script>
    function addItem() {{
        const container = document.getElementById('bundle-items');
        const div = document.createElement('div');
        div.className = 'mb-2';
        div.innerHTML = '<select name="product_ids" class="form-select">{product_options}</select>' +
                        '<input type="number" name="quantities" value="1" class="form-control d-inline" style="width:80px;">';
        container.appendChild(div);
    }}
    </script>''', active='bundles')

@app.route('/admin/edit-bundle/<int:bid>', methods=['GET','POST'])
@admin_required
def edit_bundle(bid):
    if request.method == 'POST':
        supabase.table('bundles').update({
            'name': request.form['name'],
            'discount_percent': float(request.form.get('discount_percent', 0))
        }).eq('id', bid).execute()
        supabase.table('bundle_items').delete().eq('bundle_id', bid).execute()
        product_ids = request.form.getlist('product_ids')
        quantities = request.form.getlist('quantities')
        for pid, qty in zip(product_ids, quantities):
            supabase.table('bundle_items').insert({
                'bundle_id': bid,
                'product_id': int(pid),
                'quantity': int(qty) if qty else 1
            }).execute()
        return redirect('/admin/bundles')
    bundle = supabase.table('bundles').select('*').eq('id', bid).single().execute().data
    items = supabase.table('bundle_items').select('*').eq('bundle_id', bid).execute().data or []
    products = supabase.table('products').select('id,name').eq('active', True).execute().data or []
    product_options = ''.join(f'<option value="{p["id"]}">{e(p["name"])}</option>' for p in products)
    items_html = ''.join(f'''<div class="mb-2">
        <select name="product_ids" class="form-select"><option value="{i['product_id']}" selected>{e(i.get('products',{}).get('name',''))}</option></select>
        <input type="number" name="quantities" value="{i['quantity']}" class="form-control d-inline" style="width:80px;">
    </div>''' for i in items)
    return admin_page("Edit Bundle", f'''<form method="post">{csrf_field()}
    <input class="form-control mb-2" name="name" value="{e(bundle['name'])}" required>
    <input class="form-control mb-2" type="number" step="0.01" name="discount_percent" value="{bundle['discount_percent']}" placeholder="Discount %">
    <div id="bundle-items">{items_html}</div>
    <button type="button" class="btn btn-sm btn-outline-primary" onclick="addItem()">+ Add Product</button>
    <button class="btn btn-primary mt-3 w-100">Update Bundle</button>
    </form>
    <script>
    function addItem() {{
        const container = document.getElementById('bundle-items');
        const div = document.createElement('div');
        div.className = 'mb-2';
        div.innerHTML = '<select name="product_ids" class="form-select">{product_options}</select>' +
                        '<input type="number" name="quantities" value="1" class="form-control d-inline" style="width:80px;">';
        container.appendChild(div);
    }}
    </script>''', active='bundles')

@app.route('/admin/delete-bundle/<int:bid>', methods=['POST'])
@admin_required
def delete_bundle(bid):
    supabase.table('bundles').delete().eq('id', bid).execute()
    return redirect('/admin/bundles')

# ---------- Admin: Analytics ----------
@app.route('/admin/analytics')
@admin_required
def admin_analytics():
    top_products = supabase.table('order_items').select('product_id, products(name)').execute().data
    product_sales = {}
    for item in top_products:
        pid = item['product_id']
        pname = item.get('products', {}).get('name', 'Unknown')
        product_sales[pname] = product_sales.get(pname, 0) + 1
    sorted_products = sorted(product_sales.items(), key=lambda x: x[1], reverse=True)[:10]
    top_labels = [x[0] for x in sorted_products]
    top_data = [x[1] for x in sorted_products]

    rev_by_cat = supabase.table('order_items').select('products(category), total_price').execute().data
    cat_revenue = {}
    for item in rev_by_cat:
        cat = item.get('products', {}).get('category', 'Uncategorized')
        cat_revenue[cat] = cat_revenue.get(cat, 0) + float(item['total_price'])
    cat_labels = list(cat_revenue.keys())
    cat_data = list(cat_revenue.values())

    orders = supabase.table('orders').select('user_id').execute().data
    user_counts = {}
    for o in orders:
        uid = o['user_id']
        if uid: user_counts[uid] = user_counts.get(uid, 0) + 1
    repeat_count = sum(1 for v in user_counts.values() if v > 1)
    total_customers = len(user_counts)

    body = f'''
    <div class="row">
        <div class="col-md-6 mb-4"><div class="card p-3"><h5>Top Selling Products</h5><canvas id="topProductsChart"></canvas></div></div>
        <div class="col-md-6 mb-4"><div class="card p-3"><h5>Revenue by Category</h5><canvas id="revenuePieChart"></canvas></div></div>
    </div>
    <div class="row">
        <div class="col-md-4"><div class="stat-card"><h5 class="text-info">Total Customers</h5><h3>{total_customers}</h3></div></div>
        <div class="col-md-4"><div class="stat-card"><h5 class="text-success">Repeat Customers</h5><h3>{repeat_count}</h3></div></div>
        <div class="col-md-4"><div class="stat-card"><h5 class="text-warning">Repeat Rate</h5><h3>{round(repeat_count / total_customers * 100, 1) if total_customers else 0}%</h3></div></div>
    </div>
    <script>
    new Chart(document.getElementById('topProductsChart'), {{
        type: 'bar',
        data: {{ labels: {json.dumps(top_labels)}, datasets: [{{ label: 'Units Sold', data: {json.dumps(top_data)}, backgroundColor: '#F4A261' }}] }}
    }});
    new Chart(document.getElementById('revenuePieChart'), {{
        type: 'pie',
        data: {{ labels: {json.dumps(cat_labels)}, datasets: [{{ data: {json.dumps(cat_data)}, backgroundColor: ['#0A3D62','#1B5A82','#2E8B57','#F4A261','#E76F51','#6C63FF'] }}] }}
    }});
    </script>
    '''
    return admin_page("Analytics", body, active='analytics')

# ---------- Admin: Branches (delete via POST) ----------
@app.route('/admin/branches')
@admin_required
def admin_branches():
    branches = supabase.table('branches').select('*').order('name').execute().data or []
    rows = ''.join(
        f'''<tr>
            <td>{e(b['name'])}</td><td>{e(b.get('address',''))}</td><td>{e(b.get('phone',''))}</td>
            <td>
                <a href="/admin/edit-branch/{b['id']}" class="btn btn-sm btn-warning me-1">Edit</a>
                <form action="/admin/delete-branch/{b['id']}" method="POST" class="d-inline" onsubmit="return confirm('Delete?')">
                    {csrf_field()}
                    <button class="btn btn-sm btn-danger">Delete</button>
                </form>
            </td></tr>''' for b in branches)
    body = f'''<a href="/admin/add-branch" class="btn btn-success mb-3"><i class="fas fa-plus me-2"></i>Add Branch</a>
    <div class="card border-0 shadow-sm rounded-4 p-3"><table class="table table-hover align-middle"><thead class="table-light"><tr><th>Name</th><th>Address</th><th>Phone</th><th></th></tr></thead><tbody>{rows or '<tr><td colspan="4">No branches yet.</td></tr>'}</tbody></table></div>'''
    return admin_page("Manage Branches", body, active='branches')

@app.route('/admin/add-branch', methods=['GET','POST'])
@admin_required
def add_branch():
    if request.method == 'POST':
        name = request.form['name']; address = request.form.get('address',''); phone = request.form.get('phone','')
        lat = request.form.get('latitude'); lng = request.form.get('longitude')
        data = {'name': name, 'address': address, 'phone': phone}
        if lat: data['latitude'] = float(lat)
        if lng: data['longitude'] = float(lng)
        supabase.table('branches').insert(data).execute()
        return redirect('/admin/branches')
    return admin_page("Add Branch", f'''<form method="post">{csrf_field()}
    <input class="form-control mb-2" name="name" placeholder="Branch Name" required>
    <input class="form-control mb-2" name="address" placeholder="Address">
    <input class="form-control mb-2" name="phone" placeholder="Phone">
    <div class="row"><div class="col"><input class="form-control mb-2" type="number" step="any" name="latitude" placeholder="Latitude"></div><div class="col"><input class="form-control mb-2" type="number" step="any" name="longitude" placeholder="Longitude"></div></div>
    <button class="btn btn-primary w-100">Add Branch</button></form>''', active='branches')

@app.route('/admin/edit-branch/<int:bid>', methods=['GET','POST'])
@admin_required
def edit_branch(bid):
    if request.method == 'POST':
        upd = {'name': request.form['name'], 'address': request.form.get('address',''), 'phone': request.form.get('phone','')}
        lat = request.form.get('latitude'); lng = request.form.get('longitude')
        if lat: upd['latitude'] = float(lat)
        if lng: upd['longitude'] = float(lng)
        supabase.table('branches').update(upd).eq('id', bid).execute()
        return redirect('/admin/branches')
    b = supabase.table('branches').select('*').eq('id', bid).single().execute().data
    if not b: return "Branch not found", 404
    return admin_page("Edit Branch", f'''<form method="post">{csrf_field()}
    <input class="form-control mb-2" name="name" value="{e(b['name'])}" required>
    <input class="form-control mb-2" name="address" value="{e(b.get('address',''))}">
    <input class="form-control mb-2" name="phone" value="{e(b.get('phone',''))}">
    <div class="row"><div class="col"><input class="form-control mb-2" type="number" step="any" name="latitude" value="{b.get('latitude','')}" placeholder="Latitude"></div><div class="col"><input class="form-control mb-2" type="number" step="any" name="longitude" value="{b.get('longitude','')}" placeholder="Longitude"></div></div>
    <button class="btn btn-primary w-100">Update Branch</button></form>''', active='branches')

@app.route('/admin/delete-branch/<int:bid>', methods=['POST'])
@admin_required
def delete_branch(bid):
    supabase.table('branches').delete().eq('id', bid).execute()
    return redirect('/admin/branches')

# ---------- Admin: Symptoms Management (delete via POST) ----------
@app.route('/admin/symptoms', methods=['GET', 'POST'])
@admin_required
def admin_symptoms():
    if request.method == 'POST':
        symptom = request.form['symptom']
        product_id = int(request.form['product_id'])
        try:
            supabase.table('symptom_mappings').upsert({'symptom': symptom, 'product_id': product_id}).execute()
        except:
            return admin_page("Symptoms", '<div class="alert alert-danger">Error saving mapping</div><a href="/admin/symptoms">Back</a>', active='symptoms')
        return redirect('/admin/symptoms')
    mappings = supabase.table('symptom_mappings').select('*, products(name)').order('symptom').execute().data or []
    rows = ''.join(f'''
        <tr>
            <td>{e(m['symptom'])}</td>
            <td>{e(m.get('products',{}).get('name',''))}</td>
            <td>
                <form action="/admin/symptoms/delete/{m['id']}" method="POST" class="d-inline" onsubmit="return confirm('Delete?')">
                    {csrf_field()}
                    <button class="btn btn-sm btn-danger">Delete</button>
                </form>
            </td>
        </tr>''' for m in mappings)
    products = supabase.table('products').select('id,name').eq('active',True).execute().data
    product_options = ''.join(f'<option value="{p["id"]}">{e(p["name"])}</option>' for p in products)
    body = f'''
    <h5>Add Symptom Mapping</h5>
    <form method="post" class="mb-4">
        {csrf_field()}
        <div class="row">
            <div class="col"><input class="form-control" name="symptom" placeholder="Symptom (e.g., Headache)" required></div>
            <div class="col"><select class="form-select" name="product_id" required><option value="">Choose product</option>{product_options}</select></div>
            <div class="col-auto"><button class="btn btn-primary">Add</button></div>
        </div>
    </form>
    <div class="card"><table class="table"><thead><tr><th>Symptom</th><th>Product</th><th></th></tr></thead><tbody>{rows or '<tr><td colspan="3">No mappings</td></tr>'}</tbody></table></div>
    '''
    return admin_page("Manage Symptom Mappings", body, active='symptoms')

@app.route('/admin/symptoms/delete/<int:sid>', methods=['POST'])
@admin_required
def delete_symptom_mapping(sid):
    supabase.table('symptom_mappings').delete().eq('id', sid).execute()
    return redirect('/admin/symptoms')

# ---------- Admin: Export ----------
@app.route('/admin/export-orders')
@admin_required
def export_orders():
    orders = supabase.table('orders').select('*').order('created_at',desc=True).execute().data or []
    output = io.StringIO()
    w = csv.writer(output)
    w.writerow(["ID","Date","Customer","Email","Phone","Total","Status","Payment"])
    for o in orders:
        w.writerow([str(o['id'])[:8], o['created_at'][:10], o.get('customer_name','') or o.get('shipping_name',''), o.get('customer_email','') or o.get('guest_email',''), o.get('customer_phone','') or o.get('shipping_phone',''), o['total_amount'], o.get('order_status',''), o.get('payment_method','')])
    output.seek(0)
    return Response(output.getvalue(), mimetype='text/csv', headers={"Content-Disposition":"attachment;filename=orders.csv"})

# PWA / Icons
@app.route('/manifest.json')
def manifest():
    return make_response(json.dumps({"name":f"{e(PHARMACY_NAME)} - Online Pharmacy","short_name":e(PHARMACY_NAME),"start_url":"/","display":"standalone","icons":[{"src":"/static/icon-192.png","sizes":"192x192","type":"image/png"},{"src":"/static/icon-512.png","sizes":"512x512","type":"image/png"}]}),{'Content-Type':'application/manifest+json'})

@app.route('/sw.js')
def sw():
    return Response("self.addEventListener('fetch',e=>e.respondWith(fetch(e.request)))", mimetype='application/javascript')

def _create_png(w,h,color=(10,61,98)):
    def chunk(t,d): c=t+d; return struct.pack(">I",len(d))+c+struct.pack(">I",zlib.crc32(c)&0xFFFFFFFF)
    sig = b'\x89PNG\r\n\x1a\n'; ihdr = chunk(b'IHDR', struct.pack(">IIBBBBB",w,h,8,2,0,0,0))
    raw = b''.join(b'\x00'+bytes(color)*w for _ in range(h))
    return sig+ihdr+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b'')

@app.route('/static/icon-192.png')
def icon192(): return Response(_create_png(192,192), mimetype='image/png')

@app.route('/static/icon-512.png')
def icon512(): return Response(_create_png(512,512), mimetype='image/png')

@app.route('/download')
def download(): return public_page("Download App", '<h2>Download our APK</h2><p>Install directly from <a href="#">link</a>.</p>')

if __name__ == '__main__':
    print("\n✅ Mediocare Pharmacy app starting... Visit http://localhost:8080\n")
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',8080)))
