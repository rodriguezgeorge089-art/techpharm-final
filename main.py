import os
import uvicorn
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
import flet as ft
from flet.fastapi import FastAPIAdapter
from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def flet_main(page: ft.Page):
    page.title = "OTC Medicine Marketplace"
    current_user = None

    def show_snackbar(text, color="black"):
        page.snack_bar = ft.SnackBar(ft.Text(text, color=color), open=True)
        page.update()

    def signup_view():
        email = ft.TextField(label="Email", width=300)
        password = ft.TextField(label="Password", password=True, can_reveal_password=True, width=300)
        full_name = ft.TextField(label="Full Name", width=300)
        role = ft.Dropdown(label="I am a", options=[
            ft.dropdown.Option("buyer", "Buyer"),
            ft.dropdown.Option("seller", "Seller")
        ], width=300)

        def do_signup(e):
            try:
                resp = supabase.auth.sign_up({
                    "email": email.value,
                    "password": password.value,
                    "options": {"data": {"full_name": full_name.value}}
                })
                user = resp.user
                if user:
                    supabase.table("profiles").update({"role": role.value}).eq("user_id", user.id).execute()
                    show_snackbar("Account created! Check your email to confirm.", "green")
                    page.go("/login")
            except Exception as ex:
                show_snackbar(f"Error: {ex}", "red")
            page.update()

        return ft.Column([
            ft.Text("Create Account", style="headlineMedium"),
            full_name, email, password, role,
            ft.ElevatedButton("Sign Up", on_click=do_signup),
            ft.TextButton("Already have an account? Log in", on_click=lambda _: page.go("/login"))
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    def login_view():
        email = ft.TextField(label="Email", width=300)
        password = ft.TextField(label="Password", password=True, can_reveal_password=True, width=300)

        def do_login(e):
            nonlocal current_user
            try:
                resp = supabase.auth.sign_in_with_password({"email": email.value, "password": password.value})
                current_user = resp.user
                if current_user:
                    show_snackbar("Logged in!", "green")
                    page.go("/dashboard")
            except Exception as ex:
                show_snackbar(f"Login failed: {ex}", "red")
            page.update()

        return ft.Column([
            ft.Text("Login", style="headlineMedium"),
            email, password,
            ft.ElevatedButton("Log In", on_click=do_login),
            ft.TextButton("Don't have an account? Sign up", on_click=lambda _: page.go("/signup"))
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    def dashboard_view():
        nonlocal current_user
        if not current_user:
            page.go("/login")
            return ft.Text("Redirecting...")
        try:
            profile = supabase.table("profiles").select("*").eq("user_id", current_user.id).single().execute()
            user_role = profile.data['role']
            full_name = profile.data.get('full_name', 'User')
        except Exception as ex:
            return ft.Text(f"Error loading profile: {ex}")

        def logout(e):
            nonlocal current_user
            supabase.auth.sign_out()
            current_user = None
            page.go("/login")

        return ft.Column([
            ft.Text(f"Welcome, {full_name} ({user_role})", style="headlineSmall"),
            ft.ElevatedButton("Logout", on_click=logout),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    def route_change(route):
        page.controls.clear()
        if page.route == "/signup":
            page.controls.append(signup_view())
        elif page.route == "/dashboard":
            page.controls.append(dashboard_view())
        else:
            page.controls.append(login_view())
        page.update()

    page.on_route_change = route_change
    page.go("/login")

# FastAPI app with Flet mounted via official adapter
app = FastAPI()

flet_adapter = FastAPIAdapter(flet_main, mount_path="/app")
flet_adapter.mount(app)

@app.get("/")
async def root():
    return RedirectResponse(url="/app")
