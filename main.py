import os
import json
import bcrypt
from flask import Flask, render_template, request, redirect, session, make_response
from supabase import create_client, Client

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'a-random-secret')

SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ------------------------------------------------
@app.context_processor
def utility_processor():
    user_id = session.get('user_id')
    cart_total = 0.0
    if user_id:
        response = supabase.table('cart').select('quantity, products(price)').eq('user_id', user_id).execute()
        for item in response.data:
            price = item['products']['price'] if item.get('products') else 0
            cart_total += price * item['quantity']
    else:
        guest_cart = session.get('cart', [])
        cart_total = sum(it['price'] * it['qty'] for it in guest_cart)

    wishlist_count = 0
    if user_id:
        count_res = supabase.table('wishlist').select('id', count='exact').eq('user_id', user_id).execute()
        wishlist_count = count_res.count if count_res.count else 0

    compare_ids = []
    try:
        compare_ids = json.loads(request.cookies.get('compare', '[]'))
    except:
        pass
    compare_count = len(compare_ids)

    user = None
    if user_id:
        user_res = supabase.table('users').select('full_name, email').eq('id', user_id).single().execute()
        user = user_res.data

    return dict(user=user, cart_total=cart_total, wishlist_count=wishlist_count, compare_count=compare_count)

# ------------------------------------------------
@app.route('/')
def index():
    products = supabase.table('products').select('*').execute().data
    return render_template('index.html', products=products)

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
            return 'Email already exists.'
        return redirect('/login')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user_res = supabase.table('users').select('*').eq('email', email).single().execute()
        user = user_res.data
        if not user or not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            return 'Invalid credentials'
        session['user_id'] = user['id']
        session['user_name'] = user['full_name']
        session['is_admin'] = user.get('is_admin', False)
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

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/cart/add', methods=['POST'])
def add_to_cart():
    product_id = request.form['productId']
    product = supabase.table('products').select('id, name, price').eq('id', product_id).single().execute()
    if not product.data:
        return 'Product not found', 404
    prod = product.data
    if 'user_id' in session:
        user_id = session['user_id']
        existing = supabase.table('cart').select('id, quantity').eq('user_id', user_id).eq('product_id', product_id).execute()
        if existing.data:
            supabase.table('cart').update({'quantity': existing.data[0]['quantity'] + 1}).eq('id', existing.data[0]['id']).execute()
        else:
            supabase.table('cart').insert({'user_id': user_id, 'product_id': product_id, 'quantity': 1}).execute()
    else:
        cart = session.get('cart', [])
        found = False
        for item in cart:
            if item['productId'] == product_id:
                item['qty'] += 1
                found = True
                break
        if not found:
            cart.append({'productId': product_id, 'qty': 1, 'price': float(prod['price']), 'name': prod['name']})
        session['cart'] = cart
    return redirect('/')

@app.route('/cart')
def view_cart():
    cart_items = []
    total = 0.0
    if 'user_id' in session:
        user_id = session['user_id']
        db_cart = supabase.table('cart').select('quantity, product_id, products(name, price)').eq('user_id', user_id).execute()
        for item in db_cart.data:
            prod = item['products']
            cart_items.append({'productId': item['product_id'], 'name': prod['name'], 'price': float(prod['price']), 'qty': item['quantity']})
            total += float(prod['price']) * item['quantity']
    else:
        cart_items = session.get('cart', [])
        total = sum(it['price'] * it['qty'] for it in cart_items)
    return render_template('cart.html', cart=cart_items, total=total)

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
    compare = []
    try:
        compare = json.loads(request.cookies.get('compare', '[]'))
    except:
        pass
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

@app.route('/checkout')
def checkout_page():
    return render_template('checkout.html')

@app.route('/checkout', methods=['POST'])
def checkout_process():
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
    if not order_id:
        return redirect('/')
    order = supabase.table('orders').select('*').eq('id', order_id).single().execute().data
    items = supabase.table('order_items').select('*').eq('order_id', order_id).execute().data
    return render_template('order_confirmation.html', order=order, items=items)

# Admin
@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = supabase.table('users').select('*').eq('email', email).eq('is_admin', True).single().execute()
        if user.data and bcrypt.checkpw(password.encode('utf-8'), user.data['password_hash'].encode('utf-8')):
            session['admin_id'] = user.data['id']
            return redirect('/admin/dashboard')
        return 'Invalid admin credentials'
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_id', None)
    return redirect('/admin')

from functools import wraps
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'admin_id' not in session:
            return redirect('/admin')
        return f(*args, **kwargs)
    return decorated

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    orders = supabase.table('orders').select('*').order('created_at', desc=True).execute().data
    return render_template('admin_dashboard.html', orders=orders)

@app.route('/admin/order/<int:order_id>')
@admin_required
def admin_order(order_id):
    order = supabase.table('orders').select('*').eq('id', order_id).single().execute().data
    items = supabase.table('order_items').select('*').eq('order_id', order_id).execute().data
    return render_template('admin_order.html', order=order, items=items)

@app.route('/admin/order/<int:order_id>/status', methods=['POST'])
@admin_required
def update_status(order_id):
    supabase.table('orders').update({'order_status': request.form['status']}).eq('id', order_id).execute()
    return redirect(f'/admin/order/{order_id}')

@app.route('/admin/order/<int:order_id>/invoice')
@admin_required
def invoice(order_id):
    order = supabase.table('orders').select('*').eq('id', order_id).single().execute().data
    items = supabase.table('order_items').select('*').eq('order_id', order_id).execute().data
    return render_template('invoice.html', order=order, items=items)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
