"""Module for injecting data into db
"""

import csv

import psycopg2

# Database connection details
conn = psycopg2.connect(
    dbname="ordersapidb",
    user="burn",
    password="password",
    host="localhost",
    port="5432",
)
cursor = conn.cursor()

# Path to your CSV file
CSV_FILE_PATH = "./data.csv"

# Insert data into the tables
with open(CSV_FILE_PATH, "r", encoding="utf-8") as file:
    reader = csv.DictReader(file)
    for row in reader:
        # Extract data from the CSV row
        name = row["name"]
        image_url = row["image_url"]
        product_url = row["product_url"]
        cost_price = float(row["cost_price"])
        price = float(row["price"])
        category_name = row["category_name"]
        reviews = int(row["reviews"])
        stars = float(row["stars"])
        is_best_seller = row["is_best_seller"].lower() == "true"
        quantity = int(row["quantity"])

        # Insert category into the Category table (if it doesn't already exist)
        cursor.execute(
            "INSERT INTO orders_api_category (name) VALUES (%s) ON CONFLICT (name) DO NOTHING",
            (category_name,),
        )

        # Get the category ID for the product
        cursor.execute(
            "SELECT id FROM orders_api_category WHERE name = %s", (category_name,)
        )
        category_id = cursor.fetchone()[0]

        # Insert product into the Product table
        cursor.execute(
            """
            INSERT INTO orders_api_product (
                name, image_url, product_url, cost_price, price, category_id,
                reviews, stars, is_best_seller, quantity
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                name,
                image_url,
                product_url,
                cost_price,
                price,
                category_id,
                reviews,
                stars,
                is_best_seller,
                quantity,
            ),
        )

# Commit changes and close the connection
conn.commit()
cursor.close()
conn.close()

print("Data successfully inserted!")
