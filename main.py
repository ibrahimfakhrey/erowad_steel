from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import stripe
# Initialize Stripe
stripe.api_key = 'sk_test_51QFtNmDEJNdb2MEJikWqTfL7pq4AuDodvOOT4QNNxnega50LFd4VmcK67uS6EtGNnBIPdHhThhZdz0l59TXrIJ0C00Mla3RpWA'
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///store.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key_here'

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

with app.app_context():
    class User(db.Model, UserMixin):
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(100), nullable=False)
        email = db.Column(db.String(100), unique=True, nullable=False)
        password = db.Column(db.String(200), nullable=False)

        # Relationship to Cart
        carts = db.relationship('Cart', backref='user', lazy=True)


    class Product(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(100), nullable=False)
        price = db.Column(db.Float, nullable=False)
        quantity = db.Column(db.Integer, nullable=False)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)

        # Relationship to Cart
        cart_entries = db.relationship('Cart', backref='product', lazy=True)


    class Order(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
        order_date = db.Column(db.DateTime, default=datetime.utcnow)
        shipped = db.Column(db.Boolean, default=False)


    class Cart(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
        product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
        quantity = db.Column(db.Integer, default=1)

        # Here you can specify the backref as 'cart_items' or any other name
        # product = db.relationship('Product', backref='cart_entries', lazy=True)
    db.create_all()

# User Loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Routes
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        new_user = User(name=name, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials.', 'danger')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'info')
    return redirect(url_for('login'))


@app.route('/')
def index():
    products = Product.query.all()
    return render_template('index.html', products=products)


@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)  # Ensure the product exists

    # Check if the product is already in the user's cart
    cart_item = Cart.query.filter_by(user_id=current_user.id, product_id=product_id).first()

    if cart_item:
        cart_item.quantity += 1  # Increase quantity if product is already in the cart
    else:
        cart_item = Cart(user_id=current_user.id, product_id=product_id, quantity=1)
        db.session.add(cart_item)

    db.session.commit()
    flash('Product added to cart!', 'success')
    return redirect(url_for('index'))


@app.route('/cart')
@login_required
def cart():
    # Retrieve only the current user's cart items
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    total_price = sum(item.product.price * item.quantity for item in cart_items)  # Calculate total price

    return render_template('cart.html', cart_items=cart_items, total_price=total_price)




@app.route('/orders')
@login_required
def view_orders():
    orders = Order.query.filter_by(user_id=current_user.id).all()
    return render_template('orders.html', orders=orders)

@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        name = request.form['name']
        price = request.form['price']
        quantity = request.form['quantity']


        new_product = Product(name=name, price=price, quantity=quantity)
        db.session.add(new_product)
        db.session.commit()
        flash('Product added successfully!', 'success')
        return redirect(url_for('index'))

    return render_template('add_product.html')

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    if request.method == 'POST':
        # Get the cart items for the current user
        cart_items = Cart.query.filter_by(user_id=current_user.id).all()

        if not cart_items:
            # Handle case when there are no items in the cart
            flash('Your cart is empty.', 'warning')
            return redirect(url_for('cart'))  # Redirect to the cart page

        # Calculate the total amount for the order
        total_amount = sum(item.product.price * item.quantity for item in cart_items) * 100  # amount in cents

        # Create a new Stripe payment intent
        payment_intent = stripe.PaymentIntent.create(
            amount=total_amount,
            currency='usd',  # Change this to your desired currency
            metadata={'user_id': current_user.id}  # Store user ID in metadata
        )

        # Render the checkout template with client secret to complete payment
        return render_template('checkout.html', client_secret=payment_intent['client_secret'], current_user=current_user)

    # On GET request, render the checkout page
    return render_template('checkout.html', current_user=current_user)  # Ensure current_user is passed


@app.route('/checkout/success', methods=['GET'])
@login_required
def checkout_success():
    # Handle order creation and clear the cart after successful payment
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()

    for item in cart_items:
        order = Order(
            user_id=current_user.id,
            product_id=item.product_id
        )
        db.session.add(order)
        db.session.delete(item)  # Remove item from cart

    db.session.commit()
    flash('Checkout successful! Your orders are being processed.', 'success')
    return redirect(url_for('view_orders'))

# Render the checkout success page or order confirmation
@app.route('/checkout/cancel', methods=['GET'])
@login_required
def checkout_cancel():
    flash('Payment cancelled. Please try again.', 'danger')
    return redirect(url_for('cart'))

if __name__ == '__main__':
    app.run(debug=True)
