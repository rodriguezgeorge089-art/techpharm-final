import os, csv, io
from fastapi import FastAPI, Request, Form, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="a-very-secret-key-change-me")

# ---------- Branding ----------
APP_NAME = "DawaLink Pro"
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
FONTAWESOME = '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">'
CUSTOM_CSS = f"""
<style>
  body {{ background-color: #f4f6f9; font-family: 'Segoe UI', system-ui, sans-serif; }}
  .navbar {{ box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
  .card {{ border: none; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); transition: transform 0.2s; }}
  .card:hover {{ transform: translateY(-3px); box-shadow: 0 6px 16px rgba(0,0,0,0.1); }}
  .btn-primary {{ background-color: {PRIMARY_COLOR}; border-color: {PRIMARY_COLOR}; }}
  .admin-sidebar {{ background-color: #1e293b; color: white; min-height: 100vh; }}
  .admin-sidebar a {{ color: #cbd5e1; padding: 10px; display: block; border-radius: 6px; text-decoration: none; }}
  .admin-sidebar a:hover {{ background-color: #334155; color: white; }}
  .metric-card {{ background: white; border-radius: 12px; padding: 20px; }}
  .metric-card h3 {{ font-size: 2rem; font-weight: bold; }}
  .receipt-container {{ max-width: 600px; margin: auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
  .progress-tracker {{ display: flex; justify-content: space-between; margin-bottom: 0; }}
  .step {{ text-align: center; flex: 1; position: relative; }}
  .step .circle {{ width: 30px; height: 30px; border-radius: 50%; background-color: #dee2e6; margin: 0 auto 5px; line-height: 30px; color: white; }}
  .step.active .circle {{ background-color: {PRIMARY_COLOR}; }}
  .step.completed .circle {{ background-color: #198754; }}
  .step::after {{ content: ''; position: absolute; top: 15px; left: 50%; width: 100%; height: 2px; background-color: #dee2e6; z-index: -1; }}
  .step:last-child::after {{ display: none; }}
  .step.active::after, .step.completed::after {{ background-color: {PRIMARY_COLOR}; }}
  @media (max-width: 768px) {{
    .admin-sidebar {{ min-height: auto; }}
    .admin-sidebar a {{ display: inline-block; }}
  }}
</style>
"""

def navbar(role: str = "", buyer_type: str = ""):
    admin_tab = '<a class="nav-link" href="/admin"><span class="badge bg-warning text-dark">Admin</span></a>' if role == "admin" else ""
    seller_tab = '<a class="nav-link" href="/seller">My Shop</a>' if role == "seller" else ""
    return f"""
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
      <div class="container">
        <a class="navbar-brand" href="/products"><i class="fas fa-pills"></i> {APP_NAME}</a>
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navMain">
          <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="navMain">
          <div class="navbar-nav ms-auto">
            <a class="nav-link" href="/products">Browse</a>
            <a class="nav-link" href="/cart"><i class="fas fa-shopping-cart"></i> Cart</a>
            <a class="nav-link" href="/orders">Orders</a>
            {seller_tab}
            {admin_tab}
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
    <p class="mt-3 text-center"><a href="/forgot-password">Forgot password?</a></p>
    <p class="text-center">Don't have an account? <a href="/signup">Sign up</a></p>
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
      <select class="form-control mb-2" name="role" id="roleSelect">
        <option value="buyer">Buyer</option>
        <option value="seller">Seller</option>
      </select>
      <!-- Buyer type selection (visible when role is buyer) -->
      <div id="buyerTypeDiv" class="mb-2">
        <label class="form-label">Buyer Type:</label>
        <select class="form-control" name="buyer_type">
          <option value="retail">Retail</option>
          <option value="wholesale">Wholesale</option>
        </select>
      </div>
      <button class="btn btn-primary w-100 mt-2">Sign Up</button>
    </form>
    <script>
      document.getElementById('roleSelect').addEventListener('change', function() {{
        document.getElementById('buyerTypeDiv').style.display = this.value === 'buyer' ? 'block' : 'none';
      }});
    </script>
  </div>
</div></body></html>"""

def forgot_password_page(error: str = "", success: str = ""):
    alert = f'<div class="alert alert-danger">{error}</div>' if error else ""
    succ = f'<div class="alert alert-success">{success}</div>' if success else ""
    return f"""<!DOCTYPE html><html><head><title>Forgot Password · {APP_NAME}</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
{NAV_GUEST}
<div class="container mt-5" style="max-width:400px;">
  <div class="card p-4">
    <h3 class="mb-3">Reset Password</h3>
    {alert}{succ}
    <form method="post">
      <input class="form-control mb-2" name="email" placeholder="Email" required>
      <button class="btn btn-primary w-100">Send Reset Link</button>
    </form>
    <p class="mt-3 text-center"><a href="/login">Back to Login</a></p>
  </div>
</div></body></html>"""

def dashboard_page(full_name: str, role: str, buyer_type: str = ""):
    type_badge = f' <span class="badge bg-secondary">{buyer_type}</span>' if role == "buyer" and buyer_type else ""
    return f"""<!DOCTYPE html><html><head><title>Dashboard · {APP_NAME}</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
{navbar(role, buyer_type)}
<div class="container mt-4">
  <h2>Welcome, {full_name} <span class="badge bg-info ms-2">{role}{type_badge}</span></h2>
  <div class="row mt-4">
    <div class="col-md-4 mb-3"><a href="/products" class="btn btn-outline-primary w-100 py-4 fs-5"><i class="fas fa-store"></i> Browse Products</a></div>
    <div class="col-md-4 mb-3"><a href="/cart" class="btn btn-outline-success w-100 py-4 fs-5"><i class="fas fa-shopping-cart"></i> View Cart</a></div>
    <div class="col-md-4 mb-3"><a href="/orders" class="btn btn-outline-warning w-100 py-4 fs-5"><i class="fas fa-box"></i> My Orders</a></div>
  </div>
</div></body></html>"""

def products_page(products_cards: str, role: str, buyer_type: str, page: int, total_pages: int, search: str = ""):
    pagination = ""
    if total_pages > 1:
        pagination = '<nav class="mt-3"><ul class="pagination justify-content-center">'
        for p in range(1, total_pages+1):
            active = "active" if p == page else ""
            pagination += f'<li class="page-item {active}"><a class="page-link" href="/products?page={p}&search={search}">{p}</a></li>'
        pagination += '</ul></nav>'
    return f"""<!DOCTYPE html><html><head><title>Products · {APP_NAME}</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
{navbar(role, buyer_type)}
<div class="container mt-4">
  <h2 class="mb-4">Available Medicines</h2>
  <form class="mb-4" method="get" action="/products">
    <div class="input-group input-group-lg">
      <input class="form-control" name="search" value="{search}" placeholder="Search by name or category">
      <button class="btn btn-primary">Search</button>
    </div>
  </form>
  <div class="row">
    {products_cards}
  </div>
  {pagination}
</div></body></html>"""

def product_card(product: dict, is_buyer: bool, buyer_type: str = "retail"):
    # Determine price to display and use for cart
    price = product['price']
    price_label = "KSh " + str(price)
    if is_buyer and buyer_type == "wholesale" and product.get('wholesale_price') is not None:
        price = product['wholesale_price']
        price_label = f"<span class='text-success'>Wholesale: KSh {price}</span><br><small class='text-muted'>Retail: KSh {product['price']}</small>"
    elif is_buyer and buyer_type == "retail":
        if product.get('wholesale_price'):
            price_label = f"<strong>KSh {price}</strong> <span class='badge bg-info'>Retail</span><br><small class='text-muted'>Wholesale: KSh {product['wholesale_price']}</small>"
        else:
            price_label = f"KSh {price}"
    else:
        price_label = f"KSh {price}"

    img_html = f'<img src="{product.get("image_url")}" class="card-img-top" style="height:200px; object-fit:cover;">' if product.get("image_url") else ""

    add_to_cart_form = f"""
    <form action="/cart/add/{product['id']}" method="get" class="d-flex align-items-center mt-3">
        <input type="number" name="quantity" value="1" min="1" max="{product['stock']}" class="form-control me-2" style="width:80px;">
        <button type="submit" class="btn btn-primary">Add to Cart</button>
    </form>"""

    return f"""
    <div class="col-md-4 mb-4">
      <div class="card h-100 p-3">
        {img_html}
        <div class="card-body">
          <h5 class="card-title fw-bold">{product['name']}</h5>
          <p class="card-text">{product['description']}</p>
          <p><strong>Category:</strong> {product['category']} | <strong>Stock:</strong> {product['stock']}</p>
          <div class="mb-2">{price_label}</div>
          {add_to_cart_form if is_buyer else ""}
        </div>
      </div>
    </div>"""

def cart_page(cart_items_html: str, total: str, role: str, buyer_type: str = ""):
    return f"""<!DOCTYPE html><html><head><title>Cart · {APP_NAME}</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
{navbar(role, buyer_type)}
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
      <p class="text-muted">KSh {unit_price} each</p>
    </div>
    <div class="col-md-4 d-flex align-items-center">
      <form action="/cart/update/{product_id}" method="get" class="d-flex align-items-center w-100">
        <input type="number" name="quantity" value="{quantity}" min="1" max="999" class="form-control me-2" style="width:80px;">
        <button type="submit" class="btn btn-sm btn-outline-primary">Update</button>
      </form>
    </div>
    <div class="col-md-4 text-end">
      <strong>KSh {subtotal}</strong>
      <a href="/cart/remove/{product_id}" class="btn btn-sm btn-outline-danger ms-2" onclick="return confirm('Remove this item?')">Remove</a>
    </div>
  </div>
</div>"""

def orders_page(order_list_html: str, role: str, buyer_type: str = ""):
    return f"""<!DOCTYPE html><html><head><title>Orders · {APP_NAME}</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
{navbar(role, buyer_type)}
<div class="container mt-4">
  <h2>My Orders</h2>
  {order_list_html}
</div></body></html>"""

ORDER_ITEM_HTML = """
<div class="card mb-3 p-4">
  <div class="card-body">
    <h5>Order #{order_id_short} <span class="badge bg-{status_color} ms-2">{status}</span></h5>
    <p><strong>Date:</strong> {date} | <strong>Payment:</strong> {payment_method} | <strong>Total:</strong> KSh {total}</p>
    <ul>
      {products_list}
    </ul>
    <div class="progress-tracker mt-3 mb-3">
      <div class="step {pending_class}"><div class="circle">1</div><small>Pending</small></div>
      <div class="step {confirmed_class}"><div class="circle">2</div><small>Confirmed</small></div>
      <div class="step {shipped_class}"><div class="circle">3</div><small>Shipped</small></div>
      <div class="step {delivered_class}"><div class="circle">4</div><small>Delivered</small></div>
    </div>
    <a href="/receipt/{order_id}" class="btn btn-sm btn-outline-primary"><i class="fas fa-print"></i> View Receipt</a>
  </div>
</div>"""

def seller_dashboard_page(product_cards: str, role: str):
    return f"""<!DOCTYPE html><html><head><title>My Shop · {APP_NAME}</title>{BOOTSTRAP}{CUSTOM_CSS}{FONTAWESOME}</head><body>
{navbar(role)}
<div class="container mt-4">
  <h2>My Products</h2>
  <a href="/seller/add" class="btn btn-success mb-4"><i class="fas fa-plus"></i> Add New Product</a>
  <a href="/seller/orders" class="btn btn-info mb-4"><i class="fas fa-list"></i> My Orders</a>
  <div class="row">
    {product_cards}
  </div>
</div></body></html>"""

SELLER_PRODUCT_CARD = """
<div class="col-md-4 mb-4">
  <div class="card h-100 p-3">
    {image_html}
    <div class="card-body">
      <h5 class="fw-bold">{name}</h5>
      <p>{description}</p>
      <p><strong>Category:</strong> {category} | <strong>Stock:</strong> {stock} | <strong>Cost:</strong> KSh {cost_price}</p>
      <h3 class="text-success">Retail: KSh {price}</h3>
      {wholesale_info}
      <a href="/seller/edit/{id}" class="btn btn-warning btn-sm">Edit</a>
      <a href="/seller/delete/{id}" class="btn btn-danger btn-sm" onclick="return confirm('Delete?')">Delete</a>
    </div>
  </div>
</div>"""

# Navigation placeholder
navigation = ""

ADD_PRODUCT_PAGE = f"""<!DOCTYPE html><html><head><title>Add Product · {APP_NAME}</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
{navigation}
<div class="container mt-4" style="max-width:500px;">
  <h2>Add New Product</h2>
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
    <button class="btn btn-primary w-100">Add Product</button>
  </form>
</div></body></html>"""

EDIT_PRODUCT_PAGE = f"""<!DOCTYPE html><html><head><title>Edit Product · {APP_NAME}</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
{navigation}
<div class="container mt-4" style="max-width:500px;">
  <h2>Edit Product</h2>
  <form method="post" enctype="multipart/form-data">
    <input class="form-control mb-2" name="name" value="{{name}}" required>
    <textarea class="form-control mb-2" name="description" rows="3">{{description}}</textarea>
    <input class="form-control mb-2" name="category" value="{{category}}" required>
    <input class="form-control mb-2" type="number" step="0.01" name="price" value="{{price}}" placeholder="Retail Price" required>
    <input class="form-control mb-2" type="number" step="0.01" name="wholesale_price" value="{{wholesale_price}}" placeholder="Wholesale Price (optional)">
    <input class="form-control mb-2" type="number" step="0.01" name="cost_price" value="{{cost_price}}" placeholder="Cost Price">
    <input class="form-control mb-2" type="number" name="stock" value="{{stock}}" required>
    <label class="form-label">Replace Image (leave empty to keep current)</label>
    <input class="form-control mb-2" type="file" name="image" accept="image/*">
    <button class="btn btn-primary w-100">Update Product</button>
  </form>
</div></body></html>"""

# Payment Success (updated with receipt link)
def payment_success_page(order):
    items = supabase.table("order_items").select("*, products(name)").eq("order_id", order["id"]).execute()
    items_html = "".join(
        f"<tr><td>{item['products']['name']}</td><td>{item['quantity']}</td><td>KSh {item['unit_price']}</td><td>KSh {item['quantity'] * item['unit_price']}</td></tr>"
        for item in items.data
    )
    return f"""<!DOCTYPE html><html><head><title>Payment Successful · {APP_NAME}</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
<div class="container mt-5" style="max-width:600px;">
  <div class="card p-4 text-center">
    <h2 class="text-success"><i class="fas fa-check-circle"></i> Payment Successful!</h2>
    <p>Your order has been placed and is pending admin confirmation.</p>
    <hr>
    <h5>Order Summary</h5>
    <table class="table table-bordered">
      <thead><tr><th>Product</th><th>Qty</th><th>Unit Price</th><th>Subtotal</th></tr></thead>
      <tbody>{items_html}</tbody>
      <tfoot><tr><th colspan="3" class="text-end">Total</th><th>KSh {order['total_amount']}</th></tr></tfoot>
    </table>
    <p><strong>Payment Method:</strong> {order.get('payment_method','N/A')}</p>
    <a href="/receipt/{order['id']}" class="btn btn-primary"><i class="fas fa-print"></i> View / Print Receipt</a>
    <a href="/orders" class="btn btn-outline-secondary ms-2">My Orders</a>
  </div>
</div></body></html>"""

def receipt_page(order):
    items = supabase.table("order_items").select("*, products(name)").eq("order_id", order["id"]).execute()
    items_html = "".join(
        f"<tr><td>{item['products']['name']}</td><td>{item['quantity']}</td><td>KSh {item['unit_price']}</td><td>KSh {item['quantity'] * item['unit_price']}</td></tr>"
        for item in items.data
    )
    return f"""<!DOCTYPE html><html><head><title>Receipt · {APP_NAME}</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
<div class="receipt-container mt-4">
  <div class="text-center mb-4">
    <h2><i class="fas fa-pills"></i> {APP_NAME}</h2>
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
  <div class="text-center mt-4">
    <button class="btn btn-primary" onclick="window.print()"><i class="fas fa-print"></i> Print Receipt</button>
    <a href="/orders" class="btn btn-outline-secondary">Back to Orders</a>
  </div>
</div></body></html>"""

# ---------- Admin Dashboard with Payment Verification ----------
def admin_dashboard_page(metrics, orders_html: str, role: str):
    return f"""<!DOCTYPE html><html><head><title>Admin · {APP_NAME}</title>{BOOTSTRAP}{CUSTOM_CSS}{FONTAWESOME}</head><body>
{navbar(role)}
<div class="container-fluid">
  <div class="row">
    <div class="col-md-2 admin-sidebar p-3">
      <h5><i class="fas fa-shield-alt"></i> Admin Panel</h5>
      <a href="/admin"><i class="fas fa-tachometer-alt"></i> Dashboard</a>
      <a href="/admin/inquiries"><i class="fas fa-envelope"></i> Inquiries</a>
      <a href="/admin/export-orders"><i class="fas fa-download"></i> Export CSV</a>
      <a href="/products">View Site</a>
    </div>
    <div class="col-md-10 p-4">
      <h2>Admin Dashboard</h2>
      <div class="row mt-4">
        <div class="col-md-3"><div class="metric-card text-center"><h3>{metrics['total_sales']}</h3><p>Total Sales (KSh)</p></div></div>
        <div class="col-md-3"><div class="metric-card text-center"><h3>{metrics['total_profit']}</h3><p>Estimated Profit (KSh)</p></div></div>
        <div class="col-md-3"><div class="metric-card text-center"><h3>{metrics['total_orders']}</h3><p>Total Orders</p></div></div>
        <div class="col-md-3"><div class="metric-card text-center"><h3>{metrics['total_users']}</h3><p>Registered Users</p></div></div>
      </div>
      <hr class="mt-4">
      <div class="d-flex justify-content-between align-items-center">
        <h4>Recent Orders</h4>
        <a href="/admin/export-orders" class="btn btn-sm btn-outline-success"><i class="fas fa-file-csv"></i> Export CSV</a>
      </div>
      {orders_html}
    </div>
  </div>
</div></body></html>"""

def admin_order_item(order):
    status_opts = ["pending","confirmed","shipped","delivered"]
    status_options = "".join([
        f"<option value='{s}' {'selected' if s == order['status'] else ''}>{s.capitalize()}</option>"
        for s in status_opts
    ])
    payment_status = order.get('payment_status', 'pending')
    payment_verified = payment_status == 'verified'
    items = supabase.table("order_items").select("*, products(name, cost_price)").eq("order_id", order["id"]).execute()
    products_list = "".join(
        f"<li>{item['products']['name']} x {item['quantity']} @ KSh {item['unit_price']} (Cost KSh {item['products'].get('cost_price',0)})</li>"
        for item in (items.data or [])
    )
    profit = order.get('profit', 0)
    payment_btn = ""
    if not payment_verified:
        payment_btn = f'<a href="/admin/verify-payment/{order["id"]}" class="btn btn-sm btn-outline-success ms-1">Verify Payment</a>'
    else:
        payment_btn = '<span class="badge bg-success">Payment Verified</span>'

    return f"""
    <div class="card mb-3 p-3">
      <div class="card-body">
        <h5>Order #{order['id'][:8]} — <span class="badge bg-{'warning' if order['status']=='pending' else 'info'}">{order['status']}</span></h5>
        <p><strong>Buyer:</strong> {order.get('profiles', {}).get('full_name', 'Unknown')} ({order.get('profiles', {}).get('phone', 'N/A')})</p>
        <p><strong>Total:</strong> KSh {order['total_amount']} · <strong>Profit:</strong> KSh {profit} · <strong>Payment:</strong> {order.get('payment_method', 'N/A')} · <strong>Date:</strong> {order['created_at'][:10]}</p>
        <p><strong>Payment Status:</strong> {payment_status} {payment_btn}</p>
        <ul>{products_list}</ul>
        <form method="post" action="/admin/update-order/{order['id']}" class="d-flex align-items-center">
          <select class="form-select me-2" name="status" style="width:auto;">
            {status_options}
          </select>
          <button class="btn btn-sm btn-primary">Update Status</button>
        </form>
      </div>
    </div>"""

def inquiries_page(inquiries):
    rows = "".join(
        f"<tr><td>{inq['name']}</td><td>{inq['email']}</td><td>{inq['message']}</td><td>{inq['created_at'][:10]}</td></tr>"
        for inq in inquiries
    )
    return f"""<!DOCTYPE html><html><head><title>Inquiries · Admin</title>{BOOTSTRAP}{CUSTOM_CSS}{FONTAWESOME}</head><body>
{navbar('admin')}
<div class="container-fluid">
  <div class="row">
    <div class="col-md-2 admin-sidebar p-3">
      <h5><i class="fas fa-shield-alt"></i> Admin Panel</h5>
      <a href="/admin">Dashboard</a>
      <a href="/admin/inquiries">Inquiries</a>
      <a href="/admin/export-orders">Export CSV</a>
      <a href="/products">View Site</a>
    </div>
    <div class="col-md-10 p-4">
      <h2>Customer Inquiries</h2>
      <table class="table table-bordered">
        <thead><tr><th>Name</th><th>Email</th><th>Message</th><th>Date</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
  </div>
</div></body></html>"""

TERMS_PAGE = f"""<!DOCTYPE html><html><head><title>Terms · {APP_NAME}</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
{NAV_GUEST}
<div class="container mt-4"><h2>Terms of Service</h2><p>Sample terms. Replace with real legal text.</p></div></body></html>"""

PRIVACY_PAGE = f"""<!DOCTYPE html><html><head><title>Privacy · {APP_NAME}</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
{NAV_GUEST}
<div class="container mt-4"><h2>Privacy Policy</h2><p>Sample privacy policy. Replace with real text.</p></div></body></html>"""

# ---------- Helpers ----------
def get_cart(request: Request):
    return request.session.get("cart", [])

def save_cart(request: Request, cart):
    request.session["cart"] = cart

def get_progress_classes(status):
    mapping = {
        "pending": ("active", "", "", ""),
        "confirmed": ("completed", "active", "", ""),
        "shipped": ("completed", "completed", "active", ""),
        "delivered": ("completed", "completed", "completed", "active")
    }
    return mapping.get(status, ("", "", "", ""))

def product_image_html(url):
    return f'<img src="{url}" class="card-img-top" style="height:200px; object-fit:cover;">' if url else ""

def upload_image(file: UploadFile):
    if not file or not file.filename or not service_supabase:
        return None
    try:
        contents = file.file.read()
        file_name = f"{int(os.urandom(4).hex(),16)}_{file.filename}"
        bucket = "product-images"
        service_supabase.storage.from_(bucket).upload(file_name, contents, {"content-type": file.content_type})
        return f"{SUPABASE_URL}/storage/v1/object/public/{bucket}/{file_name}"
    except:
        return None

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
def signup(full_name: str = Form(...), email: str = Form(...), password: str = Form(...),
           role: str = Form(...), buyer_type: str = Form("retail")):
    try:
        resp = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {"data": {"full_name": full_name}}
        })
        profile_data = {"role": role}
        if role == "buyer":
            profile_data["buyer_type"] = buyer_type
        supabase.table("profiles").update(profile_data).eq("user_id", resp.user.id).execute()
        return RedirectResponse("/login", status_code=303)
    except Exception as e:
        return HTMLResponse(signup_page(str(e)))

@app.get("/forgot-password", response_class=HTMLResponse)
def forgot_password_page_route():
    return HTMLResponse(forgot_password_page())

@app.post("/forgot-password")
def forgot_password(email: str = Form(...)):
    try:
        supabase.auth.reset_password_email(email)
        return HTMLResponse(forgot_password_page(success="Password reset link sent! Check your email."))
    except Exception as e:
        return HTMLResponse(forgot_password_page(error=str(e)))

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    sup = get_valid_session(request)
    if not sup: return RedirectResponse("/login")
    profile = get_user_profile(sup)
    if not profile.data:
        return RedirectResponse("/logout")
    role = profile.data.get("role", "buyer")
    full_name = profile.data.get("full_name", "User")
    buyer_type = profile.data.get("buyer_type", "")
    return HTMLResponse(dashboard_page(full_name, role, buyer_type))

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login")

# ---------- Products with wholesale/retail ----------
@app.get("/products", response_class=HTMLResponse)
def products(request: Request, search: str = "", page: int = 1):
    sup = get_valid_session(request)
    if not sup: return RedirectResponse("/login")
    profile = get_user_profile(sup)
    role = profile.data.get("role", "buyer") if profile.data else "buyer"
    buyer_type = profile.data.get("buyer_type", "retail") if role == "buyer" else ""
    is_buyer = role == "buyer"
    per_page = 6
    offset = (page - 1) * per_page
    count_query = sup.table("products").select("count", count="exact").eq("active", True)
    if search:
        count_query = count_query.or_(f"name.ilike.%{search}%,category.ilike.%{search}%")
    total = count_query.execute().count or 0
    query = sup.table("products").select("*").eq("active", True)
    if search:
        query = query.or_(f"name.ilike.%{search}%,category.ilike.%{search}%")
    result = query.range(offset, offset + per_page - 1).execute()
    products_data = result.data or []
    cards = ""
    for p in products_data:
        cards += product_card(p, is_buyer, buyer_type)
    total_pages = (total + per_page - 1) // per_page
    return HTMLResponse(products_page(cards, role, buyer_type, page, total_pages, search))

# ---------- Seller Orders ----------
@app.get("/seller/orders", response_class=HTMLResponse)
def seller_orders(request: Request):
    sup = get_valid_session(request)
    if not sup: return RedirectResponse("/login")
    profile = get_user_profile(sup)
    if not profile.data or profile.data['role'] != 'seller':
        return HTMLResponse("<div class='alert alert-danger'>Access denied</div>")
    seller_id = profile.data['id']
    result = sup.table("order_items").select("*, orders!inner(*, profiles!orders_buyer_id_fkey(full_name)), products!inner(*)").eq("products.seller_id", seller_id).order("orders.created_at", desc=True).execute()
    orders_dict = {}
    for item in result.data or []:
        order = item['orders']
        oid = order['id']
        if oid not in orders_dict:
            order['items'] = []
            orders_dict[oid] = order
        orders_dict[oid]['items'].append(item)
    html = ""
    for order in orders_dict.values():
        items_list = "".join(f"<li>{it['products']['name']} x {it['quantity']} @ KSh {it['unit_price']}</li>" for it in order['items'])
        html += f"<div class='card mb-3 p-3'><h5>Order #{order['id'][:8]} - {order['status']}</h5><p>Buyer: {order.get('profiles',{}).get('full_name','Unknown')}</p><ul>{items_list}</ul></div>"
    if not html:
        html = "<p>No orders containing your products yet.</p>"
    return HTMLResponse(f"""<!DOCTYPE html><html><head><title>My Orders · {APP_NAME}</title>{BOOTSTRAP}{CUSTOM_CSS}{FONTAWESOME}</head><body>
{navbar('seller')}
<div class="container mt-4"><h2>Orders for My Products</h2>{html}</div></body></html>""")

# ---------- Seller (remainder unchanged, but with wholesale price handling) ----------
@app.get("/seller", response_class=HTMLResponse)
def seller_dashboard(request: Request):
    sup = get_valid_session(request)
    if not sup: return RedirectResponse("/login")
    profile = get_user_profile(sup)
    if not profile.data or profile.data['role'] != 'seller':
        return HTMLResponse("<div class='alert alert-danger'>Access denied</div>")
    prods = sup.table("products").select("*").eq("seller_id", profile.data['id']).execute()
    cards = ""
    for p in (prods.data or []):
        img = product_image_html(p.get("image_url"))
        wholesale_info = f"<p><strong>Wholesale:</strong> KSh {p['wholesale_price']}</p>" if p.get("wholesale_price") else "<p>No wholesale price set</p>"
        cards += SELLER_PRODUCT_CARD.format(image_html=img, wholesale_info=wholesale_info, **p)
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
async def seller_add(request: Request, name: str = Form(...), description: str = Form(""),
                     category: str = Form(...), price: float = Form(...),
                     wholesale_price: float = Form(None), cost_price: float = Form(0),
                     stock: int = Form(...), image: UploadFile = File(None)):
    sup = get_valid_session(request)
    if not sup: return RedirectResponse("/login")
    profile = get_user_profile(sup)
    image_url = upload_image(image)
    data = {
        "seller_id": profile.data['id'], "name": name, "description": description,
        "category": category, "price": price, "cost_price": cost_price,
        "stock": stock, "image_url": image_url
    }
    if wholesale_price is not None:
        data["wholesale_price"] = wholesale_price
    sup.table("products").insert(data).execute()
    return RedirectResponse("/seller", status_code=303)

@app.get("/seller/edit/{product_id}", response_class=HTMLResponse)
def seller_edit_form(request: Request, product_id: str):
    sup = get_valid_session(request)
    if not sup: return RedirectResponse("/login")
    product = sup.table("products").select("*").eq("id", product_id).single().execute()
    page = EDIT_PRODUCT_PAGE.replace("{navigation}", navbar("seller"))
    return HTMLResponse(page.format(**product.data))

@app.post("/seller/edit/{product_id}")
async def seller_edit(request: Request, product_id: str, name: str = Form(...), description: str = Form(""),
                      category: str = Form(...), price: float = Form(...),
                      wholesale_price: float = Form(None), cost_price: float = Form(0),
                      stock: int = Form(...), image: UploadFile = File(None)):
    sup = get_valid_session(request)
    if not sup: return RedirectResponse("/login")
    update_data = {
        "name": name, "description": description, "category": category,
        "price": price, "stock": stock, "cost_price": cost_price
    }
    if wholesale_price is not None:
        update_data["wholesale_price"] = wholesale_price
    image_url = upload_image(image)
    if image_url:
        update_data["image_url"] = image_url
    sup.table("products").update(update_data).eq("id", product_id).execute()
    return RedirectResponse("/seller", status_code=303)

@app.get("/seller/delete/{product_id}")
def seller_delete(request: Request, product_id: str):
    sup = get_valid_session(request)
    if not sup: return RedirectResponse("/login")
    sup.table("products").delete().eq("id", product_id).execute()
    return RedirectResponse("/seller", status_code=303)

# ---------- Cart (now stores unit price) ----------
@app.get("/cart", response_class=HTMLResponse)
def view_cart(request: Request):
    sup = get_valid_session(request)
    if not sup: return RedirectResponse("/login")
    profile = get_user_profile(sup)
    role = profile.data.get("role", "buyer") if profile.data else "buyer"
    buyer_type = profile.data.get("buyer_type", "retail") if role == "buyer" else ""
    cart = get_cart(request)
    if not cart:
        return HTMLResponse(cart_page("<p>Your cart is empty.</p>", "0.00", role, buyer_type))
    items_html = ""
    total = 0.0
    for item in cart:
        subtotal = item["unit_price"] * item["quantity"]
        total += subtotal
        items_html += CART_ITEM.format(
            name=item.get("name", "Product"),
            unit_price=item["unit_price"],
            product_id=item["product_id"],
            quantity=item["quantity"],
            subtotal=round(subtotal, 2)
        )
    return HTMLResponse(cart_page(items_html, str(round(total, 2)), role, buyer_type))

@app.get("/cart/add/{product_id}")
def add_to_cart(request: Request, product_id: str, quantity: int = 1):
    sup = get_valid_session(request)
    if not sup: return RedirectResponse("/login")
    profile = get_user_profile(sup)
    if not profile.data or profile.data['role'] != 'buyer':
        return RedirectResponse("/products")
    buyer_type = profile.data.get("buyer_type", "retail")
    product = sup.table("products").select("*").eq("id", product_id).single().execute()
    if not product.data or not product.data['active']:
        return RedirectResponse("/products")
    # Determine unit price based on buyer type
    price = product.data['price']
    if buyer_type == "wholesale" and product.data.get('wholesale_price') is not None:
        price = product.data['wholesale_price']
    if quantity < 1:
        quantity = 1
    cart = get_cart(request)
    for item in cart:
        if item["product_id"] == product_id:
            item["quantity"] += quantity
            save_cart(request, cart)
            return RedirectResponse("/cart", status_code=303)
    cart.append({
        "product_id": product_id,
        "quantity": quantity,
        "unit_price": price,
        "name": product.data['name']
    })
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
        if not profile.data or profile.data.get("role") != "buyer":
            return RedirectResponse("/products")
        buyer_id = profile.data["id"]
        cart = get_cart(request)
        if not cart:
            return RedirectResponse("/cart")
        total = 0.0
        order_items_data = []
        for item in cart:
            product = sup.table("products").select("*").eq("id", item["product_id"]).single().execute()
            if not product.data or product.data["stock"] < item["quantity"]:
                return HTMLResponse(f"<h2>Not enough stock for '{product.data.get('name','product')}'.</h2><a href='/cart'>Back</a>")
            price = item["unit_price"]  # already selected correctly
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
            "payment_method": payment_method,
            "payment_status": "pending"
        }).execute()
        if not order.data:
            return HTMLResponse("<h2>Failed to create order.</h2>")
        order_id = order.data[0]["id"]
        for oi in order_items_data:
            oi["order_id"] = order_id
            sup.table("order_items").insert(oi).execute()
        save_cart(request, [])
        return RedirectResponse(f"/payment-success/{order_id}", status_code=303)
    except Exception as e:
        return HTMLResponse(f"<div class='alert alert-danger'>Checkout Error: {str(e)}</div>")

@app.get("/payment-success/{order_id}", response_class=HTMLResponse)
def payment_success(request: Request, order_id: str):
    sup = get_valid_session(request)
    if not sup: return RedirectResponse("/login")
    profile = get_user_profile(sup)
    if not profile.data:
        return RedirectResponse("/login")
    order = sup.table("orders").select("*").eq("id", order_id).single().execute()
    if not order.data or order.data["buyer_id"] != profile.data["id"]:
        return HTMLResponse("<div class='alert alert-danger'>Order not found or access denied.</div>")
    return HTMLResponse(payment_success_page(order.data))

@app.get("/receipt/{order_id}", response_class=HTMLResponse)
def view_receipt(request: Request, order_id: str):
    sup = get_valid_session(request)
    if not sup: return RedirectResponse("/login")
    profile = get_user_profile(sup)
    if not profile.data:
        return RedirectResponse("/login")
    order = sup.table("orders").select("*").eq("id", order_id).single().execute()
    if not order.data or order.data["buyer_id"] != profile.data["id"]:
        return HTMLResponse("<div class='alert alert-danger'>Receipt not found or access denied.</div>")
    return HTMLResponse(receipt_page(order.data))

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
        buyer_type = profile.data.get("buyer_type", "") if role == "buyer" else ""
        orders_result = sup.table("orders").select("*").eq("buyer_id", buyer_id).order("created_at", desc=True).execute()
        if not orders_result.data:
            return HTMLResponse(orders_page("<p>No orders yet.</p>", role, buyer_type))
        orders_html = ""
        for order in orders_result.data:
            items = sup.table("order_items").select("*, products(name)").eq("order_id", order["id"]).execute()
            products_list = ""
            if items.data:
                for item in items.data:
                    products_list += f"<li>{item['products']['name']} x {item['quantity']} @ KSh {item['unit_price']}</li>"
            status_color = {"pending":"warning","confirmed":"info","shipped":"primary","delivered":"success"}.get(order["status"], "secondary")
            pending_cls, confirmed_cls, shipped_cls, delivered_cls = get_progress_classes(order["status"])
            orders_html += ORDER_ITEM_HTML.format(
                order_id_short=order["id"][:8],
                order_id=order["id"],
                status=order["status"],
                status_color=status_color,
                total=order["total_amount"],
                payment_method=order.get("payment_method", "N/A"),
                date=order["created_at"][:10],
                products_list=products_list,
                pending_class=pending_cls,
                confirmed_class=confirmed_cls,
                shipped_class=shipped_cls,
                delivered_class=delivered_cls
            )
        return HTMLResponse(orders_page(orders_html, role, buyer_type))
    except Exception as e:
        return HTMLResponse(f"<div class='alert alert-danger'>Orders Error: {str(e)}</div>")

# ---------- Admin with payment verification ----------
@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request):
    sup = get_valid_session(request)
    if not sup: return RedirectResponse("/login")
    profile = get_user_profile(sup)
    if not profile.data or profile.data.get("role") != "admin":
        return HTMLResponse("<div class='alert alert-danger'>Access denied · Admins only</div>")
    # Metrics
    total_sales_result = sup.table("orders").select("total_amount").execute()
    total_sales = sum(o['total_amount'] for o in total_sales_result.data) if total_sales_result.data else 0
    profit = 0
    items = sup.table("order_items").select("quantity, unit_price, products(cost_price)").execute()
    if items.data:
        for it in items.data:
            cost = it['products']['cost_price'] if it['products'] else 0
            profit += (it['unit_price'] - cost) * it['quantity']
    total_orders = sup.table("orders").select("count", count="exact").execute()
    total_users = sup.table("profiles").select("count", count="exact").execute()
    metrics = {
        "total_sales": f"{total_sales:,.2f}",
        "total_profit": f"{profit:,.2f}",
        "total_orders": total_orders.count or 0,
        "total_users": total_users.count or 0
    }
    orders_result = sup.table("orders").select("*, profiles!orders_buyer_id_fkey(full_name, phone)").order("created_at", desc=True).execute()
    orders_html = ""
    if orders_result.data:
        for o in orders_result.data:
            o['profiles'] = o.get('profiles', {}) or {}
            # Calculate profit for order
            order_items = sup.table("order_items").select("quantity, unit_price, products(cost_price)").eq("order_id", o['id']).execute()
            order_profit = 0
            if order_items.data:
                for it in order_items.data:
                    cost = it['products']['cost_price'] if it['products'] else 0
                    order_profit += (it['unit_price'] - cost) * it['quantity']
            o['profit'] = round(order_profit, 2)
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

@app.get("/admin/verify-payment/{order_id}")
def verify_payment(request: Request, order_id: str):
    sup = get_valid_session(request)
    if not sup: return RedirectResponse("/login")
    profile = get_user_profile(sup)
    if not profile.data or profile.data.get("role") != "admin":
        return HTMLResponse("<div class='alert alert-danger'>Access denied</div>")
    sup.table("orders").update({"payment_status": "verified"}).eq("id", order_id).execute()
    return RedirectResponse("/admin", status_code=303)

@app.get("/admin/inquiries", response_class=HTMLResponse)
def admin_inquiries(request: Request):
    sup = get_valid_session(request)
    if not sup: return RedirectResponse("/login")
    profile = get_user_profile(sup)
    if not profile.data or profile.data.get("role") != "admin":
        return HTMLResponse("<div class='alert alert-danger'>Access denied</div>")
    inquiries = sup.table("inquiries").select("*").order("created_at", desc=True).execute()
    return HTMLResponse(inquiries_page(inquiries.data or []))

@app.get("/admin/export-orders")
def export_orders(request: Request):
    sup = get_valid_session(request)
    if not sup: return RedirectResponse("/login")
    profile = get_user_profile(sup)
    if not profile.data or profile.data.get("role") != "admin":
        return HTMLResponse("<div class='alert alert-danger'>Access denied</div>")
    orders = sup.table("orders").select("*, profiles!orders_buyer_id_fkey(full_name, email)").order("created_at", desc=True).execute()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Order ID", "Date", "Buyer Name", "Buyer Email", "Total Amount", "Status", "Payment Method", "Payment Status"])
    for o in orders.data or []:
        writer.writerow([o['id'][:8], o['created_at'][:10], o.get('profiles',{}).get('full_name',''), o.get('profiles',{}).get('email',''), o['total_amount'], o['status'], o.get('payment_method',''), o.get('payment_status','')])
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=orders.csv"})

# ---------- Legal & Contact ----------
@app.get("/terms", response_class=HTMLResponse)
def terms():
    return HTMLResponse(TERMS_PAGE)

@app.get("/privacy", response_class=HTMLResponse)
def privacy():
    return HTMLResponse(PRIVACY_PAGE)

@app.get("/contact", response_class=HTMLResponse)
def contact_page():
    return HTMLResponse(f"""<!DOCTYPE html><html><head><title>Contact · {APP_NAME}</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
{NAV_GUEST}
<div class="container mt-4" style="max-width:500px;">
  <h2>Contact Us</h2>
  <form method="post" action="/contact">
    <input class="form-control mb-2" name="name" placeholder="Your Name" required>
    <input class="form-control mb-2" name="email" type="email" placeholder="Your Email" required>
    <textarea class="form-control mb-2" name="message" rows="4" placeholder="Message" required></textarea>
    <button class="btn btn-primary">Send Message</button>
  </form>
</div></body></html>""")

@app.post("/contact")
def contact_submit(name: str = Form(...), email: str = Form(...), message: str = Form(...)):
    supabase.table("inquiries").insert({"name": name, "email": email, "message": message}).execute()
    return RedirectResponse("/contact?success=true", status_code=303)
