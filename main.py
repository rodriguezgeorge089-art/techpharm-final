from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

html = """<!DOCTYPE html>
<html><head><title>Login</title></head><body>
<h2>Login</h2>
<form action="/login" method="post">
  <input name="email" placeholder="Email"><br>
  <input type="password" name="password" placeholder="Password"><br>
  <button type="submit">Log In</button>
</form>
<p>Don't have an account? <a href="/signup">Sign up</a></p>
</body></html>"""

@app.get("/")
def home():
    return HTMLResponse(html)
