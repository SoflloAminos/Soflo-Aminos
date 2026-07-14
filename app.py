#!/usr/bin/env python3
"""
Retail Storefront App - Flask Application
Self-hosted web app for customer logins, inventory viewing, and order placement (payment handled separately by owner).
"""

import os
import secrets
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, redirect, url_for, request, flash, jsonify, abort
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user, login_required, current_user
)
from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, SubmitField, FloatField, IntegerField,
    TextAreaField, SelectField
)
from wtforms.validators import DataRequired, Email, Length, NumberRange, Optional
from werkzeug.security import generate_password_hash, check_password_hash

# ============== CONFIG ==============
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or secrets.token_hex(16)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///retail_app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Customize these for your store
STORE_NAME = "Your Retail Store"
STORE_TAGLINE = "Quality products, easy ordering"
CONTACT_EMAIL = "owner@yourstore.com"
LOW_STOCK_THRESHOLD = 5

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# ============== MODELS ==============
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    orders = db.relationship('Order', backref='customer', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.email}>'

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, default=0)
    category = db.Column(db.String(50), default='General')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Product {self.name}>'

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending', index=True)  # pending, paid, fulfilled, cancelled
    total_amount = db.Column(db.Float, nullable=False)
    customer_name = db.Column(db.String(100))
    customer_email = db.Column(db.String(120))
    customer_phone = db.Column(db.String(20))
    shipping_address = db.Column(db.Text)
    notes = db.Column(db.Text)

    items = db.relationship('OrderItem', backref='order', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Order #{self.id} {self.status}>'

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price_at_order = db.Column(db.Float, nullable=False)
    product_name = db.Column(db.String(150))  # snapshot for history

    def __repr__(self):
        return f'<OrderItem order={self.order_id} prod={self.product_id} qty={self.quantity}>'

# ============== LOGIN ==============
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ============== FORMS ==============
class LoginForm(FlaskForm):
    email = StringField('Email Address', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Log In')

class RegisterForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email Address', validators=[DataRequired(), Email()])
    password = PasswordField('Password (min 6 chars)', validators=[DataRequired(), Length(min=6)])
    phone = StringField('Phone Number (optional)', validators=[Optional()])
    address = TextAreaField('Shipping Address (optional)', validators=[Optional()])
    submit = SubmitField('Create My Account')

class ProductForm(FlaskForm):
    name = StringField('Product Name', validators=[DataRequired(), Length(max=150)])
    description = TextAreaField('Description')
    price = FloatField('Price ($)', validators=[DataRequired(), NumberRange(min=0.01)])
    stock = IntegerField('Initial Stock', validators=[DataRequired(), NumberRange(min=0)])
    category = StringField('Category', default='General', validators=[Optional()])
    submit = SubmitField('Add Product')

class OrderStatusForm(FlaskForm):
    status = SelectField('Update Status', choices=[
        ('pending', 'Pending - Awaiting Payment'),
        ('paid', 'Paid - Payment Received'),
        ('fulfilled', 'Fulfilled - Completed / Shipped'),
        ('cancelled', 'Cancelled - Restore Stock')
    ], validators=[DataRequired()])
    notes = TextAreaField('Add Note (optional)')
    submit = SubmitField('Update Order')

# ============== HELPERS ==============
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def seed_initial_data():
    """Create default admin + sample products if DB is empty."""
    if User.query.first() is None:
        admin = User(
            email='admin@yourstore.com',
            name='Store Owner',
            is_admin=True
        )
        admin.set_password('admin123')
        db.session.add(admin)

        # Sample retail products (replace with your actual inventory)
        sample_products = [
            Product(name='Premium Cotton T-Shirt', description='Soft, high-quality 100% cotton tee. Available in multiple colors.', 
                    price=24.99, stock=45, category='Apparel'),
            Product(name='Insulated Coffee Mug', description='12oz stainless steel mug with your logo. Keeps drinks hot for hours.', 
                    price=14.99, stock=32, category='Drinkware'),
            Product(name='Spiral Notebook - Lined', description='A5 size, 120 pages, durable cover. Perfect for notes or journaling.', 
                    price=5.99, stock=120, category='Stationery'),
            Product(name='Wireless Earbuds Pro', description='Noise-cancelling, 24hr battery, IPX5 water resistant.', 
                    price=49.99, stock=18, category='Electronics'),
            Product(name='Eco-Friendly Water Bottle', description='32oz BPA-free, leakproof, made from recycled materials.', 
                    price=19.99, stock=55, category='Drinkware'),
            Product(name='Desk Organizer Set', description='Bamboo 4-piece set: pen holder, tray, phone stand.', 
                    price=29.99, stock=22, category='Office'),
        ]
        db.session.add_all(sample_products)
        db.session.commit()
        print("✓ Initial data seeded: default admin + sample products")

# ============== ROUTES - PUBLIC & AUTH ==============
@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('shop'))
    return render_template('index.html', store_name=STORE_NAME, tagline=STORE_TAGLINE)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegisterForm()
    if form.validate_on_submit():
        existing = User.query.filter_by(email=form.email.data.lower().strip()).first()
        if existing:
            flash('An account with that email already exists. Please log in instead.', 'warning')
            return redirect(url_for('login'))
        user = User(
            email=form.email.data.lower().strip(),
            name=form.name.data.strip(),
            phone=form.phone.data.strip() if form.phone.data else None,
            address=form.address.data.strip() if form.address.data else None,
            is_admin=False
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Account created successfully! You can now log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form, store_name=STORE_NAME)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower().strip()).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=True)
            flash(f'Welcome back, {user.name.split()[0]}!', 'success')
            next_page = request.args.get('next')
            if user.is_admin:
                return redirect(next_page or url_for('admin_dashboard'))
            return redirect(next_page or url_for('shop'))
        flash('Invalid email or password. Please try again.', 'danger')
    return render_template('login.html', form=form, store_name=STORE_NAME)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('index'))

# ============== CUSTOMER ROUTES ==============
@app.route('/shop')
@login_required
def shop():
    if current_user.is_admin:
        flash('You are logged in as admin. Use the Admin Panel to manage inventory and orders.', 'info')
        return redirect(url_for('admin_dashboard'))
    products = Product.query.order_by(Product.category.asc(), Product.name.asc()).all()
    categories = sorted(set(p.category for p in products))
    return render_template('customer_shop.html', products=products, categories=categories, store_name=STORE_NAME)

@app.route('/place_order', methods=['POST'])
@login_required
def place_order():
    if current_user.is_admin:
        return jsonify({'error': 'Admins cannot place customer orders.'}), 403

    data = request.get_json(silent=True)
    if not data or 'items' not in data or len(data['items']) == 0:
        return jsonify({'error': 'Your cart is empty.'}), 400

    cart = data['items']
    cust_name = (data.get('customer_name') or current_user.name or '').strip()
    cust_email = (data.get('customer_email') or current_user.email or '').strip()
    cust_phone = (data.get('customer_phone') or current_user.phone or '').strip()
    ship_addr = (data.get('shipping_address') or current_user.address or '').strip()
    order_notes = (data.get('notes') or '').strip()

    # Validate stock & calculate total (server-side)
    order_items_to_create = []
    total_amount = 0.0

    for item in cart:
        try:
            pid = int(item.get('product_id'))
            qty = int(item.get('quantity', 0))
        except (TypeError, ValueError):
            return jsonify({'error': 'Invalid cart data.'}), 400

        if qty < 1:
            return jsonify({'error': 'Quantity must be at least 1.'}), 400

        product = Product.query.get(pid)
        if not product:
            return jsonify({'error': f'Product ID {pid} not found.'}), 400
        if qty > product.stock:
            return jsonify({'error': f'Only {product.stock} left in stock for "{product.name}".'}), 400

        line_total = round(qty * product.price, 2)
        total_amount += line_total
        order_items_to_create.append({
            'product': product,
            'qty': qty,
            'price': product.price
        })

    # Create Order + Items + deduct stock
    new_order = Order(
        user_id=current_user.id,
        status='pending',
        total_amount=round(total_amount, 2),
        customer_name=cust_name,
        customer_email=cust_email,
        customer_phone=cust_phone,
        shipping_address=ship_addr,
        notes=order_notes
    )
    db.session.add(new_order)
    db.session.flush()  # populate new_order.id

    for item in order_items_to_create:
        oi = OrderItem(
            order_id=new_order.id,
            product_id=item['product'].id,
            quantity=item['qty'],
            price_at_order=item['price'],
            product_name=item['product'].name
        )
        db.session.add(oi)
        item['product'].stock -= item['qty']  # deduct inventory

    db.session.commit()

    # Notification to owner happens via admin dashboard (pending orders count + list)
    return jsonify({
        'success': True,
        'message': 'Order placed successfully! The store owner will contact you soon to arrange payment.',
        'order_id': new_order.id,
        'total': new_order.total_amount
    })

@app.route('/my-orders')
@login_required
def my_orders():
    if current_user.is_admin:
        return redirect(url_for('admin_orders'))
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.order_date.desc()).all()
    return render_template('customer_orders.html', orders=orders, store_name=STORE_NAME)

# ============== ADMIN ROUTES ==============
@app.route('/admin')
@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    pending_count = Order.query.filter_by(status='pending').count()
    total_customers = User.query.filter_by(is_admin=False).count()
    total_products = Product.query.count()
    total_orders = Order.query.count()
    low_stock_products = Product.query.filter(Product.stock < LOW_STOCK_THRESHOLD).order_by(Product.stock.asc()).all()
    recent_orders = Order.query.order_by(Order.order_date.desc()).limit(8).all()
    return render_template(
        'admin_dashboard.html',
        pending_count=pending_count,
        total_customers=total_customers,
        total_products=total_products,
        total_orders=total_orders,
        low_stock_products=low_stock_products,
        recent_orders=recent_orders,
        store_name=STORE_NAME,
        threshold=LOW_STOCK_THRESHOLD
    )

@app.route('/admin/products')
@login_required
@admin_required
def admin_products():
    products = Product.query.order_by(Product.category.asc(), Product.name.asc()).all()
    form = ProductForm()
    return render_template('admin_products.html', products=products, form=form, store_name=STORE_NAME)

@app.route('/admin/products/add', methods=['POST'])
@login_required
@admin_required
def add_product():
    form = ProductForm()
    if form.validate_on_submit():
        new_prod = Product(
            name=form.name.data.strip(),
            description=form.description.data.strip() if form.description.data else None,
            price=round(form.price.data, 2),
            stock=form.stock.data,
            category=form.category.data.strip() if form.category.data else 'General'
        )
        db.session.add(new_prod)
        db.session.commit()
        flash(f'✓ Product "{new_prod.name}" added successfully.', 'success')
    else:
        for field, errs in form.errors.items():
            for err in errs:
                flash(f'{field.title()}: {err}', 'danger')
    return redirect(url_for('admin_products'))

@app.route('/admin/products/<int:prod_id>/update', methods=['POST'])
@login_required
@admin_required
def update_product(prod_id):
    prod = Product.query.get_or_404(prod_id)
    data = request.get_json(silent=True) or request.form.to_dict()

    try:
        if 'name' in data and data['name']:
            prod.name = data['name'].strip()
        if 'description' in data:
            prod.description = data['description'].strip() if data['description'] else None
        if 'price' in data:
            prod.price = round(float(data['price']), 2)
        if 'stock' in data:
            prod.stock = max(0, int(data['stock']))
        if 'category' in data and data['category']:
            prod.category = data['category'].strip()
        db.session.commit()
        return jsonify({'success': True, 'message': 'Product updated successfully.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/admin/products/<int:prod_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_product(prod_id):
    prod = Product.query.get_or_404(prod_id)
    # Optional: prevent delete if has order history, but for simplicity allow (or check)
    name = prod.name
    db.session.delete(prod)
    db.session.commit()
    return jsonify({'success': True, 'message': f'Product "{name}" deleted.'})

@app.route('/admin/orders')
@login_required
@admin_required
def admin_orders():
    status = request.args.get('status', 'all')
    q = Order.query.order_by(Order.order_date.desc())
    if status != 'all':
        q = q.filter_by(status=status)
    orders = q.all()
    form = OrderStatusForm()
    return render_template('admin_orders.html', orders=orders, form=form, current_status=status, store_name=STORE_NAME)

@app.route('/admin/orders/<int:order_id>/update', methods=['POST'])
@login_required
@admin_required
def update_order(order_id):
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status') or (request.get_json() or {}).get('status')
    note_text = request.form.get('notes') or (request.get_json() or {}).get('notes', '')

    if new_status not in ['pending', 'paid', 'fulfilled', 'cancelled']:
        flash('Invalid status.', 'danger')
        return redirect(url_for('admin_orders'))

    old_status = order.status
    order.status = new_status

    # Restore stock only when cancelling a non-cancelled order
    if new_status == 'cancelled' and old_status != 'cancelled':
        for item in order.items:
            prod = Product.query.get(item.product_id)
            if prod:
                prod.stock += item.quantity
        flash(f'Order #{order.id} cancelled — stock restored.', 'warning')
    elif new_status != 'cancelled' and old_status == 'cancelled':
        flash('Note: Stock was not automatically deducted when reactivating a cancelled order. Adjust manually if needed.', 'info')

    if note_text:
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M')
        prefix = f"[{timestamp} by {current_user.name}] "
        order.notes = (order.notes or '') + "\n" + prefix + note_text.strip()

    db.session.commit()
    flash(f'Order #{order.id} status changed to "{new_status}".', 'success')
    return redirect(url_for('admin_orders', status=request.args.get('status', 'all')))

# ============== ERROR HANDLERS ==============
@app.errorhandler(403)
def forbidden(e):
    return render_template('error.html', code=403, message="You don't have permission to access this page.", store_name=STORE_NAME), 403

@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', code=404, message="Page not found.", store_name=STORE_NAME), 404

# ============== MAIN ==============
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_initial_data()
    print(f"\n🚀 {STORE_NAME} is starting...")
    print("   Default admin login: admin@yourstore.com / admin123")
    print("   ⚠️  CHANGE THE ADMIN PASSWORD IMMEDIATELY after first login!\n")
    app.run(host='0.0.0.0', port=5000, debug=True)