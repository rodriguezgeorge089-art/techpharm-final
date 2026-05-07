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

# ---------- Shared CSS ----------
COMMON_CSS = """
<style>
    :root { --blue: #0A3D62; --gold: #F4A261; --grad: linear-gradient(135deg, #0A3D62, #1B5A82); }
    body { font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; background: #f4f6f9; margin: 0; }
    .navbar-public { background: white; box-shadow: 0 2px 10px rgba(0,0,0,0.05); padding: 0.5rem 0; }
    .navbar-brand { text-decoration: none; }
    .public-nav-links { display: flex; flex-wrap: nowrap; overflow-x: auto; -webkit-overflow-scrolling: touch; gap: 0.5rem; padding: 0 0.5rem; align-items: center; }
    .public-nav-links .nav-link { white-space: nowrap; padding: 0.5rem 1rem; color: #4A5568; font-weight: 600; text-decoration: none; border-radius: 20px; transition: all 0.2s; }
    .public-nav-links .nav-link:hover { background: #f0f0f0; color: var(--blue); }
    .public-nav-links .nav-link.active { background: var(--gold); color: white !important; }
    .btn-primary { background: var(--blue); border: none; border-radius: 40px; padding: 0.6rem 2rem; font-weight: 600; transition: all 0.3s; }
    .btn-primary:hover { background: var(--gold); transform: translateY(-2px); box-shadow: 0 10px 20px rgba(244,162,97,0.3); }
    .btn-outline-primary { border: 2px solid var(--gold); color: var(--blue); border-radius: 40px; }
    .btn-outline-primary:hover { background: var(--gold); color: white; }
    .card { border: none; border-radius: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); transition: transform 0.2s; }
    .card:hover { transform: translateY(-3px); box-shadow: 0 8px 20px rgba(0,0,0,0.1); }
    .hero { background: linear-gradient(135deg, #0A3D62 0%, #1B5A82 50%, #2E8B57 100%); color: white; border-radius: 24px; padding: 4rem 1.5rem; text-align: center; margin-top: 1rem; }
    .hero h1 { font-size: 3rem; font-weight: 800; letter-spacing: -0.5px; }
    .hero p { font-size: 1.2rem; max-width: 650px; margin: 1rem auto; opacity: 0.9; }
    .whatsapp-float { position: fixed; bottom: 30px; right: 30px; width: 55px; height: 55px; background: #25D366; color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 1.8rem; box-shadow: 0 5px 15px rgba(37,211,102,0.3); z-index: 1000; }
    .toast-container { position: fixed; top: 20px; right: 20px; z-index: 9999; }
    .toast { background: var(--gold); color: white; padding: 1rem 1.5rem; border-radius: 12px; font-weight: 600; box-shadow: 0 8px 20px rgba(0,0,0,0.15); animation: slideIn 0.3s; }
    @keyframes slideIn { from { transform: translateX(100%); opacity:0; } to { transform: translateX(0); opacity:1; } }
    .eye-icon { cursor: pointer; }

    /* ---------- BRAND LOGO ---------- */
    .brand-logo {
        display: flex; align-items: center; justify-content: center;
        width: 42px; height: 42px; background: white; border-radius: 50%;
        margin-right: 12px; color: var(--blue); font-size: 1.5rem;
        font-weight: bold; box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .brand-text { display: flex; flex-direction: column; line-height: 1.2; }
    .brand-name {
        font-weight: 800; font-size: 1.5rem;
        background: linear-gradient(135deg, #0A3D62, #1B5A82);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .brand-sub {
        font-size: 0.65rem; font-weight: 700; letter-spacing: 2px;
        color: #4A5568; text-transform: uppercase;
    }
    @media (max-width: 768px) {
        .hero h1 { font-size: 2rem; }
        .brand-logo { width: 34px; height: 34px; font-size: 1.2rem; margin-right: 8px; }
        .brand-name { font-size: 1.2rem; }
    }
</style>
"""

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

    links = [ ('/', 'Home'), ('/shop', 'Shop'), ('/prescription', 'Rx'),
              ('/branches', 'Branches'), ('/cart', f'Cart {int(cart_total)}') ]
    if user:
        links.append(('/my-account', 'Orders'))
        if user.get('is_admin'): links.append(('/admin', 'Admin'))
        links.append(('/logout', 'Logout'))
    else:
        links.append(('/login', 'Login'))
        links.append(('/register', 'Register'))

    nav_links_html = ''.join(f'<a class="nav-link" href="{url}">{label}</a>' for url, label in links)
    nav = f'''<nav class="navbar navbar-public sticky-top"><div class="container d-flex align-items-center">
        <a class="navbar-brand d-flex align-items-center" href="/" style="text-decoration:none;">
            <span class="brand-logo"><i class="fas fa-plus"></i></span>
            <div class="brand-text">
                <span class="brand-name">DawaLink</span>
                <span class="brand-sub">PHARMACY LTD</span>
            </div>
        </a>
        <div class="public-nav-links ms-auto">{nav_links_html}</div>
    </div></nav>'''

    return f"""<!DOCTYPE html><html><head><title>{title} – {PHARMACY_NAME}</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
{COMMON_CSS}</head><body>
{nav}
<div class="container mt-4">{body}</div>
<footer class="text-center py-4 mt-5" style="background:var(--blue);color:white;"><p>&copy; 2026 {PHARMACY_NAME}. All rights reserved.</p></footer>
<a href="https://wa.me/{PHARMACY_PHONE}?text=Hello%20DawaLink" class="whatsapp-float" target="_blank"><i class="fab fa-whatsapp"></i></a>
<div class="toast-container" id="toastContainer"></div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script>
(function(){{
    const params = new URLSearchParams(window.location.search);
    if(params.get('added')==='1'){{
        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.innerHTML = '<i class="fas fa-check-circle me-2"></i>Item added to cart!';
        document.getElementById('toastContainer').appendChild(toast);
        setTimeout(()=>toast.remove(), 3000);
        const url = new URL(window.location);
        url.searchParams.delete('added');
        window.history.replaceState({{}}, '', url);
    }}
    document.querySelectorAll('.toggle-password').forEach(btn => {{
        btn.addEventListener('click', function() {{
            const input = document.getElementById(this.dataset.target);
            const icon = this.querySelector('i');
            if (input.type === 'password') {{
                input.type = 'text';
                icon.classList.replace('fa-eye','fa-eye-slash');
            }} else {{
                input.type = 'password';
                icon.classList.replace('fa-eye-slash','fa-eye');
            }}
        }});
    }});
}})();
</script>
</body></html>"""

def admin_page(title, body, active='dashboard'):
    links = [
        ('dashboard','fa-tachometer-alt','/admin'),
        ('orders','fa-shopping-cart','/admin/orders'),
        ('products','fa-pills','/admin/products'),
        ('prescriptions','fa-file-prescription','/admin/prescriptions'),
        ('customers','fa-users','/admin/customers'),
        ('users','fa-headset','/admin/users'),
        ('create-user','fa-user-plus','/admin/create-user'),
        ('settings','fa-cog','/admin/settings'),
        ('branches','fa-map-marker-alt','/admin/branches'),
        ('export','fa-download','/admin/export-orders')
    ]

    # Desktop sidebar with brand redesign
    sidebar_html = '<div class="admin-sidebar d-none d-md-flex flex-column">'
    sidebar_html += '''
    <div class="admin-brand" style="display:flex; align-items:center; margin-bottom:2rem;">
        <span class="admin-brand-logo" style="display:flex; align-items:center; justify-content:center; width:44px; height:44px; background:white; border-radius:50%; margin-right:12px; color:#0A3D62; font-size:1.6rem; font-weight:bold; box-shadow:0 2px 8px rgba(0,0,0,0.1);"><i class="fas fa-plus"></i></span>
        <div style="display:flex; flex-direction:column; line-height:1.2;">
            <span style="font-weight:800; font-size:1.5rem; color:white;">DawaLink</span>
            <span style="font-size:0.65rem; font-weight:700; letter-spacing:2px; color:rgba(255,255,255,0.85); text-transform:uppercase;">PHARMACY LTD</span>
        </div>
    </div>'''
    for name, icon, url in links:
        active_class = 'active' if name == active else ''
        sidebar_html += f'<a href="{url}" class="{active_class}"><i class="fas {icon}"></i> {name.replace("-"," ").title()}</a>'
    sidebar_html += '<hr style="border-color:rgba(255,255,255,0.2); margin-top:auto;">'
    sidebar_html += '<a href="/" class="btn-view">🏠 View Site</a>'
    sidebar_html += '<a href="/logout" class="btn-logout">🚪 Logout</a>'
    sidebar_html += '</div>'

    # Mobile navbar (scrollable, always visible)
    mobile_links = ''
    for name, icon, url in links:
        active_class = 'active' if name == active else ''
        mobile_links += f'<a href="{url}" class="{active_class}"><i class="fas {icon}"></i> {name.replace("-"," ").title()}</a>'
    mobile_bar = f'<div class="admin-mobile-nav d-md-none">{mobile_links}</div>'

    return f"""<!DOCTYPE html>
<html>
<head>
    <title>{title} – Admin</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {{ --blue: #0A3D62; --gold: #F4A261; --grad: linear-gradient(135deg, #0A3D62, #1B5A82); }}
        .admin-sidebar {{
            width: 250px; background: var(--grad); color: white;
            min-height: 100vh; position: fixed; top: 0; left: 0; z-index: 1000;
            padding: 1.5rem 1rem; box-shadow: 2px 0 10px rgba(0,0,0,0.05);
        }}
        .admin-sidebar a {{
            color: #ffffff !important; font-weight: 600;
            display: flex; align-items: center; padding: 0.8rem 1.2rem;
            text-decoration: none; border-radius: 12px; margin-bottom: 4px;
            transition: all 0.2s;
        }}
        .admin-sidebar a i {{ width: 24px; margin-right: 12px; font-size: 1.1rem; color: #ffffff; }}
        .admin-sidebar a:hover {{
            background: rgba(244,162,97,0.9); color: #0A3D62 !important;
            transform: translateX(4px);
        }}
        .admin-sidebar a:hover i {{ color: #0A3D62; }}
        .admin-sidebar a.active {{
            background: var(--gold); color: #0A3D62 !important;
            font-weight: 700; box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }}
        .admin-sidebar a.active i {{ color: #0A3D62; }}
        .admin-sidebar .btn-view, .admin-sidebar .btn-logout {{
            display: block; padding: 0.6rem 1rem; border-radius: 8px;
            margin-bottom: 4px; text-align: center; color: white !important;
            background: rgba(255,255,255,0.15);
        }}
        .admin-sidebar .btn-logout {{ background: rgba(220,53,69,0.9); }}

        .main-admin {{
            min-height: 100vh; background: #f4f6f9;
            padding: 2rem; width: 100%;
        }}
        @media (min-width: 768px) {{
            .main-admin {{ margin-left: 250px; width: calc(100% - 250px); }}
        }}

        .admin-mobile-nav {{
            background: white; overflow-x: auto; white-space: nowrap;
            padding: 0.5rem; border-bottom: 1px solid #eee;
            position: sticky; top: 0; z-index: 1020;
        }}
        .admin-mobile-nav a {{
            display: inline-block; font-weight: 600; font-size: 0.85rem;
            padding: 0.4rem 1rem; margin: 0 2px; border-radius: 30px;
            text-decoration: none; color: var(--blue); transition: 0.2s;
        }}
        .admin-mobile-nav a i {{ margin-right: 4px; }}
        .admin-mobile-nav a:hover, .admin-mobile-nav a.active {{
            background: var(--blue); color: white !important;
        }}
        .admin-mobile-nav::-webkit-scrollbar {{ height: 4px; }}
        .admin-mobile-nav::-webkit-scrollbar-thumb {{ background: var(--gold); border-radius: 4px; }}

        .stat-card {{ background: white; border-radius: 16px; padding: 1.5rem; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }}
        .table-responsive {{ -webkit-overflow-scrolling: touch; }}
        h2 {{ color: var(--blue); }}
    </style>
</head>
<body style="display:flex; flex-direction:column;">
    {sidebar_html}
    {mobile_bar}
    <div class="main-admin">
        <h2>{title}</h2>
        <hr>{body}
    </div>
</body>
</html>"""

# ---------- Public routes ----------
@app.route('/')
def home():
    # Fetch 3 random active products for featured section
    try:
        featured = supabase.table('products').select('id,name,price,image_url').eq('active',True).limit(3).execute().data or []
    except:
        featured = []

    featured_html = ''
    if featured:
        for p in featured:
            img = f'<img src="{p["image_url"]}" style="height:150px; object-fit:cover; border-radius:12px 12px 0 0;">' if p.get('image_url') else '<div class="bg-light d-flex align-items-center justify-content-center" style="height:150px; border-radius:12px 12px 0 0;"><i class="fas fa-pills fa-3x text-muted"></i></div>'
            featured_html += f'''
            <div class="col-md-4 mb-4">
                <div class="card h-100 border-0 shadow-sm rounded-4 overflow-hidden">
                    {img}
                    <div class="card-body text-center">
                        <h5 class="fw-bold">{p['name']}</h5>
                        <p class="text-success fw-bold">KSh {p['price']}</p>
                        <a href="/shop" class="btn btn-outline-primary btn-sm rounded-pill">View Details</a>
                    </div>
                </div>
            </div>'''

    # Quick links (mobile only, blog removed)
    if session.get('user_id'):
        quick_links = '''
        <div class="d-md-none mt-4">
            <h5 class="text-center mb-3 fw-bold">Quick Links</h5>
            <div class="row g-3 text-center">
                <div class="col-4"><a href="/shop" class="card p-3 text-decoration-none h-100 shadow-sm rounded-4"><i class="fas fa-store fa-2x text-primary"></i><div class="mt-2 fw-bold small">Shop</div></a></div>
                <div class="col-4"><a href="/prescription" class="card p-3 text-decoration-none h-100 shadow-sm rounded-4"><i class="fas fa-file-prescription fa-2x text-primary"></i><div class="mt-2 fw-bold small">Rx</div></a></div>
                <div class="col-4"><a href="/branches" class="card p-3 text-decoration-none h-100 shadow-sm rounded-4"><i class="fas fa-map-marker-alt fa-2x text-primary"></i><div class="mt-2 fw-bold small">Branches</div></a></div>
                <div class="col-4"><a href="/cart" class="card p-3 text-decoration-none h-100 shadow-sm rounded-4"><i class="fas fa-shopping-cart fa-2x text-primary"></i><div class="mt-2 fw-bold small">Cart</div></a></div>
                <div class="col-4"><a href="/my-account" class="card p-3 text-decoration-none h-100 shadow-sm rounded-4"><i class="fas fa-box fa-2x text-primary"></i><div class="mt-2 fw-bold small">My Orders</div></a></div>
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
    <!-- HERO SECTION -->
    <div class="hero position-relative overflow-hidden">
        <div class="position-relative" style="z-index: 1;">
            <h1 class="display-4 fw-bold">Your Health, Delivered with Care</h1>
            <p class="lead">Genuine medicines, wellness essentials, and personal care products – delivered to your doorstep across Kenya.</p>
            <div class="d-flex flex-wrap justify-content-center gap-3 mt-4">
                <a href="/shop" class="btn btn-light btn-lg rounded-pill px-4 shadow">Shop Now</a>
                <a href="/prescription" class="btn btn-outline-light btn-lg rounded-pill px-4">Upload Prescription</a>
            </div>
        </div>
        <div class="position-absolute top-0 start-0 w-100 h-100" style="background: radial-gradient(circle at 20% 50%, rgba(255,255,255,0.05) 0%, transparent 50%);"></div>
    </div>

    <!-- TRUST BADGES -->
    <div class="row mt-4 g-3 text-center">
        <div class="col-md-4">
            <div class="bg-white rounded-4 p-4 shadow-sm h-100">
                <i class="fas fa-certificate fa-3x text-success mb-3"></i>
                <h5>100% Licensed</h5>
                <p class="text-muted small">All products sourced from approved pharmacies & manufacturers.</p>
            </div>
        </div>
        <div class="col-md-4">
            <div class="bg-white rounded-4 p-4 shadow-sm h-100">
                <i class="fas fa-truck-fast fa-3x text-warning mb-3"></i>
                <h5>Lightning Delivery</h5>
                <p class="text-muted small">Reliable courier network ensuring fast, safe delivery across Kenya.</p>
            </div>
        </div>
        <div class="col-md-4">
            <div class="bg-white rounded-4 p-4 shadow-sm h-100">
                <i class="fas fa-headset fa-3x text-info mb-3"></i>
                <h5>24/7 Expert Support</h5>
                <p class="text-muted small">Pharmacist-led customer care, always ready to assist you.</p>
            </div>
        </div>
    </div>

    <!-- WHY CHOOSE US -->
    <div class="mt-5 text-center">
        <h2 class="fw-bold" style="color: var(--blue);">Why Choose DawaLink?</h2>
        <p class="text-muted">Experience healthcare that puts you first.</p>
    </div>
    <div class="row mt-3 g-4">
        <div class="col-md-4">
            <div class="card p-4 text-center h-100 border-0 shadow-sm rounded-4">
                <i class="fas fa-pills fa-3x text-primary mb-3"></i>
                <h5>Wide Product Range</h5>
                <p>From supplements to pain relief and baby care – we have everything you need.</p>
            </div>
        </div>
        <div class="col-md-4">
            <div class="card p-4 text-center h-100 border-0 shadow-sm rounded-4">
                <i class="fas fa-shield-alt fa-3x text-success mb-3"></i>
                <h5>Genuine Quality</h5>
                <p>Every product is verified for authenticity and safety before sale.</p>
            </div>
        </div>
        <div class="col-md-4">
            <div class="card p-4 text-center h-100 border-0 shadow-sm rounded-4">
                <i class="fas fa-tags fa-3x text-warning mb-3"></i>
                <h5>Great Pricing</h5>
                <p>Competitive prices and regular discounts – your health doesn't have to be expensive.</p>
            </div>
        </div>
    </div>

    <!-- FEATURED PRODUCTS -->
    <div class="mt-5 text-center">
        <h2 class="fw-bold" style="color: var(--blue);">Featured Products</h2>
        <p class="text-muted">Our most popular health essentials.</p>
    </div>
    <div class="row mt-3">
        {featured_html if featured_html else '<div class="col-12 text-center"><p class="text-muted">No products available yet. <a href="/shop">Visit our shop</a> to browse.</p></div>'}
    </div>

    <!-- TESTIMONIALS -->
    <div class="mt-5 text-center">
        <h2 class="fw-bold" style="color: var(--blue);">What Our Customers Say</h2>
    </div>
    <div class="row mt-3 g-4">
        <div class="col-md-4">
            <div class="card p-4 border-0 shadow-sm rounded-4 h-100">
                <i class="fas fa-quote-left fa-2x text-muted mb-2"></i>
                <p class="fst-italic">"DawaLink delivered my prescription in under 2 hours! Absolutely reliable."</p>
                <strong class="mt-2">– Jane M.</strong>
            </div>
        </div>
        <div class="col-md-4">
            <div class="card p-4 border-0 shadow-sm rounded-4 h-100">
                <i class="fas fa-quote-left fa-2x text-muted mb-2"></i>
                <p class="fst-italic">"Great prices and the customer service is top-notch. I’m a loyal customer now."</p>
                <strong class="mt-2">– Peter K.</strong>
            </div>
        </div>
        <div class="col-md-4">
            <div class="card p-4 border-0 shadow-sm rounded-4 h-100">
                <i class="fas fa-quote-left fa-2x text-muted mb-2"></i>
                <p class="fst-italic">"The website is so easy to use, and my order arrived discreetly packaged."</p>
                <strong class="mt-2">– Aisha O.</strong>
            </div>
        </div>
    </div>

    <!-- FINAL CTA -->
    <div class="mt-5 text-center p-5 rounded-4" style="background: var(--grad); color: white;">
        <h2 class="fw-bold">Ready to Experience the DawaLink Difference?</h2>
        <p class="mb-4">Start shopping or upload your prescription today.</p>
        <a href="/shop" class="btn btn-light btn-lg rounded-pill px-4 me-2">Browse Products</a>
        <a href="/prescription" class="btn btn-outline-light btn-lg rounded-pill px-4">Upload Rx</a>
    </div>

    {quick_links}
    """
    user = None
    if session.get('user_id'):
        user = {'full_name': session.get('user_name', 'User'), 'is_admin': session.get('is_admin', False)}
    return public_page("Home", body, user)

# ---------- Shop, Cart, Checkout, etc. (unchanged) ----------
# (All other routes remain exactly as in the previous full code)
# ... (Include the rest of your routes: /shop, /cart/add, /cart, /checkout, /prescription, /branches, /login, /register, /my-account, etc.) ...
# (I am not repeating them here for brevity, but in your actual file they MUST be present.)
# ---------- IMPORTANT: Please copy the remaining routes from the previous complete code ----------
