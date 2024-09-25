from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///store.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


app.config['SECRET_KEY'] = 'your_secret_key_here'  # Set your secret key
db = SQLAlchemy(app)
with app.app_context():
    class Product(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(100), nullable=False)
        price = db.Column(db.Float, nullable=False)
        quantity = db.Column(db.Integer, nullable=False)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)

        def __repr__(self):
            return f'<Product {self.name}>'


    class Order(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
        customer_name = db.Column(db.String(100), nullable=False)
        customer_email = db.Column(db.String(100), nullable=False)
        customer_phone = db.Column(db.String(15), nullable=False)
        customer_address = db.Column(db.String(255), nullable=False)
        order_date = db.Column(db.DateTime, default=datetime.utcnow)
        shipped = db.Column(db.Boolean, default=False)  # New field to track shipment status

        product = db.relationship('Product', backref=db.backref('orders', lazy=True))

        def __repr__(self):
            return f'<Order {self.id}>'


    db.create_all()  # Create database tables


@app.route('/')
def index():
    products = Product.query.all()
    return render_template('index.html', products=products)

@app.route('/toggle_shipment/<int:order_id>', methods=['POST'])
def toggle_shipment(order_id):
    order = Order.query.get_or_404(order_id)
    order.shipped = not order.shipped  # Toggle the shipped status
    db.session.commit()
    flash('Order shipment status updated!', 'success')
    return redirect(url_for('view_orders'))

@app.route('/order/<int:product_id>', methods=['GET', 'POST'])
def order(product_id):
    product = Product.query.get_or_404(product_id)
    if request.method == 'POST':
        customer_name = request.form['customer_name']
        customer_email = request.form['customer_email']
        customer_phone = request.form['customer_phone']  # Get phone
        customer_address = request.form['customer_address']  # Get address

        order = Order(
            product_id=product.id,
            customer_name=customer_name,
            customer_email=customer_email,
            customer_phone=customer_phone,  # Store phone
            customer_address=customer_address  # Store address
        )
        db.session.add(order)
        db.session.commit()
        flash('Order placed successfully!', 'success')
        return redirect(url_for('index'))
    return render_template('order.html', product=product)
@app.route('/orders')
def view_orders():
    orders = Order.query.all()  # Retrieve all orders
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

if __name__ == '__main__':
    app.run(debug=True)
