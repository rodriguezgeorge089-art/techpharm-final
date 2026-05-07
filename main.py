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
    .navbar-brand { font-weight: 800; font-size: 1.5rem; color: var(--blue) !important; }
    .navbar-brand i { background: var(--gold); color: white; border-radius: 12px; padding: 6px 10px; margin-right: 8px; font-size: 1.2rem; }
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
    @media (max-width: 768px) {
        .hero h1 { font-size: 2rem; }
        .admin-desktop-sidebar { display: none !important; }
        .admin-toggle-btn { display: block !important; }
        .admin-offcanvas { width: 280px !important; }
        .admin-quick-links { display: flex !important; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 1.5rem; }
        .admin-quick-links a { flex: 1 0 auto; }
    }
    @media (min-width: 769px) {
        .admin-toggle-btn { display: none !important; }
        .admin-offcanvas { display: none !important; }
        .admin-quick-links { display: none !important; }
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

    links = [ ('/', 'Home'), ('/shop', 'Shop'), ('/blog', 'Blog'), ('/prescription', 'Rx'),
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
        <a class="navbar-brand" href="/"><i class="fas fa-pills"></i> {PHARMACY_NAME}</a>
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
        ('dashboard','fa-tachometer-alt','/admin'), ('orders','fa-shopping-cart','/admin/orders'),
        ('products','fa-pills','/admin/products'), ('prescriptions','fa-file-prescription','/admin/prescriptions'),
        ('customers','fa-users','/admin/customers'), ('users','fa-headset','/admin/users'),
        ('create-user','fa-user-plus','/admin/create-user'), ('settings','fa-cog','/admin/settings'),
        ('branches','fa-map-marker-alt','/admin/branches'), ('export','fa-download','/admin/export-orders')
    ]
    def sidebar_items():
        items = ''
        for name, icon, url in links:
            cls = 'active' if active == name else ''
            items += f'<a href="{url}" class="{cls}"><i class="fas {icon}"></i> <span>{name.replace("-"," ").title()}</span></a>'
        return items

    desktop_sidebar = f'''
    <div class="admin-desktop-sidebar d-none d-md-flex flex-column flex-shrink-0" style="width:260px; background:var(--grad); color:white; min-height:100vh; padding:1.5rem 1rem; position:fixed; top:0; left:0; z-index:1000;">
        <div class="brand" style="font-weight:800; font-size:1.6rem; margin-bottom:2rem;"><i class="fas fa-pills"></i> DawaLink</div>
        {sidebar_items()}
        <hr class="mt-auto">
        <a href="/" class="btn btn-sm btn-outline-light mb-1">View Site</a>
        <a href="/logout" class="btn btn-sm btn-outline-danger">Logout</a>
    </div>'''

    offcanvas = f'''
    <div class="offcanvas offcanvas-start admin-offcanvas" tabindex="-1" id="adminOffcanvas" style="background:var(--grad); color:white;">
        <div class="offcanvas-header"><h5 class="offcanvas-title"><i class="fas fa-pills"></i> DawaLink</h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="offcanvas"></button></div>
        <div class="offcanvas-body"><div class="d-flex flex-column">{sidebar_items()}<hr><a href="/" class="btn btn-sm btn-outline-light mb-1">View Site</a><a href="/logout" class="btn btn-sm btn-outline-danger">Logout</a></div></div>
    </div>'''

    quick_links = ''.join(f'<a href="{url}" class="btn btn-outline-primary btn-sm rounded-pill flex-fill text-center mx-1">{name.replace("-"," ").title()}</a>' for name,_,url in links)
    mobile_quick = f'<div class="admin-quick-links">{quick_links}</div>'
    toggle_btn = '<button class="btn btn-outline-primary admin-toggle-btn d-md-none mb-3" type="button" data-bs-toggle="offcanvas" data-bs-target="#adminOffcanvas"><i class="fas fa-bars"></i> Menu</button>'

    return f"""<!DOCTYPE html><html><head><title>{title} – Admin</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>
    body {{ display: flex; margin:0; }} .main-admin {{ flex:1; padding:2rem; background:#f4f6f9; min-height:100vh; }}
    .admin-desktop-sidebar a {{ color: rgba(255,255,255,0.85); display: flex; align-items: center; padding: 0.7rem 1rem; text-decoration: none; border-radius: 12px; margin-bottom: 4px; transition: all 0.2s; }}
    .admin-desktop-sidebar a:hover, .admin-desktop-sidebar a.active {{ background: #F4A261; color: #0A3D62; font-weight: 600; }}
    .admin-desktop-sidebar a i {{ width: 24px; margin-right: 12px; }}
    .offcanvas-body a {{ color: rgba(255,255,255,0.85); display: flex; align-items: center; padding: 0.7rem 1rem; text-decoration: none; border-radius: 12px; margin-bottom: 4px; }}
    .offcanvas-body a:hover, .offcanvas-body a.active {{ background: #F4A261; color: #0A3D62; font-weight: 600; }}
    .offcanvas-body a i {{ width: 24px; margin-right: 12px; }}
    .stat-card {{ background: white; border-radius: 16px; padding: 1.5rem; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }}
    .table-light th {{ background: #f8f9fa; font-weight: 600; }}
    .admin-quick-links {{ display: none; }}
    @media (max-width: 768px) {{
        .admin-desktop-sidebar {{ display: none !important; }} .admin-toggle-btn {{ display: block !important; }}
        .admin-offcanvas {{ width: 280px !important; }} .admin-quick-links {{ display: flex !important; flex-wrap: wrap; gap:0.5rem; margin-bottom:1.5rem; }}
    }}
</style></head><body style="display:flex; margin:0;">
{desktop_sidebar}
{offcanvas}
<div class="main-admin">
    {toggle_btn}
    {mobile_quick}
    <h2>{title}</h2><hr>{body}
</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body></html>"""

# ---------- Public routes ----------
@app.route('/')
def home():
    if session.get('user_id'):
        quick_links = '''
        <div class="d-md-none mt-4">
            <h5 class="text-center mb-3 fw-bold">Quick Links</h5>
            <div class="row g-3 text-center">
                <div class="col-4"><a href="/shop" class="card p-3 text-decoration-none h-100 shadow-sm rounded-4"><i class="fas fa-store fa-2x text-primary"></i><div class="mt-2 fw-bold small">Shop</div></a></div>
                <div class="col-4"><a href="/blog" class="card p-3 text-decoration-none h-100 shadow-sm rounded-4"><i class="fas fa-newspaper fa-2x text-primary"></i><div class="mt-2 fw-bold small">Blog</div></a></div>
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
                <div class="col-4"><a href="/blog" class="card p-3 text-decoration-none h-100 shadow-sm rounded-4"><i class="fas fa-newspaper fa-2x text-primary"></i><div class="mt-2 fw-bold small">Blog</div></a></div>
                <div class="col-4"><a href="/prescription" class="card p-3 text-decoration-none h-100 shadow-sm rounded-4"><i class="fas fa-file-prescription fa-2x text-primary"></i><div class="mt-2 fw-bold small">Rx</div></a></div>
                <div class="col-4"><a href="/branches" class="card p-3 text-decoration-none h-100 shadow-sm rounded-4"><i class="fas fa-map-marker-alt fa-2x text-primary"></i><div class="mt-2 fw-bold small">Branches</div></a></div>
                <div class="col-4"><a href="/cart" class="card p-3 text-decoration-none h-100 shadow-sm rounded-4"><i class="fas fa-shopping-cart fa-2x text-primary"></i><div class="mt-2 fw-bold small">Cart</div></a></div>
                <div class="col-4"><a href="/login" class="card p-3 text-decoration-none h-100 shadow-sm rounded-4"><i class="fas fa-sign-in-alt fa-2x text-primary"></i><div class="mt-2 fw-bold small">Login</div></a></div>
                <div class="col-4"><a href="/register" class="card p-3 text-decoration-none h-100 shadow-sm rounded-4"><i class="fas fa-user-plus fa-2x text-primary"></i><div class="mt-2 fw-bold small">Register</div></a></div>
            </div>
        </div>'''

    body = f"""<div class="hero">
        <h1>Your Health, Delivered with Care</h1>
        <p>Genuine medicines, premium supplements, and personal care products – delivered swiftly to your doorstep across Kenya.</p>
        <a href="/shop" class="btn btn-light btn-lg me-2 rounded-pill px-4">Shop Now</a>
        <a href="/prescription" class="btn btn-outline-light btn-lg rounded-pill px-4">Upload Prescription</a>
    </div>
    {quick_links}
    <div class="row mt-5 g-4">
        <div class="col-md-4"><div class="card p-4 text-center h-100 border-0 shadow-sm rounded-4"><i class="fas fa-certificate fa-3x text-success mb-3"></i><h5>100% Genuine</h5><p>All products sourced from licensed pharmacies.</p></div></div>
        <div class="col-md-4"><div class="card p-4 text-center h-100 border-0 shadow-sm rounded-4"><i class="fas fa-truck-fast fa-3x text-warning mb-3"></i><h5>Lightning Delivery</h5><p>Reliable courier across Kenya.</p></div></div>
        <div class="col-md-4"><div class="card p-4 text-center h-100 border-0 shadow-sm rounded-4"><i class="fas fa-headset fa-3x text-info mb-3"></i><h5>24/7 Support</h5><p>Pharmacist-led customer care.</p></div></div>
    </div>"""
    user = None
    if session.get('user_id'):
        user = {'full_name': session.get('user_name', 'User'), 'is_admin': session.get('is_admin', False)}
    return public_page("Home", body, user)

@app.route('/blog')
def blog():
    posts = [{"title":"Understanding Pain Relief","date":"2026-04-15","snippet":"Learn about OTC pain relievers."},{"title":"Essential Baby Care","date":"2026-04-10","snippet":"A guide for new parents."},{"title":"Probiotics & Gut Health","date":"2026-04-02","snippet":"How probiotics improve wellness."}]
    html = ''.join(f"""<div class="card mb-4 shadow-sm border-0 rounded-4 overflow-hidden"><div class="row g-0"><div class="col-md-4 bg-light d-flex align-items-center justify-content-center p-4"><i class="fas fa-newspaper fa-4x text-muted"></i></div><div class="col-md-8"><div class="card-body"><h5 class="fw-bold">{p['title']}</h5><small class="text-muted"><i class="far fa-calendar-alt me-1"></i>{p['date']}</small><p class="mt-2">{p['snippet']}</p></div></div></div></div>""" for p in posts)
    return public_page("Blog", html)

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
        img = f'<img src="{p.get("image_url")}" class="card-img-top" style="height:180px;object-fit:cover;">' if p.get("image_url") else '<div class="bg-light d-flex align-items-center justify-content-center" style="height:180px;"><i class="fas fa-pills fa-3x text-muted"></i></div>'
        rows += f'''<div class="col-6 col-md-4 mb-4"><div class="card h-100">{img}<div class="card-body"><h5 class="fw-bold">{p['name']}</h5><p class="text-muted small">{p['category']}</p>
        <div class="d-flex justify-content-between align-items-center"><span class="h5" style="color:var(--blue);">KSh {p['price']}</span>
        <form action="/cart/add" method="POST"><input type="hidden" name="productId" value="{p['id']}">
        <input type="number" name="quantity" value="1" min="1" class="form-control form-control-sm d-inline-block" style="width:60px;">
        <button class="btn btn-primary btn-sm rounded-pill ms-1"><i class="fas fa-cart-plus"></i></button></form></div></div></div></div>'''
    pagination = ''
    total_pages = max(1, (total+per_page-1)//per_page)
    if total_pages > 1:
        pagination = '<nav><ul class="pagination justify-content-center">'
        for p in range(1, total_pages+1):
            active = 'active' if p == page else ''
            pagination += f'<li class="page-item {active}"><a class="page-link" href="/shop?page={p}&search={search}&category={category}">{p}</a></li>'
        pagination += '</ul></nav>'
    body = f'''<h2 class="fw-bold mb-4" style="color:var(--blue);">Our Products</h2>
    <form class="row g-3 mb-4"><div class="col-md-7"><input class="form-control" name="search" value="{search}" placeholder="Search..."></div>
    <div class="col-md-3"><select class="form-select" name="category"><option value="">All</option><option value="Supplements" {'selected' if category=='Supplements' else ''}>Supplements</option><option value="Pain Relief" {'selected' if category=='Pain Relief' else ''}>Pain Relief</option><option value="Baby Care" {'selected' if category=='Baby Care' else ''}>Baby Care</option><option value="Women Health" {'selected' if category=='Women Health' else ''}>Women Health</option></select></div>
    <div class="col-md-2"><button class="btn btn-primary w-100">Filter</button></div></form>
    <div class="row">{rows}</div>{pagination}'''
    user = None
    if session.get('user_id'): user = {'full_name': session.get('user_name','User'), 'is_admin': session.get('is_admin', False)}
    return public_page("Shop", body, user)

# ---------- Cart ----------
@app.route('/cart/add', methods=['POST'])
def add_to_cart():
    pid = request.form['productId']; qty = int(request.form.get('quantity',1))
    prod = supabase.table('products').select('id,name,price').eq('id',pid).single().execute().data
    if not prod: return 'Product not found',404
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
    referrer = request.referrer
    if referrer and ('/shop' in referrer or '/' == referrer):
        redirect_url = referrer + ('&' if '?' in referrer else '?') + 'added=1'
    else:
        redirect_url = '/shop?added=1'
    return redirect(redirect_url)

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
    if not items: return public_page("Cart",'<h2>Your Cart</h2><p>Cart is empty.</p><a href="/shop" class="btn btn-primary">Start Shopping</a>')
    rows=''.join(f'<div class="card p-3 mb-2 d-flex flex-row justify-content-between align-items-center"><div><h5>{i["name"]}</h5><small>Qty: {i["qty"]} × KSh {i["price"]}</small></div><div><h4 class="text-success">KSh {i["price"]*i["qty"]:.2f}</h4><a href="/cart/remove/{i["productId"]}" class="btn btn-sm btn-outline-danger"><i class="fas fa-trash"></i></a></div></div>' for i in items)
    body=f'<h2>Your Cart</h2>{rows}<hr><div class="d-flex justify-content-between"><h4>Total</h4><h4>KSh {total:.2f}</h4></div><a href="/checkout" class="btn btn-success w-100 py-3 mt-3">Proceed to Checkout</a>'
    user = None
    if session.get('user_id'): user = {'full_name':session.get('user_name','User'),'is_admin':session.get('is_admin',False)}
    return public_page("Cart", body, user)

@app.route('/cart/remove/<pid>')
def remove_cart(pid):
    if session.get('user_id'):
        try: supabase.table('cart').delete().eq('user_id',session['user_id']).eq('product_id',pid).execute()
        except: pass
    else:
        cart = [i for i in session.get('cart',[]) if i['productId']!=pid]
        session['cart']=cart
    return redirect('/cart')

# ---------- Checkout ----------
@app.route('/checkout', methods=['GET','POST'])
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
                    <div class="col-sm-6"><h5>Invoice</h5><p><strong>Order #:</strong> {str(oid)[:8]}<br><strong>Date:</strong> {order_data['created_at'][:10]}<br><strong>Status:</strong> <span class="badge bg-warning text-dark">{order_data['order_status']}</span></p></div>
                    <div class="col-sm-6 text-sm-end"><h5>Customer</h5><p>{order_data.get('shipping_name','')}<br>{order_data.get('shipping_phone','')}<br>{order_data.get('shipping_address','')}, {order_data.get('shipping_city','')}</p></div>
                </div>
                <table class="table table-bordered">
                    <thead class="table-light"><tr><th>Product</th><th>Qty</th><th>Unit Price</th><th>Total</th></tr></thead>
                    <tbody>{"".join(f'<tr><td>{i["product_name"]}</td><td>{i["quantity"]}</td><td>KSh {i["unit_price"]}</td><td>KSh {i["total_price"]}</td></tr>' for i in items_data)}</tbody>
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
    return public_page("Checkout",'''<h2>Checkout</h2><form method="post" style="max-width:500px;">
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
    items = supabase.table('order_items').select('*').eq('order_id',oid).execute().data
    if not order: return "Order not found", 404
    item_rows = ''.join(f'<tr><td>{i["product_name"]}</td><td>{i["quantity"]}</td><td>KSh {i["unit_price"]}</td><td>KSh {i["total_price"]}</td></tr>' for i in items)
    html = f"""<!DOCTYPE html><html><head><title>Receipt #{oid}</title>
    <style>body{{font-family:'Segoe UI',sans-serif;padding:2rem;}} table{{width:100%;border-collapse:collapse;}} th,td{{padding:10px;border:1px solid #ddd;}} th{{background:#0A3D62;color:white;}} .total-row td{{font-weight:bold;}}</style></head><body>
    <h2>{PHARMACY_NAME} - Receipt #{oid}</h2>
    <p><strong>Date:</strong> {order['created_at'][:10]}<br><strong>Customer:</strong> {order.get('shipping_name','')}</p>
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
        except Exception as e:
            return public_page("Upload Error",
                f'<div class="alert alert-danger mt-5"><h4>Upload Failed</h4><p>{str(e)}</p></div><a href="/prescription">Try again</a>')
    return public_page("Upload Prescription", '''<div class="row justify-content-center mt-5"><div class="col-md-6 col-lg-5"><div class="card shadow-lg rounded-4 p-4"><div class="text-center mb-4"><i class="fas fa-file-prescription fa-3x text-primary"></i><h3 class="fw-bold mt-2">Upload Prescription</h3></div>
    <form method="post" enctype="multipart/form-data">
        <div class="mb-3"><input class="form-control" name="customer_name" placeholder="Your Name" required></div>
        <div class="mb-3"><input class="form-control" name="customer_phone" placeholder="Phone Number" required></div>
        <div class="mb-3"><textarea class="form-control" name="notes" rows="3" placeholder="Additional notes (optional)"></textarea></div>
        <div class="mb-3"><input class="form-control" type="file" name="prescription_file" accept="image/*,.pdf" required></div>
        <button class="btn btn-primary w-100 py-2 rounded-pill">Submit Prescription</button></form></div></div></div>''')

# ---------- Public Branches page with Map ----------
@app.route('/branches')
def branches():
    branches = supabase.table('branches').select('*').order('name').execute().data or []
    # Default to Nairobi, or first branch's coordinates
    map_lat = -1.2921
    map_lng = 36.8219
    if branches and branches[0].get('latitude') and branches[0].get('longitude'):
        map_lat = float(branches[0]['latitude'])
        map_lng = float(branches[0]['longitude'])

    markers_js = ''
    for b in branches:
        if b.get('latitude') is not None and b.get('longitude') is not None:
            name = b['name'].replace("'", "\\'")
            addr = (b.get('address') or '').replace("'", "\\'")
            phone = (b.get('phone') or '').replace("'", "\\'")
            popup = f"<b>{name}</b><br>{addr}<br>{phone}"
            markers_js += f"L.marker([{b['latitude']}, {b['longitude']}]).addTo(map).bindPopup('{popup}');\n"

    branch_cards = ''
    for b in branches:
        branch_cards += f'''<div class="col-md-6 col-lg-4 mb-4">
            <div class="card h-100 shadow-sm border-0 rounded-4">
                <div class="card-body">
                    <h5 class="fw-bold"><i class="fas fa-map-marker-alt text-danger me-2"></i>{b['name']}</h5>
                    <p class="mb-1"><i class="fas fa-map-pin me-2 text-muted"></i>{b.get('address','')}</p>
                    <p class="mb-0"><i class="fas fa-phone me-2 text-muted"></i>{b.get('phone','')}</p>
                </div>
            </div>
        </div>'''

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
def about(): return public_page("About",f'<h2>About {PHARMACY_NAME}</h2><p>Your trusted online pharmacy since 2026.</p>')

@app.route('/contact', methods=['GET','POST'])
def contact():
    if request.method=='POST':
        try: supabase.table('inquiries').insert({k:request.form[k] for k in ['name','email','message']}).execute()
        except: pass
        return redirect('/contact?sent=1')
    sent = 'Message sent!' if request.args.get('sent') else ''
    return public_page("Contact",f'<h2>Contact</h2><form method="post"><input class="form-control mb-2" name="name" placeholder="Name"><input class="form-control mb-2" name="email" type="email" placeholder="Email"><textarea class="form-control mb-2" name="message" rows="4" placeholder="Message"></textarea><button class="btn btn-primary">Send</button></form>{sent}')

# ---------- Authentication ----------
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        email=request.form['email']; pwd=request.form['password']
        user_res=supabase.table('users').select('*').eq('email',email).execute()
        if not user_res.data: return public_page("Login",'<div class="alert alert-danger">Invalid credentials</div><a href="/login">Try again</a>')
        user=user_res.data[0]
        if not bcrypt.checkpw(pwd.encode(),user['password_hash'].encode()): return public_page("Login",'<div class="alert alert-danger">Invalid credentials</div><a href="/login">Try again</a>')
        session['user_id']=user['id']; session['user_name']=user['full_name']; session['is_admin']=user.get('is_admin',False)
        return redirect('/')
    form = """<div class="row justify-content-center mt-5"><div class="col-md-5 col-lg-4"><div class="card shadow-lg rounded-4 p-4"><div class="text-center mb-4"><i class="fas fa-pills fa-3x text-primary"></i><h3 class="fw-bold mt-2">Welcome Back</h3><p class="text-muted">Sign in to your account</p></div>
    <form method="post"><div class="mb-3"><input class="form-control" name="email" type="email" placeholder="Email" required></div>
    <div class="mb-3"><div class="input-group"><input class="form-control" name="password" type="password" id="loginPassword" placeholder="Password" required><span class="input-group-text toggle-password" data-target="loginPassword"><i class="far fa-eye"></i></span></div></div>
    <button class="btn btn-primary w-100 py-2 rounded-pill">Sign In</button></form><p class="mt-3 text-center"><a href="/register">Create an account</a> · <a href="/">Home</a></p></div></div></div>"""
    return public_page("Login", form)

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method=='POST':
        name=request.form['full_name']; email=request.form['email']; pwd=request.form['password']
        hashed=bcrypt.hashpw(pwd.encode(),bcrypt.gensalt()).decode()
        try: supabase.table('users').insert({'full_name':name,'email':email,'password_hash':hashed}).execute()
        except: return public_page("Register",'<div class="alert alert-danger">Email already exists.</div><a href="/register">Try again</a>')
        return public_page("Registration Submitted",'<div class="text-center mt-5"><i class="fas fa-check-circle fa-5x text-success mb-3"></i><h2>Account Created</h2><p>Your account is pending approval.</p><a href="/" class="btn btn-primary rounded-pill mt-3">Home</a></div>')
    form = """<div class="row justify-content-center mt-5"><div class="col-md-5 col-lg-4"><div class="card shadow-lg rounded-4 p-4"><div class="text-center mb-4"><i class="fas fa-user-plus fa-3x text-primary"></i><h3 class="fw-bold mt-2">Create Account</h3></div>
    <form method="post"><div class="mb-3"><input class="form-control" name="full_name" placeholder="Full Name" required></div>
    <div class="mb-3"><input class="form-control" name="email" type="email" placeholder="Email" required></div>
    <div class="mb-3"><div class="input-group"><input class="form-control" name="password" type="password" id="registerPassword" placeholder="Password" required><span class="input-group-text toggle-password" data-target="registerPassword"><i class="far fa-eye"></i></span></div></div>
    <button class="btn btn-primary w-100 py-2 rounded-pill">Register</button></form><p class="mt-3 text-center"><a href="/login">Already have an account?</a></p></div></div></div>"""
    return public_page("Register", form)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/my-account')
def my_account():
    if not session.get('user_id'): return redirect('/login')
    orders = supabase.table('orders').select('*').eq('user_id',session['user_id']).order('created_at',desc=True).execute().data or []
    html=''.join(f'<div class="card mb-3 shadow-sm"><div class="card-body"><strong>Order #{str(o["id"])[:8]}</strong><br><small>{o["created_at"][:10]}</small><br>Total: KSh {o["total_amount"]}<br><span class="badge bg-info">{o.get("order_status","")}</span></div></div>' for o in orders)
    user={'full_name':session.get('user_name','User'),'is_admin':session.get('is_admin',False)}
    return public_page("My Orders",f'<h2 class="mb-4">My Orders</h2>{html or "<p>No orders yet.</p>"}',user)

# ---------- Admin decorator (MUST be defined before admin routes) ----------
def admin_required(f):
    @wraps(f)
    def decorated(*args,**kwargs):
        if not session.get('is_admin'): return redirect('/login')
        return f(*args,**kwargs)
    return decorated

# ---------- Admin routes ----------
@app.route('/admin')
@admin_required
def admin_dashboard():
    orders = supabase.table('orders').select('*').order('created_at',desc=True).limit(10).execute().data or []
    total_sales = sum(o['total_amount'] for o in orders) if orders else 0
    total_orders = supabase.table('orders').select('count',count='exact').execute().count
    total_products = supabase.table('products').select('count',count='exact').execute().count
    rows = ''.join(f'<tr><td>#{str(o["id"])[:8]}</td><td>{o.get("shipping_name","Guest")}</td><td>KSh {o["total_amount"]}</td><td><span class="badge {"bg-warning text-dark" if o.get("order_status")=="pending" else "bg-success"}">{o.get("order_status","pending")}</span></td></tr>' for o in orders)
    body = f'''<div class="row g-4 mb-4">
    <div class="col-sm-6 col-md-3"><div class="stat-card"><h5 class="text-success"><i class="fas fa-money-bill-wave me-2"></i>Total Sales</h5><h3 class="fw-bold">KSh {total_sales:,.2f}</h3></div></div>
    <div class="col-sm-6 col-md-3"><div class="stat-card"><h5 class="text-warning"><i class="fas fa-shopping-cart me-2"></i>Orders</h5><h3 class="fw-bold">{total_orders}</h3></div></div>
    <div class="col-sm-6 col-md-3"><div class="stat-card"><h5 class="text-primary"><i class="fas fa-pills me-2"></i>Products</h5><h3 class="fw-bold">{total_products}</h3></div></div>
    <div class="col-sm-6 col-md-3"><div class="stat-card"><h5 class="text-danger"><i class="fas fa-users me-2"></i>Customers</h5><h3 class="fw-bold">-</h3></div></div></div>
    <h4>Recent Orders</h4><div class="card border-0 shadow-sm rounded-4 p-3"><table class="table table-hover align-middle"><thead class="table-light"><tr><th>ID</th><th>Customer</th><th>Total</th><th>Status</th></tr></thead><tbody>{rows}</tbody></table></div>'''
    return admin_page("Dashboard", body)

@app.route('/admin/orders')
@admin_required
def admin_orders():
    orders = supabase.table('orders').select('*').order('created_at',desc=True).execute().data or []
    rows = ''.join(
        f'''<tr><td>#{str(o["id"])[:8]}</td><td>{o.get("shipping_name","Guest")}</td><td>KSh {o["total_amount"]}</td>
        <td><div class="d-flex align-items-center">
            <form method="post" action="/admin/order/{o["id"]}/status" class="d-flex">
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
    body = f'<div class="card border-0 shadow-sm rounded-4 p-3"><table class="table table-hover align-middle"><thead class="table-light"><tr><th>ID</th><th>Customer</th><th>Total</th><th>Status / Action</th></tr></thead><tbody>{rows}</tbody></table></div>'
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
    item_rows = ''.join(f'<tr><td>{i["product_name"]}</td><td>{i["quantity"]}</td><td>KSh {i["unit_price"]}</td><td>KSh {i["total_price"]}</td></tr>' for i in items)
    html = f"""<!DOCTYPE html><html><head><title>Invoice #{oid}</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
    body {{ font-family: 'Segoe UI', sans-serif; padding: 2rem; background: #fff; }}
    .invoice-box {{ max-width: 800px; margin: auto; border: 1px solid #eee; box-shadow: 0 0 10px rgba(0,0,0,0.05); padding: 2rem; }}
    .invoice-header {{ border-bottom: 2px solid #0A3D62; padding-bottom: 1rem; margin-bottom: 1.5rem; }}
    .invoice-header h2 {{ color: #0A3D62; font-weight: 700; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th {{ background: #0A3D62; color: white; padding: 10px; text-align: left; }}
    td {{ padding: 10px; border-bottom: 1px solid #ddd; }}
    .total-row td {{ font-weight: bold; border-top: 2px solid #0A3D62; }}
    .no-print {{ margin-bottom: 1rem; text-align: right; }}
</style></head><body>
<div class="invoice-box">
    <div class="no-print">
        <button onclick="window.print()" class="btn btn-primary rounded-pill"><i class="fas fa-print me-2"></i> Print</button>
        <a href="/admin/order/{oid}/invoice?download=1" class="btn btn-outline-primary rounded-pill ms-2"><i class="fas fa-download me-2"></i> Download</a>
    </div>
    <div class="invoice-header">
        <div class="row">
            <div class="col-6"><h2>{PHARMACY_NAME}</h2><p>Mombasa Road, Taji Mall, Nairobi<br>Tel: {PHARMACY_PHONE}<br>Email: {PHARMACY_EMAIL}</p></div>
            <div class="col-6 text-end"><h3>INVOICE</h3><p><strong>Invoice #:</strong> {oid}<br><strong>Date:</strong> {order['created_at'][:10]}<br><strong>Status:</strong> {order['order_status']}</p></div>
        </div>
    </div>
    <div class="row mb-4"><div class="col-6"><strong>Bill To:</strong><br>{order.get('shipping_name','')}<br>{order.get('shipping_phone','')}<br>{order.get('shipping_address','')}, {order.get('shipping_city','')}</div></div>
    <table>
        <thead><tr><th>Product</th><th>Qty</th><th>Unit Price</th><th>Total</th></tr></thead>
        <tbody>{item_rows}</tbody>
        <tfoot><tr class="total-row"><td colspan="3" class="text-end">Grand Total</td><td>KSh {order['total_amount']}</td></tr></tfoot>
    </table>
    <p class="mt-3 text-muted">Thank you for your business!</p>
</div>
</body></html>"""

    if request.args.get('download') == '1':
        resp = make_response(html)
        resp.headers['Content-Disposition'] = f'attachment; filename="invoice_{oid}.html"'
        resp.headers['Content-Type'] = 'text/html'
        return resp
    return html

# ---------- Admin: Branches management ----------
@app.route('/admin/branches')
@admin_required
def admin_branches():
    branches = supabase.table('branches').select('*').order('name').execute().data or []
    rows = ''.join(
        f'''<tr>
            <td>{b['name']}</td>
            <td>{b.get('address','')}</td>
            <td>{b.get('phone','')}</td>
            <td>
                <a href="/admin/edit-branch/{b['id']}" class="btn btn-sm btn-warning me-1">Edit</a>
                <a href="/admin/delete-branch/{b['id']}" class="btn btn-sm btn-danger" onclick="return confirm('Delete this branch?')">Delete</a>
            </td>
        </tr>''' for b in branches
    )
    body = f'''
    <a href="/admin/add-branch" class="btn btn-success mb-3"><i class="fas fa-plus me-2"></i>Add Branch</a>
    <div class="card border-0 shadow-sm rounded-4 p-3">
        <table class="table table-hover align-middle">
            <thead class="table-light"><tr><th>Name</th><th>Address</th><th>Phone</th><th></th></tr></thead>
            <tbody>{rows or '<tr><td colspan="4" class="text-center">No branches yet.</td></tr>'}</tbody>
        </table>
    </div>'''
    return admin_page("Manage Branches", body, active='branches')

@app.route('/admin/add-branch', methods=['GET','POST'])
@admin_required
def add_branch():
    if request.method == 'POST':
        name = request.form['name']
        address = request.form.get('address','')
        phone = request.form.get('phone','')
        lat = request.form.get('latitude')
        lng = request.form.get('longitude')
        data = {'name': name, 'address': address, 'phone': phone}
        if lat: data['latitude'] = float(lat)
        if lng: data['longitude'] = float(lng)
        supabase.table('branches').insert(data).execute()
        return redirect('/admin/branches')
    return admin_page("Add Branch", '''<form method="post" style="max-width:500px;">
    <input class="form-control mb-2" name="name" placeholder="Branch Name" required>
    <input class="form-control mb-2" name="address" placeholder="Address">
    <input class="form-control mb-2" name="phone" placeholder="Phone">
    <div class="row"><div class="col"><input class="form-control mb-2" type="number" step="any" name="latitude" placeholder="Latitude"></div>
    <div class="col"><input class="form-control mb-2" type="number" step="any" name="longitude" placeholder="Longitude"></div></div>
    <button class="btn btn-primary w-100">Add Branch</button></form>''', active='branches')

@app.route('/admin/edit-branch/<int:bid>', methods=['GET','POST'])
@admin_required
def edit_branch(bid):
    if request.method == 'POST':
        upd = {
            'name': request.form['name'],
            'address': request.form.get('address',''),
            'phone': request.form.get('phone','')
        }
        lat = request.form.get('latitude')
        lng = request.form.get('longitude')
        if lat: upd['latitude'] = float(lat)
        if lng: upd['longitude'] = float(lng)
        supabase.table('branches').update(upd).eq('id', bid).execute()
        return redirect('/admin/branches')
    b = supabase.table('branches').select('*').eq('id', bid).single().execute().data
    if not b: return "Branch not found", 404
    return admin_page("Edit Branch", f'''<form method="post" style="max-width:500px;">
    <input class="form-control mb-2" name="name" value="{b['name']}" required>
    <input class="form-control mb-2" name="address" value="{b.get('address','')}">
    <input class="form-control mb-2" name="phone" value="{b.get('phone','')}">
    <div class="row"><div class="col"><input class="form-control mb-2" type="number" step="any" name="latitude" value="{b.get('latitude','')}" placeholder="Latitude"></div>
    <div class="col"><input class="form-control mb-2" type="number" step="any" name="longitude" value="{b.get('longitude','')}" placeholder="Longitude"></div></div>
    <button class="btn btn-primary w-100">Update Branch</button></form>''', active='branches')

@app.route('/admin/delete-branch/<int:bid>')
@admin_required
def delete_branch(bid):
    supabase.table('branches').delete().eq('id', bid).execute()
    return redirect('/admin/branches')

# ---------- Other admin routes (Products, Prescriptions, etc.) ----------
@app.route('/admin/products')
@admin_required
def admin_products():
    prods = supabase.table('products').select('*').order('name').execute().data or []
    rows = ''.join(f'<tr><td>{p["name"]}</td><td>{p["category"]}</td><td>{p["price"]}</td><td>{p["stock"]}</td><td><a href="/admin/edit-product/{p["id"]}" class="btn btn-sm btn-warning me-1">Edit</a><a href="/admin/delete-product/{p["id"]}" class="btn btn-sm btn-danger" onclick="return confirm(\'Delete?\')">Delete</a></td></tr>' for p in prods)
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
    return admin_page("Add Product", '''<form method="post" enctype="multipart/form-data" style="max-width:500px;">
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
    <input class="form-control mb-2" name="name" value="{p['name']}" required>
    <textarea class="form-control mb-2" name="description">{p.get('description','')}</textarea>
    <input class="form-control mb-2" name="category" value="{p['category']}" required>
    <div class="row"><div class="col"><input class="form-control mb-2" type="number" step="0.01" name="price" value="{p['price']}" required></div><div class="col"><input class="form-control mb-2" type="number" name="stock" value="{p['stock']}" required></div></div>
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
    rx = supabase.table('prescriptions').select('*').order('created_at',desc=True).execute().data or []
    items = ''.join(f'<div class="card mb-2 p-3"><strong>{r["customer_name"]}</strong><br>Phone: {r["customer_phone"]}<br><a href="{r.get("file_url","#")}" target="_blank" class="btn btn-sm btn-primary mt-2">View File</a></div>' for r in rx)
    return admin_page("Prescriptions", items or '<p>No prescriptions yet.</p>', active='prescriptions')

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
    return admin_page("Customers", f'<div class="card border-0 shadow-sm rounded-4 p-3"><table class="table table-hover align-middle"><thead class="table-light"><tr><th>Name</th><th>Email</th><th>Phone</th><th>Orders</th><th>Total Spent</th></tr></thead><tbody>{rows}</tbody></table></div>', active='customers')

@app.route('/admin/users')
@admin_required
def admin_users():
    users = supabase.table('users').select('*').execute().data or []
    rows = ''.join(f'<tr><td>{u["full_name"]}</td><td>{u["email"]}</td><td><span class="badge {"bg-success" if u.get("approved") else "bg-warning text-dark"}">{"Approved" if u.get("approved") else "Pending"}</span></td><td><a href="/admin/approve-user/{u["id"]}" class="btn btn-sm btn-success me-1">Approve</a><a href="/admin/disable-user/{u["id"]}" class="btn btn-sm btn-danger">Disable</a></td></tr>' for u in users)
    return admin_page("Customer Care", f'<div class="card border-0 shadow-sm rounded-4 p-3"><table class="table table-hover align-middle"><thead class="table-light"><tr><th>Name</th><th>Email</th><th>Status</th><th>Action</th></tr></thead><tbody>{rows}</tbody></table></div>', active='users')

@app.route('/admin/approve-user/<uid>')
@admin_required
def approve_user(uid): supabase.table('users').update({'approved':True}).eq('id',uid).execute(); return redirect('/admin/users')

@app.route('/admin/disable-user/<uid>')
@admin_required
def disable_user(uid): supabase.table('users').update({'approved':False}).eq('id',uid).execute(); return redirect('/admin/users')

@app.route('/admin/create-user', methods=['GET','POST'])
@admin_required
def create_user():
    if request.method=='POST':
        name=request.form['full_name']; email=request.form['email']; pwd=request.form['password']; is_admin=request.form.get('is_admin')=='on'
        hashed=bcrypt.hashpw(pwd.encode(),bcrypt.gensalt()).decode()
        try: supabase.table('users').insert({'full_name':name,'email':email,'password_hash':hashed,'is_admin':is_admin,'approved':True}).execute()
        except: return admin_page("Add Agent",'<div class="alert alert-danger">Email exists.</div><a href="/admin/create-user">Try again</a>', active='create-user')
        return redirect('/admin/users')
    return admin_page("Add Agent",'''<form method="post" style="max-width:500px;">
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
    return admin_page("Settings",f'{msg}<form method="post" style="max-width:400px;"><input class="form-control mb-2" type="password" name="new_password" placeholder="New Password"><button class="btn btn-primary">Update</button></form>', active='settings')

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
    return make_response(json.dumps({"name":f"{PHARMACY_NAME} - Online Pharmacy","short_name":PHARMACY_NAME,"start_url":"/","display":"standalone","icons":[{"src":"/static/icon-192.png","sizes":"192x192","type":"image/png"},{"src":"/static/icon-512.png","sizes":"512x512","type":"image/png"}]}),{'Content-Type':'application/manifest+json'})

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
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',8080)))
