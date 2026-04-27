import os
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="your-super-secret-key-change-me")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------- Token Refresh Helper ----------
def get_valid_session(request: Request):
    """
    Returns a supabase client with a valid session.
    Redirects to login if unable.
    """
    token = request.session.get("access_token")
    refresh = request.session.get("refresh_token")
    if not token or not refresh:
        return None
    try:
        supabase.auth.set_session(token, refresh)
        # Try a lightweight call to see if token is still valid
        supabase.auth.get_user()
        return supabase
    except:
        try:
            # Attempt to refresh the session
            res = supabase.auth.refresh_session(refresh)
            request.session["access_token"] = res.session.access_token
            request.session["refresh_token"] = res.session.refresh_token
            supabase.auth.set_session(res.session.access_token, res.session.refresh_token)
            return supabase
        except:
            return None

# ---------- HTML Templates ----------
LOGIN_HTML = """
<!DOCTYPE html>
<html><head><title>Login</title></head><body>
<h2>Login</h2>
<form method="post">
  <input name="email" placeholder="Email" required><br>
  <input type="password" name="password" placeholder="Password" required><br>
  <button type="submit">Log In</button>
</form>
<p>Don't have an account? <a href="/signup">Sign up</a></p>
</body></html>
"""

SIGNUP_HTML = """
<!DOCTYPE html>
<html><head><title>Sign Up</title></head><body>
<h2>Create Account</h2>
<form method="post">
  <input name="full_name" placeholder="Full Name" required><br>
  <input name="email" placeholder="Email" required><br>
  <input type="password" name="password" placeholder="Password" required><br>
  <select name="role">
    <option value="buyer">Buyer</option>
    <option value="seller">Seller</option>
  </select><br>
  <button type="submit">Sign Up</button>
</form>
</body></html>
"""

DASHBOARD_HTML = """
<!DOCTYPE html>
<html><head><title>Dashboard</title></head><body>
<h2>Welcome, {full_name} ({role})</h2>
<a href="/products">Browse Products</a> |
<a href="/seller">Seller Dashboard</a> |
<a href="/logout">Logout</a>
</body></html>
"""

PRODUCTS_HTML = """
<!DOCTYPE html>
<html><head><title>Products</title></head><body>
<h2>OTC Products</h2>
<form method="get" action="/products">
  <input name="search" placeholder="Search by name or category">
  <button type="submit">Search</button>
</form>
<hr>
<div>
{product_list}
</div>
<p><a href="/dashboard">Back to Dashboard</a></p>
</body></html>
"""

PRODUCT_ITEM = """
<div style="border:1px solid #ccc; margin:10px; padding:10px;">
  <strong>{name}</strong> - ${price}<br>
  <small>{description}</small><br>
  Category: {category} | Stock: {stock}
  <a href="/cart/add/{id}">Add to Cart</a>
</div>
"""

# ---------- SELLER DASHBOARD ----------
SELLER_HTML = """
<!DOCTYPE html>
<html><head><title>Seller Dashboard</title></head><body>
<h2>My Products</h2>
<a href="/seller/add">Add New Product</a>
<hr>
<div>
{product_list}
</div>
<p><a href="/dashboard">Back to Dashboard</a></p>
</body></html>
"""

SELLER_PRODUCT_ITEM = """
<div style="border:1px solid #ccc; margin:10px; padding:10px;">
  <strong>{name}</strong> - ${price}<br>
  <small>{description}</small><br>
  Category: {category} | Stock: {stock}
  <a href="/seller/edit/{id}">Edit</a> |
  <a href="/seller/delete/{id}" onclick="return confirm('Delete this product?')">Delete</a>
</div>
"""

ADD_PRODUCT_HTML = """
<!DOCTYPE html>
<html><head><title>Add Product</title></head><body>
<h2>Add New Product</h2>
<form method="post">
  <input name="name" placeholder="Product Name" required><br>
  <textarea name="description" placeholder="Description" rows="3"></textarea><br>
  <input name="category" placeholder="Category (e.g., Pain Relief)" required><br>
  <input type="number" step="0.01" name="price" placeholder="Price" required><br>
  <input type="number" name="stock" placeholder="Stock Quantity" required><br>
  <button type="submit">Add Product</button>
</form>
<p><a href="/seller">Back to My Products</a></p>
</body></html>
"""

EDIT_PRODUCT_HTML = """
<!DOCTYPE html>
<html><head><title>Edit Product</title></head><body>
<h2>Edit Product</h2>
<form method="post">
  <input name="name" value="{name}" required><br>
  <textarea name="description" rows="3">{description}</textarea><br>
  <input name="category" value="{category}" required><br>
  <input type="number" step="0.01" name="price" value="{price}" required><br>
  <input type="number" name="stock" value="{stock}" required><br>
  <button type="submit">Update Product</button>
</form>
<p><a href="/seller">Back to My Products</a></p>
</body></html>
"""

# ---------- SHOPPING CART (with quantity & payment) ----------
CART_HTML = """
<!DOCTYPE html>
<html><head><title>Shopping Cart</title></head><body>
<h2>Your Cart</h2>
<form method="post" action="/cart/update">
  <div>
    {cart_items}
  </div>
  <hr>
  <strong>Total: ${total}</strong><br>
  <label>Payment Method:</label>
  <select name="payment_method">
    <option value="cash_on_delivery">Cash on Delivery</option>
    <option value="mobile_money">Mobile Money</option>
  </select><br><br>
  <button type="submit" formaction="/cart/checkout">Place Order</button>
</form>
<p><a href="/products">Continue Shopping</a> | <a href="/dashboard">Dashboard</a></p>
</body></html>
"""

CART_ITEM = """
<div style="border:1px solid #ccc; margin:10px; padding:10px;">
  <strong>{name}</strong> - ${price}
  <br>
  Quantity: 
  <button type="submit" form="cart_form" formaction="/cart/decrease/{product_id}">–</button>
  <input type="text" name="quantity_{product_id}" value="{quantity}" size="2" readonly>
  <button type="submit" form="cart_form" formaction="/cart/increase/{product_id}">+</button>
  <a href="/cart/remove/{product_id}" style="margin-left:20px;">Remove</a>
  <br>Subtotal: ${subtotal}
</div>
"""

ORDERS_HTML = """
<!DOCTYPE html>
<html><head><title>My Orders</title></head><body>
<h2>My Orders</h2>
<div>
{order_list}
</div>
<p><a href="/dashboard">Back to Dashboard</a></p>
</body></html>
"""

ORDER_ITEM_HTML = """
<div style="border:1px solid #ccc; margin:10px; padding:10px;">
  <strong>Order #{order_id}</strong> - Status: {status} | Total: ${total}<br>
  Payment: {payment_method} | Date: {date}
  <ul>
    {products_list}
  </ul>
</div>
"""

# ---------- Helper: cart ----------
def get_cart(request: Request):
    return request.session.get("cart", [])

def save_cart(request: Request, cart):
    request.session["cart"] = cart

# ---------- Authentication Routes ----------
@app.get("/login", response_class=HTMLResponse)
def login_page():
    return HTMLResponse(LOGIN_HTML)

@app.post("/login")
def do_login(request: Request, email: str = Form(...), password: str = Form(...)):
    try:
        resp = supabase.auth.sign_in_with_password({"email": email, "password": password})
        request.session["access_token"] = resp.session.access_token
        request.session["refresh_token"] = resp.session.refresh_token
        return RedirectResponse("/dashboard", status_code=303)
    except Exception:
        return HTMLResponse(LOGIN_HTML.replace("</body>", "<p style='color:red'>Login failed</p></body>"))

@app.get("/signup", response_class=HTMLResponse)
def signup_page():
    return HTMLResponse(SIGNUP_HTML)

@app.post("/signup")
def do_signup(full_name: str = Form(...), email: str = Form(...), password: str = Form(...), role: str = Form(...)):
    try:
        resp = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {"data": {"full_name": full_name}}
        })
        supabase.table("profiles").update({"role": role}).eq("user_id", resp.user.id).execute()
        return RedirectResponse("/login?message=Account+created", status_code=303)
    except Exception as e:
        return HTMLResponse(SIGNUP_HTML.replace("</body>", f"<p style='color:red'>Error: {e}</p></body>"))

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    sup = get_valid_session(request)
    if not sup:
        return RedirectResponse("/login")
    try:
        user = sup.auth.get_user().user
        profile = sup.table("profiles").select("*").eq("user_id", user.id).single().execute()
        return HTMLResponse(DASHBOARD_HTML.format(
            full_name=profile.data.get("full_name", "User"),
            role=profile.data.get("role", "buyer")
        ))
    except Exception:
        return RedirectResponse("/login")

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login")

@app.get("/")
def root():
    return RedirectResponse("/login")

# ---------- Products (all users) ----------
@app.get("/products", response_class=HTMLResponse)
def products_page(request: Request, search: str = ""):
    sup = get_valid_session(request)
    if not sup:
        return RedirectResponse("/login")
    query = sup.table("products").select("*").eq("active", True)
    if search:
        query = query.or_(f"name.ilike.%{search}%,category.ilike.%{search}%")
    result = query.execute()
    products = result.data if result.data else []
    product_html = "".join([PRODUCT_ITEM.format(**p) for p in products])
    return HTMLResponse(PRODUCTS_HTML.replace("{product_list}", product_html))

# ---------- Seller Management ----------
@app.get("/seller", response_class=HTMLResponse)
def seller_dashboard(request: Request):
    sup = get_valid_session(request)
    if not sup:
        return RedirectResponse("/login")
    user = sup.auth.get_user().user
    profile = supabase.table("profiles").select("*").eq("user_id", user.id).single().execute()
    if profile.data['role'] != 'seller':
        return HTMLResponse("<h2>Access Denied</h2><p>Only sellers can access this page.</p>")
    products = sup.table("products").select("*").eq("seller_id", profile.data['id']).execute()
    product_html = ""
    if products.data:
        product_html = "".join([SELLER_PRODUCT_ITEM.format(**p) for p in products.data])
    return HTMLResponse(SELLER_HTML.replace("{product_list}", product_html))

@app.get("/seller/add", response_class=HTMLResponse)
def add_product_page(request: Request):
    if not get_valid_session(request):
        return RedirectResponse("/login")
    return HTMLResponse(ADD_PRODUCT_HTML)

@app.post("/seller/add")
def add_product(request: Request, name: str = Form(...), description: str = Form(""),
                category: str = Form(...), price: float = Form(...), stock: int = Form(...)):
    sup = get_valid_session(request)
    if not sup:
        return RedirectResponse("/login")
    user = sup.auth.get_user().user
    profile = sup.table("profiles").select("id").eq("user_id", user.id).single().execute()
    sup.table("products").insert({
        "seller_id": profile.data['id'],
        "name": name,
        "description": description,
        "category": category,
        "price": price,
        "stock": stock
    }).execute()
    return RedirectResponse("/seller", status_code=303)

@app.get("/seller/edit/{product_id}", response_class=HTMLResponse)
def edit_product_page(request: Request, product_id: str):
    sup = get_valid_session(request)
    if not sup:
        return RedirectResponse("/login")
    product = sup.table("products").select("*").eq("id", product_id).single().execute()
    return HTMLResponse(EDIT_PRODUCT_HTML.format(**product.data))

@app.post("/seller/edit/{product_id}")
def update_product(request: Request, product_id: str, name: str = Form(...),
                   description: str = Form(""), category: str = Form(...),
                   price: float = Form(...), stock: int = Form(...)):
    sup = get_valid_session(request)
    if not sup:
        return RedirectResponse("/login")
    sup.table("products").update({
        "name": name,
        "description": description,
        "category": category,
        "price": price,
        "stock": stock
    }).eq("id", product_id).execute()
    return RedirectResponse("/seller", status_code=303)

@app.get("/seller/delete/{product_id}")
def delete_product(request: Request, product_id: str):
    sup = get_valid_session(request)
    if not sup:
        return RedirectResponse("/login")
    sup.table("products").delete().eq("id", product_id).execute()
    return RedirectResponse("/seller", status_code=303)

# ---------- Cart & Checkout ----------
@app.get("/cart", response_class=HTMLResponse)
def view_cart(request: Request):
    sup = get_valid_session(request)
    if not sup:
        return RedirectResponse("/login")
    cart = get_cart(request)
    if not cart:
        return HTMLResponse(CART_HTML.replace("{cart_items}", "<p>Your cart is empty.</p>").replace("{total}", "0.00"))
    product_ids = [item["product_id"] for item in cart]
    products = sup.table("products").select("*").in_("id", product_ids).execute()
    product_map = {p["id"]: p for p in products.data} if products.data else {}
    items_html = ""
    total = 0.0
    for item in cart:
        product = product_map.get(item["product_id"])
        if product:
            subtotal = product["price"] * item["quantity"]
            total += subtotal
            items_html += CART_ITEM.format(
                name=product["name"],
                price=product["price"],
                product_id=product["id"],
                quantity=item["quantity"],
                subtotal=round(subtotal, 2)
            )
    return HTMLResponse(
        CART_HTML.replace("{cart_items}", items_html)
                 .replace("{total}", str(round(total, 2)))
    )

@app.get("/cart/add/{product_id}")
def add_to_cart(request: Request, product_id: str):
    if not get_valid_session(request):
        return RedirectResponse("/login")
    cart = get_cart(request)
    for item in cart:
        if item["product_id"] == product_id:
            item["quantity"] += 1
            save_cart(request, cart)
            return RedirectResponse("/cart", status_code=303)
    cart.append({"product_id": product_id, "quantity": 1})
    save_cart(request, cart)
    return RedirectResponse("/cart", status_code=303)

@app.get("/cart/increase/{product_id}")
def increase_quantity(request: Request, product_id: str):
    if not get_valid_session(request):
        return RedirectResponse("/login")
    cart = get_cart(request)
    for item in cart:
        if item["product_id"] == product_id:
            item["quantity"] += 1
            break
    save_cart(request, cart)
    return RedirectResponse("/cart", status_code=303)

@app.get("/cart/decrease/{product_id}")
def decrease_quantity(request: Request, product_id: str):
    if not get_valid_session(request):
        return RedirectResponse("/login")
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
def remove_from_cart(request: Request, product_id: str):
    if not get_valid_session(request):
        return RedirectResponse("/login")
    cart = get_cart(request)
    cart = [item for item in cart if item["product_id"] != product_id]
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
        buyer_id = profile.data["id"]
        cart = get_cart(request)
        if not cart:
            return RedirectResponse("/cart")
        total = 0.0
        order_items_data = []
        for item in cart:
            product = sup.table("products").select("*").eq("id", item["product_id"]).single().execute()
            if not product.data or product.data["stock"] < item["quantity"]:
                return HTMLResponse(f"<h2>Error: Not enough stock for '{product.data['name'] if product.data else 'product'}'.</h2><a href='/cart'>Back to Cart</a>")
            price = product.data["price"]
            subtotal = price * item["quantity"]
            total += subtotal
            order_items_data.append({
                "product_id": item["product_id"],
                "quantity": item["quantity"],
                "unit_price": price
            })
            new_stock = product.data["stock"] - item["quantity"]
            sup.table("products").update({"stock": new_stock}).eq("id", item["product_id"]).execute()
        if not order_items_data:
            return RedirectResponse("/cart")
        order_insert = {
            "buyer_id": buyer_id,
            "total_amount": round(total, 2),
            "status": "pending",
            "payment_method": payment_method
        }
        order = sup.table("orders").insert(order_insert).execute()
        order_id = order.data[0]["id"]
        for oi in order_items_data:
            oi["order_id"] = order_id
            sup.table("order_items").insert(oi).execute()
        save_cart(request, [])
        return RedirectResponse("/orders", status_code=303)
    except Exception as e:
        return HTMLResponse(f"<h2>Error during checkout: {e}</h2><a href='/cart'>Back to Cart</a>")

# ---------- Order History ----------
@app.get("/orders", response_class=HTMLResponse)
def order_history(request: Request):
    sup = get_valid_session(request)
    if not sup:
        return RedirectResponse("/login")
    try:
        user = sup.auth.get_user().user
        profile = sup.table("profiles").select("id").eq("user_id", user.id).single().execute()
        buyer_id = profile.data["id"]
        orders = sup.table("orders").select("*").eq("buyer_id", buyer_id).order("created_at.desc").execute()
        if not orders.data:
            return HTMLResponse(ORDERS_HTML.replace("{order_list}", "<p>No orders yet.</p>"))
        orders_html = ""
        for order in orders.data:
            items = sup.table("order_items").select("*, products(name)").eq("order_id", order["id"]).execute()
            products_list = ""
            for item in items.data:
                products_list += f"<li>{item['products']['name']} x {item['quantity']} @ ${item['unit_price']}</li>"
            orders_html += ORDER_ITEM_HTML.format(
                order_id=order["id"][:8],
                status=order["status"],
                total=order["total_amount"],
                payment_method=order.get("payment_method", "N/A"),
                date=order["created_at"][:10],
                products_list=products_list
            )
        return HTMLResponse(ORDERS_HTML.replace("{order_list}", orders_html))
    except Exception as e:
        return HTMLResponse(f"<h2>Error: {e}</h2><a href='/dashboard'>Dashboard</a>")
