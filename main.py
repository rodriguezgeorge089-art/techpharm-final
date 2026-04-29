import os, csv, io
from fastapi import FastAPI, Request, Form, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="dawalink-pro-secret-key")

APP_NAME = "DawaLink Pro"
APP_TAGLINE = "Your Trusted Online Pharmacy"
PRIMARY_COLOR = "#0d6efd"

PHARMACY_ADDRESS = "Moi Avenue, Nairobi CBD"
PHARMACY_PHONE = "+254 700 123456"
PHARMACY_EMAIL = "info@dawalink.co.ke"

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
service_supabase = create_client(SUPABASE_URL, SERVICE_ROLE_KEY) if SERVICE_ROLE_KEY else supabase

# ---------- Helpers ----------
def get_current_user(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    try:
        profile = service_supabase.table("profiles").select("*").eq("user_id", user_id).single().execute()
        return profile.data if profile.data else None
    except:
        return None

def notify_admins(message: str):
    try:
        admins = service_supabase.table("profiles").select("user_id").eq("role", "admin").execute()
        if admins.data:
            for admin in admins.data:
                service_supabase.table("notifications").insert({"user_id": admin["user_id"], "message": message}).execute()
    except:
        pass

def create_notification(user_id: str, message: str):
    try:
        service_supabase.table("notifications").insert({"user_id": user_id, "message": message}).execute()
    except:
        pass

def get_unread_count(user_id: str):
    try:
        res = service_supabase.table("notifications").select("count", count="exact").eq("user_id", user_id).eq("is_read", False).execute()
        return res.count if res.count else 0
    except:
        return 0

def get_cart(request: Request):
    return request.session.get("cart", [])

def save_cart(request: Request, cart):
    request.session["cart"] = cart

def get_progress_classes(status):
    m = {
        "pending": ("active", "", "", "", ""),
        "confirmed": ("completed", "active", "", "", ""),
        "shipped": ("completed", "completed", "active", "", ""),
        "in_transit": ("completed", "completed", "completed", "active", ""),
        "delivered": ("completed", "completed", "completed", "completed", "active"),
        "returned": ("", "", "", "", "")   # no steps active for returned
    }
    return m.get(status, ("", "", "", "", ""))

def product_image_html(url):
    return f'<img src="{url}" class="card-img-top" style="height:200px; object-fit:cover;">' if url else ""

def upload_image(file: UploadFile):
    if not file or not file.filename or not service_supabase:
        return None
    try:
        contents = file.file.read()
        fname = f"{int(os.urandom(4).hex(),16)}_{file.filename}"
        service_supabase.storage.from_("product-images").upload(fname, contents, {"content-type": file.content_type})
        return f"{SUPABASE_URL}/storage/v1/object/public/product-images/{fname}"
    except:
        return None

# ---------- HTML Components ----------
BOOTSTRAP = '<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">'
FONTAWESOME = '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">'
CUSTOM_CSS = f"""
<style>
  body {{ background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); font-family: 'Segoe UI', system-ui, sans-serif; }}
  .navbar {{ box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
  .card {{ border: none; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); transition: transform 0.2s; }}
  .card:hover {{ transform: translateY(-3px); box-shadow: 0 6px 16px rgba(0,0,0,0.1); }}
  .btn-primary {{ background-color: {PRIMARY_COLOR}; border-color: {PRIMARY_COLOR}; }}
  .admin-sidebar {{ background-color: #1e293b; color: white; min-height: 100vh; }}
  .admin-sidebar a {{ color: #cbd5e1; padding: 10px; display: block; border-radius: 6px; text-decoration: none; }}
  .admin-sidebar a:hover {{ background-color: #334155; color: white; }}
  .metric-card {{ background: white; border-radius: 12px; padding: 20px; }}
  .metric-card h3 {{ font-size: 2rem; font-weight: bold; }}
  .receipt-container {{
    max-width: 320px; margin: auto; background: white; padding: 12px;
    font-family: 'Courier New', monospace; font-size: 13px;
    border: 2px dashed #198754;
  }}
  .receipt-container hr {{ border-top: 1px dashed #000; }}
  .progress-tracker {{ display: flex; justify-content: space-between; margin-bottom: 0; }}
  .step {{ text-align: center; flex: 1; position: relative; }}
  .step .circle {{ width: 30px; height: 30px; border-radius: 50%; background-color: #dee2e6; margin: 0 auto 5px; line-height: 30px; color: white; font-size: 0.85rem; }}
  .step.active .circle {{ background-color: {PRIMARY_COLOR}; }}
  .step.completed .circle {{ background-color: #198754; }}
  .step::after {{ content: ''; position: absolute; top: 15px; left: 50%; width: 100%; height: 2px; background-color: #dee2e6; z-index: -1; }}
  .step:last-child::after {{ display: none; }}
  .step.active::after, .step.completed::after {{ background-color: {PRIMARY_COLOR}; }}
  .notification-badge {{ position: absolute; top: -8px; right: -8px; font-size: 0.7rem; }}
  .price-box {{ background: #f8f9fa; border-radius: 8px; padding: 8px; margin-top: 10px; }}
  .home-card {{ padding: 30px; text-align: center; color: white; border-radius: 15px; }}
  .home-card i {{ font-size: 3rem; margin-bottom: 15px; }}
  .home-card h4 {{ font-weight: bold; }}
  .pharmacy-shop-card {{ background: linear-gradient(135deg, #0d6efd, #0099ff); }}
  .cart-card {{ background: linear-gradient(135deg, #198754, #28a745); }}
  .orders-card {{ background: linear-gradient(135deg, #ffc107, #fd7e14); color: #333; }}
  .admin-card {{ background: linear-gradient(135deg, #6f42c1, #9b59b6); }}
  .seller-card {{ background: linear-gradient(135deg, #20c997, #0d9e6c); }}
  .users-card {{ background: linear-gradient(135deg, #e83e8c, #c2185b); }}
  .approval-card {{ background: linear-gradient(135deg, #17a2b8, #0d6efd); }}
</style>
"""

def navbar(profile):
    role = profile.get("role","") if profile else ""
    buyer_type = profile.get("buyer_type","") if profile else ""
    user_id = profile.get("user_id","") if profile else ""
    admin_tab = '<a class="nav-link" href="/admin"><span class="badge bg-warning text-dark">Admin</span></a>' if role == "admin" else ""
    seller_tab = '<a class="nav-link" href="/seller">My Shop</a>' if role == "seller" else ""
    buyer_label = f' <span class="badge bg-secondary">{buyer_type}</span>' if role == "buyer" and buyer_type else ""
    bell = ""
    if user_id:
        count = get_unread_count(user_id)
        bell = f'<a class="nav-link position-relative" href="/notifications"><i class="fas fa-bell"></i>'
        if count > 0:
            bell += f'<span class="badge rounded-pill bg-danger notification-badge">{count}</span>'
        bell += '</a>'
    return f"""
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
      <div class="container">
        <a class="navbar-brand" href="/home"><i class="fas fa-pills"></i> {APP_NAME}{buyer_label}</a>
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navMain">
          <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="navMain">
          <div class="navbar-nav ms-auto">
            <a class="nav-link" href="/products">Pharmacy Shop</a>
            <a class="nav-link" href="/cart"><i class="fas fa-shopping-cart"></i> Cart</a>
            <a class="nav-link" href="/orders">Orders</a>
            {seller_tab}
            {admin_tab}
            {bell}
            <a class="nav-link" href="/logout">Logout</a>
          </div>
        </div>
      </div>
    </nav>"""

NAV_GUEST = f"""
<nav class="navbar navbar-expand-lg navbar-dark bg-primary">
  <div class="container">
    <a class="navbar-brand" href="/"><i class="fas fa-pills"></i> {APP_NAME}</a>
  </div>
</nav>"""

# ---------- Page Templates ----------
def login_page(error=""):
    alert = f'<div class="alert alert-danger">{error}</div>' if error else ""
    return f"""<!DOCTYPE html><html><head><title>Login · {APP_NAME}</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
{NAV_GUEST}
<div class="container text-center mt-5"><h1>{APP_NAME}</h1><p class="lead">{APP_TAGLINE}</p></div>
<div class="container mt-3" style="max-width:400px;"><div class="card p-4"><h3>Welcome back</h3>{alert}
<form method="post"><input class="form-control mb-2" name="email" placeholder="Email" required>
<input class="form-control mb-2" type="password" name="password" placeholder="Password" required>
<button class="btn btn-primary w-100 mt-2">Log In</button></form>
<p class="mt-3 text-center"><a href="/forgot-password">Forgot password?</a></p>
<p class="text-center">Don't have an account? <a href="/signup">Sign up</a></p></div></div></body></html>"""

def signup_page(error=""):
    alert = f'<div class="alert alert-danger">{error}</div>' if error else ""
    return f"""<!DOCTYPE html><html><head><title>Sign Up · {APP_NAME}</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
{NAV_GUEST}
<div class="container mt-4" style="max-width:400px;"><div class="card p-4"><h3>Create your account</h3>{alert}
<form method="post"><input class="form-control mb-2" name="full_name" placeholder="Full Name" required>
<input class="form-control mb-2" name="email" placeholder="Email" required>
<input class="form-control mb-2" name="phone" placeholder="Phone Number" required>
<input class="form-control mb-2" type="password" name="password" placeholder="Password" required>
<select class="form-control mb-2" name="role" id="roleSelect"><option value="buyer">Buyer</option><option value="seller">Seller</option></select>
<div id="buyerTypeDiv" class="mb-2"><label class="form-label">Buyer Type:</label>
<select class="form-control" name="buyer_type"><option value="retail">Retail</option><option value="wholesale">Wholesale</option></select></div>
<button class="btn btn-primary w-100 mt-2">Sign Up</button></form>
<script>document.getElementById('roleSelect').addEventListener('change',function(){{document.getElementById('buyerTypeDiv').style.display=this.value==='buyer'?'block':'none';}});</script>
</div></div></body></html>"""

def forgot_password_page(error="", success=""):
    alert = f'<div class="alert alert-danger">{error}</div>' if error else ""
    succ = f'<div class="alert alert-success">{success}</div>' if success else ""
    return f"""<!DOCTYPE html><html><head><title>Forgot Password · {APP_NAME}</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
{NAV_GUEST}
<div class="container mt-5" style="max-width:400px;"><div class="card p-4"><h3>Reset Password</h3>{alert}{succ}
<form method="post"><input class="form-control mb-2" name="email" placeholder="Email" required>
<button class="btn btn-primary w-100">Send Reset Link</button></form>
<p class="mt-3 text-center"><a href="/login">Back to Login</a></p></div></div></body></html>"""

def dashboard_page(profile):
    role = profile.get("role","buyer")
    buyer_type = profile.get("buyer_type","")
    full_name = profile.get("full_name","User")
    type_badge = f' <span class="badge bg-secondary">{buyer_type}</span>' if role == "buyer" and buyer_type else ""

    cards = """
        <div class="col-md-4 mb-4">
            <a href="/products" class="text-decoration-none">
                <div class="home-card pharmacy-shop-card">
                    <i class="fas fa-pills"></i>
                    <h4>Pharmacy Shop</h4>
                    <p>Browse all OTC medicines</p>
                </div>
            </a>
        </div>
        <div class="col-md-4 mb-4">
            <a href="/cart" class="text-decoration-none">
                <div class="home-card cart-card">
                    <i class="fas fa-shopping-cart"></i>
                    <h4>Shopping Cart</h4>
                    <p>Review and checkout your items</p>
                </div>
            </a>
        </div>
        <div class="col-md-4 mb-4">
            <a href="/orders" class="text-decoration-none">
                <div class="home-card orders-card">
                    <i class="fas fa-box"></i>
                    <h4>My Orders</h4>
                    <p>Track your orders & deliveries</p>
                </div>
            </a>
        </div>"""

    if role == "admin":
        cards += """
        <div class="col-md-4 mb-4">
            <a href="/admin/transactions" class="text-decoration-none">
                <div class="home-card" style="background: linear-gradient(135deg, #17a2b8, #0d6efd);">
                    <i class="fas fa-history"></i>
                    <h4>Transaction History</h4>
                    <p>All orders & receipts</p>
                </div>
            </a>
        </div>
        <div class="col-md-4 mb-4">
            <a href="/admin/users" class="text-decoration-none">
                <div class="home-card users-card">
                    <i class="fas fa-users"></i>
                    <h4>Manage Users</h4>
                    <p>View & approve registrations</p>
                </div>
            </a>
        </div>
        <div class="col-md-4 mb-4">
            <a href="/admin/pending-approvals" class="text-decoration-none">
                <div class="home-card approval-card">
                    <i class="fas fa-user-check"></i>
                    <h4>Pending Approvals</h4>
                    <p>Approve or deny signups</p>
                </div>
            </a>
        </div>"""

    if role == "seller":
        cards += """
        <div class="col-md-4 mb-4">
            <a href="/seller" class="text-decoration-none">
                <div class="home-card seller-card">
                    <i class="fas fa-store-alt"></i>
                    <h4>My Shop</h4>
                    <p>Manage your products & orders</p>
                </div>
            </a>
        </div>"""

    return f"""<!DOCTYPE html><html><head><title>Dashboard · {APP_NAME}</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
{navbar(profile)}
<div class="container mt-5">
    <div class="text-center mb-5">
        <h1>Welcome back, {full_name} <span class="badge bg-info ms-2">{role}{type_badge}</span></h1>
        <p class="lead">What would you like to do today?</p>
    </div>
    <div class="row justify-content-center">
        {cards}
    </div>
</div>
</body></html>"""

def products_page(cards, profile, page, total_pages, search=""):
    pagination = ""
    if total_pages > 1:
        pagination = '<nav class="mt-3"><ul class="pagination justify-content-center">'
        for p in range(1, total_pages+1):
            active = "active" if p == page else ""
            pagination += f'<li class="page-item {active}"><a class="page-link" href="/products?page={p}&search={search}">{p}</a></li>'
        pagination += '</ul></nav>'
    return f"""<!DOCTYPE html><html><head><title>Pharmacy Shop · {APP_NAME}</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
{navbar(profile)}
<div class="container mt-4"><h2 class="mb-4">Pharmacy Shop</h2>
<form class="mb-4" method="get" action="/products"><div class="input-group input-group-lg">
<input class="form-control" name="search" value="{search}" placeholder="Search medicines...">
<button class="btn btn-primary">Search</button></div></form>
<div class="row">{cards}</div>{pagination}</div></body></html>"""

def product_card(product, is_buyer, buyer_type="retail"):
    retail_price = product['price']
    wholesale_price = product.get('wholesale_price')
    cost_price = product.get('cost_price', 0)

    price_lines = []
    if is_buyer:
        if buyer_type == "wholesale" and wholesale_price is not None:
            display_price = wholesale_price
            price_lines.append(f"<h4 class='text-success'>Wholesale: KSh {display_price}</h4>")
            price_lines.append(f"<small class='text-muted'>Retail: KSh {retail_price}</small>")
        else:
            display_price = retail_price
            price_lines.append(f"<h4 class='text-success'>KSh {display_price}</h4>")
            if wholesale_price is not None:
                price_lines.append(f"<small class='text-muted'>Wholesale: KSh {wholesale_price}</small>")
    else:
        price_lines.append(f"<strong>Retail:</strong> KSh {retail_price}")
        if wholesale_price:
            price_lines.append(f"<strong>Wholesale:</strong> KSh {wholesale_price}")
        price_lines.append(f"<strong>Cost:</strong> KSh {cost_price}")

    price_html = "<br>".join(price_lines)

    add_to_cart = ""
    if is_buyer:
        add_to_cart = f"""<form action="/cart/add/{product['id']}" method="get" class="d-flex align-items-center mt-3">
        <input type="number" name="quantity" value="1" min="1" max="{product['stock']}" class="form-control me-2" style="width:80px;">
        <button type="submit" class="btn btn-primary">Add to Cart</button></form>"""

    img_html = f'<img src="{product.get("image_url")}" class="card-img-top" style="height:200px; object-fit:cover;">' if product.get("image_url") else ""

    return f"""<div class="col-md-4 mb-4"><div class="card h-100 p-3">{img_html}<div class="card-body">
<h5 class="card-title fw-bold">{product['name']}</h5>
<p class="card-text">{product['description']}</p>
<p><strong>Category:</strong> {product['category']} | <strong>Stock:</strong> {product['stock']}</p>
<div class="price-box">{price_html}</div>
{add_to_cart}
</div></div></div>"""

def cart_page(items_html, total, profile):
    return f"""<!DOCTYPE html><html><head><title>Cart · {APP_NAME}</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
{navbar(profile)}
<div class="container mt-4"><h2>Your Cart</h2>{items_html}<hr><div class="text-end"><h4>Total: KSh {total}</h4>
<form method="post" action="/cart/checkout" class="row g-2 align-items-center mt-3">
<div class="col-auto"><label class="form-label me-2">Payment:</label>
<select class="form-select" name="payment_method"><option value="cash_on_delivery">Cash on Delivery</option><option value="mobile_money">M Pesa</option></select></div>
<div class="col-auto"><button type="submit" class="btn btn-success">Place Order</button></div></form></div></div></body></html>"""

CART_ITEM = """<div class="card mb-3 p-3"><div class="row align-items-center">
<div class="col-md-4"><h5>{name}</h5><p class="text-muted">KSh {unit_price} each</p></div>
<div class="col-md-4 d-flex align-items-center"><form action="/cart/update/{product_id}" method="get" class="d-flex align-items-center w-100">
<input type="number" name="quantity" value="{quantity}" min="1" max="999" class="form-control me-2" style="width:80px;">
<button type="submit" class="btn btn-sm btn-outline-primary">Update</button></form></div>
<div class="col-md-4 text-end"><strong>KSh {subtotal}</strong>
<a href="/cart/remove/{product_id}" class="btn btn-sm btn-outline-danger ms-2" onclick="return confirm('Remove?')">Remove</a></div></div></div>"""

def orders_page(order_list, profile):
    return f"""<!DOCTYPE html><html><head><title>Orders · {APP_NAME}</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
{navbar(profile)}
<div class="container mt-4"><h2>My Orders</h2>{order_list}</div></body></html>"""

ORDER_ITEM_HTML = """<div class="card mb-3 p-4"><div class="card-body">
<h5>Order #{order_id_short} <span class="badge bg-{status_color} ms-2">{status}</span></h5>
<p><strong>Date:</strong> {date} | <strong>Payment:</strong> {payment_method} | <strong>Total:</strong> KSh {total}</p>
<ul>{products_list}</ul>
<div class="progress-tracker mt-3 mb-3">
<div class="step {pending_class}"><div class="circle">1</div><small>Pending</small></div>
<div class="step {confirmed_class}"><div class="circle">2</div><small>Confirmed</small></div>
<div class="step {shipped_class}"><div class="circle">3</div><small>Shipped</small></div>
<div class="step {in_transit_class}"><div class="circle">4</div><small>In Transit</small></div>
<div class="step {delivered_class}"><div class="circle">5</div><small>Delivered</small></div>
</div>
<a href="/receipt/{order_id}" class="btn btn-sm btn-outline-primary"><i class="fas fa-print"></i> View Receipt</a>
<a href="/return/{order_id}" class="btn btn-sm btn-outline-warning ms-1"><i class="fas fa-undo"></i> Return</a>
</div></div>"""

def seller_dashboard_page(cards, profile):
    return f"""<!DOCTYPE html><html><head><title>My Shop · {APP_NAME}</title>{BOOTSTRAP}{CUSTOM_CSS}{FONTAWESOME}</head><body>
{navbar(profile)}
<div class="container mt-4"><h2>My Products</h2>
<a href="/seller/add" class="btn btn-success mb-4"><i class="fas fa-plus"></i> Add New Product</a>
<a href="/seller/orders" class="btn btn-info mb-4"><i class="fas fa-list"></i> My Orders</a>
<div class="row">{cards}</div></div></body></html>"""

SELLER_PRODUCT_CARD = """<div class="col-md-4 mb-4"><div class="card h-100 p-3">{image_html}<div class="card-body">
<h5 class="fw-bold">{name}</h5><p>{description}</p>
<p><strong>Category:</strong> {category} | <strong>Stock:</strong> {stock}</p>
<div class="price-box">
  <p><strong>Retail:</strong> KSh {price}</p>
  {wholesale_info}
  <p><strong>Cost:</strong> KSh {cost_price}</p>
</div>
<a href="/seller/edit/{id}" class="btn btn-warning btn-sm">Edit</a>
<a href="/seller/delete/{id}" class="btn btn-danger btn-sm" onclick="return confirm('Delete?')">Delete</a></div></div></div>"""

navigation = ""

ADD_PRODUCT_PAGE = f"""<!DOCTYPE html><html><head><title>Add Product · {APP_NAME}</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
{navigation}<div class="container mt-4" style="max-width:500px;"><h2>Add New Product</h2>
<form method="post" enctype="multipart/form-data">
<input class="form-control mb-2" name="name" placeholder="Product Name" required>
<textarea class="form-control mb-2" name="description" placeholder="Description" rows="3"></textarea>
<input class="form-control mb-2" name="category" placeholder="Category" required>
<input class="form-control mb-2" type="number" step="0.01" name="price" placeholder="Retail Price (KSh)" required>
<input class="form-control mb-2" type="number" step="0.01" name="wholesale_price" placeholder="Wholesale Price (optional)">
<input class="form-control mb-2" type="number" step="0.01" name="cost_price" placeholder="Cost Price (KSh)">
<input class="form-control mb-2" type="number" name="stock" placeholder="Stock Quantity" required>
<label class="form-label">Product Image</label>
<input class="form-control mb-2" type="file" name="image" accept="image/*">
<button class="btn btn-primary w-100">Add Product</button></form></div></body></html>"""

EDIT_PRODUCT_PAGE = f"""<!DOCTYPE html><html><head><title>Edit Product · {APP_NAME}</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
{navigation}<div class="container mt-4" style="max-width:500px;"><h2>Edit Product</h2>
<form method="post" enctype="multipart/form-data">
<input class="form-control mb-2" name="name" value="{{name}}" required>
<textarea class="form-control mb-2" name="description" rows="3">{{description}}</textarea>
<input class="form-control mb-2" name="category" value="{{category}}" required>
<input class="form-control mb-2" type="number" step="0.01" name="price" value="{{price}}" placeholder="Retail Price" required>
<input class="form-control mb-2" type="number" step="0.01" name="wholesale_price" value="{{wholesale_price}}" placeholder="Wholesale (optional)">
<input class="form-control mb-2" type="number" step="0.01" name="cost_price" value="{{cost_price}}" placeholder="Cost Price">
<input class="form-control mb-2" type="number" name="stock" value="{{stock}}" required>
<label class="form-label">Replace Image</label>
<input class="form-control mb-2" type="file" name="image" accept="image/*">
<button class="btn btn-primary w-100">Update Product</button></form></div></body></html>"""

def receipt_page(order, buyer):
    try:
        items = service_supabase.table("order_items").select("*, products(name)").eq("order_id", order["id"]).execute()
        items_html = ""
        for item in items.data:
            items_html += f"""
            <div style="display:flex; justify-content:space-between;">
                <span>{item['products']['name']} x{item['quantity']}</span>
                <span>KSh {item['quantity'] * item['unit_price']}</span>
            </div>
            <div style="text-align:right; font-size:12px;">(@ KSh {item['unit_price']})</div>"""
    except Exception as e:
        items_html = f"<p>Error loading items: {str(e)}</p>"

    return f"""<!DOCTYPE html><html><head><title>Receipt · {APP_NAME}</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
<div class="container mt-4">
    <div class="receipt-container">
        <div class="text-center">
            <strong>{APP_NAME}</strong><br>
            {APP_TAGLINE}<br>
            {PHARMACY_ADDRESS}<br>
            Tel: {PHARMACY_PHONE}
            <hr>
            <strong>Receipt</strong><br>
            Order #{order['id'][:8]}<br>
            Date: {order['created_at'][:10]}<br>
            Payment: {order.get('payment_method','N/A')}
            <hr>
        </div>
        <div style="text-align:left;">
            Customer: {buyer.get('full_name','')}<br>
            Tel: {buyer.get('phone','')}
        </div>
        <hr>
        {items_html}
        <hr>
        <div style="display:flex; justify-content:space-between; font-weight:bold;">
            <span>Total</span>
            <span>KSh {order['total_amount']}</span>
        </div>
        <hr>
        <p class="text-center text-muted">Thank you for choosing {APP_NAME}!</p>
        <div class="text-center mt-2">
            <button class="btn btn-primary btn-sm" onclick="window.print()"><i class="fas fa-print"></i> Print</button>
            <a href="/orders" class="btn btn-outline-secondary btn-sm">Back to Orders</a>
        </div>
    </div>
</div></body></html>"""

def payment_success_page(order):
    try:
        items = service_supabase.table("order_items").select("*, products(name)").eq("order_id", order["id"]).execute()
        items_html = "".join(f"<tr><td>{i['products']['name']}</td><td>{i['quantity']}</td><td>KSh {i['unit_price']}</td><td>KSh {i['quantity']*i['unit_price']}</td></tr>" for i in items.data)
    except:
        items_html = "<tr><td colspan='4'>Error loading items</td></tr>"
    return f"""<!DOCTYPE html><html><head><title>Payment Successful · {APP_NAME}</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
<div class="container mt-5" style="max-width:600px;"><div class="card p-4 text-center">
<h2 class="text-success"><i class="fas fa-check-circle"></i> Payment Successful!</h2>
<p>Your order has been placed and is pending admin verification.</p><hr><h5>Order Summary</h5>
<table class="table table-bordered"><thead><tr><th>Product</th><th>Qty</th><th>Unit Price</th><th>Subtotal</th></tr></thead>
<tbody>{items_html}</tbody><tfoot><tr><th colspan="3" class="text-end">Total</th><th>KSh {order['total_amount']}</th></tr></tfoot></table>
<p><strong>Payment Method:</strong> {order.get('payment_method','N/A')}</p>
<a href="/receipt/{order['id']}" class="btn btn-primary"><i class="fas fa-print"></i> View / Print Receipt</a>
<a href="/orders" class="btn btn-outline-secondary ms-2">My Orders</a></div></div></body></html>"""

def admin_dashboard_page(metrics, orders_html, profile):
    return f"""<!DOCTYPE html><html><head><title>Admin · {APP_NAME}</title>{BOOTSTRAP}{CUSTOM_CSS}{FONTAWESOME}</head><body>
{navbar(profile)}
<div class="container-fluid">
  <div class="row">
    <div class="col-md-2 admin-sidebar p-3">
      <h5><i class="fas fa-shield-alt"></i> Admin Panel</h5>
      <a href="/admin"><i class="fas fa-tachometer-alt"></i> Dashboard</a>
      <a href="/admin/transactions">Transaction History</a>
      <a href="/admin/users">Manage Users</a>
      <a href="/admin/pending-approvals">Pending Approvals</a>
      <a href="/admin/inquiries">Inquiries</a>
      <a href="/admin/returns">Returns</a>
      <a href="/admin/export-orders">Export CSV</a>
      <a href="/home">Home</a>
    </div>
    <div class="col-md-10 p-4">
      <h2>Admin Dashboard</h2>
      <div class="row mt-4">
        <div class="col-md-3"><div class="metric-card text-center"><h3>{metrics['total_sales']}</h3><p>Total Sales (KSh)</p></div></div>
        <div class="col-md-3"><div class="metric-card text-center"><h3>{metrics['total_profit']}</h3><p>Estimated Profit (KSh)</p></div></div>
        <div class="col-md-3"><div class="metric-card text-center"><h3>{metrics['total_orders']}</h3><p>Total Orders</p></div></div>
        <div class="col-md-3"><div class="metric-card text-center"><h3>{metrics['total_users']}</h3><p>Registered Users</p></div></div>
      </div>
      <hr>
      <div class="d-flex justify-content-between">
        <h4>Recent Orders</h4>
        <a href="/admin/export-orders" class="btn btn-sm btn-outline-success"><i class="fas fa-file-csv"></i> Export CSV</a>
      </div>
      {orders_html}
    </div>
  </div>
</div></body></html>"""

def admin_order_item(order):
    status_opts = ["pending","confirmed","shipped","in_transit","delivered","returned"]
    status_options = "".join([f"<option value='{s}' {'selected' if s == order['status'] else ''}>{s.replace('_',' ').title()}</option>" for s in status_opts])
    payment_status = order.get('payment_status','pending')
    if payment_status == 'pending':
        payment_btn = f'<a href="/admin/payment/{order["id"]}" class="btn btn-sm btn-outline-primary ms-1">View Payment</a>'
    elif payment_status == 'verified':
        payment_btn = '<span class="badge bg-success">Approved</span>'
    else:
        payment_btn = '<span class="badge bg-danger">Denied</span>'
    products_list = order.get('items_list', '')
    profit = order.get('profit',0)
    return f"""<div class="card mb-3 p-3"><div class="card-body">
<h5>Order #{order['id'][:8]} — <span class="badge bg-{'warning' if order['status']=='pending' else 'info'}">{order['status']}</span></h5>
<p><strong>Buyer:</strong> {order.get('buyer_name','Unknown')} ({order.get('buyer_phone','N/A')})</p>
<p><strong>Total:</strong> KSh {order['total_amount']} · <strong>Profit:</strong> KSh {profit} · <strong>Payment:</strong> {order.get('payment_method','N/A')} · <strong>Date:</strong> {order['created_at'][:10]}</p>
<p><strong>Payment Status:</strong> {payment_status} {payment_btn}</p>
<ul>{products_list}</ul>
<form method="post" action="/admin/update-order/{order['id']}" class="d-flex align-items-center">
<select class="form-select me-2" name="status" style="width:auto;">{status_options}</select>
<button class="btn btn-sm btn-primary">Update Status</button></form></div></div>"""

def admin_payment_review_page(order, profile):
    try:
        buyer_name = order.get('buyer_name', 'Unknown')
        buyer_phone = order.get('buyer_phone', 'N/A')
        items = service_supabase.table("order_items").select("*, products(name)").eq("order_id", order["id"]).execute()
        items_list = "".join(f"<li>{i['products']['name']} x {i['quantity']} @ KSh {i['unit_price']}</li>" for i in (items.data or []))
    except Exception as e:
        return f"""<div class="container mt-4"><div class="alert alert-danger">Error loading payment details: {str(e)}</div><a href='/admin'>Back</a></div>"""
    return f"""<!DOCTYPE html><html><head><title>Payment Review · Admin</title>{BOOTSTRAP}{CUSTOM_CSS}{FONTAWESOME}</head><body>
{navbar(profile)}
<div class="container mt-4" style="max-width:600px;">
  <h2><i class="fas fa-credit-card"></i> Payment Review</h2>
  <div class="card p-4 mt-3">
    <h4>Order #{order['id'][:8]}</h4>
    <hr>
    <p><strong>Buyer:</strong> {buyer_name} · {buyer_phone}</p>
    <p><strong>Total:</strong> KSh {order['total_amount']}</p>
    <p><strong>Payment Method:</strong> {order.get('payment_method','N/A')}</p>
    <p><strong>Payment Status:</strong> {order.get('payment_status','pending')}</p>
    <h5>Order Items</h5>
    <ul>{items_list}</ul>
    <form method="post" action="/admin/approve-payment/{order['id']}" class="d-inline">
      <button class="btn btn-success"><i class="fas fa-check"></i> Approve Payment</button>
    </form>
    <form method="post" action="/admin/deny-payment/{order['id']}" class="d-inline ms-2">
      <button class="btn btn-danger"><i class="fas fa-times"></i> Deny Payment</button>
    </form>
    <a href="/admin" class="btn btn-outline-secondary ms-2">Back to Admin</a>
  </div>
</div></body></html>"""

def admin_users_page(users):
    rows = ""
    for u in users:
        status_badge = "bg-success" if u.get("is_approved") else "bg-warning"
        rows += f"""<tr>
            <td>{u['full_name']}</td>
            <td>{u.get('email','')}</td>
            <td>{u.get('phone','')}</td>
            <td>{u['role']}</td>
            <td><span class="badge {status_badge}">{u.get('signup_status','pending')}</span></td>
            <td>
                <a href="/admin/approve-user/{u['user_id']}" class="btn btn-sm btn-success">Approve</a>
                <a href="/admin/deny-user/{u['user_id']}" class="btn btn-sm btn-danger">Deny</a>
            </td>
        </tr>"""
    return f"""<!DOCTYPE html><html><head><title>Manage Users · Admin</title>{BOOTSTRAP}{CUSTOM_CSS}{FONTAWESOME}</head><body>
{navbar({'role':'admin'})}
<div class="container-fluid">
  <div class="row">
    <div class="col-md-2 admin-sidebar p-3">
      <h5><i class="fas fa-shield-alt"></i> Admin Panel</h5>
      <a href="/admin">Dashboard</a>
      <a href="/admin/transactions">Transaction History</a>
      <a href="/admin/users">Manage Users</a>
      <a href="/admin/pending-approvals">Pending Approvals</a>
      <a href="/admin/inquiries">Inquiries</a>
      <a href="/admin/returns">Returns</a>
      <a href="/admin/export-orders">Export CSV</a>
      <a href="/home">Home</a>
    </div>
    <div class="col-md-10 p-4">
      <h2>Registered Users</h2>
      <table class="table table-bordered">
        <thead><tr><th>Name</th><th>Email</th><th>Phone</th><th>Role</th><th>Status</th><th>Action</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
  </div>
</div></body></html>"""

def admin_transactions_page(orders):
    rows = ""
    for o in orders:
        items = service_supabase.table("order_items").select("*, products(name)").eq("order_id", o["id"]).execute()
        pl = "".join(f"<li>{i['products']['name']} x {i['quantity']} @ KSh {i['unit_price']}</li>" for i in (items.data or []))
        rows += f"""<div class="card mb-3 p-3">
          <h5>Order #{o['id'][:8]} - {o['status']}</h5>
          <p><strong>Buyer:</strong> {o.get('buyer_name','Unknown')} | <strong>Total:</strong> KSh {o['total_amount']} | <strong>Date:</strong> {o['created_at'][:10]}</p>
          <ul>{pl}</ul>
          <a href="/receipt/{o['id']}" class="btn btn-sm btn-outline-primary"><i class="fas fa-print"></i> View Receipt</a>
        </div>"""
    if not rows: rows = "<p>No transactions yet.</p>"
    return f"""<!DOCTYPE html><html><head><title>Transaction History · Admin</title>{BOOTSTRAP}{CUSTOM_CSS}{FONTAWESOME}</head><body>
{navbar({'role':'admin'})}
<div class="container-fluid">
  <div class="row">
    <div class="col-md-2 admin-sidebar p-3">
      <h5><i class="fas fa-shield-alt"></i> Admin Panel</h5>
      <a href="/admin">Dashboard</a>
      <a href="/admin/transactions">Transaction History</a>
      <a href="/admin/users">Manage Users</a>
      <a href="/admin/pending-approvals">Pending Approvals</a>
      <a href="/admin/inquiries">Inquiries</a>
      <a href="/admin/returns">Returns</a>
      <a href="/admin/export-orders">Export CSV</a>
      <a href="/home">Home</a>
    </div>
    <div class="col-md-10 p-4">
      <h2>Transaction History</h2>
      {rows}
    </div>
  </div>
</div></body></html>"""

def inquiries_page(inquiries):
    rows = "".join(f"<tr><td>{inq['name']}</td><td>{inq['email']}</td><td>{inq['message']}</td><td>{inq['created_at'][:10]}</td></tr>" for inq in inquiries)
    return f"""<!DOCTYPE html><html><head><title>Inquiries · Admin</title>{BOOTSTRAP}{CUSTOM_CSS}{FONTAWESOME}</head><body>
{navbar({'role':'admin'})}<div class="container-fluid"><div class="row">
<div class="col-md-2 admin-sidebar p-3"><h5><i class="fas fa-shield-alt"></i> Admin Panel</h5>
<a href="/admin">Dashboard</a><a href="/admin/transactions">Transaction History</a><a href="/admin/users">Manage Users</a><a href="/admin/pending-approvals">Pending Approvals</a><a href="/admin/inquiries">Inquiries</a><a href="/admin/returns">Returns</a><a href="/admin/export-orders">Export CSV</a><a href="/home">Home</a></div>
<div class="col-md-10 p-4"><h2>Customer Inquiries</h2>
<table class="table table-bordered"><thead><tr><th>Name</th><th>Email</th><th>Message</th><th>Date</th></tr></thead><tbody>{rows}</tbody></table></div></div></div></body></html>"""

def returns_management_page(returns_list):
    rows = "".join(f"""<tr>
            <td>{ret['id'][:8]}</td>
            <td>{ret.get('order_id','')[:8]}</td>
            <td>{ret.get('buyer_name','')}</td>
            <td>{ret['reason']}</td>
            <td>{ret['status']}</td>
            <td>
                <a href="/admin/return/approve/{ret['id']}" class="btn btn-sm btn-success">Approve</a>
                <a href="/admin/return/deny/{ret['id']}" class="btn btn-sm btn-danger">Deny</a>
            </td>
        </tr>""" for ret in returns_list)
    return f"""<!DOCTYPE html><html><head><title>Returns · Admin</title>{BOOTSTRAP}{CUSTOM_CSS}{FONTAWESOME}</head><body>
{navbar({'role':'admin'})}
<div class="container-fluid">
  <div class="row">
    <div class="col-md-2 admin-sidebar p-3">
      <h5><i class="fas fa-shield-alt"></i> Admin Panel</h5>
      <a href="/admin">Dashboard</a>
      <a href="/admin/transactions">Transaction History</a>
      <a href="/admin/users">Manage Users</a>
      <a href="/admin/pending-approvals">Pending Approvals</a>
      <a href="/admin/inquiries">Inquiries</a>
      <a href="/admin/returns">Returns</a>
      <a href="/admin/export-orders">Export CSV</a>
      <a href="/home">Home</a>
    </div>
    <div class="col-md-10 p-4">
      <h2>Return Requests</h2>
      <table class="table table-bordered">
        <thead><tr><th>ID</th><th>Order</th><th>Buyer</th><th>Reason</th><th>Status</th><th>Action</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
  </div>
</div></body></html>"""

def notifications_page(notifications):
    items = "".join(f"""<div class="list-group-item d-flex justify-content-between align-items-center">
            <span>{n['message']} <small class="text-muted">{n['created_at'][:10]}</small></span>
            <span class="badge {'bg-success' if n['is_read'] else 'bg-secondary'}">{'Read' if n['is_read'] else 'Unread'}</span>
        </div>""" for n in notifications)
    return f"""<!DOCTYPE html><html><head><title>Notifications</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
{navbar(None)}
<div class="container mt-4">
    <h2><i class="fas fa-bell"></i> Notifications</h2>
    <div class="list-group mt-3">{items}</div>
    <p class="mt-3"><a href="/notifications/mark-all-read" class="btn btn-sm btn-outline-primary">Mark All as Read</a></p>
</div></body></html>"""

TERMS_PAGE = f"""<!DOCTYPE html><html><head><title>Terms · {APP_NAME}</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>{NAV_GUEST}<div class="container mt-4"><h2>Terms of Service</h2><p>Sample terms.</p></div></body></html>"""
PRIVACY_PAGE = f"""<!DOCTYPE html><html><head><title>Privacy · {APP_NAME}</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>{NAV_GUEST}<div class="container mt-4"><h2>Privacy Policy</h2><p>Sample policy.</p></div></body></html>"""

# ---------- Routes ----------
@app.get("/")
def root(): return RedirectResponse("/login")

@app.get("/login", response_class=HTMLResponse)
def login_page_route(): return HTMLResponse(login_page())

@app.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...)):
    try:
        r = supabase.auth.sign_in_with_password({"email": email, "password": password})
        if r.user:
            profile = service_supabase.table("profiles").select("is_approved").eq("user_id", r.user.id).single().execute()
            if profile.data and not profile.data.get("is_approved", True):
                return HTMLResponse(login_page("Your account is pending admin approval."))
            request.session["user_id"] = r.user.id
            return RedirectResponse("/home", 303)
        else:
            return HTMLResponse(login_page("Login failed."))
    except:
        return HTMLResponse(login_page("Invalid email or password"))

@app.get("/signup", response_class=HTMLResponse)
def signup_page_route(): return HTMLResponse(signup_page())

@app.post("/signup")
def signup(full_name: str = Form(...), email: str = Form(...), phone: str = Form(...), password: str = Form(...), role: str = Form(...), buyer_type: str = Form("retail")):
    try:
        r = supabase.auth.sign_up({"email": email, "password": password, "options": {"data": {"full_name": full_name}}})
        data = {"role": role, "phone": phone, "is_approved": False, "signup_status": "pending"}
        if role == "buyer": data["buyer_type"] = buyer_type
        service_supabase.table("profiles").update(data).eq("user_id", r.user.id).execute()
        notify_admins(f"New signup by {full_name} ({email}) requires approval.")
        return RedirectResponse("/login?message=Account+created+awaiting+approval", 303)
    except Exception as e:
        return HTMLResponse(signup_page(str(e)))

@app.get("/forgot-password", response_class=HTMLResponse)
def forgot_password_page_route(): return HTMLResponse(forgot_password_page())

@app.post("/forgot-password")
def forgot_password(email: str = Form(...)):
    try:
        supabase.auth.reset_password_email(email)
        return HTMLResponse(forgot_password_page(success="Password reset link sent!"))
    except Exception as e:
        return HTMLResponse(forgot_password_page(error=str(e)))

@app.get("/home", response_class=HTMLResponse)
def home(request: Request):
    profile = get_current_user(request)
    if not profile: return RedirectResponse("/login")
    return HTMLResponse(dashboard_page(profile))

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)

# ---------- Products ----------
@app.get("/products", response_class=HTMLResponse)
def products(request: Request, search: str = "", page: int = 1):
    profile = get_current_user(request)
    if not profile: return RedirectResponse("/login")
    role = profile.get("role","buyer")
    buyer_type = profile.get("buyer_type","") if role == "buyer" else ""
    is_buyer = role == "buyer"
    per_page = 6; offset = (page-1)*per_page
    count_q = service_supabase.table("products").select("count", count="exact").eq("active", True)
    if search: count_q = count_q.or_(f"name.ilike.%{search}%,category.ilike.%{search}%")
    total = count_q.execute().count or 0
    q = service_supabase.table("products").select("*").eq("active", True)
    if search: q = q.or_(f"name.ilike.%{search}%,category.ilike.%{search}%")
    res = q.range(offset, offset+per_page-1).execute()
    cards = "".join(product_card(pr, is_buyer, buyer_type) for pr in (res.data or []))
    total_pages = (total + per_page - 1)//per_page
    return HTMLResponse(products_page(cards, profile, page, total_pages, search))

# ---------- Seller ----------
@app.get("/seller", response_class=HTMLResponse)
def seller_dashboard(request: Request):
    profile = get_current_user(request)
    if not profile or profile['role'] != 'seller': return RedirectResponse("/login")
    prods = service_supabase.table("products").select("*").eq("seller_id", profile['id']).execute()
    cards = ""
    for pr in (prods.data or []):
        img = product_image_html(pr.get("image_url"))
        wholesale_info = ""
        if pr.get("wholesale_price"):
            wholesale_info = f"<p><strong>Wholesale:</strong> KSh {pr['wholesale_price']}</p>"
        else:
            wholesale_info = "<p>No wholesale price set</p>"
        cards += SELLER_PRODUCT_CARD.format(image_html=img, wholesale_info=wholesale_info, **pr)
    return HTMLResponse(seller_dashboard_page(cards, profile))

@app.get("/seller/add", response_class=HTMLResponse)
def seller_add_form(request: Request):
    profile = get_current_user(request)
    if not profile or profile['role'] != 'seller': return RedirectResponse("/login")
    return HTMLResponse(ADD_PRODUCT_PAGE.replace("{navigation}", navbar(profile)))

@app.post("/seller/add")
async def seller_add(request: Request, name: str = Form(...), description: str = Form(""), category: str = Form(...),
                     price: float = Form(...), wholesale_price: float = Form(None), cost_price: float = Form(0),
                     stock: int = Form(...), image: UploadFile = File(None)):
    profile = get_current_user(request)
    if not profile or profile['role'] != 'seller': return RedirectResponse("/login")
    img_url = upload_image(image)
    data = {"seller_id": profile['id'], "name": name, "description": description, "category": category,
            "price": price, "cost_price": cost_price, "stock": stock, "image_url": img_url}
    if wholesale_price is not None: data["wholesale_price"] = wholesale_price
    service_supabase.table("products").insert(data).execute()
    return RedirectResponse("/seller", 303)

@app.get("/seller/edit/{product_id}", response_class=HTMLResponse)
def seller_edit_form(request: Request, product_id: str):
    profile = get_current_user(request)
    if not profile or profile['role'] != 'seller': return RedirectResponse("/login")
    prod = service_supabase.table("products").select("*").eq("id", product_id).single().execute()
    return HTMLResponse(EDIT_PRODUCT_PAGE.replace("{navigation}", navbar(profile)).format(**prod.data))

@app.post("/seller/edit/{product_id}")
async def seller_edit(request: Request, product_id: str, name: str = Form(...), description: str = Form(""),
                      category: str = Form(...), price: float = Form(...), wholesale_price: float = Form(None),
                      cost_price: float = Form(0), stock: int = Form(...), image: UploadFile = File(None)):
    profile = get_current_user(request)
    if not profile or profile['role'] != 'seller': return RedirectResponse("/login")
    upd = {"name": name, "description": description, "category": category, "price": price, "stock": stock, "cost_price": cost_price}
    if wholesale_price is not None: upd["wholesale_price"] = wholesale_price
    img_url = upload_image(image)
    if img_url: upd["image_url"] = img_url
    service_supabase.table("products").update(upd).eq("id", product_id).execute()
    return RedirectResponse("/seller", 303)

@app.get("/seller/delete/{product_id}")
def seller_delete(request: Request, product_id: str):
    profile = get_current_user(request)
    if not profile or profile['role'] != 'seller': return RedirectResponse("/login")
    service_supabase.table("products").delete().eq("id", product_id).execute()
    return RedirectResponse("/seller", 303)

@app.get("/seller/orders", response_class=HTMLResponse)
def seller_orders(request: Request):
    profile = get_current_user(request)
    if not profile or profile['role'] != 'seller': return RedirectResponse("/login")
    sid = profile['id']
    res = service_supabase.table("order_items").select("*, orders!inner(*), products!inner(*)").eq("products.seller_id", sid).order("orders.created_at", desc=True).execute()
    orders_dict = {}
    for item in (res.data or []):
        order = item['orders']; oid = order['id']
        if oid not in orders_dict: orders_dict[oid] = order; order['items'] = []
        orders_dict[oid]['items'].append(item)
    html = ""
    for order in orders_dict.values():
        il = "".join(f"<li>{it['products']['name']} x {it['quantity']} @ KSh {it['unit_price']}</li>" for it in order['items'])
        html += f"<div class='card mb-3 p-3'><h5>Order #{order['id'][:8]} - {order['status']}</h5><ul>{il}</ul></div>"
    if not html: html = "<p>No orders yet.</p>"
    return HTMLResponse(f"""<!DOCTYPE html><html><head><title>My Orders · {APP_NAME}</title>{BOOTSTRAP}{CUSTOM_CSS}{FONTAWESOME}</head><body>
{navbar(profile)}
<div class="container mt-4"><h2>Orders for My Products</h2>{html}</div></body></html>""")

# ---------- Cart ----------
@app.get("/cart", response_class=HTMLResponse)
def view_cart(request: Request):
    profile = get_current_user(request)
    if not profile: return RedirectResponse("/login")
    cart = get_cart(request)
    if not cart: return HTMLResponse(cart_page("<p>Your cart is empty.</p>", "0.00", profile))
    items_html, total = "", 0.0
    for item in cart:
        st = item["unit_price"] * item["quantity"]
        total += st
        items_html += CART_ITEM.format(name=item.get("name","Product"), unit_price=item["unit_price"],
                                       product_id=item["product_id"], quantity=item["quantity"], subtotal=round(st,2))
    return HTMLResponse(cart_page(items_html, str(round(total,2)), profile))

@app.get("/cart/add/{product_id}")
def add_to_cart(request: Request, product_id: str, quantity: int = 1):
    profile = get_current_user(request)
    if not profile or profile['role'] != 'buyer': return RedirectResponse("/products")
    bt = profile.get("buyer_type","retail")
    prod = service_supabase.table("products").select("*").eq("id", product_id).single().execute()
    if not prod.data or not prod.data['active']: return RedirectResponse("/products")
    price = prod.data['wholesale_price'] if bt == "wholesale" and prod.data.get('wholesale_price') is not None else prod.data['price']
    if quantity < 1: quantity = 1
    cart = get_cart(request)
    for item in cart:
        if item["product_id"] == product_id:
            item["quantity"] += quantity; save_cart(request, cart)
            return RedirectResponse("/cart", 303)
    cart.append({"product_id": product_id, "quantity": quantity, "unit_price": price, "name": prod.data['name']})
    save_cart(request, cart)
    return RedirectResponse("/cart", 303)

@app.get("/cart/update/{product_id}")
def update_cart_item(request: Request, product_id: str, quantity: int = 1):
    if not get_current_user(request): return RedirectResponse("/login")
    if quantity < 1: quantity = 1
    cart = get_cart(request)
    for item in cart:
        if item["product_id"] == product_id: item["quantity"] = quantity; break
    save_cart(request, cart)
    return RedirectResponse("/cart", 303)

@app.get("/cart/remove/{product_id}")
def remove_from_cart(request: Request, product_id: str):
    if not get_current_user(request): return RedirectResponse("/login")
    cart = [i for i in get_cart(request) if i["product_id"] != product_id]
    save_cart(request, cart)
    return RedirectResponse("/cart", 303)

@app.get("/cart/checkout")
def checkout_get(): return RedirectResponse("/cart", status_code=303)

@app.post("/cart/checkout")
def checkout(request: Request, payment_method: str = Form("cash_on_delivery")):
    profile = get_current_user(request)
    if not profile or profile.get("role") != "buyer": return RedirectResponse("/products")
    cart = get_cart(request)
    if not cart: return RedirectResponse("/cart")
    total = 0.0; order_items = []
    for item in cart:
        prod = service_supabase.table("products").select("*").eq("id", item["product_id"]).single().execute()
        if not prod.data or prod.data["stock"] < item["quantity"]:
            return HTMLResponse(f"<h2>Not enough stock for '{prod.data.get('name','product')}'.</h2><a href='/cart'>Back</a>")
        st = item["unit_price"] * item["quantity"]; total += st
        order_items.append({"product_id": item["product_id"], "quantity": item["quantity"], "unit_price": item["unit_price"]})
        new_stock = prod.data["stock"] - item["quantity"]
        service_supabase.table("products").update({"stock": new_stock}).eq("id", item["product_id"]).execute()
    if not order_items: return RedirectResponse("/cart")
    order = service_supabase.table("orders").insert({
        "buyer_id": profile['id'], "total_amount": round(total,2),
        "status": "pending", "payment_method": payment_method, "payment_status": "pending"
    }).execute()
    if not order.data: return HTMLResponse("<h2>Failed to create order.</h2>")
    oid = order.data[0]["id"]
    for oi in order_items:
        oi["order_id"] = oid
        service_supabase.table("order_items").insert(oi).execute()
    save_cart(request, [])
    notify_admins(f"New order #{oid[:8]} placed, awaiting payment.")
    return RedirectResponse(f"/payment-success/{oid}", 303)

@app.get("/payment-success/{order_id}", response_class=HTMLResponse)
def payment_success(request: Request, order_id: str):
    profile = get_current_user(request)
    if not profile: return RedirectResponse("/login")
    order = service_supabase.table("orders").select("*").eq("id", order_id).single().execute()
    if not order.data or order.data["buyer_id"] != profile["id"]:
        return HTMLResponse("<div class='alert alert-danger'>Order not found or access denied.</div>")
    return HTMLResponse(payment_success_page(order.data))

# Receipt – admins can view any receipt, buyers only their own
@app.get("/receipt/{order_id}", response_class=HTMLResponse)
def view_receipt(request: Request, order_id: str):
    profile = get_current_user(request)
    if not profile: return RedirectResponse("/login")
    try:
        order = service_supabase.table("orders").select("*").eq("id", order_id).single().execute()
        if not order.data:
            return HTMLResponse("<div class='alert alert-danger'>Receipt not found.</div>")
        if order.data["buyer_id"] != profile["id"] and profile.get("role") != "admin":
            return HTMLResponse("<div class='alert alert-danger'>Receipt not found or access denied.</div>")
        buyer = service_supabase.table("profiles").select("full_name, phone").eq("id", order.data["buyer_id"]).single().execute()
        buyer_data = buyer.data if buyer.data else {}
        return HTMLResponse(receipt_page(order.data, buyer_data))
    except Exception as e:
        return HTMLResponse(f"<div class='alert alert-danger'>Error loading receipt: {str(e)}</div>")

@app.get("/orders", response_class=HTMLResponse)
def orders(request: Request):
    profile = get_current_user(request)
    if not profile: return RedirectResponse("/login")
    buyer_id = profile["id"]
    res = service_supabase.table("orders").select("*").eq("buyer_id", buyer_id).order("created_at", desc=True).execute()
    if not res.data: return HTMLResponse(orders_page("<p>No orders yet.</p>", profile))
    html = ""
    for o in res.data:
        items = service_supabase.table("order_items").select("*, products(name)").eq("order_id", o["id"]).execute()
        pl = "".join(f"<li>{i['products']['name']} x {i['quantity']} @ KSh {i['unit_price']}</li>" for i in (items.data or []))
        sc = {"pending":"warning","confirmed":"info","shipped":"primary","in_transit":"info","delivered":"success","returned":"danger"}.get(o["status"],"secondary")
        pcls = get_progress_classes(o["status"])
        html += ORDER_ITEM_HTML.format(order_id_short=o["id"][:8], order_id=o["id"], status=o["status"],
                                       status_color=sc, total=o["total_amount"],
                                       payment_method=o.get("payment_method","N/A"), date=o["created_at"][:10],
                                       products_list=pl,
                                       pending_class=pcls[0], confirmed_class=pcls[1],
                                       shipped_class=pcls[2], in_transit_class=pcls[3],
                                       delivered_class=pcls[4])
    return HTMLResponse(orders_page(html, profile))

# ---------- Returns ----------
@app.get("/return/{order_id}", response_class=HTMLResponse)
def return_request_page(request: Request, order_id: str):
    profile = get_current_user(request)
    if not profile: return RedirectResponse("/login")
    order = service_supabase.table("orders").select("*").eq("id", order_id).single().execute()
    if not order.data or order.data["buyer_id"] != profile["id"]: return HTMLResponse("<div class='alert alert-danger'>Order not found.</div>")
    return HTMLResponse(f"""<!DOCTYPE html><html><head><title>Return Request</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
{navbar(profile)}
<div class="container mt-4" style="max-width:500px;">
  <h2>Request Return for Order #{order_id[:8]}</h2>
  <form method="post" action="/return/{order_id}">
    <textarea class="form-control mb-2" name="reason" rows="3" placeholder="Reason for return" required></textarea>
    <button class="btn btn-warning">Submit Return Request</button>
    <a href="/orders" class="btn btn-outline-secondary ms-2">Cancel</a>
  </form>
</div></body></html>""")

@app.post("/return/{order_id}")
def submit_return(request: Request, order_id: str, reason: str = Form(...)):
    profile = get_current_user(request)
    if not profile: return RedirectResponse("/login")
    service_supabase.table("returns").insert({
        "order_id": order_id,
        "buyer_id": profile["id"],
        "reason": reason,
        "status": "pending"
    }).execute()
    notify_admins(f"New return request for order #{order_id[:8]}.")
    create_notification(profile["id"], f"Your return request for order #{order_id[:8]} has been submitted.")
    return RedirectResponse("/orders", 303)

# ---------- Admin ----------
@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request):
    profile = get_current_user(request)
    if not profile or profile.get("role") != "admin": return RedirectResponse("/login")
    all_orders = service_supabase.table("orders").select("*").order("created_at", desc=True).execute().data or []
    buyer_ids = list(set(o['buyer_id'] for o in all_orders))
    buyers_map = {}
    if buyer_ids:
        buyers = service_supabase.table("profiles").select("id, full_name, phone").in_("id", buyer_ids).execute().data or []
        for b in buyers: buyers_map[b['id']] = b
    all_items = service_supabase.table("order_items").select("*, products(name, cost_price)").execute().data or []
    items_by_order = {}
    for it in all_items: items_by_order.setdefault(it['order_id'], []).append(it)

    # Exclude returned orders from sales metrics
    active_orders = [o for o in all_orders if o['status'] != 'returned']
    total_sales = sum(o['total_amount'] for o in active_orders)
    total_orders = len(active_orders)
    total_users = service_supabase.table("profiles").select("count", count="exact").execute().count or 0
    profit = 0
    returned_order_ids = {o['id'] for o in all_orders if o['status'] == 'returned'}
    for it in all_items:
        if it['order_id'] in returned_order_ids:
            continue
        cost = it['products']['cost_price'] if it['products'] else 0
        profit += (it['unit_price'] - cost) * it['quantity']

    metrics = {
        "total_sales": f"{total_sales:,.2f}",
        "total_profit": f"{profit:,.2f}",
        "total_orders": total_orders,
        "total_users": total_users
    }

    orders_html = ""
    for order in all_orders:
        buyer = buyers_map.get(order['buyer_id'], {"full_name": "Unknown", "phone": "N/A"})
        order['buyer_name'] = buyer.get('full_name','Unknown')
        order['buyer_phone'] = buyer.get('phone','N/A')
        items_data = items_by_order.get(order['id'], [])
        order['items_list'] = "".join(f"<li>{it['products']['name']} x {it['quantity']} @ KSh {it['unit_price']} (Cost KSh {it['products'].get('cost_price',0)})</li>" for it in items_data)
        order['profit'] = sum((it['unit_price'] - (it['products']['cost_price'] if it['products'] else 0)) * it['quantity'] for it in items_data)
        orders_html += admin_order_item(order)

    if not orders_html:
        orders_html = "<p>No orders yet.</p>"

    return HTMLResponse(admin_dashboard_page(metrics, orders_html, profile))

@app.post("/admin/update-order/{order_id}")
def admin_update_order(request: Request, order_id: str, status: str = Form(...)):
    profile = get_current_user(request)
    if not profile or profile.get("role") != "admin": return RedirectResponse("/login")
    allowed = ["pending","confirmed","shipped","in_transit","delivered","returned"]
    if status not in allowed: return RedirectResponse("/admin", 303)
    service_supabase.table("orders").update({"status": status}).eq("id", order_id).execute()
    order = service_supabase.table("orders").select("buyer_id").eq("id", order_id).single().execute()
    if order.data:
        create_notification(order.data["buyer_id"], f"Order #{order_id[:8]} status updated to {status}.")
    notify_admins(f"Order #{order_id[:8]} status changed to {status}.")
    return RedirectResponse("/admin", 303)

@app.get("/admin/payment/{order_id}", response_class=HTMLResponse)
def admin_payment_review(request: Request, order_id: str):
    profile = get_current_user(request)
    if not profile or profile.get("role") != "admin": return RedirectResponse("/login")
    order = service_supabase.table("orders").select("*").eq("id", order_id).single().execute()
    if not order.data: return HTMLResponse("<div class='alert alert-danger'>Order not found.</div>")
    order_data = order.data
    try:
        buyer = service_supabase.table("profiles").select("full_name, phone").eq("id", order_data["buyer_id"]).single().execute()
        order_data['buyer_name'] = buyer.data['full_name'] if buyer.data else "Unknown"
        order_data['buyer_phone'] = buyer.data['phone'] if buyer.data else "N/A"
    except:
        order_data['buyer_name'] = "Unknown"
        order_data['buyer_phone'] = "N/A"
    return HTMLResponse(admin_payment_review_page(order_data, profile))

@app.post("/admin/approve-payment/{order_id}")
def admin_approve_payment(request: Request, order_id: str):
    profile = get_current_user(request)
    if not profile or profile.get("role") != "admin": return RedirectResponse("/login")
    service_supabase.table("orders").update({"payment_status": "verified", "status": "confirmed"}).eq("id", order_id).execute()
    order = service_supabase.table("orders").select("buyer_id").eq("id", order_id).single().execute()
    if order.data:
        create_notification(order.data["buyer_id"], f"Payment for order #{order_id[:8]} approved. Order confirmed.")
    notify_admins(f"Payment approved for order #{order_id[:8]}")
    return RedirectResponse("/admin", 303)

@app.post("/admin/deny-payment/{order_id}")
def admin_deny_payment(request: Request, order_id: str):
    profile = get_current_user(request)
    if not profile or profile.get("role") != "admin": return RedirectResponse("/login")
    service_supabase.table("orders").update({"payment_status": "denied"}).eq("id", order_id).execute()
    order = service_supabase.table("orders").select("buyer_id").eq("id", order_id).single().execute()
    if order.data:
        create_notification(order.data["buyer_id"], f"Payment for order #{order_id[:8]} denied. Contact support.")
    notify_admins(f"Payment denied for order #{order_id[:8]}")
    return RedirectResponse("/admin", 303)

# ---------- User Management ----------
@app.get("/admin/users", response_class=HTMLResponse)
def admin_users(request: Request):
    profile = get_current_user(request)
    if not profile or profile.get("role") != "admin": return RedirectResponse("/login")
    users = service_supabase.table("profiles").select("*").execute().data or []
    return HTMLResponse(admin_users_page(users))

@app.get("/admin/pending-approvals", response_class=HTMLResponse)
def admin_pending_approvals(request: Request):
    profile = get_current_user(request)
    if not profile or profile.get("role") != "admin": return RedirectResponse("/login")
    pending = service_supabase.table("profiles").select("*").eq("signup_status", "pending").execute().data or []
    return HTMLResponse(admin_users_page(pending))

@app.get("/admin/approve-user/{user_id}")
def admin_approve_user(request: Request, user_id: str):
    profile = get_current_user(request)
    if not profile or profile.get("role") != "admin": return RedirectResponse("/login")
    service_supabase.table("profiles").update({"is_approved": True, "signup_status": "approved"}).eq("user_id", user_id).execute()
    create_notification(user_id, "Your account has been approved. You can now log in.")
    return RedirectResponse("/admin/users", 303)

@app.get("/admin/deny-user/{user_id}")
def admin_deny_user(request: Request, user_id: str):
    profile = get_current_user(request)
    if not profile or profile.get("role") != "admin": return RedirectResponse("/login")
    service_supabase.table("profiles").update({"is_approved": False, "signup_status": "denied"}).eq("user_id", user_id).execute()
    create_notification(user_id, "Your account registration has been denied. Contact support.")
    return RedirectResponse("/admin/users", 303)

# ---------- Transaction History ----------
@app.get("/admin/transactions", response_class=HTMLResponse)
def admin_transactions(request: Request):
    profile = get_current_user(request)
    if not profile or profile.get("role") != "admin": return RedirectResponse("/login")
    all_orders = service_supabase.table("orders").select("*").order("created_at", desc=True).execute().data or []
    buyer_ids = list(set(o['buyer_id'] for o in all_orders))
    buyers_map = {}
    if buyer_ids:
        buyers = service_supabase.table("profiles").select("id, full_name").in_("id", buyer_ids).execute().data or []
        for b in buyers: buyers_map[b['id']] = b['full_name']
    for o in all_orders:
        o['buyer_name'] = buyers_map.get(o['buyer_id'], 'Unknown')
    return HTMLResponse(admin_transactions_page(all_orders))

# ---------- Returns Management (with sale reversal) ----------
@app.get("/admin/returns", response_class=HTMLResponse)
def admin_returns(request: Request):
    profile = get_current_user(request)
    if not profile or profile.get("role") != "admin": return RedirectResponse("/login")
    returns = service_supabase.table("returns").select("*").order("created_at", desc=True).execute().data or []
    buyer_ids = [ret['buyer_id'] for ret in returns]
    buyers = {}
    if buyer_ids:
        profiles = service_supabase.table("profiles").select("id, full_name").in_("id", buyer_ids).execute().data or []
        buyers = {p['id']: p['full_name'] for p in profiles}
    for ret in returns:
        ret['buyer_name'] = buyers.get(ret['buyer_id'], 'Unknown')
    return HTMLResponse(returns_management_page(returns))

@app.get("/admin/return/approve/{return_id}")
def admin_approve_return(request: Request, return_id: str):
    profile = get_current_user(request)
    if not profile or profile.get("role") != "admin": return RedirectResponse("/login")
    # Fetch return request
    ret = service_supabase.table("returns").select("*").eq("id", return_id).single().execute()
    if not ret.data:
        return RedirectResponse("/admin/returns", 303)
    order_id = ret.data["order_id"]
    buyer_id = ret.data["buyer_id"]
    # Restore stock for each item in the order
    order_items = service_supabase.table("order_items").select("product_id, quantity").eq("order_id", order_id).execute().data or []
    for item in order_items:
        product = service_supabase.table("products").select("stock, seller_id").eq("id", item["product_id"]).single().execute()
        if product.data:
            new_stock = product.data["stock"] + item["quantity"]
            service_supabase.table("products").update({"stock": new_stock}).eq("id", item["product_id"]).execute()
            # Notify seller
            seller_id = product.data["seller_id"]
            if seller_id:
                create_notification(seller_id, f"Return approved for product #{item['product_id']} in order #{order_id[:8]}. Stock restored.")
    # Mark order as returned
    service_supabase.table("orders").update({"status": "returned"}).eq("id", order_id).execute()
    # Update return request status
    service_supabase.table("returns").update({"status": "approved"}).eq("id", return_id).execute()
    # Notify buyer
    create_notification(buyer_id, f"Your return request #{return_id[:8]} has been approved. Stock restored, sale reversed.")
    notify_admins(f"Return #{return_id[:8]} approved, order #{order_id[:8]} marked returned.")
    return RedirectResponse("/admin/returns", 303)

@app.get("/admin/return/deny/{return_id}")
def admin_deny_return(request: Request, return_id: str):
    profile = get_current_user(request)
    if not profile or profile.get("role") != "admin": return RedirectResponse("/login")
    service_supabase.table("returns").update({"status": "denied"}).eq("id", return_id).execute()
    ret = service_supabase.table("returns").select("buyer_id").eq("id", return_id).single().execute()
    if ret.data:
        create_notification(ret.data["buyer_id"], f"Your return request #{return_id[:8]} has been denied.")
    return RedirectResponse("/admin/returns", 303)

@app.get("/admin/inquiries", response_class=HTMLResponse)
def admin_inquiries(request: Request):
    profile = get_current_user(request)
    if not profile or profile.get("role") != "admin": return RedirectResponse("/login")
    inq = service_supabase.table("inquiries").select("*").order("created_at", desc=True).execute().data or []
    return HTMLResponse(inquiries_page(inq))

@app.get("/admin/export-orders")
def export_orders(request: Request):
    profile = get_current_user(request)
    if not profile or profile.get("role") != "admin": return RedirectResponse("/login")
    orders = service_supabase.table("orders").select("*, profiles!orders_buyer_id_fkey(full_name, email)").order("created_at", desc=True).execute().data or []
    output = io.StringIO()
    w = csv.writer(output)
    w.writerow(["Order ID","Date","Buyer","Total","Status","Payment Method","Payment Status"])
    for o in orders:
        buyer = o.get("profiles", {}) or {}
        w.writerow([o['id'][:8], o['created_at'][:10], buyer.get("full_name",""), o['total_amount'], o['status'], o.get('payment_method',''), o.get('payment_status','')])
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=orders.csv"})

@app.get("/notifications", response_class=HTMLResponse)
def view_notifications(request: Request):
    profile = get_current_user(request)
    if not profile: return RedirectResponse("/login")
    user_id = profile["user_id"]
    notifs = service_supabase.table("notifications").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
    service_supabase.table("notifications").update({"is_read": True}).eq("user_id", user_id).eq("is_read", False).execute()
    return HTMLResponse(notifications_page(notifs.data or []))

@app.get("/notifications/mark-all-read")
def mark_all_read(request: Request):
    profile = get_current_user(request)
    if not profile: return RedirectResponse("/login")
    service_supabase.table("notifications").update({"is_read": True}).eq("user_id", profile["user_id"]).execute()
    return RedirectResponse("/notifications", 303)

@app.get("/terms", response_class=HTMLResponse)
def terms(): return HTMLResponse(TERMS_PAGE)

@app.get("/privacy", response_class=HTMLResponse)
def privacy(): return HTMLResponse(PRIVACY_PAGE)

@app.get("/contact", response_class=HTMLResponse)
def contact_page():
    return HTMLResponse(f"""<!DOCTYPE html><html><head><title>Contact · {APP_NAME}</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
{NAV_GUEST}<div class="container mt-4" style="max-width:500px;"><h2>Contact Us</h2>
<form method="post" action="/contact"><input class="form-control mb-2" name="name" placeholder="Your Name" required>
<input class="form-control mb-2" name="email" type="email" placeholder="Your Email" required>
<textarea class="form-control mb-2" name="message" rows="4" placeholder="Message" required></textarea>
<button class="btn btn-primary">Send Message</button></form></div></body></html>""")

@app.post("/contact")
def contact_submit(name: str = Form(...), email: str = Form(...), message: str = Form(...)):
    service_supabase.table("inquiries").insert({"name": name, "email": email, "message": message}).execute()
    return RedirectResponse("/contact?success=true", 303)

# Catch-all
@app.get("/{full_path:path}")
def catch_all(full_path: str):
    return RedirectResponse("/login", status_code=303)
