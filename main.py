import os, csv, io, json, uuid, re
from datetime import datetime
from fastapi import FastAPI, Request, Form, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse, Response
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

# ---------- Multi‑language support ----------
LANG = {
    "en": {
        "login": "Login", "signup": "Sign Up", "email": "Email", "password": "Password",
        "full_name": "Full Name", "role": "Role", "buyer": "Buyer", "seller": "Seller",
        "admin": "Admin", "retail": "Retail", "wholesale": "Wholesale",
        "welcome_back": "Welcome back", "forgot_password": "Forgot password?",
        "no_account": "Don't have an account?", "create_account": "Create your account",
        "dashboard": "Dashboard", "pharmacy_shop": "Pharmacy Shop", "cart": "Cart",
        "orders": "Orders", "my_shop": "My Shop", "logout": "Logout",
        "browse": "Browse", "search_placeholder": "Search medicines...",
        "add_to_cart": "Add to Cart", "update": "Update", "remove": "Remove",
        "total": "Total", "place_order": "Place Order", "payment_method": "Payment",
        "cash_on_delivery": "Cash on Delivery", "mobile_money": "M Pesa",
        "receipt": "Receipt", "print": "Print", "back_to_orders": "Back to Orders",
        "no_orders": "No orders yet.", "status": "Status", "pending": "Pending",
        "confirmed": "Confirmed", "shipped": "Shipped", "in_transit": "In Transit",
        "delivered": "Delivered", "view_receipt": "View Receipt",
        "return": "Return", "reason": "Reason", "submit_return": "Submit Return Request",
        "cancel": "Cancel", "thank_you": "Thank you for choosing DawaLink Pro!",
        "notifications": "Notifications", "mark_all_read": "Mark All as Read",
        "read": "Read", "unread": "Unread", "settings": "Settings",
        "language": "Language", "english": "English", "swahili": "Swahili",
        "analytics": "Analytics", "total_sales": "Total Sales (KSh)",
        "estimated_profit": "Estimated Profit (KSh)", "total_orders": "Total Orders",
        "registered_users": "Registered Users", "export_csv": "Export CSV",
        "inquiries": "Inquiries", "returns": "Returns",
        "verify_payment": "Verify Payment", "approve": "Approve",
        "deny": "Deny", "approved": "Approved", "denied": "Denied",
        "error_loading_receipt": "Error loading receipt:",
        "error_loading_payment": "Error loading payment details:",
        "reviews": "Reviews", "rating": "Rating", "comment": "Comment",
        "submit_review": "Submit Review", "no_reviews": "No reviews yet.",
        "tracking": "Tracking", "tracking_number": "Tracking Number",
        "carrier": "Carrier", "add_tracking": "Add Tracking",
        "bulk_upload": "Bulk Upload", "choose_file": "Choose CSV File",
        "upload": "Upload", "low_stock_alert": "Low Stock Alert",
        "stock": "Stock", "cost": "Cost", "retail_price": "Retail Price",
        "wholesale_price": "Wholesale Price",
    },
    "sw": {
        "login": "Ingia", "signup": "Jisajili", "email": "Barua pepe",
        "password": "Nywila", "full_name": "Jina Kamili", "role": "Jukumu",
        "buyer": "Mnunuzi", "seller": "Muuzaji", "admin": "Msimamizi",
        "retail": "Rejareja", "wholesale": "Jumla",
        "welcome_back": "Karibu tena", "forgot_password": "Umesahau nywila?",
        "no_account": "Huna akaunti?", "create_account": "Fungua akaunti",
        "dashboard": "Dashibodi", "pharmacy_shop": "Duka la Dawa",
        "cart": "Kikapu", "orders": "Maagizo", "my_shop": "Duka Langu",
        "logout": "Toka", "browse": "Vinjari",
        "search_placeholder": "Tafuta dawa...", "add_to_cart": "Ongeza kwa Kikapu",
        "update": "Sasisha", "remove": "Ondoa", "total": "Jumla",
        "place_order": "Weka Agizo", "payment_method": "Malipo",
        "cash_on_delivery": "Lipa kwa Mkono", "mobile_money": "M Pesa",
        "receipt": "Risiti", "print": "Chapisha", "back_to_orders": "Rudi kwa Maagizo",
        "no_orders": "Hakuna maagizo bado.", "status": "Hali",
        "pending": "Inasubiri", "confirmed": "Imethibitishwa",
        "shipped": "Imesafirishwa", "in_transit": "Safarini",
        "delivered": "Imewasilishwa", "view_receipt": "Tazama Risiti",
        "return": "Rejesha", "reason": "Sababu", "submit_return": "Tuma Ombi la Kurejesha",
        "cancel": "Ghairi", "thank_you": "Asante kwa kuchagua DawaLink Pro!",
        "notifications": "Arifa", "mark_all_read": "Weka zote kuwa zimesomwa",
        "read": "Imesomwa", "unread": "Haijasomwa", "settings": "Mipangilio",
        "language": "Lugha", "english": "Kiingereza", "swahili": "Kiswahili",
        "analytics": "Uchambuzi", "total_sales": "Mauzo Yote (KSh)",
        "estimated_profit": "Faida Kadiriwa (KSh)", "total_orders": "Maagizo Yote",
        "registered_users": "Watumiaji Waliosajiliwa", "export_csv": "Hamisha CSV",
        "inquiries": "Maswali", "returns": "Marejesho",
        "verify_payment": "Thibitisha Malipo", "approve": "Idhinisha",
        "deny": "Kataa", "approved": "Imeidhinishwa", "denied": "Imekataliwa",
        "error_loading_receipt": "Hitilafu kupakia risiti:",
        "error_loading_payment": "Hitilafu kupakia maelezo ya malipo:",
        "reviews": "Maoni", "rating": "Ukadiriaji", "comment": "Maoni",
        "submit_review": "Tuma Maoni", "no_reviews": "Hakuna maoni bado.",
        "tracking": "Ufuatiliaji", "tracking_number": "Nambari ya Ufuatiliaji",
        "carrier": "Mchukuzi", "add_tracking": "Ongeza Ufuatiliaji",
        "bulk_upload": "Upakiaji wa Wingi", "choose_file": "Chagua Faili ya CSV",
        "upload": "Pakia", "low_stock_alert": "Tahadhari ya Hisa Chache",
        "stock": "Hisa", "cost": "Gharama", "retail_price": "Bei ya Rejareja",
        "wholesale_price": "Bei ya Jumla",
    }
}

def t(key, lang="en"):
    """Return translated string for given key."""
    return LANG.get(lang, LANG["en"]).get(key, LANG["en"].get(key, key))

def get_lang(request: Request):
    """Get language from session or default to en."""
    return request.session.get("lang", "en")

# ---------- Session & Notifications ----------
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
                service_supabase.table("notifications").insert({
                    "user_id": admin["user_id"],
                    "message": message
                }).execute()
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

# ---------- HTML Components (multi‑language) ----------
BOOTSTRAP = '<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">'
FONTAWESOME = '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">'
CHARTJS = '<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>'
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
  .star-rating {{ color: #ffc107; }}
</style>
"""

PWA_MANIFEST = {
    "name": APP_NAME,
    "short_name": APP_NAME,
    "start_url": "/home",
    "display": "standalone",
    "background_color": "#ffffff",
    "theme_color": PRIMARY_COLOR,
    "icons": []  # you can add icons later
}

SERVICE_WORKER = """
self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open('dawalink-v1').then((cache) => {
      return cache.addAll([
        '/',
        '/login',
        '/home',
        '/products',
      ]);
    })
  );
});
self.addEventListener('fetch', (e) => {
  e.respondWith(
    caches.match(e.request).then((response) => response || fetch(e.request))
  );
});
"""

def navbar(profile, lang="en"):
    role = profile.get("role","") if profile else ""
    buyer_type = profile.get("buyer_type","") if profile else ""
    user_id = profile.get("user_id","") if profile else ""
    admin_tab = f'<a class="nav-link" href="/admin"><span class="badge bg-warning text-dark">{t("admin", lang)}</span></a>' if role == "admin" else ""
    seller_tab = f'<a class="nav-link" href="/seller">{t("my_shop", lang)}</a>' if role == "seller" else ""
    buyer_label = f' <span class="badge bg-secondary">{t(buyer_type, lang)}</span>' if role == "buyer" and buyer_type else ""
    bell = ""
    if user_id:
        count = get_unread_count(user_id)
        bell = f'<a class="nav-link position-relative" href="/notifications"><i class="fas fa-bell"></i>'
        if count > 0:
            bell += f'<span class="badge rounded-pill bg-danger notification-badge">{count}</span>'
        bell += '</a>'
    lang_switcher = f"""
    <li class="nav-item dropdown">
      <a class="nav-link dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown">
        {t("language", lang)}
      </a>
      <ul class="dropdown-menu">
        <li><a class="dropdown-item" href="/set-language/en">English</a></li>
        <li><a class="dropdown-item" href="/set-language/sw">Kiswahili</a></li>
      </ul>
    </li>"""
    return f"""
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
      <div class="container">
        <a class="navbar-brand" href="/home"><i class="fas fa-pills"></i> {APP_NAME}{buyer_label}</a>
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navMain">
          <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="navMain">
          <div class="navbar-nav ms-auto">
            <a class="nav-link" href="/products">{t("pharmacy_shop", lang)}</a>
            <a class="nav-link" href="/cart"><i class="fas fa-shopping-cart"></i> {t("cart", lang)}</a>
            <a class="nav-link" href="/orders">{t("orders", lang)}</a>
            {seller_tab}
            {admin_tab}
            {bell}
            {lang_switcher}
            <a class="nav-link" href="/logout">{t("logout", lang)}</a>
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

# ---------- Page templates (multi‑language) ----------
def login_page(error="", lang="en"):
    alert = f'<div class="alert alert-danger">{error}</div>' if error else ""
    return f"""<!DOCTYPE html><html><head><title>{t("login", lang)} · {APP_NAME}</title>{BOOTSTRAP}{CUSTOM_CSS}</head><body>
{NAV_GUEST}
<div class="container text-center mt-5"><h1>{APP_NAME}</h1><p class="lead">{APP_TAGLINE}</p></div>
<div class="container mt-3" style="max-width:400px;"><div class="card p-4"><h3>{t("welcome_back", lang)}</h3>{alert}
<form method="post"><input class="form-control mb-2" name="email" placeholder="{t("email", lang)}" required>
<input class="form-control mb-2" type="password" name="password" placeholder="{t("password", lang)}" required>
<button class="btn btn-primary w-100 mt-2">{t("login", lang)}</button></form>
<p class="mt-3 text-center"><a href="/forgot-password">{t("forgot_password", lang)}</a></p>
<p class="text-center">{t("no_account", lang)} <a href="/signup">{t("signup", lang)}</a></p></div></div></body></html>"""

# ... (all other page functions will be similarly extended with lang parameter and translation calls)
# Due to the extreme length, I will provide the full file in the final answer, but I'll note that the full code is available. I'll write a complete, ready-to-copy version now that includes all features. I'll ensure that every template uses the lang parameter and t() function.

# I'll create the full main.py with all features, then offer it as the final answer.
