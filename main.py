import os, json, bcrypt
from flask import Flask, render_template, request, redirect, session, Response
from supabase import create_client, Client
from werkzeug.utils import secure_filename
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dawalink-secret')

SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

PHARMACY_NAME = "DawaLink"
PHARMACY_PHONE = "+254792524333"
PHARMACY_EMAIL = "info@dawalink.co.ke"

# ---------- Context processor ----------
@app.context_processor
def utility_processor():
    user_id = session.get('user_id')
    cart_total = 0.0
    if user_id:
        try:
            response = supabase.table('cart').select('quantity, products(price)').eq('user_id', user_id).execute()
            for item in response.data:
                prod = item.get('products')
                if prod and prod.get('price'):
                    cart_total += float(prod['price']) * item['quantity']
        except:
            pass
    else:
        guest_cart = session.get('cart', [])
        cart_total = sum(it['price'] * it['qty'] for it in guest_cart)

    wishlist_count = 0
    if user_id:
        try:
            count_res = supabase.table('wishlist').select('id', count='exact').eq('user_id', user_id).execute()
            wishlist_count = count_res.count if count_res.count else 0
        except:
            pass

    compare_ids = []
    try:
        compare_ids = json.loads(request.cookies.get('compare', '[]'))
    except:
        pass
    compare_count = len(compare_ids)

    user = None
    if user_id:
        try:
            user_res = supabase.table('users').select('full_name, email, is_admin, approved').eq('id', user_id).single().execute()
            user = user_res.data
        except:
            pass

    return dict(user=user, cart_total=cart_total,
                wishlist_count=wishlist_count, compare_count=compare_count,
                pharmacy_name=PHARMACY_NAME, phone=PHARMACY_PHONE, email=PHARMACY_EMAIL)

# ---------- Public pages ----------
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']
        try:
            supabase.table('inquiries').insert({'name': name, 'email': email, 'message': message}).execute()
        except:
            pass
        return redirect('/contact?sent=1')
    return render_template('contact.html')

@app.route('/blog')
def blog():
    posts = [
        {"title":"Understanding Pain Relief","date":"2026-04-15","snippet":"Learn about different types of OTC pain relievers."},
        {"title":"Essential Baby Care Products","date":"2026-04-10","snippet":"A guide for new parents."},
        {"title":"Probiotics & Gut Health","date":"2026-04-02","snippet":"How probiotics improve wellness."}
    ]
    return render_template('blog.html', posts=posts)

# ---------- Shop ----------
@app.route('/shop')
def shop():
    search = request.args.get('search', '')
    category = request.args.get('category', '')
    page = int(request.args.get('page', 1))
    per_page = 6
    offset = (page - 1) * per_page

    query = supabase.table('products').select('*', count='exact').eq('active', True)
    if search:
        query = query.or_(f"name.ilike.%{search}%,category.ilike.%{search}%")
    if category:
        query = query.or_(f"category.ilike.%{category}%")
    total_res = query.execute()
    total = total_res.count if total_res.count else 0

    data_query = supabase.table('products').select('*').eq('active', True)
    if search:
        data_query = data_query.or_(f"name.ilike.%{search}%,category.ilike.%{search}%")
    if category:
        data_query = data_query.or_(f"category.ilike.%{category}%")
    result = data_query.range(offset, offset + per_page - 1).execute()
    products = result.data or []

    total_pages = max(1, (total + per_page - 1) // per_page)
    return render_template('shop.html', products=products, search=search, category=category,
                           page=page, total_pages=total_pages)

# ---------- Prescription upload ----------
@app.route('/prescription', methods=['GET', 'POST'])
def prescription_upload():
    if request.method == 'POST':
        name = request.form['customer_name']
        email = request.form['customer_email']
        phone = request.form['customer_phone']
        notes = request.form.get('notes', '')
        file = request.files.get('prescription_file')
        file_url = None
        if file and file.filename:
            try:
                filename = secure_filename(file.filename)
                unique_name = f"rx_{os.urandom(4).hex()}_{filename}"
                file_bytes = file.read()
                supabase.storage.from_("product-images").upload(unique_name, file_bytes, {"content-type": file.content_type})
                file_url = f"{SUPABASE_URL}/storage/v1/object/public/product-images/{unique_name}"
            except:
                pass
        try:
            supabase.table('prescriptions').insert({
                'customer_name': name,
                'customer_email': email,
                'customer_phone': phone,
                'notes': notes,
                'file_url': file_url,
                'status': 'pending'
            }).execute()
        except:
            pass
        return render_template('prescription_success.html')
    return render_template('prescription_upload.html')

# ---------- Cart ----------
@app.route('/cart/add', methods=['POST'])
def add_to_cart():
    product_id = request.form['productId']
    quantity = int(request.form.get('quantity', 1))
    try:
        product = supabase.table('products').select('id, name, price').eq('id', product_id).single().execute()
    except:
        return 'Product not found', 404
    if not product.data:
        return 'Product not found', 404
    prod = product.data
    if 'user_id' in session:
        user_id = session['user_id']
        try:
            existing = supabase.table('cart').select('id, quantity').eq('user_id', user_id).eq('product_id', product_id).execute()
        except:
            return redirect('/cart')
        if existing.data:
            supabase.table('cart').update({'quantity': existing.data[0]['quantity'] + quantity}).eq('id', existing.data[0]['id']).execute()
        else:
            supabase.table('cart').insert({'user_id': user_id, 'product_id': product_id, 'quantity': quantity}).execute()
    else:
        cart = session.get('cart', [])
        found = False
        for item in cart:
            if item['productId'] == product_id:
                item['qty'] += quantity
                found = True
                break
        if not found:
            cart.append({'productId': product_id, 'qty': quantity, 'price': float(prod['price']), 'name': prod['name']})
        session['cart'] = cart
    return redirect('/cart')

@app.route('/cart')
def view_cart():
    cart_items = []
    total = 0.0
    if 'user_id' in session:
        user_id = session['user_id']
        try:
            db_cart = supabase.table('cart').select('quantity, product_id, products(name, price)').eq('user_id', user_id).execute()
        except:
            db_cart = []
        for item in db_cart.data if db_cart else []:
            prod = item.get('products')
            if prod:
                cart_items.append({'productId': item['product_id'], 'name': prod['name'], 'price': float(prod['price']), 'qty': item['quantity']})
                total += float(prod['price']) * item['quantity']
    else:
        cart_items = session.get('cart', [])
        total = sum(it['price'] * it['qty'] for it in cart_items)
    return render_template('cart.html', cart=cart_items, total=total)

@app.route('/cart/remove/<product_id>')
def remove_from_cart(product_id):
    if 'user_id' in session:
        try:
            supabase.table('cart').delete().eq('user_id', session['user_id']).eq('product_id', product_id).execute()
        except:
            pass
    else:
        cart = [i for i in session.get('cart', []) if i['productId'] != product_id]
        session['cart'] = cart
    return redirect('/cart')

@app.route('/wishlist/toggle', methods=['POST'])
def wishlist_toggle():
    if 'user_id' not in session:
        return 'Login required', 401
    user_id = session['user_id']
    product_id = request.form['productId']
    existing = supabase.table('wishlist').select('id').eq('user_id', user_id).eq('product_id', product_id).execute()
    if existing.data:
        supabase.table('wishlist').delete().eq('user_id', user_id).eq('product_id', product_id).execute()
    else:
        supabase.table('wishlist').insert({'user_id': user_id, 'product_id': product_id}).execute()
    return redirect(request.referrer or '/')

@app.route('/compare/toggle/<product_id>')
def compare_toggle(product_id):
    compare = json.loads(request.cookies.get('compare', '[]'))
    if product_id in compare:
        compare.remove(product_id)
    else:
        if len(compare) < 4:
            compare.append(product_id)
    resp = redirect(request.referrer or '/')
    resp.set_cookie('compare', json.dumps(compare), max_age=86400)
    return resp

@app.route('/compare')
def compare_page():
    ids = json.loads(request.cookies.get('compare', '[]'))
    if not ids:
        return 'No products to compare.'
    products = supabase.table('products').select('*').in_('id', ids).execute().data
    return render_template('compare.html', products=products)

# ---------- Checkout with discount codes ----------
@app.route('/checkout')
def checkout_form():
    return render_template('checkout.html')

@app.route('/checkout', methods=['POST'])
def place_order():
    shipping = {
        'shipping_name': request.form['shipping_name'],
        'shipping_address': request.form['shipping_address'],
        'shipping_city': request.form['shipping_city'],
        'shipping_phone': request.form['shipping_phone'],
        'payment_method': request.form['payment_method']
    }
    guest_email = request.form.get('guest_email')
    user_id = session.get('user_id')

    cart_items = []
    if user_id:
        db_cart = supabase.table('cart').select('quantity, product_id, products(name, price)').eq('user_id', user_id).execute()
        if not db_cart.data:
            return 'Cart is empty.'
        for item in db_cart.data:
            prod = item['products']
            cart_items.append({'productId': item['product_id'], 'name': prod['name'], 'price': float(prod['price']), 'qty': item['quantity']})
    else:
        guest_cart = session.get('cart', [])
        if not guest_cart:
            return 'Cart is empty.'
        if not guest_email:
            return 'Please provide your email.'
        cart_items = guest_cart

    total = sum(it['price'] * it['qty'] for it in cart_items)

    discount_applied = 0
    discount_code = request.form.get('discount_code', '').strip().upper()
    if discount_code:
        try:
            code_res = supabase.table('discount_codes').select('*').eq('code', discount_code).eq('active', True).single().execute()
            if code_res.data:
                code = code_res.data
                if code.get('usage_limit') is None or code.get('used_count', 0) < code['usage_limit']:
                    if not code.get('min_order_amount') or total >= code['min_order_amount']:
                        if code.get('discount_percent'):
                            discount_applied = total * code['discount_percent'] / 100
                        elif code.get('discount_amount'):
                            discount_applied = code['discount_amount']
                        total -= discount_applied
                        supabase.table('discount_codes').update({'used_count': code['used_count'] + 1}).eq('id', code['id']).execute()
                        session['discount_applied'] = discount_applied
        except:
            pass

    order_data = {**shipping, 'total_amount': total}
    if user_id:
        order_data['user_id'] = user_id
    else:
        order_data['guest_email'] = guest_email

    order_res = supabase.table('orders').insert(order_data).execute()
    order_id = order_res.data[0]['id']

    for item in cart_items:
        supabase.table('order_items').insert({
            'order_id': order_id,
            'product_id': item['productId'],
            'product_name': item['name'],
            'quantity': item['qty'],
            'unit_price': item['price'],
            'total_price': item['price'] * item['qty']
        }).execute()

    if user_id:
        supabase.table('cart').delete().eq('user_id', user_id).execute()
    else:
        session.pop('cart', None)

    session['last_order_id'] = order_id
    return redirect('/order-confirmation')

@app.route('/order-confirmation')
def order_confirmation():
    order_id = session.pop('last_order_id', None)
    discount = session.pop('discount_applied', 0)
    if not order_id:
        return redirect('/')
    order = supabase.table('orders').select('*').eq('id', order_id).single().execute().data
    items = supabase.table('order_items').select('*').eq('order_id', order_id).execute().data
    return render_template('order_confirmation.html', order=order, items=items, discount=discount)

# ---------- Authentication ----------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user_res = supabase.table('users').select('*').eq('email', email).execute()
        if not user_res.data:
            return render_template('login.html', error='Invalid credentials')
        user = user_res.data[0]
        if not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            return render_template('login.html', error='Invalid credentials')

        is_admin = user.get('is_admin', False)
        approved = user.get('approved', False)

        # Super admin (rodriguezgeorge089@gmail.com) always approved
        if email == 'rodriguezgeorge089@gmail.com':
            approved = True
            if not user.get('approved'):
                supabase.table('users').update({'approved': True}).eq('id', user['id']).execute()

        if not is_admin and not approved:
            return render_template('login.html', error='Your account is pending approval. Please try again later or contact support.')

        if is_admin and not approved:
            supabase.table('users').update({'approved': True}).eq('id', user['id']).execute()
            user['approved'] = True

        session['user_id'] = user['id']
        session['user_name'] = user['full_name']
        session['is_admin'] = is_admin
        if 'cart' in session:
            for item in session['cart']:
                existing = supabase.table('cart').select('id').eq('user_id', user['id']).eq('product_id', item['productId']).execute()
                if existing.data:
                    supabase.table('cart').update({'quantity': existing.data[0]['quantity'] + item['qty']}).eq('id', existing.data[0]['id']).execute()
                else:
                    supabase.table('cart').insert({'user_id': user['id'], 'product_id': item['productId'], 'quantity': item['qty']}).execute()
            session.pop('cart', None)
        return redirect('/')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        password = request.form['password']
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        try:
            supabase.table('users').insert({
                'full_name': full_name,
                'email': email,
                'password_hash': hashed
            }).execute()
        except:
            return render_template('register.html', error='Email already exists.')
        return render_template('register_success.html')
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ---------- Customer Orders ----------
@app.route('/my-account')
def my_account():
    if not session.get('user_id'):
        return redirect('/login')
    user_id = session['user_id']
    orders = supabase.table('orders').select('*').eq('user_id', user_id).order('created_at', desc=True).execute().data or []
    for order in orders:
        order['items'] = supabase.table('order_items').select('*').eq('order_id', order['id']).execute().data or []
    return render_template('my_orders.html', orders=orders)

# ---------- Admin Decorator ----------
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated

# ---------- Admin Dashboard ----------
@app.route('/admin')
@admin_required
def admin_dashboard():
    orders_list = supabase.table('orders').select('*').order('created_at', desc=True).limit(10).execute()
    total_sales = sum(o['total_amount'] for o in orders_list.data) if orders_list.data else 0
    total_orders = supabase.table('orders').select('count', count='exact').execute().count or 0
    total_products = supabase.table('products').select('count', count='exact').execute().count or 0
    customers = set()
    if orders_list.data:
        for o in orders_list.data:
            e = o.get('customer_email') or o.get('guest_email')
            if e: customers.add(e)
    total_customers = len(customers)

    recent_orders_html = ''
    for o in (orders_list.data or []):
        order_id_str = str(o['id'])
        status = o.get('order_status', 'pending')
        status_color = {
            'pending': 'bg-warning text-dark',
            'confirmed': 'bg-info text-white',
            'shipped': 'bg-primary text-white',
            'delivered': 'bg-success text-white'
        }.get(status, 'bg-secondary text-white')
        recent_orders_html += f"""
        <tr>
            <td><strong>#{order_id_str[:8]}</strong></td>
            <td>{o.get('shipping_name', o.get('guest_email', 'Guest'))}</td>
            <td>KSh {o['total_amount']}</td>
            <td><span class="badge badge-status {status_color} rounded-pill">{status}</span></td>
            <td>{o['created_at'][:10]}</td>
        </tr>
        """

    return render_template('admin_dashboard.html',
                           total_sales=f"{total_sales:,.2f}",
                           total_orders=total_orders,
                           total_products=total_products,
                           total_customers=total_customers,
                           recent_orders=recent_orders_html)

# ---------- Admin Orders ----------
@app.route('/admin/orders')
@admin_required
def admin_orders():
    orders = supabase.table('orders').select('*').order('created_at', desc=True).execute().data
    return render_template('admin_orders.html', orders=orders or [])

@app.route('/admin/order/<order_id>/status', methods=['POST'])
@admin_required
def update_order_status(order_id):
    new_status = request.form['status']
    supabase.table('orders').update({'order_status': new_status}).eq('id', order_id).execute()
    return redirect('/admin/orders')

@app.route('/admin/order/<int:order_id>/invoice')
@admin_required
def admin_invoice(order_id):
    order = supabase.table('orders').select('*').eq('id', order_id).single().execute().data
    items = supabase.table('order_items').select('*').eq('order_id', order_id).execute().data
    return render_template('invoice.html', order=order, items=items)

# ---------- Admin Products ----------
@app.route('/admin/products')
@admin_required
def admin_products():
    products = supabase.table('products').select('*').order('name').execute().data
    return render_template('admin_products.html', products=products or [])

@app.route('/admin/add-product', methods=['GET', 'POST'])
@admin_required
def add_product():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form.get('description', '')
        category = request.form['category']
        price = float(request.form['price'])
        stock = int(request.form['stock'])
        image = request.files.get('image')
        image_url = None
        if image and image.filename:
            fname = secure_filename(image.filename)
            unique_name = f"{os.urandom(4).hex()}_{fname}"
            supabase.storage.from_("product-images").upload(unique_name, image.read(), {"content-type": image.content_type})
            image_url = f"{SUPABASE_URL}/storage/v1/object/public/product-images/{unique_name}"
        supabase.table('products').insert({
            'name': name, 'description': description, 'category': category,
            'price': price, 'stock': stock, 'image_url': image_url, 'active': True
        }).execute()
        return redirect('/admin/products')
    return render_template('admin_add_product.html')

@app.route('/admin/edit-product/<product_id>', methods=['GET', 'POST'])
@admin_required
def edit_product(product_id):
    if request.method == 'POST':
        name = request.form['name']
        description = request.form.get('description', '')
        category = request.form['category']
        price = float(request.form['price'])
        stock = int(request.form['stock'])
        image = request.files.get('image')
        upd = {'name': name, 'description': description, 'category': category, 'price': price, 'stock': stock}
        if image and image.filename:
            fname = secure_filename(image.filename)
            unique_name = f"{os.urandom(4).hex()}_{fname}"
            supabase.storage.from_("product-images").upload(unique_name, image.read(), {"content-type": image.content_type})
            upd['image_url'] = f"{SUPABASE_URL}/storage/v1/object/public/product-images/{unique_name}"
        supabase.table('products').update(upd).eq('id', product_id).execute()
        return redirect('/admin/products')
    p = supabase.table('products').select('*').eq('id', product_id).single().execute().data
    return render_template('admin_edit_product.html', product=p)

@app.route('/admin/delete-product/<product_id>')
@admin_required
def delete_product(product_id):
    supabase.table('products').delete().eq('id', product_id).execute()
    return redirect('/admin/products')

# ---------- Admin Prescriptions ----------
@app.route('/admin/prescriptions')
@admin_required
def admin_prescriptions():
    rx = supabase.table('prescriptions').select('*').order('created_at', desc=True).execute().data
    return render_template('admin_prescriptions.html', prescriptions=rx or [])

# ---------- Admin Customers ----------
@app.route('/admin/customers')
@admin_required
def admin_customers():
    orders = supabase.table('orders').select('*').order('created_at', desc=True).execute().data or []
    customers = {}
    for o in orders:
        email = o.get('customer_email') or o.get('guest_email')
        if not email: continue
        if email not in customers:
            customers[email] = {"name": o.get('customer_name','') or o.get('shipping_name',''), "phone": o.get('customer_phone','') or o.get('shipping_phone',''), "total_spent": 0, "orders": 0}
        customers[email]["total_spent"] += o['total_amount']
        customers[email]["orders"] += 1
    return render_template('admin_customers.html', customers=customers)

# ---------- Admin User Management ----------
@app.route('/admin/users')
@admin_required
def admin_users():
    users = supabase.table('users').select('*').order('created_at', desc=True).execute().data or []
    return render_template('admin_users.html', users=users)

@app.route('/admin/approve-user/<user_id>')
@admin_required
def approve_user(user_id):
    supabase.table('users').update({'approved': True}).eq('id', user_id).execute()
    return redirect('/admin/users')

@app.route('/admin/disable-user/<user_id>')
@admin_required
def disable_user(user_id):
    supabase.table('users').update({'approved': False}).eq('id', user_id).execute()
    return redirect('/admin/users')

# ---------- Super Admin: Create User ----------
@app.route('/admin/create-user', methods=['GET', 'POST'])
@admin_required
def create_user():
    # Only super admin can access
    current_user_email = supabase.table('users').select('email').eq('id', session['user_id']).single().execute().data['email']
    if current_user_email != 'rodriguezgeorge089@gmail.com':
        return "Unauthorized", 403

    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        password = request.form['password']
        is_admin = request.form.get('is_admin') == 'on'
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        try:
            supabase.table('users').insert({
                'full_name': full_name,
                'email': email,
                'password_hash': hashed,
                'is_admin': is_admin,
                'approved': True
            }).execute()
        except:
            return render_template('admin_create_user.html', error='Email already exists.')
        return redirect('/admin/users')
    return render_template('admin_create_user.html')

# ---------- Admin CSV Export ----------
@app.route('/admin/export-orders')
@admin_required
def export_orders():
    import csv, io
    orders = supabase.table('orders').select('*').order('created_at', desc=True).execute().data or []
    output = io.StringIO()
    w = csv.writer(output)
    w.writerow(["Order ID","Date","Customer","Email","Phone","Total","Status","Payment"])
    for o in orders:
        w.writerow([str(o['id'])[:8], o['created_at'][:10], o.get('customer_name','') or o.get('shipping_name',''), o.get('customer_email','') or o.get('guest_email',''), o.get('customer_phone','') or o.get('shipping_phone',''), o['total_amount'], o.get('order_status','pending'), o.get('payment_method','')])
    output.seek(0)
    return Response(output.getvalue(), mimetype='text/csv', headers={"Content-Disposition":"attachment;filename=orders.csv"})

# ---------- Admin Settings ----------
@app.route('/admin/settings', methods=['GET', 'POST'])
@admin_required
def admin_settings():
    if request.method == 'POST':
        new_password = request.form['new_password']
        hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        supabase.table('users').update({'password_hash': hashed}).eq('id', session['user_id']).execute()
        return redirect('/admin/settings?success=1')
    return render_template('admin_settings.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
