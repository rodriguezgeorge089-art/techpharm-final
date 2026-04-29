import os, io, csv, urllib.parse
from fastapi import FastAPI, Request, Form, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="dawalink-pharmacy-secret")

APP_NAME = "DawaLink"
APP_TAGLINE = "Medicine At Your Convenience!!"
PRIMARY_COLOR = "#0d6efd"
PHARMACY_PHONE = "+254792524333"          # No spaces, correct number
PHARMACY_EMAIL = "info@dawalink.co.ke"
PHARMACY_ADDRESS = " Mombasa Road, Taji Mall, Nairobi"

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
service_supabase = create_client(SUPABASE_URL, SERVICE_ROLE_KEY) if SERVICE_ROLE_KEY else supabase

# ---------- Helpers ----------
def get_cart(request: Request):
    return request.session.get("cart", [])

def save_cart(request: Request, cart):
    request.session["cart"] = cart

# ---------- HTML Components ----------
BOOTSTRAP = '<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">'
FONTAWESOME = '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">'
BOOTSTRAP_JS = '<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>'
CUSTOM_CSS = f"""
<style>
  body {{ background: #f5f7fa; font-family: 'Segoe UI', system-ui, sans-serif; }}
  .navbar {{ box-shadow: 0 2px 8px rgba(0,0,0,0.1); background: white; }}
  .card {{ border: none; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); transition: transform 0.2s; }}
  .card:hover {{ transform: translateY(-3px); box-shadow: 0 6px 16px rgba(0,0,0,0.1); }}
  .btn-primary {{ background-color: {PRIMARY_COLOR}; border-color: {PRIMARY_COLOR}; }}
  .hero {{ background: linear-gradient(135deg, {PRIMARY_COLOR}, #004085); color: white; padding: 5rem 0; text-align: center; }}
  .hero h1 {{ font-size: 3rem; font-weight: bold; margin-bottom: 1rem; }}
  .hero p {{ font-size: 1.2rem; opacity: 0.9; max-width: 600px; margin: 0 auto 2rem; }}
  .feature-card {{ transition: transform 0.3s ease; border-radius: 10px; background: white; padding: 2rem; text-align: center; }}
  .feature-card:hover {{ transform: translateY(-5px); box-shadow: 0 10px 20px rgba(0,0,0,0.1); }}
  .top-category-card {{ background: white; border-radius: 10px; padding: 1.5rem; text-align: center; box-shadow: 0 2px 10px rgba(0,0,0,0.05); transition: all 0.3s ease; }}
  .top-category-card:hover {{ box-shadow: 0 5px 15px rgba(0,0,0,0.1); transform: translateY(-3px); }}
  .footer {{ background: #f8f9fa; padding: 3rem 0; margin-top: 3rem; border-top: 1px solid #dee2e6; }}
  .top-bar {{ background-color: {PRIMARY_COLOR}; color: white; font-size: 0.9rem; }}
  .filter-sidebar {{ background: white; padding: 1.5rem; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }}
  .admin-sidebar {{ background-color: #1e293b; color: white; min-height: 100vh; }}
  .admin-sidebar a {{ color: #cbd5e1; padding: 10px; display: block; text-decoration: none; border-radius: 6px; }}
  .admin-sidebar a:hover {{ background-color: #334155; color: white; }}
  .metric-card {{ background: white; border-radius: 12px; padding: 20px; }}
  .metric-card h3 {{ font-size: 2rem; font-weight: bold; }}
  .dropdown-mega {{ min-width: 300px; }}
</style>
"""

def top_bar():
    return f"""
    <div class="top-bar py-1" id="topBar">
      <div class="container d-flex justify-content-between">
        <span>Product update ongoing – if you search and don't find a product please call <strong>{PHARMACY_PHONE}</strong> for assistance!!</span>
        <button onclick="document.getElementById('topBar').style.display='none'" class="btn-close btn-close-white"></button>
      </div>
    </div>"""

def public_navbar():
    return f"""
    {top_bar()}
    <nav class="navbar navbar-expand-lg navbar-light bg-white shadow-sm">
      <div class="container">
        <a class="navbar-brand fw-bold text-primary" href="/"><i class="fas fa-pills"></i> {APP_NAME}<br><small class="text-muted" style="font-size:0.7rem;">Online Pharmacy</small></a>
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navPublic">
          <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="navPublic">
          <ul class="navbar-nav ms-auto">
            <li class="nav-item"><a class="nav-link" href="/">Home</a></li>
            <li class="nav-item"><a class="nav-link" href="/about">About Us</a></li>
            <li class="nav-item"><a class="nav-link" href="/contact">Contact</a></li>
            <li class="nav-item dropdown">
              <a class="nav-link dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown">All Departments</a>
              <ul class="dropdown-menu dropdown-mega p-3">
                <li class="dropdown-header fw-bold">Shop by Category</li>
                <li><a class="dropdown-item" href="/shop?category=Supplements">Supplements</a></li>
                <li><a class="dropdown-item" href="/shop?category=Baby+Care">Baby Care</a></li>
                <li><a class="dropdown-item" href="/shop?category=Probiotics">Probiotics</a></li>
                <li><a class="dropdown-item" href="/shop?category=Prescription">Prescription</a></li>
                <li><a class="dropdown-item" href="/shop?category=Colds+and+Flu">Colds and Flu</a></li>
                <li><hr class="dropdown-divider"></li>
                <li><a class="dropdown-item text-primary" href="/shop"><strong>See All Products</strong></a></li>
              </ul>
            </li>
            <li class="nav-item"><a class="nav-link" href="/prescription">Prescriptions</a></li>
            <li class="nav-item"><a class="nav-link" href="/blog">Blog</a></li>
            <li class="nav-item"><a class="nav-link" href="/cart"><i class="fas fa-shopping-cart"></i> Cart</a></li>
            <li class="nav-item"><a class="btn btn-primary ms-3" href="/login">Admin Login</a></li>
          </ul>
        </div>
      </div>
    </nav>"""

# ---------- Public Pages ----------
PUBLIC_HOME = f"""<!DOCTYPE html><html><head><title>{APP_NAME}</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
{public_navbar()}
<section class="hero"><div class="container">
    <h1>{APP_TAGLINE}</h1>
    <p>Your trusted source for quality OTC medicines, supplements, and personal care products — delivered to your doorstep.</p>
    <a href="/shop" class="btn btn-light btn-lg mt-3">Shop Now</a>
    <a href="/upload-prescription" class="btn btn-outline-light btn-lg mt-3 ms-2">Click to Upload Prescription<br><small>Get a quote immediately</small></a>
</div></section>
<section class="container my-5">
    <h2 class="text-center mb-4">Why Choose {APP_NAME}?</h2>
    <div class="row g-4">
        <div class="col-md-4"><div class="feature-card"><i class="fas fa-certificate fa-3x text-primary mb-3"></i><h5>Genuine Products</h5><p>All medicines sourced from licensed pharmacies.</p></div></div>
        <div class="col-md-4"><div class="feature-card"><i class="fas fa-truck-fast fa-3x text-primary mb-3"></i><h5>Fast Delivery</h5><p>Reliable courier services across Kenya.</p></div></div>
        <div class="col-md-4"><div class="feature-card"><i class="fas fa-headset fa-3x text-primary mb-3"></i><h5>Expert Support</h5><p>Pharmacist-led customer care.</p></div></div>
    </div>
</section>
<section class="bg-light py-5">
    <div class="container">
        <h2 class="text-center mb-4">Top Categories</h2>
        <div class="row g-4">
            <div class="col-md-3"><a href="/shop?category=Supplements" class="text-decoration-none"><div class="top-category-card"><i class="fas fa-flask fa-2x text-success mb-2"></i><h5>Supplements</h5></div></a></div>
            <div class="col-md-3"><a href="/shop?category=Pain+Relief" class="text-decoration-none"><div class="top-category-card"><i class="fas fa-heart fa-2x text-danger mb-2"></i><h5>Pain Relief</h5></div></a></div>
            <div class="col-md-3"><a href="/shop?category=Baby+Care" class="text-decoration-none"><div class="top-category-card"><i class="fas fa-baby fa-2x text-info mb-2"></i><h5>Baby Care</h5></div></a></div>
            <div class="col-md-3"><a href="/shop?category=Women+Health" class="text-decoration-none"><div class="top-category-card"><i class="fas fa-female fa-2x mb-2" style="color:#e83e8c;"></i><h5>Women Health</h5></div></a></div>
        </div>
    </div>
</section>
<footer class="footer"><div class="container"><div class="row">
    <div class="col-md-4"><h5><i class="fas fa-pills"></i> {APP_NAME}<br><small>Online Pharmacy</small></h5><p class="text-muted">{PHARMACY_ADDRESS}<br>Tel: {PHARMACY_PHONE}<br>Email: {PHARMACY_EMAIL}</p></div>
    <div class="col-md-4"><h5>Quick Links</h5><ul class="list-unstyled"><li><a href="/shop">Shop</a></li><li><a href="/about">About Us</a></li><li><a href="/contact">Contact</a></li><li><a href="/upload-prescription">Upload Prescription</a></li><li><a href="/blog">Blog</a></li></ul></div>
    <div class="col-md-4"><h5>Working Hours</h5><p class="text-muted">Mon - Fri: 8AM - 6PM<br>Sat: 8AM - 1PM<br>Sun: Closed</p></div>
</div><hr><p class="text-center text-muted">&copy; 2026 {APP_NAME}. All rights reserved. Terms & Conditions Apply.</p></div></footer>
<div class="position-fixed bottom-0 start-0 w-100 bg-dark text-white p-3 d-flex justify-content-between align-items-center" id="cookieConsent">
  <span>We use cookies and other similar technologies to improve your browsing experience and the functionality of our site. <a href="/privacy" class="text-info">Privacy Policy</a>.</span>
  <button onclick="document.getElementById('cookieConsent').style.display='none'" class="btn btn-outline-light btn-sm">Accept All</button>
</div>
{BOOTSTRAP_JS}
</body></html>"""

ABOUT_PAGE = f"""<!DOCTYPE html><html><head><title>About Us</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
{public_navbar()}
<div class="container mt-4"><h2>About {APP_NAME} Online Pharmacy</h2><p>{APP_NAME} is your trusted online pharmacy, providing quality OTC medicines and health products since 2026. We partner with licensed pharmacies to ensure you receive genuine products at competitive prices. Our mission is to make healthcare accessible and affordable for every Kenyan, one click at a time.</p></div>
<footer class="footer mt-5"><div class="container"><p class="text-center text-muted">&copy; 2026 {APP_NAME}. All rights reserved.</p></div></footer>
{BOOTSTRAP_JS}
</body></html>"""

# ---------- Prescription Upload (Customer) ----------
@app.get("/upload-prescription", response_class=HTMLResponse)
def upload_prescription_form():
    return HTMLResponse(f"""<!DOCTYPE html><html><head><title>Upload Prescription</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
{public_navbar()}
<div class="container mt-4" style="max-width:600px;">
  <h2>Upload Prescription</h2>
  <p>Fill in your details and upload your prescription. Our pharmacist will get back to you with a quote.</p>
  <form method="post" action="/upload-prescription" enctype="multipart/form-data">
    <input type="text" class="form-control mb-2" name="customer_name" placeholder="Your Name" required>
    <input type="email" class="form-control mb-2" name="customer_email" placeholder="Your Email" required>
    <input type="text" class="form-control mb-2" name="customer_phone" placeholder="Phone Number" required>
    <textarea class="form-control mb-2" name="notes" placeholder="Additional notes"></textarea>
    <label class="form-label">Upload Prescription (image/PDF)</label>
    <input type="file" class="form-control mb-2" name="prescription_file" accept="image/*,.pdf" required>
    <button class="btn btn-primary w-100">Submit</button>
  </form>
</div>
{BOOTSTRAP_JS}
</body></html>""")

@app.post("/upload-prescription")
async def handle_upload(request: Request, customer_name: str = Form(...), customer_email: str = Form(...), customer_phone: str = Form(...), notes: str = Form(""), prescription_file: UploadFile = File(...)):
    # Save file to Supabase Storage
    contents = await prescription_file.read()
    fname = f"rx_{int(os.urandom(4).hex(),16)}_{prescription_file.filename}"
    service_supabase.storage.from_("product-images").upload(fname, contents, {"content-type": prescription_file.content_type})
    file_url = f"{SUPABASE_URL}/storage/v1/object/public/product-images/{fname}"
    # Insert a record into a 'prescriptions' table (create if not existed)
    service_supabase.table("prescriptions").insert({
        "customer_name": customer_name, "customer_email": customer_email, "customer_phone": customer_phone,
        "notes": notes, "file_url": file_url, "status": "pending"
    }).execute()
    return HTMLResponse(f"""<!DOCTYPE html><html><head><title>Prescription Received</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
{public_navbar()}
<div class="container mt-5 text-center">
  <h2 class="text-success"><i class="fas fa-check-circle"></i> Thank You!</h2>
  <p>We received your prescription. Our pharmacist will contact you shortly with a quote.</p>
  <a href="/" class="btn btn-primary">Back to Home</a>
</div>
{BOOTSTRAP_JS}
</body></html>""")

# ---------- Shop Page (public) ----------
@app.get("/shop", response_class=HTMLResponse)
def shop(request: Request, search: str = "", category: str = "", page: int = 1):
    per_page = 6; offset = (page-1)*per_page
    query = service_supabase.table("products").select("*", count="exact").eq("active", True)
    if search: query = query.or_(f"name.ilike.%{search}%,category.ilike.%{search}%")
    if category: query = query.or_(f"category.ilike.%{category}%")
    total = query.execute().count or 0
    data_query = service_supabase.table("products").select("*").eq("active", True)
    if search: data_query = data_query.or_(f"name.ilike.%{search}%,category.ilike.%{search}%")
    if category: data_query = data_query.or_(f"category.ilike.%{category}%")
    result = data_query.range(offset, offset+per_page-1).execute()
    products = result.data or []
    cards_html = ""
    for pr in products:
        img = f'<img src="{pr.get("image_url")}" class="card-img-top" style="height:200px; object-fit:cover;">' if pr.get("image_url") else ""
        price = pr.get("price", 0)
        stock = pr.get("stock", 0)
        cards_html += f"""<div class="col-md-4 mb-4"><div class="card h-100 p-3">{img}<div class="card-body">
            <h5 class="card-title">{pr.get("name","")}</h5>
            <p>{pr.get("description","")}</p>
            <p><strong>Category:</strong> {pr.get("category","")} | <strong>Stock:</strong> {stock}</p>
            <h4 class="text-success">KSh {price}</h4>
            <form action="/cart/add/{pr["id"]}" method="get" class="d-flex align-items-center mt-3">
                <input type="number" name="quantity" value="1" min="1" max="{stock}" class="form-control me-2" style="width:80px;">
                <button type="submit" class="btn btn-primary">Add to Cart</button>
            </form>
        </div></div></div>"""
    if not cards_html: cards_html = "<p>No products found.</p>"
    pagination = ""
    total_pages = (total + per_page - 1)//per_page
    if total_pages > 1:
        pagination = '<nav><ul class="pagination justify-content-center">'
        for p in range(1, total_pages+1):
            active = "active" if p == page else ""
            pagination += f'<li class="page-item {active}"><a class="page-link" href="/shop?page={p}&search={search}&category={category}">{p}</a></li>'
        pagination += '</ul></nav>'
    return HTMLResponse(f"""<!DOCTYPE html><html><head><title>Shop</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
{public_navbar()}
<div class="container mt-4"><h2>Products</h2>
<form class="mb-4" method="get" action="/shop">
    <div class="row g-3">
        <div class="col-md-8"><input class="form-control" name="search" value="{search}" placeholder="Search products..."></div>
        <div class="col-md-3">
            <select class="form-control" name="category">
                <option value="">All Categories</option>
                <option value="Supplements" {'selected' if category=='Supplements' else ''}>Supplements</option>
                <option value="Pain Relief" {'selected' if category=='Pain Relief' else ''}>Pain Relief</option>
                <option value="Baby Care" {'selected' if category=='Baby Care' else ''}>Baby Care</option>
                <option value="Women Health" {'selected' if category=='Women Health' else ''}>Women Health</option>
            </select>
        </div>
        <div class="col-md-1"><button class="btn btn-primary w-100">Search</button></div>
    </div>
</form>
<div class="row">{cards_html}</div>
{pagination}
</div>
<footer class="footer mt-5"><div class="container"><p class="text-center text-muted">&copy; 2026 {APP_NAME}. All rights reserved.</p></div></footer>
{BOOTSTRAP_JS}
</body></html>""")

# ---------- Cart ----------
@app.get("/cart", response_class=HTMLResponse)
def view_cart(request: Request):
    cart = get_cart(request)
    if not cart:
        return HTMLResponse(f"""<!DOCTYPE html><html><head><title>Cart</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
{public_navbar()}<div class="container mt-4"><h2>Your Cart</h2><p>Your cart is empty.</p><a href="/shop" class="btn btn-primary">Continue Shopping</a></div>{BOOTSTRAP_JS}</body></html>""")
    ids = [item["product_id"] for item in cart]
    prods = service_supabase.table("products").select("*").in_("id", ids).execute().data or []
    pmap = {p["id"]: p for p in prods}
    items_html = ""
    total = 0.0
    for item in cart:
        p = pmap.get(item["product_id"])
        if p:
            subtotal = p["price"] * item["quantity"]
            total += subtotal
            items_html += f"""<div class="card mb-3 p-3"><div class="row align-items-center">
                <div class="col-md-4"><h5>{p['name']}</h5><p class="text-muted">KSh {p['price']} each</p></div>
                <div class="col-md-4">
                    <form action="/cart/update/{item['product_id']}" method="get" class="d-flex">
                        <input type="number" name="quantity" value="{item['quantity']}" min="1" max="999" class="form-control me-2" style="width:80px;">
                        <button class="btn btn-sm btn-outline-primary">Update</button>
                    </form>
                </div>
                <div class="col-md-4 text-end"><strong>KSh {subtotal:.2f}</strong> <a href="/cart/remove/{item['product_id']}" class="btn btn-sm btn-outline-danger">Remove</a></div>
            </div></div>"""
    return HTMLResponse(f"""<!DOCTYPE html><html><head><title>Cart</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
{public_navbar()}
<div class="container mt-4"><h2>Your Cart</h2>{items_html}<hr><h4>Total: KSh {total:.2f}</h4>
<a href="/checkout" class="btn btn-success">Proceed to Checkout</a> <a href="/shop" class="btn btn-outline-secondary">Continue Shopping</a>
</div>{BOOTSTRAP_JS}</body></html>""")

@app.get("/cart/add/{product_id}")
def add_to_cart(request: Request, product_id: str, quantity: int = 1):
    if quantity < 1: quantity = 1
    cart = get_cart(request)
    for item in cart:
        if item["product_id"] == product_id:
            item["quantity"] += quantity
            save_cart(request, cart)
            return RedirectResponse("/cart", 303)
    cart.append({"product_id": product_id, "quantity": quantity})
    save_cart(request, cart)
    return RedirectResponse("/cart", 303)

@app.get("/cart/update/{product_id}")
def update_cart(request: Request, product_id: str, quantity: int = 1):
    if quantity < 1: quantity = 1
    cart = get_cart(request)
    for item in cart:
        if item["product_id"] == product_id:
            item["quantity"] = quantity
            break
    save_cart(request, cart)
    return RedirectResponse("/cart", 303)

@app.get("/cart/remove/{product_id}")
def remove_cart(request: Request, product_id: str):
    cart = [i for i in get_cart(request) if i["product_id"] != product_id]
    save_cart(request, cart)
    return RedirectResponse("/cart", 303)

# ---------- Checkout ----------
@app.get("/checkout", response_class=HTMLResponse)
def checkout_form(request: Request):
    cart = get_cart(request)
    if not cart: return RedirectResponse("/cart")
    return HTMLResponse(f"""<!DOCTYPE html><html><head><title>Checkout</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
{public_navbar()}
<div class="container mt-4" style="max-width:600px;"><h2>Checkout</h2>
<form method="post" action="/checkout">
    <h5>Customer Details</h5>
    <input class="form-control mb-2" name="customer_name" placeholder="Full Name" required>
    <input class="form-control mb-2" name="customer_email" placeholder="Email" required>
    <input class="form-control mb-2" name="customer_phone" placeholder="Phone Number" required>
    <input class="form-control mb-2" name="customer_address" placeholder="Delivery Address">
    <h5 class="mt-3">Payment Method</h5>
    <select class="form-control mb-2" name="payment_method">
        <option value="cash_on_delivery">Cash on Delivery</option>
        <option value="mobile_money">M-Pesa</option>
    </select>
    <button class="btn btn-success w-100 mt-3">Place Order</button>
</form></div>
{BOOTSTRAP_JS}
</body></html>""")

@app.post("/checkout")
def place_order(request: Request, customer_name: str = Form(...), customer_email: str = Form(...), customer_phone: str = Form(...), customer_address: str = Form(""), payment_method: str = Form("cash_on_delivery")):
    cart = get_cart(request)
    if not cart: return RedirectResponse("/cart")
    ids = [item["product_id"] for item in cart]
    prods = service_supabase.table("products").select("*").in_("id", ids).execute().data or []
    pmap = {p["id"]: p for p in prods}
    total = 0.0
    order_items = []
    for item in cart:
        p = pmap.get(item["product_id"])
        if p and p["stock"] >= item["quantity"]:
            st = p["price"] * item["quantity"]
            total += st
            order_items.append({"product_id": item["product_id"], "quantity": item["quantity"], "unit_price": p["price"]})
            new_stock = p["stock"] - item["quantity"]
            service_supabase.table("products").update({"stock": new_stock}).eq("id", item["product_id"]).execute()
    if not order_items: return RedirectResponse("/cart")
    order = service_supabase.table("orders").insert({
        "total_amount": round(total,2),
        "status": "pending",
        "payment_method": payment_method,
        "customer_name": customer_name,
        "customer_email": customer_email,
        "customer_phone": customer_phone,
        "customer_address": customer_address
    }).execute()
    if not order.data: return HTMLResponse("<h2>Order failed. Please try again.</h2>")
    order_id = order.data[0]["id"]
    for oi in order_items:
        oi["order_id"] = order_id
        service_supabase.table("order_items").insert(oi).execute()
    save_cart(request, [])
    return RedirectResponse(f"/order-confirmation/{order_id}", 303)

@app.get("/order-confirmation/{order_id}", response_class=HTMLResponse)
def order_confirmation(order_id: str):
    order = service_supabase.table("orders").select("*").eq("id", order_id).single().execute()
    if not order.data: return HTMLResponse("<h2>Order not found</h2>")
    return HTMLResponse(f"""<!DOCTYPE html><html><head><title>Order Confirmed</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
{public_navbar()}
<div class="container mt-5 text-center" style="max-width:600px;">
    <h2 class="text-success"><i class="fas fa-check-circle"></i> Thank You!</h2>
    <p>Your order <strong>#{order_id[:8]}</strong> has been placed successfully. We will contact you shortly.</p>
    <a href="/shop" class="btn btn-primary">Continue Shopping</a>
</div>
{BOOTSTRAP_JS}
</body></html>""")

# ---------- Prescription Product Listing ----------
def prescription_page(products, current_filters, sort_by, page, total_pages):
    min_price = current_filters.get("min_price", "")
    max_price = current_filters.get("max_price", "")
    in_stock = current_filters.get("in_stock", "")
    checked = "checked" if in_stock == "1" else ""
    sort_options = {"default": "Default", "price_asc": "Price: Low to High", "price_desc": "Price: High to Low"}
    sort_sel = "".join(f"<option value='{v}' {'selected' if sort_by==v else ''}>{l}</option>" for v,l in sort_options.items())
    cards_html = ""
    for pr in products:
        img = f'<img src="{pr.get("image_url")}" class="card-img-top" style="height:200px; object-fit:cover;">' if pr.get("image_url") else ""
        name = pr.get("name", "")
        price = pr.get("price", 0)
        whatsapp_url = f"https://wa.me/{PHARMACY_PHONE}?text={urllib.parse.quote(f'Hi, I am interested in {name} (KSh {price})')}"
        add_to_cart_url = f"/cart/add/{pr['id']}?quantity=1"
        cards_html += f"""<div class="col-md-4 mb-4"><div class="card product-card h-100 p-3">{img}<div class="card-body"><h5 class="card-title">{name}</h5><h4 class="text-success">KSh {price}</h4>
            <div class="d-grid gap-1 mt-2"><a href="{add_to_cart_url}" class="btn btn-primary btn-sm">Add to Cart</a><a href="{add_to_cart_url}" class="btn btn-success btn-sm">Buy Now</a><a href="{whatsapp_url}" target="_blank" class="btn btn-outline-success btn-sm">WhatsApp</a></div></div></div>"""
    if not cards_html: cards_html = "<p>No products found.</p>"
    pagination = ""
    if total_pages > 1:
        filter_params = f"&min_price={min_price}&max_price={max_price}&in_stock={in_stock}&sort={sort_by}"
        pagination = '<nav><ul class="pagination justify-content-center">' + "".join(
            f'<li class="page-item {"active" if p==page else ""}"><a class="page-link" href="/prescription?page={p}{filter_params}">{p}</a></li>' for p in range(1,total_pages+1)
        ) + '</ul></nav>'
    return f"""<!DOCTYPE html><html><head><title>Prescriptions</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
{public_navbar()}<div class="container mt-4"><div class="row">
<div class="col-md-3"><div class="filter-sidebar"><h5>Filter</h5>
<form method="get" action="/prescription">
    <div class="mb-3"><label class="form-label">Price (KSh)</label><div class="d-flex"><input type="number" name="min_price" class="form-control me-1" placeholder="Min" value="{min_price}"><input type="number" name="max_price" class="form-control ms-1" placeholder="Max" value="{max_price}"></div></div>
    <div class="mb-3"><div class="form-check"><input class="form-check-input" type="checkbox" name="in_stock" value="1" id="inStock" {checked}><label class="form-check-label" for="inStock">In Stock</label></div></div>
    <button type="submit" class="btn btn-primary btn-sm w-100">Filter</button><a href="/prescription" class="btn btn-outline-secondary btn-sm w-100 mt-2">Clear</a>
</form></div></div>
<div class="col-md-9"><div class="d-flex justify-content-between mb-3"><h2>Prescriptions</h2>
<form method="get" action="/prescription" class="d-flex"><select name="sort" class="form-select me-2" style="width:auto;">{sort_sel}</select><input type="hidden" name="min_price" value="{min_price}"><input type="hidden" name="max_price" value="{max_price}"><input type="hidden" name="in_stock" value="{in_stock}"><button type="submit" class="btn btn-outline-primary btn-sm">Sort</button></form></div>
<div class="row">{cards_html}</div>{pagination}</div>
</div></div><footer class="footer mt-5"><div class="container"><p class="text-center text-muted">&copy; 2026 {APP_NAME}. All rights reserved.</p></div></footer>{BOOTSTRAP_JS}</body></html>"""

@app.get("/prescription", response_class=HTMLResponse)
def prescription_list(request: Request):
    min_price = request.query_params.get("min_price",""); max_price = request.query_params.get("max_price",""); in_stock = request.query_params.get("in_stock",""); sort = request.query_params.get("sort","default"); page = int(request.query_params.get("page",1)); per_page = 9
    query = service_supabase.table("products").select("*", count="exact").eq("active", True)
    if min_price: query = query.gte("price", float(min_price))
    if max_price: query = query.lte("price", float(max_price))
    if in_stock == "1": query = query.gt("stock", 0)
    if sort == "price_asc": query = query.order("price", desc=False)
    elif sort == "price_desc": query = query.order("price", desc=True)
    else: query = query.order("name")
    total = query.execute().count or 0
    offset = (page-1)*per_page
    result = query.range(offset, offset+per_page-1).execute()
    products = result.data or []
    total_pages = max(1, (total + per_page - 1)//per_page)
    filters = {"min_price": min_price, "max_price": max_price, "in_stock": in_stock}
    return HTMLResponse(prescription_page(products, filters, sort, page, total_pages))

# ---------- Blog (Placeholder) ----------
@app.get("/blog", response_class=HTMLResponse)
def blog():
    return HTMLResponse(f"""<!DOCTYPE html><html><head><title>Blog</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
{public_navbar()}<div class="container mt-4"><h2>Blog</h2><p>Coming soon!</p></div></body></html>""")

# ---------- Admin Panel (Full Backend) ----------
@app.get("/login", response_class=HTMLResponse)
def admin_login_page(error=""):
    alert = f'<div class="alert alert-danger">{error}</div>' if error else ""
    return HTMLResponse(f"""<!DOCTYPE html><html><head><title>Admin Login</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
{public_navbar()}<div class="container mt-5" style="max-width:400px;"><div class="card p-4"><h3>Admin Login</h3>{alert}
<form method="post" action="/login"><input class="form-control mb-2" name="email" placeholder="Email" required><input class="form-control mb-2" type="password" name="password" placeholder="Password" required><button class="btn btn-primary w-100 mt-2">Log In</button></form></div></div>{BOOTSTRAP_JS}</body></html>""")

@app.post("/login")
def admin_login(request: Request, email: str = Form(...), password: str = Form(...)):
    try:
        r = supabase.auth.sign_in_with_password({"email": email, "password": password})
        if r.user:
            request.session["user_id"] = r.user.id
            return RedirectResponse("/admin", 303)
        return admin_login_page("Login failed")
    except:
        return admin_login_page("Invalid credentials")

def admin_dashboard_page(metrics, orders_html):
    return f"""<!DOCTYPE html><html><head><title>Admin · {APP_NAME}</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
<nav class="navbar navbar-dark bg-primary"><div class="container"><a class="navbar-brand" href="/admin">{APP_NAME} Admin</a><a class="btn btn-light" href="/logout">Logout</a></div></nav>
<div class="container-fluid"><div class="row">
<div class="col-md-2 admin-sidebar p-3">
    <h5><i class="fas fa-shield-alt"></i> Admin Panel</h5>
    <a href="/admin"><i class="fas fa-tachometer-alt"></i> Dashboard</a>
    <a href="/admin/orders"><i class="fas fa-shopping-cart"></i> Orders</a>
    <a href="/admin/products"><i class="fas fa-pills"></i> Products</a>
    <a href="/admin/prescriptions"><i class="fas fa-file-prescription"></i> Prescriptions</a>
    <a href="/admin/customers"><i class="fas fa-users"></i> Customers</a>
    <a href="/admin/settings"><i class="fas fa-cog"></i> Settings</a>
    <a href="/admin/export-orders"><i class="fas fa-download"></i> Export CSV</a>
    <a href="/">View Site</a>
</div>
<div class="col-md-10 p-4">
    <h2>Dashboard</h2>
    <div class="row mt-4">
        <div class="col-md-3"><div class="metric-card text-center"><h3>{metrics['total_sales']}</h3><p>Total Sales (KSh)</p></div></div>
        <div class="col-md-3"><div class="metric-card text-center"><h3>{metrics['total_orders']}</h3><p>Total Orders</p></div></div>
        <div class="col-md-3"><div class="metric-card text-center"><h3>{metrics['total_products']}</h3><p>Products</p></div></div>
        <div class="col-md-3"><div class="metric-card text-center"><h3>{metrics['total_customers']}</h3><p>Customers</p></div></div>
    </div>
    <hr><h4>Recent Orders</h4>{orders_html}
</div></div></div>{BOOTSTRAP_JS}</body></html>"""

@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request):
    if not request.session.get("user_id"): return RedirectResponse("/login")
    orders = service_supabase.table("orders").select("*").order("created_at", desc=True).limit(10).execute().data or []
    orders_html = "".join(f"""<div class="card mb-2 p-2"><strong>#{o['id'][:8]}</strong> - {o['status']} | KSh {o['total_amount']} | {o.get('customer_name','')} | {o['created_at'][:10]}</div>""" for o in orders)
    total_sales = sum(o['total_amount'] for o in orders) if orders else 0
    total_orders = service_supabase.table("orders").select("count", count="exact").execute().count or 0
    total_products = service_supabase.table("products").select("count", count="exact").execute().count or 0
    cust_emails = set(o.get('customer_email','') for o in service_supabase.table("orders").select("customer_email").execute().data or [])
    metrics = {"total_sales": f"{total_sales:,.2f}", "total_orders": total_orders, "total_products": total_products, "total_customers": len(cust_emails)}
    return HTMLResponse(admin_dashboard_page(metrics, orders_html))

@app.get("/admin/orders", response_class=HTMLResponse)
def admin_orders(request: Request):
    if not request.session.get("user_id"): return RedirectResponse("/login")
    orders = service_supabase.table("orders").select("*").order("created_at", desc=True).execute().data or []
    html = ""
    for o in orders:
        items = service_supabase.table("order_items").select("*, products(name)").eq("order_id", o["id"]).execute().data or []
        il = "".join(f"<li>{i['products']['name']} x {i['quantity']} @ KSh {i['unit_price']}</li>" for i in items)
        html += f"""<div class="card mb-3 p-3"><h5>Order #{o['id'][:8]} - {o['status']}</h5>
        <p><strong>Customer:</strong> {o.get('customer_name','')} ({o.get('customer_phone','')}) | <strong>Total:</strong> KSh {o['total_amount']} | <strong>Date:</strong> {o['created_at'][:10]}</p>
        <ul>{il}</ul>
        <form method="post" action="/admin/update-order/{o['id']}" class="d-flex align-items-center">
            <select class="form-control me-2" name="status" style="width:auto;">
                <option value="pending" {'selected' if o['status']=='pending' else ''}>Pending</option>
                <option value="confirmed" {'selected' if o['status']=='confirmed' else ''}>Confirmed</option>
                <option value="shipped" {'selected' if o['status']=='shipped' else ''}>Shipped</option>
                <option value="delivered" {'selected' if o['status']=='delivered' else ''}>Delivered</option>
            </select>
            <button class="btn btn-sm btn-primary">Update</button>
        </form></div>"""
    if not html: html = "<p>No orders yet.</p>"
    return HTMLResponse(f"""<!DOCTYPE html><html><head><title>Orders · Admin</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
<nav class="navbar navbar-dark bg-primary"><div class="container"><a class="navbar-brand" href="/admin">{APP_NAME} Admin</a><a class="btn btn-light" href="/logout">Logout</a></div></nav>
<div class="container-fluid"><div class="row">
<div class="col-md-2 admin-sidebar p-3"><h5>Admin Panel</h5><a href="/admin">Dashboard</a><a href="/admin/orders">Orders</a><a href="/admin/products">Products</a><a href="/admin/prescriptions">Prescriptions</a><a href="/admin/customers">Customers</a><a href="/admin/settings">Settings</a><a href="/admin/export-orders">Export CSV</a><a href="/">View Site</a></div>
<div class="col-md-10 p-4"><h2>All Orders</h2>{html}</div></div></div>{BOOTSTRAP_JS}</body></html>""")

@app.post("/admin/update-order/{order_id}")
def admin_update_order(request: Request, order_id: str, status: str = Form(...)):
    if not request.session.get("user_id"): return RedirectResponse("/login")
    service_supabase.table("orders").update({"status": status}).eq("id", order_id).execute()
    return RedirectResponse("/admin/orders", 303)

@app.get("/admin/products", response_class=HTMLResponse)
def admin_products(request: Request):
    if not request.session.get("user_id"): return RedirectResponse("/login")
    products = service_supabase.table("products").select("*").order("name").execute().data or []
    rows = "".join(f"""<tr><td>{p['name']}</td><td>{p['category']}</td><td>{p['price']}</td><td>{p['stock']}</td>
        <td><a href="/admin/edit-product/{p['id']}" class="btn btn-sm btn-warning">Edit</a> <a href="/admin/delete-product/{p['id']}" class="btn btn-sm btn-danger">Delete</a></td></tr>""" for p in products)
    return HTMLResponse(f"""<!DOCTYPE html><html><head><title>Products · Admin</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
<nav class="navbar navbar-dark bg-primary"><div class="container"><a class="navbar-brand" href="/admin">{APP_NAME} Admin</a><a class="btn btn-light" href="/logout">Logout</a></div></nav>
<div class="container-fluid"><div class="row">
<div class="col-md-2 admin-sidebar p-3"><h5>Admin Panel</h5><a href="/admin">Dashboard</a><a href="/admin/orders">Orders</a><a href="/admin/products">Products</a><a href="/admin/prescriptions">Prescriptions</a><a href="/admin/customers">Customers</a><a href="/admin/settings">Settings</a><a href="/admin/export-orders">Export CSV</a><a href="/">View Site</a></div>
<div class="col-md-10 p-4"><h2>Products</h2><a href="/admin/add-product" class="btn btn-success mb-3">+ Add Product</a>
<table class="table"><thead><tr><th>Name</th><th>Category</th><th>Price</th><th>Stock</th><th>Action</th></tr></thead><tbody>{rows}</tbody></table></div></div></div>{BOOTSTRAP_JS}</body></html>""")

@app.get("/admin/add-product", response_class=HTMLResponse)
def admin_add_product_form(request: Request):
    if not request.session.get("user_id"): return RedirectResponse("/login")
    return HTMLResponse(f"""<!DOCTYPE html><html><head><title>Add Product</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
<nav class="navbar navbar-dark bg-primary"><div class="container"><a class="navbar-brand" href="/admin">{APP_NAME} Admin</a></div></nav>
<div class="container mt-4" style="max-width:500px;"><h2>Add Product</h2>
<form method="post" action="/admin/add-product" enctype="multipart/form-data">
    <input class="form-control mb-2" name="name" placeholder="Product Name" required>
    <textarea class="form-control mb-2" name="description" placeholder="Description" rows="3"></textarea>
    <input class="form-control mb-2" name="category" placeholder="Category" required>
    <input class="form-control mb-2" type="number" step="0.01" name="price" placeholder="Price (KSh)" required>
    <input class="form-control mb-2" type="number" name="stock" placeholder="Stock Quantity" required>
    <label class="form-label">Product Image</label><input class="form-control mb-2" type="file" name="image" accept="image/*">
    <button class="btn btn-primary w-100">Add Product</button>
</form></div></body></html>""")

@app.post("/admin/add-product")
async def admin_add_product(request: Request, name: str = Form(...), description: str = Form(""), category: str = Form(...), price: float = Form(...), stock: int = Form(...), image: UploadFile = File(None)):
    if not request.session.get("user_id"): return RedirectResponse("/login")
    img_url = None
    if image and image.filename:
        contents = await image.read()
        fname = f"{int(os.urandom(4).hex(),16)}_{image.filename}"
        service_supabase.storage.from_("product-images").upload(fname, contents, {"content-type": image.content_type})
        img_url = f"{SUPABASE_URL}/storage/v1/object/public/product-images/{fname}"
    service_supabase.table("products").insert({"name": name, "description": description, "category": category, "price": price, "stock": stock, "image_url": img_url}).execute()
    return RedirectResponse("/admin/products", 303)

@app.get("/admin/edit-product/{product_id}", response_class=HTMLResponse)
def admin_edit_product_form(request: Request, product_id: str):
    if not request.session.get("user_id"): return RedirectResponse("/login")
    p = service_supabase.table("products").select("*").eq("id", product_id).single().execute().data
    return HTMLResponse(f"""<!DOCTYPE html><html><head><title>Edit Product</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
<nav class="navbar navbar-dark bg-primary"><div class="container"><a class="navbar-brand" href="/admin">Admin</a></div></nav>
<div class="container mt-4" style="max-width:500px;"><h2>Edit Product</h2>
<form method="post" action="/admin/edit-product/{product_id}" enctype="multipart/form-data">
    <input class="form-control mb-2" name="name" value="{p['name']}" required>
    <textarea class="form-control mb-2" name="description" rows="3">{p.get('description','')}</textarea>
    <input class="form-control mb-2" name="category" value="{p['category']}" required>
    <input class="form-control mb-2" type="number" step="0.01" name="price" value="{p['price']}" required>
    <input class="form-control mb-2" type="number" name="stock" value="{p['stock']}" required>
    <label>Replace Image</label><input class="form-control mb-2" type="file" name="image" accept="image/*">
    <button class="btn btn-primary w-100">Update Product</button>
</form></div></body></html>""")

@app.post("/admin/edit-product/{product_id}")
async def admin_edit_product(request: Request, product_id: str, name: str = Form(...), description: str = Form(""), category: str = Form(...), price: float = Form(...), stock: int = Form(...), image: UploadFile = File(None)):
    if not request.session.get("user_id"): return RedirectResponse("/login")
    upd = {"name": name, "description": description, "category": category, "price": price, "stock": stock}
    if image and image.filename:
        contents = await image.read()
        fname = f"{int(os.urandom(4).hex(),16)}_{image.filename}"
        service_supabase.storage.from_("product-images").upload(fname, contents, {"content-type": image.content_type})
        upd["image_url"] = f"{SUPABASE_URL}/storage/v1/object/public/product-images/{fname}"
    service_supabase.table("products").update(upd).eq("id", product_id).execute()
    return RedirectResponse("/admin/products", 303)

@app.get("/admin/delete-product/{product_id}")
def admin_delete_product(request: Request, product_id: str):
    if not request.session.get("user_id"): return RedirectResponse("/login")
    service_supabase.table("products").delete().eq("id", product_id).execute()
    return RedirectResponse("/admin/products", 303)

# ---------- Admin Prescriptions Management ----------
@app.get("/admin/prescriptions", response_class=HTMLResponse)
def admin_prescriptions(request: Request):
    if not request.session.get("user_id"): return RedirectResponse("/login")
    rx = service_supabase.table("prescriptions").select("*").order("created_at", desc=True).execute().data or []
    html = ""
    for r in rx:
        html += f"""<div class="card mb-3 p-3">
        <h5>Prescription from {r['customer_name']}</h5>
        <p><strong>Email:</strong> {r['customer_email']} | <strong>Phone:</strong> {r['customer_phone']}</p>
        <p><strong>Notes:</strong> {r.get('notes','')}</p>
        <a href="{r['file_url']}" target="_blank" class="btn btn-sm btn-primary">View File</a>
        </div>"""
    if not html: html = "<p>No prescriptions uploaded yet.</p>"
    return HTMLResponse(f"""<!DOCTYPE html><html><head><title>Prescriptions · Admin</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
<nav class="navbar navbar-dark bg-primary"><div class="container"><a class="navbar-brand" href="/admin">{APP_NAME} Admin</a><a class="btn btn-light" href="/logout">Logout</a></div></nav>
<div class="container-fluid"><div class="row">
<div class="col-md-2 admin-sidebar p-3"><h5>Admin Panel</h5><a href="/admin">Dashboard</a><a href="/admin/orders">Orders</a><a href="/admin/products">Products</a><a href="/admin/prescriptions">Prescriptions</a><a href="/admin/customers">Customers</a><a href="/admin/settings">Settings</a><a href="/admin/export-orders">Export CSV</a><a href="/">View Site</a></div>
<div class="col-md-10 p-4"><h2>Uploaded Prescriptions</h2>{html}</div></div></div>{BOOTSTRAP_JS}</body></html>""")

@app.get("/admin/customers", response_class=HTMLResponse)
def admin_customers(request: Request):
    if not request.session.get("user_id"): return RedirectResponse("/login")
    orders = service_supabase.table("orders").select("customer_name, customer_email, customer_phone").execute().data or []
    seen = set(); customers = []
    for o in orders:
        if o['customer_email'] not in seen and o['customer_email']:
            seen.add(o['customer_email']); customers.append(o)
    rows = "".join(f"<tr><td>{c['customer_name']}</td><td>{c['customer_email']}</td><td>{c['customer_phone']}</td></tr>" for c in customers)
    return HTMLResponse(f"""<!DOCTYPE html><html><head><title>Customers · Admin</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
<nav class="navbar navbar-dark bg-primary"><div class="container"><a class="navbar-brand" href="/admin">Admin</a><a class="btn btn-light" href="/logout">Logout</a></div></nav>
<div class="container-fluid"><div class="row">
<div class="col-md-2 admin-sidebar p-3"><h5>Admin Panel</h5><a href="/admin">Dashboard</a><a href="/admin/orders">Orders</a><a href="/admin/products">Products</a><a href="/admin/prescriptions">Prescriptions</a><a href="/admin/customers">Customers</a><a href="/admin/settings">Settings</a><a href="/admin/export-orders">Export CSV</a><a href="/">View Site</a></div>
<div class="col-md-10 p-4"><h2>Customers</h2><table class="table"><thead><tr><th>Name</th><th>Email</th><th>Phone</th></tr></thead><tbody>{rows}</tbody></table></div></div></div></body></html>""")

# ---------- Admin Settings (Edit Credentials) ----------
@app.get("/admin/settings", response_class=HTMLResponse)
def admin_settings(request: Request):
    if not request.session.get("user_id"): return RedirectResponse("/login")
    return HTMLResponse(f"""<!DOCTYPE html><html><head><title>Settings · Admin</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
<nav class="navbar navbar-dark bg-primary"><div class="container"><a class="navbar-brand" href="/admin">{APP_NAME} Admin</a><a class="btn btn-light" href="/logout">Logout</a></div></nav>
<div class="container-fluid"><div class="row">
<div class="col-md-2 admin-sidebar p-3"><h5>Admin Panel</h5><a href="/admin">Dashboard</a><a href="/admin/orders">Orders</a><a href="/admin/products">Products</a><a href="/admin/prescriptions">Prescriptions</a><a href="/admin/customers">Customers</a><a href="/admin/settings">Settings</a><a href="/admin/export-orders">Export CSV</a><a href="/">View Site</a></div>
<div class="col-md-10 p-4">
    <h2>Settings</h2>
    <h4>Change Admin Password</h4>
    <form method="post" action="/admin/settings" style="max-width:400px;">
        <input class="form-control mb-2" name="new_password" type="password" placeholder="New Password" required>
        <button class="btn btn-primary">Update Password</button>
    </form>
</div></div></div></body></html>""")

@app.post("/admin/settings")
def admin_update_password(request: Request, new_password: str = Form(...)):
    if not request.session.get("user_id"): return RedirectResponse("/login")
    # Update password via Supabase Auth Admin API (service_role required)
    service_supabase.auth.admin.update_user_by_id(
        request.session["user_id"],
        {"password": new_password}
    )
    return RedirectResponse("/admin/settings?success=1", 303)

@app.get("/admin/export-orders")
def export_orders(request: Request):
    if not request.session.get("user_id"): return RedirectResponse("/login")
    orders = service_supabase.table("orders").select("*").order("created_at", desc=True).execute().data or []
    output = io.StringIO(); w = csv.writer(output)
    w.writerow(["Order ID","Date","Customer","Email","Phone","Total","Status","Payment"])
    for o in orders:
        w.writerow([o['id'][:8], o['created_at'][:10], o.get('customer_name',''), o.get('customer_email',''), o.get('customer_phone',''), o['total_amount'], o['status'], o.get('payment_method','')])
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=orders.csv"})

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/")

# ---------- Static Pages ----------
@app.get("/")
def home():
    return HTMLResponse(PUBLIC_HOME)

@app.get("/about", response_class=HTMLResponse)
def about():
    return HTMLResponse(ABOUT_PAGE)

@app.get("/contact", response_class=HTMLResponse)
def contact():
    return HTMLResponse(f"""<!DOCTYPE html><html><head><title>Contact</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
{public_navbar()}<div class="container mt-4"><h2>Contact Us</h2><p>{PHARMACY_ADDRESS}<br>Tel: {PHARMACY_PHONE}<br>Email: {PHARMACY_EMAIL}</p></div>
<footer class="footer mt-5"><div class="container"><p class="text-center text-muted">&copy; 2026 {APP_NAME}. All rights reserved.</p></div></footer>
{BOOTSTRAP_JS}
</body></html>""")

@app.get("/terms", response_class=HTMLResponse)
def terms():
    return HTMLResponse(f"""<!DOCTYPE html><html><head><title>Terms</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
{public_navbar()}<div class="container mt-4"><h2>Terms of Service</h2><p>Sample terms.</p></div></body></html>""")

@app.get("/privacy", response_class=HTMLResponse)
def privacy():
    return HTMLResponse(f"""<!DOCTYPE html><html><head><title>Privacy</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
{public_navbar()}<div class="container mt-4"><h2>Privacy Policy</h2><p>Sample policy.</p></div></body></html>""")
