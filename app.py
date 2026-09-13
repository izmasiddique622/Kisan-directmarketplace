from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from mysql.connector import Error
import hashlib
import os

from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# ============================================================
# FLASK SECRET KEY
# ============================================================

app.secret_key = os.getenv(
    "FLASK_SECRET_KEY",
    "kisan-direct-marketplace-secret-key"
)


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT", "3306")),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
            ssl_ca=os.path.join(
                os.path.dirname(__file__),
                "ca.pem"
            ),
            ssl_verify_cert=True,
            ssl_verify_identity=True
        )

        return connection

    except Error as e:
        print("DATABASE CONNECTION ERROR:", e)
        return None


# ============================================================
# PASSWORD HASH
# ============================================================

def hash_password(password):
    return hashlib.sha256(
        password.encode("utf-8")
    ).hexdigest()


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():
    return render_template("index.html")


# ============================================================
# REGISTER
# ============================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get(
            "confirm_password",
            ""
        )
        role = request.form.get("role", "buyer").strip().lower()

        # ----------------------------
        # Basic validation
        # ----------------------------

        if not name:
            flash(
                "Please enter your name.",
                "danger"
            )
            return render_template("register.html")

        if not email:
            flash(
                "Please enter your email.",
                "danger"
            )
            return render_template("register.html")

        if not password:
            flash(
                "Please enter a password.",
                "danger"
            )
            return render_template("register.html")

        if password != confirm_password:
            flash(
                "Passwords do not match.",
                "danger"
            )
            return render_template("register.html")

        if len(password) < 6:
            flash(
                "Password must be at least 6 characters.",
                "danger"
            )
            return render_template("register.html")

        # Only buyer and farmer are allowed
        if role not in ["buyer", "farmer"]:
            role = "buyer"

        connection = get_db_connection()

        if connection is None:
            flash(
                "Database connection failed.",
                "danger"
            )
            return render_template("register.html")

        cursor = None

        try:

            cursor = connection.cursor()

            # ----------------------------
            # Check duplicate email
            # ----------------------------

            cursor.execute(
                """
                SELECT id
                FROM users
                WHERE email = %s
                """,
                (email,)
            )

            existing_user = cursor.fetchone()

            if existing_user:
                flash(
                    "Email already registered. Please login.",
                    "warning"
                )

                return redirect(
                    url_for("login")
                )

            # ----------------------------
            # Hash password
            # ----------------------------

            hashed_password = hash_password(password)

            # ----------------------------
            # Insert new user
            # ----------------------------

            cursor.execute(
                """
                INSERT INTO users
                (name, email, password, role)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    name,
                    email,
                    hashed_password,
                    role
                )
            )

            connection.commit()

            flash(
                "Registration successful! Please login.",
                "success"
            )

            return redirect(
                url_for("login")
            )

        except Error as e:

            print(
                "REGISTER ERROR:",
                e
            )

            connection.rollback()

            flash(
                "Registration failed. Please try again.",
                "danger"
            )

            return render_template(
                "register.html"
            )

        finally:

            if cursor:
                cursor.close()

            connection.close()

    return render_template(
        "register.html"
    )


# ============================================================
# LOGIN
# ============================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

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

        connection = get_db_connection()

        if connection is None:

            flash(
                "Database connection failed.",
                "danger"
            )

            return render_template(
                "login.html"
            )

        cursor = None

        try:

            cursor = connection.cursor(
                dictionary=True
            )

            hashed_password = hash_password(
                password
            )

            cursor.execute(
                """
                SELECT *
                FROM users
                WHERE email = %s
                AND password = %s
                """,
                (
                    email,
                    hashed_password
                )
            )

            user = cursor.fetchone()

            if user:

                session["user_id"] = user["id"]
                session["user_name"] = user["name"]
                session["user_email"] = user["email"]
                session["role"] = user["role"]

                if user["role"] == "farmer":

                    return redirect(
                        url_for("farmer")
                    )

                return redirect(
                    url_for("buyer")
                )

            flash(
                "Invalid email or password.",
                "danger"
            )

        except Error as e:

            print(
                "LOGIN ERROR:",
                e
            )

            flash(
                "Login failed. Please try again.",
                "danger"
            )

        finally:

            if cursor:
                cursor.close()

            connection.close()

    return render_template(
        "login.html"
    )


# ============================================================
# FARMER LOGIN
# ============================================================

@app.route(
    "/farmer-login",
    methods=["GET", "POST"]
)
def farmer_login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

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
                "farmer_login.html"
            )

        connection = get_db_connection()

        if connection is None:

            flash(
                "Database connection failed.",
                "danger"
            )

            return render_template(
                "farmer_login.html"
            )

        cursor = None

        try:

            cursor = connection.cursor(
                dictionary=True
            )

            hashed_password = hash_password(
                password
            )

            cursor.execute(
                """
                SELECT *
                FROM users
                WHERE email = %s
                AND password = %s
                AND role = 'farmer'
                """,
                (
                    email,
                    hashed_password
                )
            )

            user = cursor.fetchone()

            if user:

                session["user_id"] = user["id"]
                session["user_name"] = user["name"]
                session["user_email"] = user["email"]
                session["role"] = user["role"]

                return redirect(
                    url_for("farmer")
                )

            flash(
                "Invalid farmer email or password.",
                "danger"
            )

        except Error as e:

            print(
                "FARMER LOGIN ERROR:",
                e
            )

            flash(
                "Farmer login failed.",
                "danger"
            )

        finally:

            if cursor:
                cursor.close()

            connection.close()

    return render_template(
        "farmer_login.html"
    )


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "You have been logged out.",
        "success"
    )

    return redirect(
        url_for("login")
    )


# ============================================================
# BUYER DASHBOARD
# ============================================================

@app.route("/buyer")
def buyer():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    connection = get_db_connection()

    if connection is None:

        flash(
            "Database connection failed.",
            "danger"
        )

        return render_template(
            "buyer.html",
            products=[]
        )

    cursor = None
    products = []

    try:

        cursor = connection.cursor(
            dictionary=True
        )

        cursor.execute(
            """
            SELECT *
            FROM products
            ORDER BY id DESC
            """
        )

        products = cursor.fetchall()

    except Error as e:

        print(
            "BUYER ERROR:",
            e
        )

        flash(
            "Unable to load products.",
            "danger"
        )

    finally:

        if cursor:
            cursor.close()

        connection.close()

    return render_template(
        "buyer.html",
        products=products
    )


# ============================================================
# FARMER DASHBOARD
# ============================================================

@app.route("/farmer")
def farmer():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    if session.get("role") != "farmer":

        return redirect(
            url_for("buyer")
        )

    farmer_id = session["user_id"]

    connection = get_db_connection()

    if connection is None:

        flash(
            "Database connection failed.",
            "danger"
        )

        return render_template(
            "farmer.html",
            products=[],
            orders=[],
            farmer_orders=[]
        )

    cursor = None

    products = []
    orders_list = []

    try:

        cursor = connection.cursor(
            dictionary=True
        )

        # ----------------------------
        # Farmer products
        # ----------------------------

        cursor.execute(
            """
            SELECT *
            FROM products
            WHERE farmer_id = %s
            ORDER BY id DESC
            """,
            (farmer_id,)
        )

        products = cursor.fetchall()

        # ----------------------------
        # Farmer orders
        # ----------------------------

        cursor.execute(
            """
            SELECT
                o.id AS order_id,
                o.user_id,
                o.customer_name,
                COALESCE(o.email, '') AS email,
                o.phone,
                o.address,
                o.total,
                o.status,
                o.created_at,
                COALESCE(o.payment_method, '') AS payment_method,
                COALESCE(o.payment_status, '') AS payment_status,
                COALESCE(o.transaction_id, '') AS transaction_id,

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

            WHERE oi.farmer = %s

            ORDER BY
                o.id DESC,
                oi.id ASC
            """,
            (session["user_name"],)
        )

        orders_list = cursor.fetchall()

    except Error as e:

        print(
            "FARMER DASHBOARD ERROR:",
            e
        )

        flash(
            "Unable to load farmer data.",
            "danger"
        )

    finally:

        if cursor:
            cursor.close()

        connection.close()

    return render_template(
        "farmer.html",
        products=products,
        orders=orders_list,
        farmer_orders=orders_list
    )


# ============================================================
# ADD PRODUCT
# ============================================================

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

        return redirect(
            url_for("login")
        )

    if session.get("role") != "farmer":

        return redirect(
            url_for("buyer")
        )

    if request.method == "POST":

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
            "Not Specified"
        ).strip()

        image = request.form.get(
            "image",
            ""
        ).strip()

        if not name or not category or not price or not unit:

            flash(
                "Please fill all required fields.",
                "danger"
            )

            return render_template(
                "add_product.html"
            )

        try:

            price = float(price)

            if price <= 0:

                flash(
                    "Price must be greater than 0.",
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

        connection = get_db_connection()

        if connection is None:

            flash(
                "Database connection failed.",
                "danger"
            )

            return render_template(
                "add_product.html"
            )

        cursor = None

        try:

            cursor = connection.cursor()

            cursor.execute(
                """
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
                """,
                (
                    session["user_id"],
                    name,
                    category,
                    price,
                    unit,
                    session["user_name"],
                    location,
                    image
                )
            )

            connection.commit()

            flash(
                "Product added successfully!",
                "success"
            )

            return redirect(
                url_for("farmer")
            )

        except Error as e:

            print(
                "ADD PRODUCT ERROR:",
                e
            )

            connection.rollback()

            flash(
                "Unable to add product.",
                "danger"
            )

        finally:

            if cursor:
                cursor.close()

            connection.close()

    return render_template(
        "add_product.html"
    )


# ============================================================
# EDIT PRODUCT
# ============================================================

@app.route(
    "/edit-product/<int:product_id>",
    methods=["GET", "POST"]
)
def edit_product(product_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    if session.get("role") != "farmer":

        return redirect(
            url_for("buyer")
        )

    connection = get_db_connection()

    if connection is None:

        flash(
            "Database connection failed.",
            "danger"
        )

        return redirect(
            url_for("farmer")
        )

    cursor = None

    try:

        cursor = connection.cursor(
            dictionary=True
        )

        # ----------------------------
        # Check product belongs to farmer
        # ----------------------------

        cursor.execute(
            """
            SELECT *
            FROM products
            WHERE id = %s
            AND farmer_id = %s
            """,
            (
                product_id,
                session["user_id"]
            )
        )

        product = cursor.fetchone()

        if not product:

            flash(
                "Product not found.",
                "danger"
            )

            return redirect(
                url_for("farmer")
            )

        # ----------------------------
        # Update product
        # ----------------------------

        if request.method == "POST":

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

            try:

                price = float(price)

            except ValueError:

                flash(
                    "Please enter a valid price.",
                    "danger"
                )

                return render_template(
                    "edit-product.html",
                    product=product
                )

            cursor.execute(
                """
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
                """,
                (
                    name,
                    category,
                    price,
                    unit,
                    location,
                    image,
                    product_id,
                    session["user_id"]
                )
            )

            connection.commit()

            flash(
                "Product updated successfully!",
                "success"
            )

            return redirect(
                url_for("farmer")
            )

    except Error as e:

        print(
            "EDIT PRODUCT ERROR:",
            e
        )

        flash(
            "Unable to edit product.",
            "danger"
        )

        return redirect(
            url_for("farmer")
        )

    finally:

        if cursor:
            cursor.close()

        connection.close()

    return render_template(
        "edit-product.html",
        product=product
    )


# ============================================================
# DELETE PRODUCT
# ============================================================

@app.route(
    "/farmer/delete-product/<int:product_id>",
    methods=["POST", "GET"]
)
def delete_product(product_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    if session.get("role") != "farmer":

        return redirect(
            url_for("buyer")
        )

    connection = get_db_connection()

    if connection is None:

        flash(
            "Database connection failed.",
            "danger"
        )

        return redirect(
            url_for("farmer")
        )

    cursor = None

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            DELETE FROM products
            WHERE id = %s
            AND farmer_id = %s
            """,
            (
                product_id,
                session["user_id"]
            )
        )

        connection.commit()

        flash(
            "Product deleted successfully!",
            "success"
        )

    except Error as e:

        print(
            "DELETE PRODUCT ERROR:",
            e
        )

        connection.rollback()

        flash(
            "Unable to delete product.",
            "danger"
        )

    finally:

        if cursor:
            cursor.close()

        connection.close()

    return redirect(
        url_for("farmer")
    )


# ============================================================
# ADD TO CART
# ============================================================

@app.route(
    "/add-to-cart",
    methods=["POST"]
)
def add_to_cart():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    product_id = request.form.get(
        "product_id"
    )

    quantity = request.form.get(
        "quantity",
        "1"
    )

    try:

        quantity = int(quantity)

        if quantity < 1:
            quantity = 1

    except ValueError:

        quantity = 1

    connection = get_db_connection()

    if connection is None:

        flash(
            "Database connection failed.",
            "danger"
        )

        return redirect(
            url_for("buyer")
        )

    cursor = None

    try:

        cursor = connection.cursor(
            dictionary=True
        )

        cursor.execute(
            """
            SELECT *
            FROM products
            WHERE id = %s
            """,
            (product_id,)
        )

        product = cursor.fetchone()

        if not product:

            flash(
                "Product not found.",
                "danger"
            )

            return redirect(
                url_for("buyer")
            )

        # ----------------------------
        # Check existing cart item
        # ----------------------------

        cursor.execute(
            """
            SELECT id, quantity
            FROM cart
            WHERE user_id = %s
            AND product_id = %s
            """,
            (
                session["user_id"],
                product_id
            )
        )

        existing = cursor.fetchone()

        if existing:

            cursor.execute(
                """
                UPDATE cart
                SET quantity = quantity + %s
                WHERE id = %s
                """,
                (
                    quantity,
                    existing["id"]
                )
            )

        else:

            cursor.execute(
                """
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
                """,
                (
                    session["user_id"],
                    product["id"],
                    product["name"],
                    product["price"],
                    product["unit"],
                    product["farmer"],
                    product["location"],
                    product["image"],
                    quantity
                )
            )

        connection.commit()

        flash(
            "Product added to cart!",
            "success"
        )

    except Error as e:

        print(
            "ADD TO CART ERROR:",
            e
        )

        connection.rollback()

        flash(
            "Unable to add product to cart.",
            "danger"
        )

    finally:

        if cursor:
            cursor.close()

        connection.close()

    return redirect(
        url_for("cart")
    )


# ============================================================
# CART
# ============================================================

@app.route("/cart")
def cart():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    connection = get_db_connection()

    if connection is None:

        return render_template(
            "cart.html",
            cart_items=[],
            total_items=0,
            subtotal=0,
            total=0
        )

    cursor = None
    cart_items = []

    total_items = 0
    subtotal = 0

    try:

        cursor = connection.cursor(
            dictionary=True
        )

        cursor.execute(
            """
            SELECT *
            FROM cart
            WHERE user_id = %s
            ORDER BY id DESC
            """,
            (session["user_id"],)
        )

        cart_items = cursor.fetchall()

        for item in cart_items:

            item_total = (
                float(item["price"])
                * int(item["quantity"])
            )

            item["item_total"] = item_total

            total_items += int(
                item["quantity"]
            )

            subtotal += item_total

    except Error as e:

        print(
            "CART ERROR:",
            e
        )

        flash(
            "Unable to load cart.",
            "danger"
        )

    finally:

        if cursor:
            cursor.close()

        connection.close()

    return render_template(
        "cart.html",
        cart_items=cart_items,
        total_items=total_items,
        subtotal=subtotal,
        total=subtotal
    )


# ============================================================
# INCREASE CART
# ============================================================

@app.route(
    "/increase-cart/<int:cart_id>"
)
def increase_cart(cart_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    connection = get_db_connection()

    if connection is None:

        return redirect(
            url_for("cart")
        )

    cursor = None

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE cart
            SET quantity = quantity + 1
            WHERE id = %s
            AND user_id = %s
            """,
            (
                cart_id,
                session["user_id"]
            )
        )

        connection.commit()

    except Error as e:

        print(
            "INCREASE CART ERROR:",
            e
        )

        connection.rollback()

    finally:

        if cursor:
            cursor.close()

        connection.close()

    return redirect(
        url_for("cart")
    )


# ============================================================
# DECREASE CART
# ============================================================

@app.route(
    "/decrease-cart/<int:cart_id>"
)
def decrease_cart(cart_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    connection = get_db_connection()

    if connection is None:

        return redirect(
            url_for("cart")
        )

    cursor = None

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE cart
            SET quantity = quantity - 1
            WHERE id = %s
            AND user_id = %s
            AND quantity > 1
            """,
            (
                cart_id,
                session["user_id"]
            )
        )

        connection.commit()

    except Error as e:

        print(
            "DECREASE CART ERROR:",
            e
        )

        connection.rollback()

    finally:

        if cursor:
            cursor.close()

        connection.close()

    return redirect(
        url_for("cart")
    )


# ============================================================
# REMOVE FROM CART
# ============================================================

@app.route(
    "/remove-from-cart/<int:cart_id>"
)
def remove_from_cart(cart_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    connection = get_db_connection()

    if connection is None:

        return redirect(
            url_for("cart")
        )

    cursor = None

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            DELETE FROM cart
            WHERE id = %s
            AND user_id = %s
            """,
            (
                cart_id,
                session["user_id"]
            )
        )

        connection.commit()

    except Error as e:

        print(
            "REMOVE CART ERROR:",
            e
        )

        connection.rollback()

    finally:

        if cursor:
            cursor.close()

        connection.close()

    return redirect(
        url_for("cart")
    )


# ============================================================
# CLEAR CART
# ============================================================

@app.route("/clear-cart")
def clear_cart():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    connection = get_db_connection()

    if connection is None:

        return redirect(
            url_for("cart")
        )

    cursor = None

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            DELETE FROM cart
            WHERE user_id = %s
            """,
            (session["user_id"],)
        )

        connection.commit()

        flash(
            "Cart cleared successfully.",
            "success"
        )

    except Error as e:

        print(
            "CLEAR CART ERROR:",
            e
        )

        connection.rollback()

    finally:

        if cursor:
            cursor.close()

        connection.close()

    return redirect(
        url_for("cart")
    )


# ============================================================
# CHECKOUT
# ============================================================

@app.route("/checkout")
def checkout():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    connection = get_db_connection()

    if connection is None:

        flash(
            "Database connection failed.",
            "danger"
        )

        return redirect(
            url_for("cart")
        )

    cursor = None
    cart_items = []
    total = 0

    try:

        cursor = connection.cursor(
            dictionary=True
        )

        cursor.execute(
            """
            SELECT *
            FROM cart
            WHERE user_id = %s
            ORDER BY id DESC
            """,
            (session["user_id"],)
        )

        cart_items = cursor.fetchall()

        for item in cart_items:

            total += (
                float(item["price"])
                * int(item["quantity"])
            )

    except Error as e:

        print(
            "CHECKOUT ERROR:",
            e
        )

        flash(
            "Unable to load checkout.",
            "danger"
        )

        return redirect(
            url_for("cart")
        )

    finally:

        if cursor:
            cursor.close()

        connection.close()

    if not cart_items:

        flash(
            "Your cart is empty.",
            "warning"
        )

        return redirect(
            url_for("buyer")
        )

    return render_template(
        "checkout.html",
        cart_items=cart_items,
        total=total
    )


# ============================================================
# PLACE ORDER
# ============================================================

@app.route(
    "/place-order",
    methods=["POST"]
)
def place_order():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    customer_name = request.form.get(
        "customer_name",
        session.get("user_name", "")
    ).strip()

    phone = request.form.get(
        "phone",
        ""
    ).strip()

    address = request.form.get(
        "address",
        ""
    ).strip()

    payment_method = request.form.get(
        "payment_method",
        "COD"
    ).strip()

    transaction_id = request.form.get(
        "transaction_id",
        ""
    ).strip()

    connection = get_db_connection()

    if connection is None:

        flash(
            "Database connection failed.",
            "danger"
        )

        return redirect(
            url_for("checkout")
        )

    cursor = None

    try:

        cursor = connection.cursor(
            dictionary=True
        )

        # ----------------------------
        # Get cart
        # ----------------------------

        cursor.execute(
            """
            SELECT *
            FROM cart
            WHERE user_id = %s
            """,
            (session["user_id"],)
        )

        cart_items = cursor.fetchall()

        if not cart_items:

            flash(
                "Your cart is empty.",
                "warning"
            )

            return redirect(
                url_for("buyer")
            )

        # ----------------------------
        # Calculate total
        # ----------------------------

        total = 0

        for item in cart_items:

            total += (
                float(item["price"])
                * int(item["quantity"])
            )

        # ----------------------------
        # Insert order
        # ----------------------------

        cursor.execute(
            """
            INSERT INTO orders
            (
                user_id,
                customer_name,
                email,
                phone,
                address,
                total,
                status,
                payment_method,
                payment_status,
                transaction_id
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
                %s,
                %s
            )
            """,
            (
                session["user_id"],
                customer_name,
                session.get("user_email", ""),
                phone,
                address,
                total,
                "Pending",
                payment_method,
                "Pending",
                transaction_id
            )
        )

        order_id = cursor.lastrowid

        # ----------------------------
        # Insert order items
        # ----------------------------

        for item in cart_items:

            cursor.execute(
                """
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
                """,
                (
                    order_id,
                    item["product_id"],
                    item["product_name"],
                    item["price"],
                    item["unit"],
                    item["quantity"],
                    item["farmer"],
                    item["location"],
                    item["image"]
                )
            )

        # ----------------------------
        # Clear cart
        # ----------------------------

        cursor.execute(
            """
            DELETE FROM cart
            WHERE user_id = %s
            """,
            (session["user_id"],)
        )

        connection.commit()

        flash(
            "Order placed successfully!",
            "success"
        )

        return redirect(
            url_for("orders")
        )

    except Error as e:

        print(
            "PLACE ORDER ERROR:",
            e
        )

        connection.rollback()

        flash(
            "Unable to place order.",
            "danger"
        )

        return redirect(
            url_for("checkout")
        )

    finally:

        if cursor:
            cursor.close()

        connection.close()


# ============================================================
# ORDERS
# ============================================================

@app.route("/orders")
def orders():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    connection = get_db_connection()

    if connection is None:

        return render_template(
            "orders.html",
            orders=[]
        )

    cursor = None
    orders_list = []

    try:

        cursor = connection.cursor(
            dictionary=True
        )

        cursor.execute(
            """
            SELECT *
            FROM orders
            WHERE user_id = %s
            ORDER BY id DESC
            """,
            (session["user_id"],)
        )

        orders_list = cursor.fetchall()

        # ----------------------------
        # Get items for each order
        # ----------------------------

        for order in orders_list:

            cursor.execute(
                """
                SELECT *
                FROM order_items
                WHERE order_id = %s
                ORDER BY id ASC
                """,
                (order["id"],)
            )

            order["items"] = cursor.fetchall()

    except Error as e:

        print(
            "ORDERS ERROR:",
            e
        )

        flash(
            "Unable to load orders.",
            "danger"
        )

    finally:

        if cursor:
            cursor.close()

        connection.close()

    return render_template(
        "orders.html",
        orders=orders_list
    )


# ============================================================
# FARMER UPDATE ORDER STATUS
# ============================================================

@app.route(
    "/farmer/order/<int:order_id>/status",
    methods=["POST"]
)
def update_order_status(order_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    if session.get("role") != "farmer":

        return redirect(
            url_for("buyer")
        )

    status = request.form.get(
        "status",
        "Pending"
    ).strip()

    connection = get_db_connection()

    if connection is None:

        flash(
            "Database connection failed.",
            "danger"
        )

        return redirect(
            url_for("farmer")
        )

    cursor = None

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE orders
            SET status = %s
            WHERE id = %s
            AND id IN
            (
                SELECT order_id
                FROM order_items
                WHERE farmer = %s
            )
            """,
            (
                status,
                order_id,
                session["user_name"]
            )
        )

        connection.commit()

        flash(
            "Order status updated successfully!",
            "success"
        )

    except Error as e:

        print(
            "UPDATE ORDER STATUS ERROR:",
            e
        )

        connection.rollback()

        flash(
            "Unable to update order status.",
            "danger"
        )

    finally:

        if cursor:
            cursor.close()

        connection.close()

    return redirect(
        url_for("farmer")
    )


# ============================================================
# CONTACT
# ============================================================

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

        print(
            "CONTACT MESSAGE:",
            name,
            email,
            message
        )

        flash(
            "Thank you! Your message has been received.",
            "success"
        )

        return redirect(
            url_for("home")
        )

    return render_template(
        "contact.html"
    )


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":

    port = int(
        os.getenv(
            "PORT",
            "5000"
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=True
    )
