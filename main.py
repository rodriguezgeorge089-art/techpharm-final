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

# ---------- HTML templates ----------
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
<a href="/logout">Logout</a>
</body></html>
"""

# ---------- Routes ----------
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
    token = request.session.get("access_token")
    if not token:
        return RedirectResponse("/login")
    try:
        supabase.auth.set_session(token, request.session.get("refresh_token"))
        user = supabase.auth.get_user().user
        profile = supabase.table("profiles").select("*").eq("user_id", user.id).single().execute()
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
# ---------- PRODUCTS PAGE ----------
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
</div>
"""

@app.get("/products", response_class=HTMLResponse)
def products_page(request: Request, search: str = ""):
    token = request.session.get("access_token")
    if not token:
        return RedirectResponse("/login")
    try:
        supabase.auth.set_session(token, request.session.get("refresh_token"))
    except:
        return RedirectResponse("/login")
    
    query = supabase.table("products").select("*").eq("active", True)
    if search:
        query = query.or_(f"name.ilike.%{search}%,category.ilike.%{search}%")
    result = query.execute()
    
    products = result.data if result.data else []
    product_html = "".join([PRODUCT_ITEM.format(**p) for p in products])
    
    return HTMLResponse(PRODUCTS_HTML.replace("{product_list}", product_html))
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

@app.get("/seller", response_class=HTMLResponse)
def seller_dashboard(request: Request):
    token = request.session.get("access_token")
    if not token:
        return RedirectResponse("/login")
    try:
        supabase.auth.set_session(token, request.session.get("refresh_token"))
        user = supabase.auth.get_user().user
        profile = supabase.table("profiles").select("*").eq("user_id", user.id).single().execute()
        
        if profile.data['role'] != 'seller':
            return HTMLResponse("<h2>Access Denied</h2><p>Only sellers can access this page.</p>")
        
        # Fetch seller's own products
        products = supabase.table("products").select("*").eq("seller_id", profile.data['id']).execute()
        product_html = ""
        if products.data:
            product_html = "".join([SELLER_PRODUCT_ITEM.format(**p) for p in products.data])
        
        return HTMLResponse(SELLER_HTML.replace("{product_list}", product_html))
    except:
        return RedirectResponse("/login")

@app.get("/seller/add", response_class=HTMLResponse)
def add_product_page(request: Request):
    token = request.session.get("access_token")
    if not token:
        return RedirectResponse("/login")
    return HTMLResponse(ADD_PRODUCT_HTML)

@app.post("/seller/add")
def add_product(request: Request, name: str = Form(...), description: str = Form(""),
                category: str = Form(...), price: float = Form(...), stock: int = Form(...)):
    token = request.session.get("access_token")
    if not token:
        return RedirectResponse("/login")
    try:
        supabase.auth.set_session(token, request.session.get("refresh_token"))
        user = supabase.auth.get_user().user
        profile = supabase.table("profiles").select("id").eq("user_id", user.id).single().execute()
        
        supabase.table("products").insert({
            "seller_id": profile.data['id'],
            "name": name,
            "description": description,
            "category": category,
            "price": price,
            "stock": stock
        }).execute()
        
        return RedirectResponse("/seller", status_code=303)
    except Exception as e:
        return HTMLResponse(ADD_PRODUCT_HTML.replace("</body>", f"<p style='color:red'>Error: {e}</p></body>"))

@app.get("/seller/edit/{product_id}", response_class=HTMLResponse)
def edit_product_page(request: Request, product_id: str):
    token = request.session.get("access_token")
    if not token:
        return RedirectResponse("/login")
    try:
        supabase.auth.set_session(token, request.session.get("refresh_token"))
        product = supabase.table("products").select("*").eq("id", product_id).single().execute()
        return HTMLResponse(EDIT_PRODUCT_HTML.format(**product.data))
    except:
        return RedirectResponse("/seller")

@app.post("/seller/edit/{product_id}")
def update_product(request: Request, product_id: str, name: str = Form(...),
                   description: str = Form(""), category: str = Form(...),
                   price: float = Form(...), stock: int = Form(...)):
    token = request.session.get("access_token")
    if not token:
        return RedirectResponse("/login")
    try:
        supabase.auth.set_session(token, request.session.get("refresh_token"))
        supabase.table("products").update({
            "name": name,
            "description": description,
            "category": category,
            "price": price,
            "stock": stock
        }).eq("id", product_id).execute()
        return RedirectResponse("/seller", status_code=303)
    except:
        return RedirectResponse("/seller")

@app.get("/seller/delete/{product_id}")
def delete_product(request: Request, product_id: str):
    token = request.session.get("access_token")
    if not token:
        return RedirectResponse("/login")
    try:
        supabase.auth.set_session(token, request.session.get("refresh_token"))
        supabase.table("products").delete().eq("id", product_id).execute()
        return RedirectResponse("/seller", status_code=303)
    except:
        return RedirectResponse("/seller")
