import os
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="a-very-secret-key-change-me")

# ---------- Branding ----------
APP_NAME = "DawaLink"
APP_TAGLINE = "Your Trusted Online Pharmacy"
PRIMARY_COLOR = "#0d6efd"

# ---------- Supabase clients ----------
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
service_supabase = create_client(SUPABASE_URL, SERVICE_ROLE_KEY) if SERVICE_ROLE_KEY else None

# ---------- Token & Profile helpers ----------
def get_valid_session(request: Request):
    token = request.session.get("access_token")
    refresh = request.session.get("refresh_token")
    if not token or not refresh:
        return None
    try:
        supabase.auth.set_session(token, refresh)
        supabase.auth.get_user()
        return supabase
    except:
        try:
            res = supabase.auth.refresh_session(refresh)
            request.session["access_token"] = res.session.access_token
            request.session["refresh_token"] = res.session.refresh_token
            supabase.auth.set_session(res.session.access_token, res.session.refresh_token)
            return supabase
        except:
            return None

def get_user_profile(sup: Client):
    user = sup.auth.get_user().user
    return sup.table("profiles").select("*").eq("user_id", user.id).single().execute()

# ---------- HTML Components ----------
BOOTSTRAP = '<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">'
CUSTOM_CSS = f"""
<style>
  body {{ background-color: #f4f6f9; font-family: 'Segoe UI', system-ui, sans-serif; }}
  .navbar {{ box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
  .card {{ border: none; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); transition: transform 0.2s; }}
  .card:hover {{ transform: translateY(-3px); box-shadow: 0 6px 16px rgba(0,0,0,0.1); }}
  .admin-sidebar {{ background-color: #1e293b; color: white; min-height: 100vh; }}
  .admin-sidebar a {{ color: #cbd5e1; padding: 10px; display: block; border-radius: 6px; text-decoration: none; }}
  .admin-sidebar a:hover {{ background-color: #334155; color: white; }}
  .metric-card {{ background: white; border-radius: 12px; padding: 20px; }}
  .metric-card h3 {{ font-size: 2rem; font-weight: bold; }}
  .receipt-container {{ max-width: 600px; margin: auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
  .btn-primary {{ background-color: {PRIMARY_COLOR}; border-color: {PRIMARY_COLOR}; }}
</style>
"""

def navbar(role: str = ""):
    admin_tab = '<a class="nav-link" href="/admin"><span class="badge bg-warning text-dark">Admin</span></a>' if role == "admin" else ""
    seller_tab = '<a class="nav-link" href="/seller">My Shop</a>' if role == "seller" else ""
    return f"""
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
      <div class="container">
        <a class="navbar-brand" href="/products">💊 {APP_NAME}</a>
        <div class="navbar-nav ms-auto">
          <a class="nav-link" href="/products">Browse</a>
          <a class="nav-link" href="/cart">Cart</a>
          <a class="nav-link" href="/orders">Orders</a>
          {seller_tab}
          {admin_tab}
          <a class="nav-link" href="/logout">Logout</a>
        </div>
      </div>
    </nav>"""

NAV_GUEST = f"""
<nav class="navbar navbar-expand-lg navbar-dark bg-primary">
  <div class="container">
    <a class="navbar-brand" href="/">💊 {APP_NAME}</a>
  </div>
</nav>"""

def login_page(error: str = ""):
    alert = f'<div class="alert alert-danger">{error}</div>' if error else ""
    return f"""<!DOCTYPE html><html><head><title>Login · {APP_NAME}</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
{NAV_GUEST}
<div class="container text-center mt-5">
  <h1>{APP_NAME}</h1>
  <p class="lead">{APP_TAGLINE}</p>
</div>
<div class="container mt-3" style="max-width:400px;">
  <div class="card p-4">
    <h3 class="mb-3">Welcome back</h3>
    {alert}
    <form method="post">
      <input class="form-control mb-2" name="email" placeholder="Email" required>
      <input class="form-control mb-2" type="password" name="password" placeholder="Password" required>
      <button class="btn btn-primary w-100 mt-2">Log In</button>
    </form>
    <p class="mt-3 text-center">Don't have an account? <a href="/signup">Sign up</a></p>
  </div>
</div></body></html>"""

def signup_page(error: str = ""):
    alert = f'<div class="alert alert-danger">{error}</div>' if error else ""
    return f"""<!DOCTYPE html><html><head><title>Sign Up · {APP_NAME}</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
{NAV_GUEST}
<div class="container mt-4" style="max-width:400px;">
  <div class="card p-4">
    <h3 class="mb-3">Create your account</h3>
    {alert}
    <form method="post">
      <input class="form-control mb-2" name="full_name" placeholder="Full Name" required>
      <input class="form-control mb-2" name="email" placeholder="Email" required>
      <input class="form-control mb-2" type="password" name="password" placeholder="Password" required>
      <select class="form-control mb-2" name="role">
        <option value="buyer">Buyer</option>
        <option value="seller">Seller</option>
      </select>
      <button class="btn btn-primary w-100 mt-2">Sign Up</button>
    </form>
  </div>
</div></body></html>"""

def dashboard_page(full_name: str, role: str):
    return f"""<!DOCTYPE html><html><head><title>Dashboard · {APP_NAME}</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
{navbar(role)}
<div class="container mt-4">
  <h2>Welcome, {full_name} <span class="badge bg-info ms-2">{role}</span></h2>
  <div class="row mt-4">
    <div class="col-md-4 mb-3"><a href="/products" class="btn btn-outline-primary w-100 py-4 fs-5">🛒 Browse Products</a></div>
    <div class="col-md-4 mb-3"><a href="/cart" class="btn btn-outline-success w-100 py-4 fs-5">🧺 View Cart</a></div>
    <div class="col-md-4 mb-3"><a href="/orders" class="btn btn-outline-warning w-100 py-4 fs-5">📦 My Orders</a></div>
  </div>
</div></body></html>"""

def products_page(products_cards: str, role: str):
    return f"""<!DOCTYPE html><html><head><title>Products · {APP_NAME}</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
{navbar(role)}
<div class="container mt-4">
  <h2 class="mb-4">Available Medicines</h2>
  <form class="mb-4" method="get" action="/products">
    <div class="input-group input-group-lg">
      <input class="form-control" name="search" placeholder="Search by name or category">
      <button class="btn btn-primary">Search</button>
    </div>
  </form>
  <div class="row">
    {products_cards}
  </div>
</div></body></html>"""

PRODUCT_CARD = """
<div class="col-md-4 mb-4">
  <div class="card h-100 p-3">
    <div class="card-body">
      <h5 class="card-title fw-bold">{name}</h5>
      <p class="card-text">{description}</p>
      <p><strong>Category:</strong> {category} | <strong>Stock:</strong> {stock}</p>
      <h3 class="text-success">KSh {price}</h3>
      <form action="/cart/add/{id}" method="get" class="d-flex align-items-center mt-3">
        <input type="number" name="quantity" value="1" min="1" max="{stock}" class="form-control me-2" style="width:80px;">
        <button type="submit" class="btn btn-primary">Add to Cart</button>
      </form>
    </div>
  </div>
</div>"""

def cart_page(cart_items_html: str, total: str, role: str):
    return f"""<!DOCTYPE html><html><head><title>Cart · {APP_NAME}</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
{navbar(role)}
<div class="container mt-4">
  <h2>Your Cart</h2>
  {cart_items_html}
  <hr>
  <div class="text-end">
    <h4>Total: KSh {total}</h4>
    <form method="post" action="/cart/checkout" class="row g-2 align-items-center mt-3">
      <div class="col-auto">
        <label class="form-label me-2">Payment:</label>
        <select class="form-select" name="payment_method">
          <option value="cash_on_delivery">Cash on Delivery</option>
          <option value="mobile_money">M‑Pesa</option>
        </select>
      </div>
      <div class="col-auto">
        <button type="submit" class="btn btn-success">Place Order</button>
      </div>
    </form>
  </div>
</div></body></html>"""

CART_ITEM = """
<div class="card mb-3 p-3">
  <div class="row align-items-center">
    <div class="col-md-4">
      <h5>{name}</h5>
      <p class="text-muted">KSh {price} each</p>
    </div>
    <div class="col-md-4 d-flex align-items-center">
      <form action="/cart/update/{product_id}" method="get" class="d-flex align-items-center w-100">
        <input type="number" name="quantity" value="{quantity}" min="1" max="999" class="form-control me-2" style="width:80px;">
        <button type="submit" class="btn btn-sm btn-outline-primary">Update</button>
      </form>
    </div>
    <div class="col-md-4 text-end">
      <strong>KSh {subtotal}</strong>
      <a href="/cart/remove/{product_id}" class="btn btn-sm btn-outline-danger ms-2">Remove</a>
    </div>
  </div>
</div>"""

def orders_page(order_list_html: str, role: str, success: bool = False):
    success_msg = '<div class="alert alert-success">✅ Payment successful! Your order has been placed.</div>' if success else ""
    return f"""<!DOCTYPE html><html><head><title>Orders · {APP_NAME}</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
{navbar(role)}
<div class="container mt-4">
  <h2>My Orders</h2>
  {success_msg}
  {order_list_html}
</div></body></html>"""

ORDER_ITEM_HTML = """
<div class="card mb-3 p-3">
  <div class="card-body">
    <h5>Order #{order_id} <span class="badge bg-{status_color} ms-2">{status}</span></h5>
    <p><strong>Date:</strong> {date} | <strong>Payment:</strong> {payment_method} | <strong>Total:</strong> KSh {total}</p>
    <ul>
      {products_list}
    </ul>
    <a href="/receipt/{order_id}" class="btn btn-sm btn-outline-primary">View Receipt</a>
  </div>
</div>"""

def seller_dashboard_page(product_cards: str, role: str):
    return f"""<!DOCTYPE html><html><head><title>My Shop · {APP_NAME}</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
{navbar(role)}
<div class="container mt-4">
  <h2>My Products</h2>
  <a href="/seller/add" class="btn btn-success mb-4">+ Add New Product</a>
  <div class="row">
    {product_cards}
  </div>
</div></body></html>"""

SELLER_PRODUCT_CARD = """
<div class="col-md-4 mb-4">
  <div class="card h-100 p-3">
    <div class="card-body">
      <h5 class="fw-bold">{name}</h5>
      <p>{description}</p>
      <p><strong>Category:</strong> {category} | <strong>Stock:</strong> {stock}</p>
      <h3 class="text-success">KSh {price}</h3>
      <a href="/seller/edit/{id}" class="btn btn-warning btn-sm">Edit</a>
      <a href="/seller/delete/{id}" class="btn btn-danger btn-sm" onclick="return confirm('Delete?')">Delete</a>
    </div>
  </div>
</div>"""

navigation = ""
ADD_PRODUCT_PAGE = f"""<!DOCTYPE html><html><head><title>Add Product · {APP_NAME}</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
{navigation}
<div class="container mt-4" style="max-width:500px;">
  <h2>Add New Product</h2>
  <form method="post">
    <input class="form-control mb-2" name="name" placeholder="Product Name" required>
    <textarea class="form-control mb-2" name="description" placeholder="Description" rows="3"></textarea>
    <input class="form-control mb-2" name="category" placeholder="Category" required>
    <input class="form-control mb-2" type="number" step="0.01" name="price" placeholder="Price (KSh)" required>
    <input class="form-control mb-2" type="number" name="stock" placeholder="Stock Quantity" required>
    <button class="btn btn-primary w-100">Add Product</button>
  </form>
</div></body></html>"""

EDIT_PRODUCT_PAGE = f"""<!DOCTYPE html><html><head><title>Edit Product · {APP_NAME}</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
{navigation}
<div class="container mt-4" style="max-width:500px;">
  <h2>Edit Product</h2>
  <form method="post">
    <input class="form-control mb-2" name="name" value="{{name}}" required>
    <textarea class="form-control mb-2" name="description" rows="3">{{description}}</textarea>
    <input class="form-control mb-2" name="category" value="{{category}}" required>
    <input class="form-control mb-2" type="number" step="0.01" name="price" value="{{price}}" required>
    <input class="form-control mb-2" type="number" name="stock" value="{{stock}}" required>
    <button class="btn btn-primary w-100">Update Product</button>
  </form>
</div></body></html>"""

# ---------- Admin Dashboard ----------
def admin_dashboard_page(metrics, orders_html: str, role: str):
    return f"""<!DOCTYPE html><html><head><title>Admin · DawaLink</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
{navbar(role)}
<div class="container-fluid">
  <div class="row">
    <div class="col-md-2 admin-sidebar p-3">
      <h5>🛡️ Admin Panel</h5>
      <a href="/admin">Dashboard</a>
      <a href="/admin/inquiries">Inquiries</a>
      <a href="/products">View Site</a>
    </div>
    <div class="col-md-10 p-4">
      <h2>Admin Dashboard</h2>
      <div class="row mt-4">
        <div class="col-md-3"><div class="metric-card text-center"><h3>{metrics['total_sales']}</h3><p>Total Sales (KSh)</p></div></div>
        <div class="col-md-3"><div class="metric-card text-center"><h3>{metrics['total_orders']}</h3><p>Total Orders</p></div></div>
        <div class="col-md-3"><div class="metric-card text-center"><h3>{metrics['total_products']}</h3><p>Products in Stock</p></div></div>
        <div class="col-md-3"><div class="metric-card text-center"><h3>{metrics['total_users']}</h3><p>Registered Users</p></div></div>
      </div>
      <hr class="mt-4">
      <h4>Recent Orders</h4>
      {orders_html}
    </div>
  </div>
</div></body></html>"""

def admin_order_item(order):
    status_opts = ["pending","confirmed","shipped","delivered"]
    options = "".join([
        f"<option value='{s}' {'selected' if s == order['status'] else ''}>{s.capitalize()}</option>"
        for s in status_opts
    ])
    items = supabase.table("order_items").select("*, products(name)").eq("order_id", order["id"]).execute()
    products_list = "".join(
        f"<li>{item['products']['name']} x {item['quantity']} @ KSh {item['unit_price']}</li>"
        for item in (items.data or [])
    )
    return f"""
    <div class="card mb-3 p-3">
      <div class="card-body">
        <h5>Order #{order['id'][:8]} — <span class="badge bg-{'warning' if order['status']=='pending' else 'info'}">{order['status']}</span></h5>
        <p><strong>Buyer:</strong> {order.get('profiles', {}).get('full_name', 'Unknown')} ({order.get('profiles', {}).get('phone', 'N/A')})</p>
        <p><strong>Total:</strong> KSh {order['total_amount']} · <strong>Payment:</strong> {order.get('payment_method', 'N/A')} · <strong>Date:</strong> {order['created_at'][:10]}</p>
        <ul>{products_list}</ul>
        <form method="post" action="/admin/update-order/{order['id']}" class="d-flex align-items-center">
          <select class="form-select me-2" name="status" style="width:auto;">
            {options}
          </select>
          <button class="btn btn-sm btn-primary">Update Status</button>
        </form>
      </div>
    </div>"""

# ---------- Receipt Page ----------
def receipt_page(order):
    items = supabase.table("order_items").select("*, products(name)").eq("order_id", order["id"]).execute()
    items_html = "".join(
        f"<tr><td>{item['products']['name']}</td><td>{item['quantity']}</td><td>KSh {item['unit_price']}</td><td>KSh {item['quantity'] * item['unit_price']}</td></tr>"
        for item in items.data
    )
    return f"""<!DOCTYPE html><html><head><title>Receipt · DawaLink</title>{BOOTSTRAP}</head><body onload="window.print()">
<div class="receipt-container mt-4">
  <div class="text-center mb-4">
    <h2>💊 DawaLink</h2>
    <p>{APP_TAGLINE}</p>
    <hr>
    <h4>Receipt for Order #{order['id'][:8]}</h4>
  </div>
  <p><strong>Date:</strong> {order['created_at'][:10]} &nbsp;&nbsp; <strong>Payment:</strong> {order.get('payment_method','N/A')}</p>
  <p><strong>Status:</strong> {order['status']}</p>
  <table class="table table-bordered">
    <thead><tr><th>Product</th><th>Qty</th><th>Unit Price</th><th>Subtotal</th></tr></thead>
    <tbody>{items_html}</tbody>
    <tfoot><tr><th colspan="3" class="text-end">Total</th><th>KSh {order['total_amount']}</th></tr></tfoot>
  </table>
  <div class="text-center mt-4"><button class="btn btn-primary" onclick="window.print()">Print Receipt</button> <a href="/orders" class="btn btn-outline-secondary">Back to Orders</a></div>
</div></body></html>"""

# ---------- Cart helpers ----------
def get_cart(request: Request):
    return request.session.get("cart", [])

def save_cart(request: Request, cart):
    request.session["cart"] = cart

# ---------- Routes ----------
@app.get("/")
def root():
    return RedirectResponse("/login")

@app.get("/login", response_class=HTMLResponse)
def login_page_route():
    return HTMLResponse(login_page())

@app.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...)):
    try:
        resp = supabase.auth.sign_in_with_password({"email": email, "password": password})
        request.session["access_token"] = resp.session.access_token
        request.session["refresh_token"] = resp.session.refresh_token
        return RedirectResponse("/products", status_code=303)
    except:
        return HTMLResponse(login_page("Invalid email or password"))

@app.get("/signup", response_class=HTMLResponse)
def signup_page_route():
    return HTMLResponse(signup_page())

@app.post("/signup")
def signup(full_name: str = Form(...), email: str = Form(...), password: str = Form(...), role: str = Form(...)):
    try:
        resp = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {"data": {"full_name": full_name}}
        })
        supabase.table("profiles").update({"role": role}).eq("user_id", resp.user.id).execute()
        return RedirectResponse("/login", status_code=303)
    except Exception as e:
        return HTMLResponse(signup_page(str(e)))

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    sup = get_valid_session(request)
    if not sup: return RedirectResponse("/login")
    profile = get_user_profile(sup)
    if not profile.data:
        return RedirectResponse("/logout")
    role = profile.data.get("role", "buyer")
    full_name = profile.data.get("full_name", "User")
    return HTMLResponse(dashboard_page(full_name, role))

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login")

# ---------- Products ----------
@app.get("/products", response_class=HTMLResponse)
def products(request: Request, search: str = ""):
    sup = get_valid_session(request)
    if not sup: return RedirectResponse("/login")
    profile = get_user_profile(sup)
    role = profile.data.get("role", "buyer") if profile.data else "buyer"
    query = sup.table("products").select("*").eq("active", True)
    if search:
        query = query.or_(f"name.ilike.%{search}%,category.ilike.%{search}%")
    result = query.execute()
    products = result.data or []
    cards = "".join([PRODUCT_CARD.format(**p) for p in products])
    return HTMLResponse(products_page(cards, role))

# ---------- Seller (seller only) ----------
@app.get("/seller", response_class=HTMLResponse)
def seller_dashboard(request: Request):
    sup = get_valid_session(request)
    if not sup: return RedirectResponse("/login")
    profile = get_user_profile(sup)
    if not profile.data or profile.data['role'] != 'seller':
        return HTMLResponse("<div class='alert alert-danger'>Access denied</div>")
    prods = sup.table("products").select("*").eq("seller_id", profile.data['id']).execute()
    cards = "".join([SELLER_PRODUCT_CARD.format(**p) for p in (prods.data or [])])
    return HTMLResponse(seller_dashboard_page(cards, role="seller"))

@app.get("/seller/add", response_class=HTMLResponse)
def seller_add_form(request: Request):
    sup = get_valid_session(request)
    if not sup: return RedirectResponse("/login")
    profile = get_user_profile(sup)
    if not profile.data or profile.data['role'] != 'seller':
        return HTMLResponse("<div class='alert alert-danger'>Only sellers can add products</div>")
    nav = navbar("seller")
    return HTMLResponse(ADD_PRODUCT_PAGE.replace("{navigation}", nav))

@app.post("/seller/add")
def seller_add(request: Request, name: str = Form(...), description: str = Form(""),
               category: str = Form(...), price: float = Form(...), stock: int = Form(...)):
    sup = get_valid_session(request)
    if not sup: return RedirectResponse("/login")
    profile = get_user_profile(sup)
    sup.table("products").insert({
        "seller_id": profile.data['id'], "name": name, "description": description,
        "category": category, "price": price, "stock": stock
    }).execute()
    return RedirectResponse("/seller", status_code=303)

@app.get("/seller/edit/{product_id}", response_class=HTMLResponse)
def seller_edit_form(request: Request, product_id: str):
    sup = get_valid_session(request)
    if not sup: return RedirectResponse("/login")
    product = sup.table("products").select("*").eq("id", product_id).single().execute()
    page = EDIT_PRODUCT_PAGE.replace("{navigation}", navbar("seller"))
    return HTMLResponse(page.format(**product.data))

@app.post("/seller/edit/{product_id}")
def seller_edit(request: Request, product_id: str, name: str = Form(...), description: str = Form(""),
                category: str = Form(...), price: float = Form(...), stock: int = Form(...)):
    sup = get_valid_session(request)
    if not sup: return RedirectResponse("/login")
    sup.table("products").update({
        "name": name, "description": description, "category": category,
        "price": price, "stock": stock
    }).eq("id", product_id).execute()
    return RedirectResponse("/seller", status_code=303)

@app.get("/seller/delete/{product_id}")
def seller_delete(request: Request, product_id: str):
    sup = get_valid_session(request)
    if not sup: return RedirectResponse("/login")
    sup.table("products").delete().eq("id", product_id).execute()
    return RedirectResponse("/seller", status_code=303)

# ---------- Cart ----------
@app.get("/cart", response_class=HTMLResponse)
def view_cart(request: Request):
    sup = get_valid_session(request)
    if not sup: return RedirectResponse("/login")
    profile = get_user_profile(sup)
    role = profile.data.get("role", "buyer") if profile.data else "buyer"
    cart = get_cart(request)
    if not cart:
        return HTMLResponse(cart_page("<p>Your cart is empty.</p>", "0.00", role))
    product_ids = [item["product_id"] for item in cart]
    products = sup.table("products").select("*").in_("id", product_ids).execute()
    pmap = {p["id"]: p for p in products.data} if products.data else {}
    items_html = ""
    total = 0.0
    for item in cart:
        p = pmap.get(item["product_id"])
        if p:
            subtotal = p["price"] * item["quantity"]
            total += subtotal
            items_html += CART_ITEM.format(
                name=p["name"], price=p["price"], product_id=p["id"],
                quantity=item["quantity"], subtotal=round(subtotal, 2)
            )
    return HTMLResponse(cart_page(items_html, str(round(total, 2)), role))

@app.get("/cart/add/{product_id}")
def add_to_cart(request: Request, product_id: str, quantity: int = 1):
    if not get_valid_session(request): return RedirectResponse("/login")
    if quantity < 1:
        quantity = 1
    cart = get_cart(request)
    for item in cart:
        if item["product_id"] == product_id:
            item["quantity"] += quantity
            save_cart(request, cart)
            return RedirectResponse("/cart", status_code=303)
    cart.append({"product_id": product_id, "quantity": quantity})
    save_cart(request, cart)
    return RedirectResponse("/cart", status_code=303)

@app.get("/cart/update/{product_id}")
def update_cart_item(request: Request, product_id: str, quantity: int = 1):
    if not get_valid_session(request): return RedirectResponse("/login")
    if quantity < 1:
        quantity = 1
    cart = get_cart(request)
    for item in cart:
        if item["product_id"] == product_id:
            item["quantity"] = quantity
            break
    save_cart(request, cart)
    return RedirectResponse("/cart", status_code=303)

@app.get("/cart/remove/{product_id}")
def remove_from_cart(request: Request, product_id: str):
    if not get_valid_session(request): return RedirectResponse("/login")
    cart = [item for item in get_cart(request) if item["product_id"] != product_id]
    save_cart(request, cart)
    return RedirectResponse("/cart", status_code=303)

@app.post("/cart/checkout")
def checkout(request: Request, payment_method: str = Form("cash_on_delivery")):
    sup = get_valid_session(request)
    if not sup:
        return RedirectResponse("/login")
    try:
        profile = get_user_profile(sup)
        if not profile.data:
            return HTMLResponse("<h2>Error: Profile not found.</h2>")
        buyer_id = profile.data["id"]
        cart = get_cart(request)
        if not cart:
            return RedirectResponse("/cart")

        total = 0.0
        order_items_data = []
        for item in cart:
            product = sup.table("products").select("*").eq("id", item["product_id"]).single().execute()
            if not product.data:
                return HTMLResponse(f"<h2>Product {item['product_id']} not found.</h2>")
            if product.data["stock"] < item["quantity"]:
                return HTMLResponse(f"<h2>Not enough stock for '{product.data['name']}'.</h2>")
            price = product.data["price"]
            subtotal = price * item["quantity"]
            total += subtotal
            order_items_data.append({
                "product_id": item["product_id"],
                "quantity": item["quantity"],
                "unit_price": price
            })
            new_stock = product.data["stock"] - item["quantity"]
            if service_supabase:
                service_supabase.table("products").update({"stock": new_stock}).eq("id", item["product_id"]).execute()
            else:
                sup.table("products").update({"stock": new_stock}).eq("id", item["product_id"]).execute()

        if not order_items_data:
            return RedirectResponse("/cart")

        order = sup.table("orders").insert({
            "buyer_id": buyer_id,
            "total_amount": round(total, 2),
            "status": "pending",
            "payment_method": payment_method
        }).execute()

        if not order.data:
            return HTMLResponse("<h2>Failed to create order.</h2>")

        order_id = order.data[0]["id"]
        for oi in order_items_data:
            oi["order_id"] = order_id
            sup.table("order_items").insert(oi).execute()

        save_cart(request, [])
        # Redirect to receipt page
        return RedirectResponse(f"/receipt/{order_id}", status_code=303)

    except Exception as e:
        return HTMLResponse(f"<div class='alert alert-danger'>Checkout Error: {str(e)}</div>")

# ---------- Orders (customer) ----------
@app.get("/orders", response_class=HTMLResponse)
def orders(request: Request):
    sup = get_valid_session(request)
    if not sup: return RedirectResponse("/login")
    try:
        profile = get_user_profile(sup)
        if not profile.data:
            return RedirectResponse("/dashboard")
        buyer_id = profile.data["id"]
        role = profile.data.get("role", "buyer")
        orders_result = sup.table("orders").select("*").eq("buyer_id", buyer_id).order("created_at", desc=True).execute()

        if not orders_result.data:
            return HTMLResponse(orders_page("<p>No orders yet.</p>", role))

        orders_html = ""
        for order in orders_result.data:
            items = sup.table("order_items").select("*, products(name)").eq("order_id", order["id"]).execute()
            products_list = ""
            if items.data:
                for item in items.data:
                    products_list += f"<li>{item['products']['name']} x {item['quantity']} @ KSh {item['unit_price']}</li>"
            status_color = {"pending":"warning","confirmed":"info","shipped":"primary","delivered":"success"}.get(order["status"], "secondary")
            orders_html += ORDER_ITEM_HTML.format(
                order_id=order["id"][:8],
                status=order["status"],
                status_color=status_color,
                total=order["total_amount"],
                payment_method=order.get("payment_method", "N/A"),
                date=order["created_at"][:10],
                products_list=products_list,
                order_id=order["id"]
            )
        return HTMLResponse(orders_page(orders_html, role))
    except Exception as e:
        return HTMLResponse(f"<div class='alert alert-danger'>Orders Error: {str(e)}</div>")

# ---------- Receipt ----------
@app.get("/receipt/{order_id}", response_class=HTMLResponse)
def view_receipt(request: Request, order_id: str):
    sup = get_valid_session(request)
    if not sup: return RedirectResponse("/login")
    # Verify the order belongs to the current user
    profile = get_user_profile(sup)
    if not profile.data:
        return RedirectResponse("/login")
    order = sup.table("orders").select("*").eq("id", order_id).single().execute()
    if not order.data or order.data["buyer_id"] != profile.data["id"]:
        return HTMLResponse("<div class='alert alert-danger'>Receipt not found or access denied.</div>")
    return HTMLResponse(receipt_page(order.data))

# ---------- Admin ----------
@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request):
    sup = get_valid_session(request)
    if not sup: return RedirectResponse("/login")
    profile = get_user_profile(sup)
    if not profile.data or profile.data.get("role") != "admin":
        return HTMLResponse("<div class='alert alert-danger'>Access denied · Admins only</div>")
    
    # Aggregate metrics
    total_sales_result = sup.table("orders").select("total_amount").execute()
    total_sales = sum(o['total_amount'] for o in total_sales_result.data) if total_sales_result.data else 0
    
    total_orders = sup.table("orders").select("count", count="exact").execute()
    total_orders_count = total_orders.count if total_orders.count else 0
    
    total_products = sup.table("products").select("count", count="exact").eq("active", True).execute()
    total_products_count = total_products.count if total_products.count else 0
    
    total_users = sup.table("profiles").select("count", count="exact").execute()
    total_users_count = total_users.count if total_users.count else 0
    
    metrics = {
        "total_sales": f"{total_sales:,.2f}",
        "total_orders": total_orders_count,
        "total_products": total_products_count,
        "total_users": total_users_count
    }
    
    # Fetch all orders
    orders_result = sup.table("orders").select("*, profiles!orders_buyer_id_fkey(full_name, phone)").order("created_at", desc=True).execute()
    orders_html = ""
    if orders_result.data:
        for o in orders_result.data:
            o['profiles'] = o.get('profiles', {}) or {}
            orders_html += admin_order_item(o)
    else:
        orders_html = "<p>No orders yet.</p>"
    
    return HTMLResponse(admin_dashboard_page(metrics, orders_html, role="admin"))

@app.post("/admin/update-order/{order_id}")
def admin_update_order(request: Request, order_id: str, status: str = Form(...)):
    sup = get_valid_session(request)
    if not sup: return RedirectResponse("/login")
    profile = get_user_profile(sup)
    if not profile.data or profile.data.get("role") != "admin":
        return HTMLResponse("<div class='alert alert-danger'>Access denied</div>")
    allowed = ["pending","confirmed","shipped","delivered"]
    if status not in allowed:
        return RedirectResponse("/admin", status_code=303)
    sup.table("orders").update({"status": status}).eq("id", order_id).execute()
    return RedirectResponse("/admin", status_code=303)
