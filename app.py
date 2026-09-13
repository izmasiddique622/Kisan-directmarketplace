from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from mysql.connector import Error
import hashlib
import resend
import os
from dotenv import load_dotenv

load_dotenv()

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL")

# =========================================================
# FLASK APP
# =========================================================

app = Flask(__name__)

app.secret_key = os.getenv(
    "FLASK_SECRET_KEY",
    "development-only-change-this-key"
)


# =========================================================
# EMAIL CONFIGURATION
# =========================================================

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD", "")

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465


# =========================================================
# SEND EMAIL
# =========================================================

def send_email(to_email, subject, message):
    try:
        if not to_email or not EMAIL_ADDRESS or not EMAIL_APP_PASSWORD:
            print("EMAIL NOT CONFIGURED")
            return False

        email = EmailMessage()
        email["From"] = EMAIL_ADDRESS
        email["To"] = to_email
        email["Subject"] = subject
        email.set_content(message)

        with smtplib.SMTP_SSL(
            SMTP_SERVER,
            SMTP_PORT,
            timeout=8
        ) as server:
            server.login(
                EMAIL_ADDRESS,
                EMAIL_APP_PASSWORD
            )
            server.send_message(email)

        print("EMAIL SENT SUCCESSFULLY TO:", to_email)
        return True

    except Exception as e:
        print("EMAIL ERROR:", e)
        return False


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        ssl_ca=os.path.join(os.path.dirname(__file__), "ca.pem"),
        ssl_disabled=False,
        connection_timeout=10
    )

# =========================================================
# PASSWORD HASH
# =========================================================

def hash_password(password):

    return hashlib.sha256(
        password.encode()
    ).hexdigest()


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# =========================================================
# GENERAL LOGIN
# =========================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        if not email or not password:

            flash(
                "Please enter email and password.",
                "danger"
            )

            return render_template(
                "login.html"
            )

        db = None
        cursor = None

        try:

            hashed_password = hash_password(
                password
            )

            db = get_db_connection()

            cursor = db.cursor(
                dictionary=True
            )

            cursor.execute("""

                SELECT
                    id,
                    name,
                    email,
                    password,
                    role

                FROM users

                WHERE email = %s

                AND password = %s

            """, (
                email,
                hashed_password
            ))

            user = cursor.fetchone()

            if not user:

                flash(
                    "Invalid email or password.",
                    "danger"
                )

                return render_template(
                    "login.html"
                )

            session.clear()

            session["user_id"] = user["id"]

            session["user_name"] = user["name"]

            session["user_email"] = user["email"]

            session["role"] = user["role"]

            if user["role"] == "farmer":

                flash(
                    "Farmer login successful!",
                    "success"
                )

                return redirect(
                    url_for("farmer")
                )

            else:

                flash(
                    "Buyer login successful!",
                    "success"
                )

                return redirect(
                    url_for("buyer")
                )

        except Error as e:

            print(
                "LOGIN ERROR:",
                e
            )

            flash(
                "Database error. Please check MySQL.",
                "danger"
            )

            return render_template(
                "login.html"
            )

        finally:

            if cursor:
                cursor.close()

            if db:
                db.close()

    return render_template(
        "login.html"
    )


# =========================================================
# FARMER LOGIN
# =========================================================

@app.route(
    "/farmer-login",
    methods=["GET", "POST"]
)
def farmer_login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        if not email or not password:

            flash(
                "Please enter farmer email and password.",
                "danger"
            )

            return render_template(
                "farmer_login.html"
            )

        db = None
        cursor = None

        try:

            hashed_password = hash_password(
                password
            )

            db = get_db_connection()

            cursor = db.cursor(
                dictionary=True
            )

            cursor.execute("""

                SELECT
                    id,
                    name,
                    email,
                    password,
                    role

                FROM users

                WHERE email = %s

                AND password = %s

                AND role = 'farmer'

            """, (
                email,
                hashed_password
            ))

            farmer_user = cursor.fetchone()

            if not farmer_user:

                flash(
                    "Invalid farmer email or password.",
                    "danger"
                )

                return render_template(
                    "farmer_login.html"
                )

            session.clear()

            session["user_id"] = farmer_user["id"]

            session["user_name"] = farmer_user["name"]

            session["user_email"] = farmer_user["email"]

            session["role"] = farmer_user["role"]

            flash(
                "Farmer login successful!",
                "success"
            )

            return redirect(
                url_for("farmer")
            )

        except Error as e:

            print(
                "FARMER LOGIN ERROR:",
                e
            )

            flash(
                "Database error. Please check MySQL.",
                "danger"
            )

            return render_template(
                "farmer_login.html"
            )

        finally:

            if cursor:
                cursor.close()

            if db:
                db.close()

    return render_template(
        "farmer_login.html"
    )


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "You have been logged out.",
        "success"
    )

    return redirect(
        url_for("home")
    )


# =========================================================
# BUYER MARKETPLACE
# =========================================================

@app.route("/buyer")
def buyer():

    db = None
    cursor = None

    try:

        db = get_db_connection()

        cursor = db.cursor(
            dictionary=True
        )

        cursor.execute("""

            SELECT
                id,
                farmer_id,
                name,
                category,
                price,
                unit,
                farmer,
                location,
                image,
                created_at

            FROM products

            ORDER BY id DESC

        """)

        products = cursor.fetchall()

        return render_template(
            "buyer.html",
            products=products
        )

    except Error as e:

        print(
            "BUYER PRODUCTS ERROR:",
            e
        )

        return (
            "Database error: "
            + str(e)
        )

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()


# =========================================================
# FARMER DASHBOARD
# =========================================================

@app.route("/farmer")
def farmer():

    if "user_id" not in session:

        flash(
            "Please login as a farmer first.",
            "warning"
        )

        return redirect(
            url_for("farmer_login")
        )

    if session.get("role") != "farmer":

        flash(
            "Only farmers can access the Farmer Dashboard.",
            "danger"
        )

        return redirect(
            url_for("home")
        )

    farmer_id = session["user_id"]

    farmer_name = session.get(
        "user_name",
        ""
    )

    db = None
    cursor = None

    try:

        db = get_db_connection()

        cursor = db.cursor(
            dictionary=True
        )

        # =================================================
        # FARMER USER
        # =================================================

        cursor.execute("""

            SELECT
                id,
                name,
                email,
                role

            FROM users

            WHERE id = %s

            AND role = 'farmer'

        """, (
            farmer_id,
        ))

        user = cursor.fetchone()

        if not user:

            session.clear()

            flash(
                "Farmer account not found.",
                "danger"
            )

            return redirect(
                url_for("farmer_login")
            )

        # =================================================
        # FARMER PRODUCTS
        # =================================================

        cursor.execute("""

            SELECT
                id AS product_id,
                name AS product_name,
                category,
                price,
                unit,
                farmer,
                location,
                image,
                created_at

            FROM products

            WHERE farmer_id = %s

            OR farmer = %s

            ORDER BY id DESC

        """, (
            farmer_id,
            farmer_name
        ))

        products = cursor.fetchall()

        # =================================================
        # FARMER ORDERS
        # =================================================

        cursor.execute("""

            SELECT
                o.id AS order_id,
                o.user_id,
                o.customer_name,
                o.email,
                o.phone,
                o.address,
                o.total,
                o.status,
                o.delivery_status,
                o.tracking_location,
                o.tracking_message,
                o.created_at,

                oi.id AS order_item_id,
                oi.product_id,
                oi.product_name,
                oi.price,
                oi.unit,
                oi.quantity,
                oi.farmer,
                oi.location,
                oi.image

            FROM orders o

            INNER JOIN order_items oi
                ON o.id = oi.order_id

            WHERE

                oi.product_id IN
                (
                    SELECT id
                    FROM products
                    WHERE farmer_id = %s
                )

                OR oi.farmer = %s

            ORDER BY o.id DESC

        """, (
            farmer_id,
            farmer_name
        ))

        farmer_orders = cursor.fetchall()

        return render_template(
            "farmer.html",
            user=user,
            products=products,
            farmer_orders=farmer_orders
        )

    except Error as e:

        print(
            "FARMER DASHBOARD ERROR:",
            e
        )

        return (
            "Database error: "
            + str(e)
        )

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()


# =========================================================
# UPDATE FARMER ORDER STATUS
# =========================================================

@app.route(
    "/farmer/order/<int:order_id>/status",
    methods=["POST"]
)
def update_order_status(order_id):

    if "user_id" not in session:

        flash(
            "Please login as a farmer first.",
            "warning"
        )

        return redirect(
            url_for("farmer_login")
        )

    if session.get("role") != "farmer":

        flash(
            "Only farmers can update order status.",
            "danger"
        )

        return redirect(
            url_for("home")
        )

    new_status = request.form.get(
        "status",
        ""
    ).strip()

    allowed_statuses = [

        "Order Placed",

        "Confirmed",

        "Shipped",

        "Out for Delivery",

        "Delivered"
    ]

    if new_status not in allowed_statuses:

        flash(
            "Invalid order status.",
            "danger"
        )

        return redirect(
            url_for("farmer")
        )

    farmer_id = session["user_id"]

    farmer_name = session.get(
        "user_name",
        ""
    )

    db = None
    cursor = None

    try:

        db = get_db_connection()

        cursor = db.cursor(
            dictionary=True
        )

        # =================================================
        # VERIFY ORDER
        # =================================================

        cursor.execute("""

            SELECT
                o.id AS order_id,
                o.user_id,
                o.email,
                o.customer_name

            FROM orders o

            INNER JOIN order_items oi
                ON o.id = oi.order_id

            WHERE

                o.id = %s

                AND
                (
                    oi.product_id IN
                    (
                        SELECT id
                        FROM products
                        WHERE farmer_id = %s
                    )

                    OR oi.farmer = %s
                )

            LIMIT 1

        """, (
            order_id,
            farmer_id,
            farmer_name
        ))

        order = cursor.fetchone()

        if not order:

            flash(
                "Order not found or you cannot update this order.",
                "danger"
            )

            return redirect(
                url_for("farmer")
            )

        buyer_email = order.get(
            "email",
            ""
        )

        buyer_name = order.get(
            "customer_name",
            "Buyer"
        )

        # =================================================
        # UPDATE ORDER STATUS
        # =================================================

        cursor.execute("""

            UPDATE orders

            SET
                status = %s,
                delivery_status = %s

            WHERE id = %s

        """, (
            new_status,
            new_status,
            order_id
        ))

        db.commit()

        # =================================================
        # SEND STATUS EMAIL
        # =================================================

        if buyer_email:

            email_subject = (
                "Kisan Direct Marketplace - "
                "Order #"
                + str(order_id)
                + " Status Updated"
            )

            email_message = (

                "Hello "
                + str(buyer_name)
                + ",\n\n"

                "Your order status has been updated.\n\n"

                "Order ID: #"
                + str(order_id)
                + "\n"

                "New Status: "
                + new_status
                + "\n\n"

                "Thank you for using "
                "Kisan Direct Marketplace.\n\n"

                "Regards,\n"
                "Kisan Direct Marketplace"
            )

            send_email(
                buyer_email,
                email_subject,
                email_message
            )

        flash(
            "Order #"
            + str(order_id)
            + " status updated to "
            + new_status
            + ".",
            "success"
        )

        return redirect(
            url_for("farmer")
        )

    except Error as e:

        if db:
            db.rollback()

        print(
            "UPDATE ORDER STATUS ERROR:",
            e
        )

        flash(
            "Unable to update order status: "
            + str(e),
            "danger"
        )

        return redirect(
            url_for("farmer")
        )

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()


# =========================================================
# ADD PRODUCT
# =========================================================

@app.route(
    "/farmer/add-product",
    methods=["GET", "POST"]
)
@app.route(
    "/add-product",
    methods=["GET", "POST"]
)
def add_product():

    if "user_id" not in session:

        flash(
            "Please login as a farmer first.",
            "warning"
        )

        return redirect(
            url_for("farmer_login")
        )

    if session.get("role") != "farmer":

        flash(
            "Only farmers can add products.",
            "danger"
        )

        return redirect(
            url_for("home")
        )

    if request.method == "GET":

        return render_template(
            "add_product.html"
        )

    name = request.form.get(
        "name",
        ""
    ).strip()

    category = request.form.get(
        "category",
        ""
    ).strip()

    price = request.form.get(
        "price",
        ""
    ).strip()

    unit = request.form.get(
        "unit",
        ""
    ).strip()

    location = request.form.get(
        "location",
        ""
    ).strip()

    image = request.form.get(
        "image",
        ""
    ).strip()

    farmer_id = session["user_id"]

    farmer_name = session.get(
        "user_name",
        "Farmer"
    )

    if not name:

        flash(
            "Please enter product name.",
            "danger"
        )

        return render_template(
            "add_product.html"
        )

    if not category:

        flash(
            "Please select a category.",
            "danger"
        )

        return render_template(
            "add_product.html"
        )

    if not price:

        flash(
            "Please enter product price.",
            "danger"
        )

        return render_template(
            "add_product.html"
        )

    if not unit:

        flash(
            "Please select product unit.",
            "danger"
        )

        return render_template(
            "add_product.html"
        )

    try:

        price_value = float(price)

        if price_value < 0:

            flash(
                "Price cannot be negative.",
                "danger"
            )

            return render_template(
                "add_product.html"
            )

    except ValueError:

        flash(
            "Please enter a valid price.",
            "danger"
        )

        return render_template(
            "add_product.html"
        )

    db = None
    cursor = None

    try:

        db = get_db_connection()

        cursor = db.cursor()

        cursor.execute("""

            INSERT INTO products
            (
                farmer_id,
                name,
                category,
                price,
                unit,
                farmer,
                location,
                image
            )

            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )

        """, (
            farmer_id,
            name,
            category,
            price_value,
            unit,
            farmer_name,
            location,
            image
        ))

        db.commit()

        flash(
            "Product added successfully!",
            "success"
        )

        return redirect(
            url_for("farmer")
        )

    except Error as e:

        if db:
            db.rollback()

        print(
            "ADD PRODUCT ERROR:",
            e
        )

        flash(
            "Unable to add product: "
            + str(e),
            "danger"
        )

        return render_template(
            "add_product.html"
        )

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()


# =========================================================
# EDIT FARMER PRODUCT
# =========================================================

@app.route(
    "/edit-product/<int:product_id>",
    methods=["GET", "POST"]
)
def edit_product(product_id):

    if "user_id" not in session:

        flash(
            "Please login as a farmer first.",
            "warning"
        )

        return redirect(
            url_for("farmer_login")
        )

    if session.get("role") != "farmer":

        flash(
            "Only farmers can edit products.",
            "danger"
        )

        return redirect(
            url_for("home")
        )

    farmer_id = session["user_id"]

    db = None
    cursor = None

    try:

        db = get_db_connection()

        cursor = db.cursor(
            dictionary=True
        )

        # =================================================
        # GET PRODUCT
        # =================================================

        cursor.execute("""

            SELECT
                id,
                farmer_id,
                name,
                category,
                price,
                unit,
                location,
                image

            FROM products

            WHERE id = %s

            AND farmer_id = %s

        """, (
            product_id,
            farmer_id
        ))

        product = cursor.fetchone()

        if not product:

            flash(
                "Product not found or you cannot edit this product.",
                "danger"
            )

            return redirect(
                url_for("farmer")
            )

        # =================================================
        # SHOW EDIT FORM
        # =================================================

        if request.method == "GET":

            return render_template(
                "edit_product.html",
                product=product
            )

        # =================================================
        # GET FORM DATA
        # =================================================

        name = request.form.get(
            "name",
            ""
        ).strip()

        category = request.form.get(
            "category",
            ""
        ).strip()

        price = request.form.get(
            "price",
            ""
        ).strip()

        unit = request.form.get(
            "unit",
            ""
        ).strip()

        location = request.form.get(
            "location",
            ""
        ).strip()

        image = request.form.get(
            "image",
            ""
        ).strip()

        # =================================================
        # VALIDATION
        # =================================================

        if not name:

            flash(
                "Please enter product name.",
                "danger"
            )

            return render_template(
                "edit_product.html",
                product=product
            )

        if not category:

            flash(
                "Please select a category.",
                "danger"
            )

            return render_template(
                "edit_product.html",
                product=product
            )

        if not price:

            flash(
                "Please enter product price.",
                "danger"
            )

            return render_template(
                "edit_product.html",
                product=product
            )

        if not unit:

            flash(
                "Please select product unit.",
                "danger"
            )

            return render_template(
                "edit_product.html",
                product=product
            )

        try:

            price_value = float(price)

            if price_value < 0:

                flash(
                    "Price cannot be negative.",
                    "danger"
                )

                return render_template(
                    "edit_product.html",
                    product=product
                )

        except ValueError:

            flash(
                "Please enter a valid price.",
                "danger"
            )

            return render_template(
                "edit_product.html",
                product=product
            )

        # =================================================
        # UPDATE PRODUCT
        # =================================================

        cursor.execute("""

            UPDATE products

            SET
                name = %s,
                category = %s,
                price = %s,
                unit = %s,
                location = %s,
                image = %s

            WHERE id = %s

            AND farmer_id = %s

        """, (
            name,
            category,
            price_value,
            unit,
            location,
            image,
            product_id,
            farmer_id
        ))

        db.commit()

        flash(
            "Product updated successfully.",
            "success"
        )

        return redirect(
            url_for("farmer")
        )

    except Error as e:

        if db:
            db.rollback()

        print(
            "EDIT PRODUCT ERROR:",
            e
        )

        flash(
            "Unable to update product: "
            + str(e),
            "danger"
        )

        return redirect(
            url_for("farmer")
        )

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()


# =========================================================
# DELETE FARMER PRODUCT
# =========================================================

@app.route(
    "/farmer/delete-product/<int:product_id>",
    methods=["POST"]
)
def delete_product(product_id):

    if "user_id" not in session:

        flash(
            "Please login as a farmer first.",
            "warning"
        )

        return redirect(
            url_for("farmer_login")
        )

    if session.get("role") != "farmer":

        flash(
            "Only farmers can delete products.",
            "danger"
        )

        return redirect(
            url_for("home")
        )

    farmer_id = session["user_id"]

    db = None
    cursor = None

    try:

        db = get_db_connection()

        cursor = db.cursor()

        cursor.execute("""

            DELETE FROM products

            WHERE id = %s

            AND farmer_id = %s

        """, (
            product_id,
            farmer_id
        ))

        db.commit()

        if cursor.rowcount > 0:

            flash(
                "Product deleted successfully.",
                "success"
            )

        else:

            flash(
                "Product not found or you cannot delete it.",
                "danger"
            )

    except Error as e:

        if db:
            db.rollback()

        print(
            "DELETE PRODUCT ERROR:",
            e
        )

        flash(
            "Unable to delete product.",
            "danger"
        )

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()

    return redirect(
        url_for("farmer")
    )


# =========================================================
# ADD TO CART
# =========================================================

@app.route(
    "/add-to-cart",
    methods=["POST"]
)
def add_to_cart():

    if "user_id" not in session:

        flash(
            "Please login as a buyer first.",
            "warning"
        )

        return redirect(
            url_for("login")
        )

    if session.get("role") != "buyer":

        flash(
            "Only buyers can add products to cart.",
            "warning"
        )

        return redirect(
            url_for("buyer")
        )

    product_id = request.form.get(
        "product_id",
        ""
    ).strip()

    if not product_id:

        flash(
            "Product ID is missing.",
            "danger"
        )

        return redirect(
            url_for("buyer")
        )

    try:

        product_id = int(product_id)

    except ValueError:

        flash(
            "Invalid product ID.",
            "danger"
        )

        return redirect(
            url_for("buyer")
        )

    user_id = session["user_id"]

    db = None
    cursor = None

    try:

        db = get_db_connection()

        cursor = db.cursor(
            dictionary=True
        )

        cursor.execute("""

            SELECT
                id,
                name,
                price,
                unit,
                farmer,
                location,
                image

            FROM products

            WHERE id = %s

        """, (
            product_id,
        ))

        product = cursor.fetchone()

        if not product:

            flash(
                "Product not found.",
                "danger"
            )

            return redirect(
                url_for("buyer")
            )

        cursor.execute("""

            SELECT
                id,
                quantity

            FROM cart

            WHERE user_id = %s

            AND product_id = %s

        """, (
            user_id,
            product_id
        ))

        existing = cursor.fetchone()

        if existing:

            cursor.execute("""

                UPDATE cart

                SET quantity = quantity + 1

                WHERE id = %s

                AND user_id = %s

            """, (
                existing["id"],
                user_id
            ))

            message = (
                product["name"]
                + " quantity increased in cart."
            )

        else:

            cursor.execute("""

                INSERT INTO cart
                (
                    user_id,
                    product_id,
                    product_name,
                    price,
                    unit,
                    farmer,
                    location,
                    image,
                    quantity
                )

                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )

            """, (
                user_id,
                product["id"],
                product["name"],
                product["price"],
                product["unit"],
                product["farmer"],
                product["location"],
                product["image"],
                1
            ))

            message = (
                product["name"]
                + " added to cart successfully!"
            )

        db.commit()

        flash(
            message,
            "success"
        )

        return redirect(
            url_for("cart")
        )

    except Error as e:

        if db:
            db.rollback()

        print(
            "ADD TO CART ERROR:",
            e
        )

        flash(
            "Unable to add product to cart: "
            + str(e),
            "danger"
        )

        return redirect(
            url_for("buyer")
        )

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()


# =========================================================
# CART
# =========================================================

@app.route("/cart")
def cart():

    if "user_id" not in session:

        flash(
            "Please login to view your cart.",
            "warning"
        )

        return redirect(
            url_for("login")
        )

    if session.get("role") != "buyer":

        flash(
            "Only buyers can use the cart.",
            "warning"
        )

        return redirect(
            url_for("buyer")
        )

    user_id = session["user_id"]

    db = None
    cursor = None

    try:

        db = get_db_connection()

        cursor = db.cursor(
            dictionary=True
        )

        cursor.execute("""

            SELECT
                id,
                user_id,
                product_id,
                product_name,
                price,
                unit,
                farmer,
                location,
                image,
                quantity

            FROM cart

            WHERE user_id = %s

            ORDER BY id DESC

        """, (
            user_id,
        ))

        cart_items = cursor.fetchall()

        total_items = 0

        subtotal = 0.0

        for item in cart_items:

            quantity = int(
                item["quantity"] or 0
            )

            price = float(
                item["price"] or 0
            )

            total_items += quantity

            subtotal += (
                price * quantity
            )

        return render_template(
            "cart.html",
            cart=cart_items,
            cart_items=cart_items,
            total_items=total_items,
            subtotal=subtotal
        )

    except Error as e:

        print(
            "CART ERROR:",
            e
        )

        return (
            "Database error: "
            + str(e)
        )

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()


# =========================================================
# INCREASE CART
# =========================================================

@app.route(
    "/increase-cart/<int:cart_id>"
)
def increase_cart(cart_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    if session.get("role") != "buyer":

        return redirect(
            url_for("buyer")
        )

    db = None
    cursor = None

    try:

        db = get_db_connection()

        cursor = db.cursor()

        cursor.execute("""

            UPDATE cart

            SET quantity = quantity + 1

            WHERE id = %s

            AND user_id = %s

        """, (
            cart_id,
            session["user_id"]
        ))

        db.commit()

    except Error as e:

        if db:
            db.rollback()

        print(
            "INCREASE CART ERROR:",
            e
        )

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()

    return redirect(
        url_for("cart")
    )


# =========================================================
# DECREASE CART
# =========================================================

@app.route(
    "/decrease-cart/<int:cart_id>"
)
def decrease_cart(cart_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    if session.get("role") != "buyer":

        return redirect(
            url_for("buyer")
        )

    user_id = session["user_id"]

    db = None
    cursor = None

    try:

        db = get_db_connection()

        cursor = db.cursor(
            dictionary=True
        )

        cursor.execute("""

            SELECT quantity

            FROM cart

            WHERE id = %s

            AND user_id = %s

        """, (
            cart_id,
            user_id
        ))

        item = cursor.fetchone()

        if item:

            quantity = int(
                item["quantity"]
            )

            if quantity > 1:

                cursor.execute("""

                    UPDATE cart

                    SET quantity = quantity - 1

                    WHERE id = %s

                    AND user_id = %s

                """, (
                    cart_id,
                    user_id
                ))

            else:

                cursor.execute("""

                    DELETE FROM cart

                    WHERE id = %s

                    AND user_id = %s

                """, (
                    cart_id,
                    user_id
                ))

        db.commit()

    except Error as e:

        if db:
            db.rollback()

        print(
            "DECREASE CART ERROR:",
            e
        )

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()

    return redirect(
        url_for("cart")
    )


# =========================================================
# REMOVE FROM CART
# =========================================================

@app.route(
    "/remove-from-cart/<int:cart_id>"
)
def remove_from_cart(cart_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    if session.get("role") != "buyer":

        return redirect(
            url_for("buyer")
        )

    db = None
    cursor = None

    try:

        db = get_db_connection()

        cursor = db.cursor()

        cursor.execute("""

            DELETE FROM cart

            WHERE id = %s

            AND user_id = %s

        """, (
            cart_id,
            session["user_id"]
        ))

        db.commit()

        flash(
            "Product removed from cart.",
            "success"
        )

    except Error as e:

        if db:
            db.rollback()

        print(
            "REMOVE CART ERROR:",
            e
        )

        flash(
            "Unable to remove product.",
            "danger"
        )

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()

    return redirect(
        url_for("cart")
    )


# =========================================================
# CLEAR CART
# =========================================================

@app.route("/clear-cart")
def clear_cart():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    if session.get("role") != "buyer":

        return redirect(
            url_for("buyer")
        )

    db = None
    cursor = None

    try:

        db = get_db_connection()

        cursor = db.cursor()

        cursor.execute("""

            DELETE FROM cart

            WHERE user_id = %s

        """, (
            session["user_id"],
        ))

        db.commit()

        flash(
            "Cart cleared successfully.",
            "success"
        )

    except Error as e:

        if db:
            db.rollback()

        print(
            "CLEAR CART ERROR:",
            e
        )

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()

    return redirect(
        url_for("cart")
    )


# =========================================================
# CHECKOUT
# =========================================================

@app.route("/checkout")
def checkout():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    if session.get("role") != "buyer":

        return redirect(
            url_for("buyer")
        )

    user_id = session["user_id"]

    db = None
    cursor = None

    try:

        db = get_db_connection()

        cursor = db.cursor(
            dictionary=True
        )

        cursor.execute("""

            SELECT *

            FROM cart

            WHERE user_id = %s

            ORDER BY id DESC

        """, (
            user_id,
        ))

        cart_items = cursor.fetchall()

        if not cart_items:

            flash(
                "Your cart is empty.",
                "warning"
            )

            return redirect(
                url_for("cart")
            )

        total = 0.0

        for item in cart_items:

            total += (
                float(item["price"] or 0)
                *
                int(item["quantity"] or 0)
            )

        return render_template(
            "checkout.html",
            cart=cart_items,
            cart_items=cart_items,
            total=total
        )

    except Error as e:

        print(
            "CHECKOUT ERROR:",
            e
        )

        return (
            "Database error: "
            + str(e)
        )

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()


# =========================================================
# PLACE ORDER
# =========================================================

@app.route(
    "/place-order",
    methods=["POST"]
)
def place_order():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    if session.get("role") != "buyer":

        return redirect(
            url_for("buyer")
        )

    user_id = session["user_id"]

    # =====================================================
    # CHECKOUT DETAILS
    # =====================================================

    customer_name = request.form.get(
        "customer_name",
        ""
    ).strip()

    email = request.form.get(
        "email",
        ""
    ).strip()

    phone = request.form.get(
        "phone",
        ""
    ).strip()

    pincode = request.form.get(
        "pincode",
        ""
    ).strip()

    house = request.form.get(
        "house",
        ""
    ).strip()

    address = request.form.get(
        "address",
        ""
    ).strip()

    city = request.form.get(
        "city",
        ""
    ).strip()

    state = request.form.get(
        "state",
        ""
    ).strip()

    instructions = request.form.get(
        "instructions",
        ""
    ).strip()

    payment_method = request.form.get(
        "payment_method",
        "Cash on Delivery"
    ).strip()

    # =====================================================
    # VALIDATION
    # =====================================================

    if not customer_name:

        flash(
            "Please enter customer name.",
            "danger"
        )

        return redirect(
            url_for("checkout")
        )

    if not email:

        flash(
            "Please enter the email address where you want the confirmation email.",
            "danger"
        )

        return redirect(
            url_for("checkout")
        )

    if "@" not in email:

        flash(
            "Please enter a valid email address.",
            "danger"
        )

        return redirect(
            url_for("checkout")
        )

    if not phone:

        flash(
            "Please enter phone number.",
            "danger"
        )

        return redirect(
            url_for("checkout")
        )

    if not pincode:

        flash(
            "Please enter PIN code.",
            "danger"
        )

        return redirect(
            url_for("checkout")
        )

    if not house:

        flash(
            "Please enter house/building.",
            "danger"
        )

        return redirect(
            url_for("checkout")
        )

    if not address:

        flash(
            "Please enter complete delivery address.",
            "danger"
        )

        return redirect(
            url_for("checkout")
        )

    if not city:

        flash(
            "Please enter city/village.",
            "danger"
        )

        return redirect(
            url_for("checkout")
        )

    if not state:

        flash(
            "Please enter state.",
            "danger"
        )

        return redirect(
            url_for("checkout")
        )

    # =====================================================
    # COMPLETE ADDRESS
    # =====================================================

    complete_address = (
        house
        + ", "
        + address
        + ", "
        + city
        + ", "
        + state
        + " - "
        + pincode
    )

    if instructions:

        complete_address += (
            " | Delivery Instructions: "
            + instructions
        )

    db = None
    cursor = None

    try:

        db = get_db_connection()

        cursor = db.cursor(
            dictionary=True
        )

        # =================================================
        # GET CART
        # =================================================

        cursor.execute("""

            SELECT *

            FROM cart

            WHERE user_id = %s

            ORDER BY id ASC

        """, (
            user_id,
        ))

        cart_items = cursor.fetchall()

        if not cart_items:

            flash(
                "Your cart is empty.",
                "warning"
            )

            return redirect(
                url_for("cart")
            )

        # =================================================
        # CALCULATE TOTAL
        # =================================================

        total = 0.0

        for item in cart_items:

            total += (
                float(item["price"] or 0)
                *
                int(item["quantity"] or 0)
            )

        # =================================================
        # CREATE ORDER
        # =================================================

        cursor.execute("""

            INSERT INTO orders
            (
                user_id,
                customer_name,
                email,
                phone,
                address,
                total,
                status,
                delivery_status
            )

            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )

        """, (
            user_id,
            customer_name,
            email,
            phone,
            complete_address,
            total,
            "Order Placed",
            "Order Placed"
        ))

        order_id = cursor.lastrowid

        # =================================================
        # CREATE ORDER ITEMS
        # =================================================

        for item in cart_items:

            cursor.execute("""

                INSERT INTO order_items
                (
                    order_id,
                    product_id,
                    product_name,
                    price,
                    unit,
                    quantity,
                    farmer,
                    location,
                    image
                )

                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )

            """, (
                order_id,
                item["product_id"],
                item["product_name"],
                item["price"],
                item["unit"],
                item["quantity"],
                item["farmer"],
                item["location"],
                item["image"]
            ))

        # =================================================
        # CLEAR CART
        # =================================================

        cursor.execute("""

            DELETE FROM cart

            WHERE user_id = %s

        """, (
            user_id,
        ))

        db.commit()

        # =================================================
        # ORDER CONFIRMATION EMAIL
        # =================================================

        email_subject = (
            "Kisan Direct Marketplace - "
            "Order Confirmation #"
            + str(order_id)
        )

        email_message = (

            "Hello "
            + customer_name
            + ",\n\n"

            "Your order has been placed successfully!\n\n"

            "Order Details\n"
            "-------------------------\n"

            "Order ID: #"
            + str(order_id)
            + "\n"

            "Customer Name: "
            + customer_name
            + "\n"

            "Email: "
            + email
            + "\n"

            "Phone: "
            + phone
            + "\n"

            "Delivery Address: "
            + complete_address
            + "\n"

            "Payment Method: "
            + payment_method
            + "\n"

            "Total Amount: ₹"
            + str(round(total, 2))
            + "\n"

            "Status: Order Placed\n"

            "-------------------------\n\n"

            "You can check your order status "
            "from the Orders section of "
            "Kisan Direct Marketplace.\n\n"

            "Thank you for shopping with us!\n\n"

            "Regards,\n"
            "Kisan Direct Marketplace"
        )

        email_sent = send_email(
            email,
            email_subject,
            email_message
        )

        if email_sent:

            flash(
                "Order placed successfully! Confirmation email sent to "
                + email,
                "success"
            )

        else:

            flash(
                "Order placed successfully, but confirmation email could not be sent.",
                "warning"
            )

        return redirect(
            url_for("orders")
        )

    except Error as e:

        if db:
            db.rollback()

        print(
            "PLACE ORDER ERROR:",
            e
        )

        flash(
            "Database error: "
            + str(e),
            "danger"
        )

        return redirect(
            url_for("checkout")
        )

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()

# =========================================================
# BUYER ORDERS
# =========================================================

@app.route("/orders")
def orders():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    if session.get("role") != "buyer":

        return redirect(
            url_for("buyer")
        )

    db = None
    cursor = None

    try:

        db = get_db_connection()

        cursor = db.cursor(
            dictionary=True
        )

        # =================================================
        # SYNC OLD ORDERS
        # =================================================

        cursor.execute("""

            UPDATE orders

            SET delivery_status = status

            WHERE user_id = %s

            AND
            (
                delivery_status IS NULL

                OR delivery_status <> status
            )

        """, (
            session["user_id"],
        ))

        db.commit()

        # =================================================
        # GET BUYER ORDERS
        # =================================================

        cursor.execute("""

            SELECT *

            FROM orders

            WHERE user_id = %s

            ORDER BY id DESC

        """, (
            session["user_id"],
        ))

        orders_list = cursor.fetchall()

        # =================================================
        # GET ORDER ITEMS
        # =================================================

        for order in orders_list:

            cursor.execute("""

                SELECT
                    id,
                    order_id,
                    product_id,
                    product_name,
                    price,
                    unit,
                    quantity,
                    farmer,
                    location,
                    image

                FROM order_items

                WHERE order_id = %s

                ORDER BY id ASC

            """, (
                order["id"],
            ))

            order["items"] = cursor.fetchall()

        return render_template(
            "orders.html",
            orders=orders_list
        )

    except Error as e:

        print(
            "ORDERS ERROR:",
            e
        )

        return (
            "Database error: "
            + str(e)
        )

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()


# =========================================================
# CONTACT US
# =========================================================

@app.route(
    "/contact",
    methods=["GET", "POST"]
)
def contact():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip()

        message = request.form.get(
            "message",
            ""
        ).strip()

        # =================================================
        # VALIDATION
        # =================================================

        if not name:

            flash(
                "Please enter your name.",
                "danger"
            )

            return redirect(
                url_for("contact")
            )

        if not email:

            flash(
                "Please enter your email.",
                "danger"
            )

            return redirect(
                url_for("contact")
            )

        if "@" not in email:

            flash(
                "Please enter a valid email address.",
                "danger"
            )

            return redirect(
                url_for("contact")
            )

        if not message:

            flash(
                "Please enter your message.",
                "danger"
            )

            return redirect(
                url_for("contact")
            )

        # =================================================
        # CONTACT EMAIL
        # =================================================

        email_subject = (
            "Kisan Direct Marketplace - "
            "Contact Us Message"
        )

        email_message = (

            "New Contact Us Message\n"
            "========================\n\n"

            "Name: "
            + name
            + "\n"

            "Email: "
            + email
            + "\n\n"

            "Message:\n"
            + message
            + "\n\n"

            "========================\n"
            "Kisan Direct Marketplace"
        )

        # =================================================
        # SEND CONTACT MESSAGE
        # =================================================

        email_sent = send_email(
            EMAIL_ADDRESS,
            email_subject,
            email_message
        )

        if email_sent:

            flash(
                "Your message has been sent successfully!",
                "success"
            )

        else:

            flash(
                "Unable to send your message. Please try again.",
                "danger"
            )

        return redirect(
            url_for("contact")
        )

    return render_template(
        "contact.html"
    )


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=False,
        host="0.0.0.0",
        port=int(
            os.getenv(
                "PORT",
                "5000"
            )
        )
    )

