import os
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="a-very-secret-key-change-me")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------- Token helper (prevents logout) ----------
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

# ---------- Common HTML parts ----------
BOOTSTRAP = '<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">'

NAV_LOGGED_IN = """
<nav class="navbar navbar-expand-lg navbar-dark bg-primary mb-4">
  <div class="container">
    <a class="navbar-brand" href="/dashboard">OTC Market</a>
    <div class="navbar-nav">
      <a class="nav-link" href="/products">Browse</a>
      <a class="nav-link" href="/cart">Cart</a>
      <a class="nav-link" href="/orders">Orders</a>
      <a class="nav-link" href="/seller">My Shop</a>
      <a class="nav-link" href="/logout">Logout</a>
    </div>
  </div>
</nav>
"""

NAV_GUEST = """
<nav class="navbar navbar-expand-lg navbar-dark bg-primary mb-4">
  <div class="container">
    <a class="navbar-brand" href="/">OTC Market</a>
  </div>
</nav>
"""

# ---------- Page Templates (Bootstrap 5) ----------
LOGIN_PAGE = f"""<!DOCTYPE html><html><head><title>Login</title>{BOOTSTRAP}</head><body>
{NAV_GUEST}
<div class="container" style="max-width:400px;">
  <h2 class="mb-3">Login</h2>
  <form method="post">
    <input class="form-control mb-2" name="email" placeholder="Email" required>
    <input class="form-control mb-2" type="password" name="password" placeholder="Password" required>
    <button class="btn btn-primary w-100">Log In</button>
  </form>
  <p class="mt-2">Don't have an account? <a href="/signup">Sign up</a></p>
</div></body></html>"""

SIGNUP_PAGE = f"""<!DOCTYPE html><html><head><title>Sign Up</title>{BOOTSTRAP}</head><body>
{NAV_GUEST}
<div class="container" style="max-width:400px;">
  <h2 class="mb-3">Create Account</h2>
  <form method="post">
    <input class="form-control mb-2" name="full_name" placeholder="Full Name" required>
    <input class="form-control mb-2" name="email" placeholder="Email" required>
    <input class="form-control mb-2" type="password" name="password" placeholder="Password" required>
    <select class="form-control mb-2" name="role">
      <option value="buyer">Buyer</option>
      <option value="seller">Seller</option>
    </select>
    <button class="btn btn-primary w-100">Sign Up</button>
  </form>
</div></body></html>"""

DASHBOARD_PAGE = f"""<!DOCTYPE html><html><head><title>Dashboard</title>{BOOTSTRAP}</head><body>
{NAV_LOGGED_IN}
<div class="container">
  <h2>Welcome, {{full_name}} <span class="badge bg-info">{{role}}</span></h2>
  <div class="row mt-4">
    <div class="col-md-4 mb-3"><a href="/products" class="btn btn-outline-primary w-100 py-3">Browse Products</a></div>
    <div class="col-md-4 mb-3"><a href="/cart" class="btn btn-outline-success w-100 py-3">View Cart</a></div>
    <div class="col-md-4 mb-3"><a href="/orders" class="btn btn-outline-warning w-100 py-3">My Orders</a></div>
  </div>
</div></body></html>"""

PRODUCTS_PAGE = f"""<!DOCTYPE html><html><head><title>Products</title>{BOOTSTRAP}</head><body>
{NAV_LOGGED_IN}
<div class="container">
  <h2>OTC Products</h2>
  <form class="mb-3" method="get" action="/products">
    <div class="input-group">
      <input class="form-control" name="search" placeholder="Search by name or category">
      <button class="btn btn-primary">Search</button>
    </div>
  </form>
  <div class="row">
    {{product_cards}}
  </div>
</div></body></html>"""

PRODUCT_CARD = """
<div class="col-md-4 mb-3">
  <div class="card h-100">
    <div class="card-body">
      <h5 class="card-title">{name}</h5>
      <p class="card-text">{description}</p>
      <p><strong>Category:</strong> {category} | <strong>Stock:</strong> {stock}</p>
      <h4 class="text-success">${price}</h4>
      <form action="/cart/add/{id}" method="get" class="d-flex align-items-center">
        <input type="number" name="quantity" value="1" min="1" max="{stock}" class="form-control me-2" style="width:70px;">
        <button type="submit" class="btn btn-primary">Add to Cart</button>
      </form>
    </div>
  </div>
</div>"""

CART_PAGE = f"""<!DOCTYPE html><html><head><title>Cart</title>{BOOTSTRAP}</head><body>
{NAV_LOGGED_IN}
<div class="container">
  <h2>Your Cart</h2>
  {{cart_items}}
  <hr>
  <div class="text-end">
    <h4>Total: ${{total}}</h4>
    <form method="post" action="/cart/checkout" class="row g-2 align-items-center">
      <div class="col-auto">
        <label class="form-label me-2">Payment:</label>
        <select class="form-select" name="payment_method">
          <option value="cash_on_delivery">Cash on Delivery</option>
          <option value="mobile_money">Mobile Money</option>
        </select>
      </div>
      <div class="col-auto">
        <button type="submit" class="btn btn-success">Place Order</button>
      </div>
    </form>
  </div>
</div></body></html>"""

CART_ITEM = """
<div class="card mb-2">
  <div class="card-body d-flex justify-content-between align-items-center">
    <div>
      <h5 class="card-title">{name}</h5>
      <p class="card-text">${price} each</p>
    </div>
    <div class="d-flex align-items-center">
      <a href="/cart/decrease/{product_id}" class="btn btn-sm btn-outline-secondary">–</a>
      <span class="mx-2">{quantity}</span>
      <a href="/cart/increase/{product_id}" class="btn btn-sm btn-outline-secondary">+</a>
    </div>
    <div>
      <strong>${subtotal}</strong>
      <a href="/cart/remove/{product_id}" class="btn btn-sm btn-outline-danger ms-2">Remove</a>
    </div>
  </div>
</div>"""

ORDERS_PAGE = f"""<!DOCTYPE html><html><head><title>Orders</title>{BOOTSTRAP}</head><body>
{NAV_LOGGED_IN}
<div class="container">
  <h2>My Orders</h2>
  {{order_list}}
</div></body></html>"""

ORDER_ITEM_HTML = """
<div class="card mb-3">
  <div class="card-body">
    <h5 class="card-title">Order #{order_id}</h5>
    <p><strong>Date:</strong> {date} | <strong>Status:</strong> <span class="badge bg-warning">{status}</span></p>
    <p><strong>Payment:</strong> {payment_method} | <strong>Total:</strong> ${total}</p>
    <ul>
      {products_list}
    </ul>
  </div>
</div>"""

SELLER_PAGE = f"""<!DOCTYPE html><html><head><title>My Shop</title>{BOOTSTRAP}</head><body>
{NAV_LOGGED_IN}
<div class="container">
  <h2>My Products</h2>
  <a href="/seller/add" class="btn btn-success mb-3">Add New Product</a>
  <div class="row">
    {{product_cards}}
  </div>
</div></body></html>"""

SELLER_PRODUCT_CARD = """
<div class="col-md-4 mb-3">
  <div class="card h-100">
    <div class="card-body">
      <h5 class="card-title">{name}</h5>
      <p>{description}</p>
      <p><strong>Category:</strong> {category} | <strong>Stock:</strong> {stock}</p>
      <h4 class="text-success">${price}</h4>
      <a href="/seller/edit/{id}" class="btn btn-warning btn-sm">Edit</a>
      <a href="/seller/delete/{id}" class="btn btn-danger btn-sm" onclick="return confirm('Delete?')">Delete</a>
    </div>
  </div>
</div>"""

ADD_PRODUCT_PAGE = f"""<!DOCTYPE html><html><head><title>Add Product</title>{BOOTSTRAP}</head><body>
{NAV_LOGGED_IN}
<div class="container" style="max-width:500px;">
  <h2>Add New Product</h2>
  <form method="post">
    <input class="form-control mb-2" name="name" placeholder="Product Name" required>
    <textarea class="form-control mb-2" name="description" placeholder="Description" rows="3"></textarea>
    <input class="form-control mb-2" name="category" placeholder="Category" required>
    <input class="form-control mb-2" type="number" step="0.01" name="price" placeholder="Price" required>
    <input class="form-control mb-2" type="number" name="stock" placeholder="Stock" required>
    <button class="btn btn-primary w-100">Add Product</button>
  </form>
</div></body></html>"""

EDIT_PRODUCT_PAGE = f"""<!DOCTYPE html><html><head><title>Edit Product</title>{BOOTSTRAP}</head><body>
{NAV_LOGGED_IN}
<div class="container" style="max-width:500px;">
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
def login_page():
    return HTMLResponse(LOGIN_PAGE)

@app.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...)):
    try:
        resp = supabase.auth.sign_in_with_password({"email": email, "password": password})
        request.session["access_token"] = resp.session.access_token
        request.session["refresh_token"] = resp.session.refresh_token
        return RedirectResponse("/dashboard", status_code=303)
    except:
        return HTMLResponse(LOGIN_PAGE.replace("</body>", "<div class='alert alert-danger m-3'>Login failed</div></body>"))

@app.get("/signup", response_class=HTMLResponse)
def signup_page():
    return HTMLResponse(SIGNUP_PAGE)

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
        return HTMLResponse(SIGNUP_PAGE.replace("</body>", f"<div class='alert alert-danger m-3'>Error: {e}</div></body>"))

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    sup = get_valid_session(request)
    if not sup: return RedirectResponse("/login")
    user = sup.auth.get_user().user
    profile = sup.table("profiles").select("*").eq("user_id", user.id).single().execute()
    return HTMLResponse(DASHBOARD_PAGE.format(
        full_name=profile.data.get("full_name", "User"),
        role=profile.data.get("role", "buyer")
    ))

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login")

# ---------- Products ----------
@app.get("/products", response_class=HTMLResponse)
def products(request: Request, search: str = ""):
    sup = get_valid_session(request)
    if not sup: return RedirectResponse("/login")
    query = sup.table("products").select("*").eq("active", True)
    if search:
        query = query.or_(f"name.ilike.%{search}%,category.ilike.%{search}%")
    result = query.execute()
    products = result.data or []
    cards = "".join([PRODUCT_CARD.format(**p) for p in products])
    return HTMLResponse(PRODUCTS_PAGE.replace("{product_cards}", cards))

# ---------- Seller ----------
@app.get("/seller", response_class=HTMLResponse)
def seller_dashboard(request: Request):
    sup = get_valid_session(request)
    if not sup: return RedirectResponse("/login")
    user = sup.auth.get_user().user
    profile = sup.table("profiles").select("*").eq("user_id", user.id).single().execute()
    if profile.data['role'] != 'seller':
        return HTMLResponse("<div class='alert alert-danger'>Access denied</div>")
    prods = sup.table("products").select("*").eq("seller_id", profile.data['id']).execute()
    cards = "".join([SELLER_PRODUCT_CARD.format(**p) for p in (prods.data or [])])
    return HTMLResponse(SELLER_PAGE.replace("{product_cards}", cards))

@app.get("/seller/add", response_class=HTMLResponse)
def seller_add_form(request: Request):
    if not get_valid_session(request): return RedirectResponse("/login")
    return HTMLResponse(ADD_PRODUCT_PAGE)

@app.post("/seller/add")
def seller_add(request: Request, name: str = Form(...), description: str = Form(""),
               category: str = Form(...), price: float = Form(...), stock: int = Form(...)):
    sup = get_valid_session(request)
    if not sup: return RedirectResponse("/login")
    user = sup.auth.get_user().user
    profile = sup.table("profiles").select("id").eq("user_id", user.id).single().execute()
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
    return HTMLResponse(EDIT_PRODUCT_PAGE.format(**product.data))

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
    cart = get_cart(request)
    if not cart:
        return HTMLResponse(CART_PAGE.replace("{cart_items}", "<p>Your cart is empty.</p>").replace("{total}", "0.00"))
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
    return HTMLResponse(CART_PAGE.replace("{cart_items}", items_html).replace("{total}", str(round(total, 2))))

@app.get("/cart/add/{product_id}")
def add_to_cart(request: Request, product_id: str, quantity: int = 1):
    if not get_valid_session(request): return RedirectResponse("/login")
    if quantity < 1:
        quantity = 1
    cart = get_cart(request)
    # Check if product already in cart, then add quantity
    for item in cart:
        if item["product_id"] == product_id:
            item["quantity"] += quantity
            save_cart(request, cart)
            return RedirectResponse("/cart", status_code=303)
    cart.append({"product_id": product_id, "quantity": quantity})
    save_cart(request, cart)
    return RedirectResponse("/cart", status_code=303)

@app.get("/cart/increase/{product_id}")
def increase(request: Request, product_id: str):
    if not get_valid_session(request): return RedirectResponse("/login")
    cart = get_cart(request)
    for item in cart:
        if item["product_id"] == product_id:
            item["quantity"] += 1
            break
    save_cart(request, cart)
    return RedirectResponse("/cart", status_code=303)

@app.get("/cart/decrease/{product_id}")
def decrease(request: Request, product_id: str):
    if not get_valid_session(request): return RedirectResponse("/login")
    cart = get_cart(request)
    for item in cart:
        if item["product_id"] == product_id:
            if item["quantity"] > 1:
                item["quantity"] -= 1
            else:
                cart.remove(item)
            break
    save_cart(request, cart)
    return RedirectResponse("/cart", status_code=303)

@app.get("/cart/remove/{product_id}")
def remove(request: Request, product_id: str):
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
        user = sup.auth.get_user().user
        profile = sup.table("profiles").select("id").eq("user_id", user.id).single().execute()
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
                return HTMLResponse(f"<h2>Product {item['product_id']} not found.</h2><a href='/cart'>Back</a>")
            if product.data["stock"] < item["quantity"]:
                return HTMLResponse(f"<h2>Not enough stock for '{product.data['name']}'.</h2><a href='/cart'>Back</a>")
            price = product.data["price"]
            subtotal = price * item["quantity"]
            total += subtotal
            order_items_data.append({
                "product_id": item["product_id"],
                "quantity": item["quantity"],
                "unit_price": price
            })
            # Reduce stock
            new_stock = product.data["stock"] - item["quantity"]
            sup.table("products").update({"stock": new_stock}).eq("id", item["product_id"]).execute()

        if not order_items_data:
            return RedirectResponse("/cart")

        # Create order
        order = sup.table("orders").insert({
            "buyer_id": buyer_id,
            "total_amount": round(total, 2),
            "status": "pending",
            "payment_method": payment_method
        }).execute()

        if not order.data:
            return HTMLResponse("<h2>Failed to create order. Please try again.</h2>")

        order_id = order.data[0]["id"]

        # Insert order items
        for oi in order_items_data:
            oi["order_id"] = order_id
            sup.table("order_items").insert(oi).execute()

        # Clear cart
        save_cart(request, [])
        return RedirectResponse("/orders", status_code=303)

    except Exception as e:
        return HTMLResponse(f"<div class='alert alert-danger'>Checkout error: {str(e)}</div><a href='/cart'>Back</a>")

# ---------- Orders ----------
@app.get("/orders", response_class=HTMLResponse)
def orders(request: Request):
    sup = get_valid_session(request)
    if not sup: return RedirectResponse("/login")
    user = sup.auth.get_user().user
    profile = sup.table("profiles").select("id").eq("user_id", user.id).single().execute()
    if not profile.data:
        return RedirectResponse("/dashboard")
    buyer_id = profile.data["id"]
    orders = sup.table("orders").select("*").eq("buyer_id", buyer_id).order("created_at", ascending=False).execute()
    if not orders.data:
        return HTMLResponse(ORDERS_PAGE.replace("{order_list}", "<p>No orders yet.</p>"))

    orders_html = ""
    for order in orders.data:
        items = sup.table("order_items").select("*, products(name)").eq("order_id", order["id"]).execute()
        products_list = "".join(
            f"<li>{item['products']['name']} x {item['quantity']} @ ${item['unit_price']}</li>"
            for item in items.data
        )
        orders_html += ORDER_ITEM_HTML.format(
            order_id=order["id"][:8],
            status=order["status"],
            total=order["total_amount"],
            payment_method=order.get("payment_method", "N/A"),
            date=order["created_at"][:10],
            products_list=products_list
        )
    return HTMLResponse(ORDERS_PAGE.replace("{order_list}", orders_html))
