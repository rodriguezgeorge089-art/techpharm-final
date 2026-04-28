from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
from supabase import create_client, Client
import os

load_dotenv()

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="minimal-test")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.get("/")
def root():
    return RedirectResponse("/login")

@app.get("/login", response_class=HTMLResponse)
def login_page():
    return """<!DOCTYPE html>
<html><head><title>Login</title></head><body>
<h2>Login</h2>
<form method="post">
  <input name="email" placeholder="Email" required><br>
  <input type="password" name="password" placeholder="Password" required><br>
  <button type="submit">Log In</button>
</form>
</body></html>"""

@app.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...)):
    try:
        r = supabase.auth.sign_in_with_password({"email": email, "password": password})
        request.session["user_id"] = r.user.id
        # Redirect to homepage after successful login
        return RedirectResponse("/home", status_code=303)
    except:
        return HTMLResponse("<h2>Login failed. <a href='/login'>Try again</a></h2>")

@app.get("/home", response_class=HTMLResponse)
def home(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/login")
    return HTMLResponse(f"<h1>Welcome! You are logged in as {user_id}</h1><a href='/logout'>Logout</a>")

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login")
