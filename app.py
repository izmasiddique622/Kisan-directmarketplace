from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from mysql.connector import Error
import hashlib
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv(
    "FLASK_SECRET_KEY",
    "development-only-change-this-key"
)


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
    return hashlib.sha256(password.encode()).hexdigest()


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():
    return render_template("index.html")


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Please enter email and password.", "danger")
            return redirect(url_for("login"))

        conn = None
        cursor = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            password_hash = hash_password(password)

            cursor.execute(
                """
                SELECT *
                FROM users
                WHERE email = %s AND password = %s
                """,
                (email, password_hash)
            )

            user = cursor.fetchone()

            if user:

                session["user_id"] = user["id"]
                session["user_name"] = user.get("name", "")
                session["user_email"] = user.get("email", "")
                session["role"] = user.get("role", "buyer")

                role = user.get("role", "buyer")

                flash("Login successful!", "success")

                if role == "farmer":
                    return redirect(url_for("farmer"))

                return redirect(url_for("buyer"))

            flash("Invalid email or password.", "danger")

        except Error as e:
            print("LOGIN ERROR:", e)
            flash("Unable to connect to database.", "danger")

        finally:
            if cursor:
                cursor.close()

            if conn:
                conn.close()

        return redirect(url_for("login"))

    return render_template("login.html")


# =========================================================
# FARMER LOGIN
# =========================================================

@app.route("/farmer-login", methods=["GET", "POST"])
def farmer_login():

    if request.method == "POST":

        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Please enter email and password.", "danger")
            return redirect(url_for("farmer_login"))

        conn = None
        cursor = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            password_hash = hash_password(password)

            cursor.execute(
                """
                SELECT *
                FROM users
                WHERE email = %s
                AND password = %s
                AND role = 'farmer'
                """,
                (email, password_hash)
            )

            user = cursor.fetchone()

            if user:

                session["user_id"] = user["id"]
                session["user_name"] = user.get("name", "")
                session["user_email"] = user.get("email", "")
                session["role"] = "farmer"

                flash("Farmer login successful!", "success")

                return redirect(url_for("farmer"))

            flash("Invalid farmer email or password.", "danger")

        except Error as e:
            print("FARMER LOGIN ERROR:", e)
            flash("Unable to connect to database.", "danger")

        finally:
            if cursor:
                cursor.close()

            if conn:
                conn.close()

        return redirect(url_for("farmer_login"))

    return render_template("farmer-login.html")


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    flash("You have been logged out.", "success")

    return redirect(url_for("home"))


# =========================================================
# BUYER DASHBOARD
# =========================================================

@app.route("/buyer")
def buyer():

    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("login"))

    conn = None
    cursor = None

    products = []

    try:

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT *
            FROM products
            ORDER BY id DESC
            """
        )

        products = cursor.fetchall()

    except Error as e:

        print("BUYER ERROR:", e)

        flash("Unable to load products.", "danger")

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()

    return render_template(
        "buyer.html",
        products=products
    )


# =========================================================
# FARMER DASHBOARD
# =========================================================

@app.route("/farmer")
def farmer():

    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("login"))

    if session.get("role") != "farmer":
        flash("Farmer access required.", "danger")
        return redirect(url_for("buyer"))

    conn = None
    cursor = None

    products = []
    orders_list = []

    try:

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Farmer's products
        cursor.execute(
            """
            SELECT *
            FROM products
            WHERE farmer_id = %s
            ORDER BY id DESC
            """,
            (session["user_id"],)
        )

        products = cursor.fetchall()

        # Farmer's orders
        cursor.execute(
            """
            SELECT DISTINCT
                o.id,
                o.user_id,
                o.customer_name,
                o.phone,
                o.address,
                o.total,
                o.status,
                o.created_at
            FROM orders o
            INNER JOIN order_items oi
                ON o.id = oi.order_id
            WHERE oi.farmer = %s
            ORDER BY o.id DESC
            """,
            (session.get("user_name", ""),)
        )

        orders_list = cursor.fetchall()

    except Error as e:

        print("FARMER DASHBOARD ERROR:", e)

        flash("Unable to load farmer dashboard.", "danger")

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()

    return render_template(
        "farmer.html",
        products=products,
        orders=orders_list
    )


# =========================================================
# ADD PRODUCT
# =========================================================

@app.route("/farmer/add-product", methods=["GET", "POST"])
@app.route("/add-product", methods=["GET", "POST"])
def add_product():

    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("login"))

    if session.get("role") != "farmer":
        flash("Only farmers can add products.", "danger")
        return redirect(url_for("buyer"))

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        category = request.form.get("category", "").strip()
        price = request.form.get("price", "0").strip()
        unit = request.form.get("unit", "").strip()
        location = request.form.get("location", "").strip()
        image = request.form.get("image", "").strip()

        farmer_name = session.get("user_name", "")

        if not name or not category or not price or not unit:
            flash("Please fill all required product details.", "danger")
            return redirect(url_for("add_product"))

        conn = None
        cursor = None

        try:

            conn = get_db_connection()
            cursor = conn.cursor()

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
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    session["user_id"],
                    name,
                    category,
                    price,
                    unit,
                    farmer_name,
                    location,
                    image
                )
            )

            conn.commit()

            flash("Product added successfully!", "success")

            return redirect(url_for("farmer"))

        except Error as e:

            print("ADD PRODUCT ERROR:", e)

            if conn:
                conn.rollback()

            flash("Unable to add product.", "danger")

        finally:

            if cursor:
                cursor.close()

            if conn:
                conn.close()

    return render_template("add-product.html")


# =========================================================
# EDIT PRODUCT
# =========================================================

@app.route("/edit-product/<int:product_id>", methods=["GET", "POST"])
def edit_product(product_id):

    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("login"))

    if session.get("role") != "farmer":
        flash("Only farmers can edit products.", "danger")
        return redirect(url_for("buyer"))

    conn = None
    cursor = None

    try:

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT *
            FROM products
            WHERE id = %s
            AND farmer_id = %s
            """,
            (product_id, session["user_id"])
        )

        product = cursor.fetchone()

        if not product:
            flash("Product not found.", "danger")
            return redirect(url_for("farmer"))

        if request.method == "POST":

            name = request.form.get("name", "").strip()
            category = request.form.get("category", "").strip()
            price = request.form.get("price", "0").strip()
            unit = request.form.get("unit", "").strip()
            location = request.form.get("location", "").strip()
            image = request.form.get("image", "").strip()

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

            conn.commit()

            flash("Product updated successfully!", "success")

            return redirect(url_for("farmer"))

    except Error as e:

        print("EDIT PRODUCT ERROR:", e)

        if conn:
            conn.rollback()

        flash("Unable to update product.", "danger")

        return redirect(url_for("farmer"))

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()

    return render_template(
        "edit-product.html",
        product=product
    )


# =========================================================
# DELETE PRODUCT
# =========================================================

@app.route("/farmer/delete-product/<int:product_id>")
def delete_product(product_id):

    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("login"))

    if session.get("role") != "farmer":
        flash("Only farmers can delete products.", "danger")
        return redirect(url_for("buyer"))

    conn = None
    cursor = None

    try:

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            DELETE FROM products
            WHERE id = %s
            AND farmer_id = %s
            """,
            (product_id, session["user_id"])
        )

        conn.commit()

        flash("Product deleted successfully!", "success")

    except Error as e:

        print("DELETE PRODUCT ERROR:", e)

        if conn:
            conn.rollback()

        flash("Unable to delete product.", "danger")

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()

    return redirect(url_for("farmer"))


# =========================================================
# ADD TO CART
# =========================================================

@app.route("/add-to-cart", methods=["POST"])
def add_to_cart():

    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("login"))

    product_id = request.form.get("product_id")

    if not product_id:
        flash("Product not selected.", "danger")
        return redirect(url_for("buyer"))

    conn = None
    cursor = None

    try:

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

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
            flash("Product not found.", "danger")
            return redirect(url_for("buyer"))

        cursor.execute(
            """
            SELECT *
            FROM cart
            WHERE user_id = %s
            AND product_id = %s
            """,
            (
                session["user_id"],
                product_id
            )
        )

        existing_item = cursor.fetchone()

        if existing_item:

            cursor.execute(
                """
                UPDATE cart
                SET quantity = quantity + 1
                WHERE id = %s
                """,
                (existing_item["id"],)
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
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    session["user_id"],
                    product["id"],
                    product["name"],
                    product["price"],
                    product["unit"],
                    product.get("farmer", ""),
                    product.get("location", ""),
                    product.get("image", ""),
                    1
                )
            )

        conn.commit()

        flash("Product added to cart!", "success")

    except Error as e:

        print("ADD TO CART ERROR:", e)

        if conn:
            conn.rollback()

        flash("Unable to add product to cart.", "danger")

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()

    return redirect(url_for("cart"))


# =========================================================
# CART
# =========================================================

@app.route("/cart")
def cart():

    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("login"))

    conn = None
    cursor = None

    cart_items = []
    total = 0

    try:

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

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

            item_total = float(item["price"]) * int(item["quantity"])

            item["item_total"] = item_total

            total += item_total

    except Error as e:

        print("CART ERROR:", e)

        flash("Unable to load cart.", "danger")

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()

    return render_template(
        "cart.html",
        cart_items=cart_items,
        total=total
    )


# =========================================================
# INCREASE CART
# =========================================================

@app.route("/increase-cart/<int:cart_id>")
def increase_cart(cart_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = None
    cursor = None

    try:

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE cart
            SET quantity = quantity + 1
            WHERE id = %s
            AND user_id = %s
            """,
            (cart_id, session["user_id"])
        )

        conn.commit()

    except Error as e:

        print("INCREASE CART ERROR:", e)

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()

    return redirect(url_for("cart"))


# =========================================================
# DECREASE CART
# =========================================================

@app.route("/decrease-cart/<int:cart_id>")
def decrease_cart(cart_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = None
    cursor = None

    try:

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT quantity
            FROM cart
            WHERE id = %s
            AND user_id = %s
            """,
            (cart_id, session["user_id"])
        )

        item = cursor.fetchone()

        if item:

            if int(item["quantity"]) > 1:

                cursor.execute(
                    """
                    UPDATE cart
                    SET quantity = quantity - 1
                    WHERE id = %s
                    AND user_id = %s
                    """,
                    (cart_id, session["user_id"])
                )

            else:

                cursor.execute(
                    """
                    DELETE FROM cart
                    WHERE id = %s
                    AND user_id = %s
                    """,
                    (cart_id, session["user_id"])
                )

            conn.commit()

    except Error as e:

        print("DECREASE CART ERROR:", e)

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()

    return redirect(url_for("cart"))


# =========================================================
# REMOVE FROM CART
# =========================================================

@app.route("/remove-from-cart/<int:cart_id>")
def remove_from_cart(cart_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = None
    cursor = None

    try:

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            DELETE FROM cart
            WHERE id = %s
            AND user_id = %s
            """,
            (cart_id, session["user_id"])
        )

        conn.commit()

        flash("Item removed from cart.", "success")

    except Error as e:

        print("REMOVE CART ERROR:", e)

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()

    return redirect(url_for("cart"))


# =========================================================
# CLEAR CART
# =========================================================

@app.route("/clear-cart")
def clear_cart():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = None
    cursor = None

    try:

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            DELETE FROM cart
            WHERE user_id = %s
            """,
            (session["user_id"],)
        )

        conn.commit()

        flash("Cart cleared.", "success")

    except Error as e:

        print("CLEAR CART ERROR:", e)

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()

    return redirect(url_for("cart"))


# =========================================================
# CHECKOUT
# =========================================================

@app.route("/checkout")
def checkout():

    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("login"))

    conn = None
    cursor = None

    cart_items = []
    total = 0

    try:

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

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

            item["item_total"] = (
                float(item["price"]) *
                int(item["quantity"])
            )

            total += item["item_total"]

    except Error as e:

        print("CHECKOUT ERROR:", e)

        flash("Unable to load checkout.", "danger")

        return redirect(url_for("cart"))

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()

    if not cart_items:
        flash("Your cart is empty.", "danger")
        return redirect(url_for("cart"))

    return render_template(
        "checkout.html",
        cart_items=cart_items,
        total=total
    )


# =========================================================
# PLACE ORDER
# =========================================================

@app.route("/place-order", methods=["POST"])
def place_order():

    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("login"))

    customer_name = request.form.get(
        "customer_name",
        session.get("user_name", "")
    ).strip()

    phone = request.form.get("phone", "").strip()

    address = request.form.get("address", "").strip()

    payment_method = request.form.get(
        "payment_method",
        "Cash on Delivery"
    ).strip()

    transaction_id = request.form.get(
        "transaction_id",
        ""
    ).strip()

    if not customer_name or not phone or not address:

        flash(
            "Please enter customer name, phone and address.",
            "danger"
        )

        return redirect(url_for("checkout"))

    conn = None
    cursor = None

    try:

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get cart
        cursor.execute(
            """
            SELECT *
            FROM cart
            WHERE user_id = %s
            ORDER BY id ASC
            """,
            (session["user_id"],)
        )

        cart_items = cursor.fetchall()

        if not cart_items:

            flash("Your cart is empty.", "danger")

            return redirect(url_for("cart"))

        total = 0

        for item in cart_items:

            total += (
                float(item["price"]) *
                int(item["quantity"])
            )

        # Create order
        cursor.execute(
            """
            INSERT INTO orders
            (
                user_id,
                customer_name,
                phone,
                address,
                total,
                status,
                payment_method,
                payment_status,
                transaction_id
            )
            VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                session["user_id"],
                customer_name,
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

        # Insert order items
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
                (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    order_id,
                    item["product_id"],
                    item["product_name"],
                    item["price"],
                    item["unit"],
                    item["quantity"],
                    item.get("farmer", ""),
                    item.get("location", ""),
                    item.get("image", "")
                )
            )

        # Clear cart
        cursor.execute(
            """
            DELETE FROM cart
            WHERE user_id = %s
            """,
            (session["user_id"],)
        )

        conn.commit()

        flash(
            f"Order #{order_id} placed successfully!",
            "success"
        )

        return redirect(url_for("orders"))

    except Error as e:

        print("PLACE ORDER ERROR:", e)

        if conn:
            conn.rollback()

        flash(
            "Unable to place order. Please try again.",
            "danger"
        )

        return redirect(url_for("checkout"))

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


# =========================================================
# ORDERS
# =========================================================

@app.route("/orders")
def orders():

    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("login"))

    conn = None
    cursor = None

    orders_list = []

    try:

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

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

        print("ORDERS ERROR:", e)

        flash(
            "Unable to load orders.",
            "danger"
        )

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()

    return render_template(
        "orders.html",
        orders=orders_list
    )


# =========================================================
# UPDATE ORDER STATUS - FARMER
# =========================================================

@app.route(
    "/farmer/order/<int:order_id>/status",
    methods=["POST"]
)
def update_order_status(order_id):

    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("login"))

    if session.get("role") != "farmer":
        flash("Only farmers can update order status.", "danger")
        return redirect(url_for("buyer"))

    status = request.form.get(
        "status",
        "Pending"
    ).strip()

    allowed_statuses = [
        "Pending",
        "Confirmed",
        "Processing",
        "Shipped",
        "Out for Delivery",
        "Delivered",
        "Cancelled"
    ]

    if status not in allowed_statuses:
        flash("Invalid order status.", "danger")
        return redirect(url_for("farmer"))

    conn = None
    cursor = None

    try:

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Check that this order contains farmer's product
        cursor.execute(
            """
            SELECT oi.id
            FROM order_items oi
            WHERE oi.order_id = %s
            AND oi.farmer = %s
            LIMIT 1
            """,
            (
                order_id,
                session.get("user_name", "")
            )
        )

        farmer_item = cursor.fetchone()

        if not farmer_item:

            flash(
                "You cannot update this order.",
                "danger"
            )

            return redirect(url_for("farmer"))

        cursor.execute(
            """
            UPDATE orders
            SET status = %s
            WHERE id = %s
            """,
            (
                status,
                order_id
            )
        )

        conn.commit()

        flash(
            f"Order #{order_id} status updated to {status}.",
            "success"
        )

    except Error as e:

        print("UPDATE ORDER STATUS ERROR:", e)

        if conn:
            conn.rollback()

        flash(
            "Unable to update order status.",
            "danger"
        )

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()

    return redirect(url_for("farmer"))


# =========================================================
# CONTACT
# =========================================================

@app.route("/contact", methods=["GET", "POST"])
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

        if not name or not message:

            flash(
                "Please enter your name and message.",
                "danger"
            )

            return redirect(url_for("contact"))

        # Email functionality has been removed.
        # This form only confirms submission.

        flash(
            "Thank you! Your message has been received.",
            "success"
        )

        return redirect(url_for("contact"))

    return render_template("contact.html")


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    port = int(
        os.getenv("PORT", "5000")
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=True
    )
