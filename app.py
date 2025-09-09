#Step 2
from model import get_db_connection
from flask import Flask, jsonify, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import mysql.connector
from datetime import datetime

#Step 3
app = Flask(__name__)
app.secret_key = 'wverihdfuvuwi2482'

#Step 4

app.config['PROFILE_UPLOAD_FOLDER'] = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static', 'profiles')
os.makedirs(app.config['PROFILE_UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename, filetype):
    if filetype == 'image':
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions
    return False

#Step 5

@app.context_processor
def inject_current_year():
    return {'current_year': datetime.now().year}

#Step 6

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        number = request.form['number']
        password = request.form['password']
        profile_image = request.files['profile_image']
        role = request.form['role']

        if profile_image and allowed_file(profile_image.filename, 'image'):
            filename = secure_filename(profile_image.filename)
            image_path = os.path.join(app.config['PROFILE_UPLOAD_FOLDER'], filename)
            profile_image.save(image_path)
        else:
            flash('Invalid image file.', 'danger')
            return redirect(request.url)

        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                'INSERT INTO users (name, email, number, password, image_path, role) VALUES (%s, %s, %s, %s, %s, %s)',
                (name, email, number, hashed_password, filename, role)
            )
            conn.commit()
            flash('Registration successful. Please login.', 'success')
            return redirect(url_for('login'))
        except mysql.connector.IntegrityError:
            flash('Email already exists.', 'danger')
        finally:
            cursor.close()
            conn.close()

    return render_template('register.html', title="Register")


#Step 8
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True) 
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        user = cursor.fetchone()

        cursor.close()
        conn.close()
    
        if user and check_password_hash(user['password'], password):
         

            session['email'] = user['email']
            session['name'] = user['name']
            session['role'] = user['role']

            flash('Login successful!', 'success')
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user['role']== 'provider':
                return redirect(url_for('provider_dashboard'))
            else:
                return redirect(url_for('index'))
        else:
            flash('Invalid email or password', 'danger')

    return render_template('login.html', title="Login")


#Step 9
@app.route('/contact' , methods=['GET', 'POST'])
def contact():
    return render_template('contact.html')
#Step 10

@app.route('/profile')
def profile():
    if 'email' not in session:
        flash('Please login to view your profile.', 'warning')
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True) 
    cursor.execute("SELECT * FROM users WHERE email = %s", (session['email'],))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('login'))

    return render_template('profile.html', user=user)




################################ Admin Dashboard and Routes ################################

#Step 15
@app.route('/admin_dashboard')
def admin_dashboard():
    if 'email' not in session or session.get('role') != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Total users (excluding admin)
    cursor.execute("SELECT COUNT(*) as total_users FROM users WHERE role != 'admin' AND role != 'provider'")
    total_users = cursor.fetchone()['total_users']

    # Total providers
    cursor.execute("SELECT COUNT(*) as total_providers FROM users WHERE role = 'provider'")
    total_providers = cursor.fetchone()['total_providers']

    # Total orders
    cursor.execute("SELECT COUNT(*) as total_orders FROM orders")
    total_orders = cursor.fetchone()['total_orders']

    # Total revenue
    cursor.execute("SELECT IFNULL(SUM(service_price), 0) as total_revenue FROM orders")
    total_revenue = cursor.fetchone()['total_revenue']

    cursor.close()
    conn.close()

    return render_template('admin_dashboard.html',
                           total_users=total_users,
                           total_providers=total_providers,
                           total_orders=total_orders,
                           total_revenue=total_revenue,
                           title="Admin Dashboard")

@app.route('/admin/create_service', methods=['GET', 'POST'])
def admin_create_service():
    if 'email' not in session or session.get('role') != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT id, name, specialization FROM users WHERE role='provider'")
    providers = cursor.fetchall()

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        provider_id = request.form['provider_id']
        price = request.form['price']
        file = request.files['file']
        if file and allowed_file(file.filename, 'image'):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['PROFILE_UPLOAD_FOLDER'], filename)
            file.save(file_path)
        else:
            flash('Invalid image file.', 'danger')

       
        cursor.execute(
            'INSERT INTO services (name, description, provider_id, price, image_file) VALUES (%s, %s, %s, %s, %s)',
            (name, description, provider_id, price, filename)
        )

       
        cursor.execute("SELECT specialization FROM users WHERE id=%s", (provider_id,))
        spec = cursor.fetchone()['specialization']
        if spec:
            new_spec = spec + ', ' + name
        else:
            new_spec = name
        cursor.execute("UPDATE users SET specialization=%s WHERE id=%s", (new_spec, provider_id))

        conn.commit()
        flash('Service created and provider updated successfully!', 'success')
        return redirect(url_for('admin_create_service'))

    cursor.close()
    conn.close()
    return render_template('admin_create_service.html', providers=providers, title="Create Service")


@app.route('/admin/view_services')
def view_services():
    if 'email' not in session or session.get('role') != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT s.id, s.name, s.description, s.price, u.name AS provider_name 
        FROM services s 
        JOIN users u ON s.provider_id = u.id
    """)
    services = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin_view_services.html', services=services, title="View Services")


@app.route('/admin/edit_service/<int:service_id>', methods=['GET', 'POST'])
def edit_service(service_id):
    if 'email' not in session or session.get('role') != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Get service details
    cursor.execute("SELECT * FROM services WHERE id = %s", (service_id,))
    service = cursor.fetchone()

    # Get providers for dropdown
    cursor.execute("SELECT id, name FROM users WHERE role='provider'")
    providers = cursor.fetchall()

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        provider_id = request.form['provider_id']
        price = request.form['price']
        file = request.files['']

        cursor.execute("""
            UPDATE services SET name=%s, description=%s, provider_id=%s, price=%s WHERE id=%s
        """, (name, description, provider_id, price, service_id))

        conn.commit()
        flash('Service updated successfully!', 'success')
        return redirect(url_for('view_services'))

    cursor.close()
    conn.close()
    return render_template('admin_edit_service.html', service=service, providers=providers, title="Edit Service")


@app.route('/admin/delete_service/<int:service_id>', methods=['POST'])
def delete_service(service_id):
    if 'email' not in session or session.get('role') != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM services WHERE id = %s", (service_id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash('Service deleted successfully!', 'success')
    return redirect(url_for('view_services'))



@app.route('/admin/users')
def admin_users_list():
    if 'email' not in session or session.get('role') != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE role != 'admin' AND role != 'provider'")
    users = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('admin_users_list.html', users=users, title="Users List")

@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if 'email' not in session or session.get('role') != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
  
    cursor.execute("DELETE FROM users WHERE id = %s AND role NOT IN ('admin', 'provider')", (user_id,))
    conn.commit()
    cursor.close()
    conn.close()

    flash('User deleted successfully.', 'success')
    return redirect(url_for('admin_users_list'))


@app.route('/admin/providers')
def admin_providers_list():
    if 'email' not in session or session.get('role') != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE role = 'provider'")
    providers = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('admin_provider_list.html', providers=providers, title="Providers List")


@app.route('/admin/providers/edit/<int:provider_id>', methods=['GET', 'POST'])
def admin_edit_provider(provider_id):
    if 'email' not in session or session.get('role') != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE id = %s AND role = 'provider'", (provider_id,))
    provider = cursor.fetchone()

    if not provider:
        flash('Provider not found.', 'danger')
        return redirect(url_for('admin_providers_list'))

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        number = request.form['number']
        specialization = request.form['specialization']  # new field

        cursor.execute(
            "UPDATE users SET name=%s, email=%s, number=%s, specialization=%s WHERE id=%s",
            (name, email, number, specialization, provider_id)
        )
        conn.commit()
        flash('Provider updated successfully.', 'success')
        return redirect(url_for('admin_providers_list'))

    cursor.close()
    conn.close()
    return render_template('admin_edit_provider.html', provider=provider, title="Edit Provider")



@app.route('/admin/providers/delete/<int:provider_id>')
def admin_delete_provider(provider_id):
    if 'email' not in session or session.get('role') != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id=%s AND role='provider'", (provider_id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash('Provider deleted successfully.', 'success')
    return redirect(url_for('admin_providers_list'))

    

@app.route('/admin/orders')
def admin_orders_list():
    if 'email' not in session or session.get('role') != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
    SELECT o.id, o.amount, o.status, o.created_at, o.service_name,
           o.card_last4, o.payment_status, o.service_price,
           u.name AS user_name, p.name AS provider_name
    FROM orders o
    LEFT JOIN users u ON o.user_id = u.id
    LEFT JOIN users p ON o.provider_id = p.id
    ORDER BY o.created_at DESC
""")

    orders = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('admin_orders.html', orders=orders, title="Orders List")


@app.route('/admin/order/update/<int:order_id>', methods=['POST'])
def admin_update_order_status(order_id):
    if 'email' not in session or session.get('role') != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("UPDATE orders SET status=%s WHERE id=%s", ('Completed', order_id))
    conn.commit()
    cursor.close()
    conn.close()

    flash('Order status updated successfully.', 'success')
    return redirect(url_for('admin_orders_list'))


#################################### Provider Dashboard and Routes ####################################

@app.route('/provider/dashboard')
def provider_dashboard():
    if 'email' not in session or session.get('role') != 'provider':
        flash('Access denied.', 'danger')
        return redirect(url_for('login'))

   
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM orders WHERE provider_id = (SELECT id FROM users WHERE email = %s)", (session['email'],))
    orders = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('provider_dashboard.html', orders=orders, title="Provider Dashboard")

@app.route('/provider/order/update/<int:order_id>', methods=['POST'])
def update_order_status(order_id):
    if 'email' not in session or session.get('role') != 'provider':
        flash('Access denied.', 'danger')
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Example: update order status to Completed
    cursor.execute("UPDATE orders SET status=%s WHERE id=%s", ('Completed', order_id))
    conn.commit()
    cursor.close()
    conn.close()

    flash('Order status updated successfully.', 'success')
    return redirect(url_for('provider_dashboard'))






################################### User Dashboard and Routes ###################################


@app.route('/')
def index():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT s.*, u.name AS provider_name FROM services s JOIN users u ON s.provider_id = u.id")
    services = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('index.html', services=services, title="Home")



@app.route('/book_service/<int:service_id>', methods=['POST'])
def book_service(service_id):
    if 'email' not in session:
        flash('Please login to book a service.', 'danger')
        return redirect(url_for('login'))

    card_number = request.form['card_number']
    expiry = request.form['expiry']
    cvv = request.form['cvv']

    # Basic validation
    if not (card_number.isdigit() and len(card_number) == 16):
        flash('Invalid card number', 'danger')
        return redirect(request.referrer)
    if not (cvv.isdigit() and len(cvv) == 3):
        flash('Invalid CVV', 'danger')
        return redirect(request.referrer)
   

    card_last4 = card_number[-4:] 

    user_email = session['email']

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Get user ID
    cursor.execute("SELECT id FROM users WHERE email=%s", (user_email,))
    user = cursor.fetchone()
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('index'))
    user_id = user['id']

    # Get service details
    cursor.execute("SELECT * FROM services WHERE id=%s", (service_id,))
    service = cursor.fetchone()
    if not service:
        flash('Service not found.', 'danger')
        return redirect(url_for('index'))

    # Insert order with masked card info and payment status Paid
    cursor.execute(
        "INSERT INTO orders (user_id, provider_id, service_name, service_price, amount, card_last4, payment_status, status) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        (user_id, service['provider_id'], service['name'], service['price'], service['price'], card_last4, 'Paid', 'Pending')
    )

    conn.commit()
    cursor.close()
    conn.close()

    flash('Service booked and paid successfully!', 'success')
    return redirect(url_for('my_orders'))




@app.route('/my_orders')
def my_orders():
    if 'email' not in session:
        flash('Please login to view your orders.', 'danger')
        return redirect(url_for('login'))

    user_email = session['email']

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Get user ID
    cursor.execute("SELECT id FROM users WHERE email=%s", (user_email,))
    user = cursor.fetchone()
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('index'))
    user_id = user['id']

    # Fetch user's orders
    cursor.execute("""
        SELECT o.*, u.name AS provider_name
        FROM orders o
        JOIN users u ON o.provider_id = u.id
        WHERE o.user_id = %s
        ORDER BY o.created_at DESC
    """, (user_id,))
    orders = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('my_orders.html', orders=orders, title="My Orders")

#Step 18
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

#Step 11
if __name__ == '__main__':
    app.run(debug=True)
