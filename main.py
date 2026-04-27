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
