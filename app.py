import os
import json
from decimal import Decimal

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv
from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, jsonify
)

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "hardwarehub-dev-key")


def get_db():
    database_url = os.getenv("DATABASE_URL")

    if database_url:
        return psycopg.connect(database_url, row_factory=dict_row)

    return psycopg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "sanjana_admane_hardware_shop"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgresql"),
        row_factory=dict_row
    )


def dashboard_data():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT p.product_id, p.product_name,
                       c.category_name, s.supplier_name,
                       p.price, p.stock_quantity
                FROM products p
                JOIN categories c ON p.category_id = c.category_id
                JOIN suppliers s ON p.supplier_id = s.supplier_id
                ORDER BY p.product_id
            """)
            products = cur.fetchall()

            cur.execute("SELECT COUNT(*) AS total FROM categories")
            categories = cur.fetchone()["total"]

            cur.execute("SELECT COUNT(*) AS total FROM suppliers")
            suppliers = cur.fetchone()["total"]

            cur.execute("SELECT COUNT(*) AS total FROM customers")
            customers = cur.fetchone()["total"]

            cur.execute("""
                SELECT COUNT(*) AS total,
                       COALESCE(SUM(total_amount), 0) AS amount
                FROM sales
            """)
            sales = cur.fetchone()

    stock_value = sum(
        p["price"] * p["stock_quantity"] for p in products
    )

    low_stock = sum(
        1 for p in products if p["stock_quantity"] < 15
    )

    return {
        "products": products,
        "products_count": len(products),
        "categories_count": categories,
        "suppliers_count": suppliers,
        "customers_count": customers,
        "sales_count": sales["total"],
        "sales_amount": sales["amount"],
        "total_stock_value": stock_value,
        "low_stock": low_stock
    }


@app.route("/")
def home():
    try:
        return render_template("index.html", data=dashboard_data(), error=None)
    except Exception as e:
        return render_template("index.html", data=None, error=str(e))


# ---------------- PRODUCTS ----------------

@app.route("/products")
def products():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT p.*, c.category_name, s.supplier_name
                FROM products p
                JOIN categories c ON p.category_id = c.category_id
                JOIN suppliers s ON p.supplier_id = s.supplier_id
                ORDER BY p.product_id
            """)
            product_list = cur.fetchall()

            cur.execute("SELECT * FROM categories ORDER BY category_name")
            categories = cur.fetchall()

            cur.execute("SELECT * FROM suppliers ORDER BY supplier_name")
            suppliers = cur.fetchall()

    return render_template(
        "products.html",
        products=product_list,
        categories=categories,
        suppliers=suppliers
    )


@app.route("/products/add", methods=["POST"])
def add_product():
    try:
        name = request.form["product_name"].strip()
        category = request.form["category_id"]
        supplier = request.form["supplier_id"]
        price = Decimal(request.form["price"])
        stock = int(request.form["stock_quantity"])

        if not name or price < 0 or stock < 0:
            raise ValueError("Enter valid product details.")

        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO products
                    (product_name, category_id, supplier_id, price, stock_quantity)
                    VALUES (%s, %s, %s, %s, %s)
                """, (name, category, supplier, price, stock))

        flash("Product added successfully!", "success")
    except Exception as e:
        flash(f"Could not add product: {e}", "error")

    return redirect(url_for("products"))


@app.route("/products/edit/<int:product_id>", methods=["POST"])
def edit_product(product_id):
    try:
        name = request.form["product_name"].strip()
        category = request.form["category_id"]
        supplier = request.form["supplier_id"]
        price = Decimal(request.form["price"])
        stock = int(request.form["stock_quantity"])

        if not name or price < 0 or stock < 0:
            raise ValueError("Enter valid product details.")

        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE products
                    SET product_name=%s, category_id=%s,
                        supplier_id=%s, price=%s, stock_quantity=%s
                    WHERE product_id=%s
                """, (name, category, supplier, price, stock, product_id))

                if cur.rowcount == 0:
                    flash("Product not found.", "error")
                else:
                    flash("Product updated successfully!", "success")

    except Exception as e:
        flash(f"Could not update product: {e}", "error")

    return redirect(url_for("products"))


@app.route("/products/delete/<int:product_id>", methods=["POST"])
def delete_product(product_id):
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM products WHERE product_id=%s",
                    (product_id,)
                )
                if cur.rowcount == 0:
                    flash("Product not found.", "error")
                else:
                    flash("Product deleted successfully!", "success")

    except Exception:
        flash("Cannot delete this product because it may have sales records.", "error")

    return redirect(url_for("products"))


# ---------------- CATEGORIES ----------------

@app.route("/categories", methods=["GET", "POST"])
def categories():
    if request.method == "POST":
        name = request.form["category_name"].strip()
        description = request.form.get("description", "").strip()

        if not name:
            flash("Category name is required.", "error")
            return redirect(url_for("categories"))

        try:
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO categories (category_name, description)
                        VALUES (%s, %s)
                    """, (name, description))
            flash("Category added!", "success")
        except Exception as e:
            flash(f"Could not add category: {e}", "error")

        return redirect(url_for("categories"))

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM categories ORDER BY category_id")
            items = cur.fetchall()

    return render_template("categories.html", categories=items)


@app.route("/categories/delete/<int:item_id>", methods=["POST"])
def delete_category(item_id):
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM categories WHERE category_id=%s",
                    (item_id,)
                )
        flash("Category deleted!", "success")
    except Exception:
        flash("Cannot delete a category that is used by products.", "error")

    return redirect(url_for("categories"))


# ---------------- SUPPLIERS ----------------

@app.route("/suppliers", methods=["GET", "POST"])
def suppliers():
    if request.method == "POST":
        name = request.form["supplier_name"].strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()
        address = request.form.get("address", "").strip()

        try:
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO suppliers
                        (supplier_name, phone, email, address)
                        VALUES (%s, %s, %s, %s)
                    """, (name, phone, email, address))
            flash("Supplier added!", "success")
        except Exception as e:
            flash(f"Could not add supplier: {e}", "error")

        return redirect(url_for("suppliers"))

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM suppliers ORDER BY supplier_id")
            items = cur.fetchall()

    return render_template("suppliers.html", suppliers=items)


@app.route("/suppliers/delete/<int:item_id>", methods=["POST"])
def delete_supplier(item_id):
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM suppliers WHERE supplier_id=%s",
                    (item_id,)
                )
        flash("Supplier deleted!", "success")
    except Exception:
        flash("Cannot delete a supplier that is used by products.", "error")

    return redirect(url_for("suppliers"))


# ---------------- CUSTOMERS ----------------

@app.route("/customers")
def customers():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM customers ORDER BY customer_id DESC")
            items = cur.fetchall()

    return render_template("customers.html", customers=items)


# ---------------- SALES ----------------

@app.route("/sales")
def sales():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT s.sale_id, s.sale_date, c.customer_name,
                       p.product_name, s.quantity, s.total_amount,
                       s.payment_method, s.payment_status
                FROM sales s
                JOIN customers c ON s.customer_id = c.customer_id
                JOIN products p ON s.product_id = p.product_id
                ORDER BY s.sale_id DESC
            """)
            items = cur.fetchall()

    return render_template("sales.html", sales=items)


# ---------------- CUSTOMER STORE ----------------

@app.route("/store")
def store():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT p.product_id, p.product_name,
                       p.price, p.stock_quantity,
                       c.category_name
                FROM products p
                LEFT JOIN categories c
                ON p.category_id = c.category_id
                WHERE p.stock_quantity > 0
                ORDER BY p.product_name
            """)
            items = cur.fetchall()

    return render_template("store.html", products=items)


# ---------------- CUSTOMER CHECKOUT ----------------

@app.route("/checkout", methods=["POST"])
def checkout():
    try:
        name = request.form.get("customer_name", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()
        address = request.form.get("address", "").strip()

        cart = json.loads(request.form.get("cart_items", "[]"))

        if not all([name, phone, email, address]):
            raise ValueError("Please fill all customer details.")

        if not cart:
            raise ValueError("Your cart is empty.")

        payment_method = request.form.get("payment_method")

        if payment_method != "COD":
            raise ValueError("Invalid payment method.")

        with get_db() as conn:
            with conn.cursor() as cur:

                # Find existing customer by email
                cur.execute("""
                    SELECT customer_id
                    FROM customers
                    WHERE email = %s
                    ORDER BY customer_id
                    LIMIT 1
                """, (email,))

                customer = cur.fetchone()

                if customer:
                    customer_id = customer["customer_id"]

                    cur.execute("""
                        UPDATE customers
                        SET customer_name = %s,
                            phone = %s,
                            address = %s
                        WHERE customer_id = %s
                    """, (name, phone, address, customer_id))

                else:
                    cur.execute("""
                        INSERT INTO customers
                        (customer_name, phone, email, address)
                        VALUES (%s, %s, %s, %s)
                        RETURNING customer_id
                    """, (name, phone, email, address))

                    customer_id = cur.fetchone()["customer_id"]

                # Save each purchased product
                for item in cart:
                    product_id = int(item["id"])
                    quantity = int(item["quantity"])

                    if quantity <= 0:
                        raise ValueError("Invalid product quantity.")

                    # Check actual stock and price in database
                    cur.execute("""
                        SELECT price, stock_quantity
                        FROM products
                        WHERE product_id = %s
                        FOR UPDATE
                    """, (product_id,))

                    product = cur.fetchone()

                    if not product:
                        raise ValueError("Product not found.")

                    if product["stock_quantity"] < quantity:
                        raise ValueError(
                            "Insufficient stock for product ID "
                            + str(product_id)
                        )

                    total = product["price"] * quantity

                    cur.execute("""
                        INSERT INTO sales
                        (customer_id, product_id, sale_date,
                         quantity, total_amount,
                         payment_method, payment_status)
                        VALUES (%s, %s, CURRENT_DATE,
                                %s, %s, %s, %s)
                    """, (
                        customer_id,
                        product_id,
                        quantity,
                        total,
                        "COD",
                        "Pending"
                    ))

                    # Reduce available stock
                    cur.execute("""
                        UPDATE products
                        SET stock_quantity = stock_quantity - %s
                        WHERE product_id = %s
                    """, (quantity, product_id))

        flash("Order placed successfully! Payment: Cash on Delivery.", "success")

    except Exception as e:
        flash(f"Order could not be placed: {e}", "error")

    return redirect(url_for("store"))


if __name__ == "__main__":
    app.run(debug=True)
