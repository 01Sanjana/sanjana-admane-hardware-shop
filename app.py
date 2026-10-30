
import os
from flask import Flask, render_template
import psycopg

app = Flask(__name__)

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": " sanjana_admane_hardware_shop",
    "user": "postgres",
    "password":"postgresql"
}


def get_dashboard_data():
    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:

            # Fetch products with category and supplier details
            cur.execute("""
                SELECT
                    p.product_id,
                    p.product_name,
                    c.category_name,
                    s.supplier_name,
                    p.price,
                    p.stock_quantity
                FROM products p
                JOIN categories c
                    ON p.category_id = c.category_id
                JOIN suppliers s
                    ON p.supplier_id = s.supplier_id
                ORDER BY p.product_id;
            """)
            products = cur.fetchall()

            # Total categories
            cur.execute("SELECT COUNT(*) FROM categories;")
            categories_count = cur.fetchone()[0]

            # Total suppliers
            cur.execute("SELECT COUNT(*) FROM suppliers;")
            suppliers_count = cur.fetchone()[0]

            # Total sales
            cur.execute("""
                SELECT COUNT(*), COALESCE(SUM(total_amount), 0)
                FROM sales;
            """)
            sales_count, sales_amount = cur.fetchone()

    total_stock_value = sum(
        float(p[4]) * int(p[5]) for p in products
    )

    low_stock = sum(
        1 for p in products if int(p[5]) < 15
    )

    return {
        "products": products,
        "products_count": len(products),
        "categories_count": categories_count,
        "suppliers_count": suppliers_count,
        "sales_count": sales_count,
        "sales_amount": float(sales_amount),
        "total_stock_value": total_stock_value,
        "low_stock": low_stock
    }


@app.route("/")
def home():
    try:
        data = get_dashboard_data()
        return render_template(
            "index.html",
            data=data,
            error=None
        )
    except Exception as e:
        return render_template(
            "index.html",
            data=None,
            error=str(e)
        )


if __name__ == "__main__":
    app.run(debug=True)
