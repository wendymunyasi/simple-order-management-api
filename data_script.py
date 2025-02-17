"""
Script to insert data into the database from a CSV file.
"""

import csv

import psycopg2

# from decouple import config

# Database connection details
conn = psycopg2.connect(
    dbname="ordersapidb",
    user="burn",
    password="password",
    host="localhost",
    port="5432",
)
# Database connection details for Neon DB
# conn = psycopg2.connect(
#     dbname=config("DB_NAME"),
#     user=config("DB_USER"),
#     password=config("DB_PASSWORD"),
#     host=config("DB_HOST"),
#     port=config("DB_PORT"),
#     sslmode=config("DB_SSLMODE"),  # Pass sslmode directly as a parameter
# )
cursor = conn.cursor()

# Path to your CSV file
CSV_FILE_PATH = "./data.csv"

# Reset the sequence for the `id` column in the `orders_api_category` table
cursor.execute(
    "SELECT setval('orders_api_category_id_seq', (SELECT MAX(id) FROM orders_api_category))"
)

# Create a set to track unique categories
unique_categories = set()

# Insert data into the tables
with open(CSV_FILE_PATH, "r", encoding="utf-8") as file:
    reader = csv.DictReader(file)
    for row in reader:
        # Extract data from the CSV row
        name = row["name"]
        product_url = row["product_url"]
        cost_price = float(row["cost_price"])
        price = float(row["price"])
        category_name = row["category_name"]
        reviews = int(row["reviews"])
        stars = float(row["stars"])
        is_best_seller = row["is_best_seller"].lower() == "true"
        quantity = int(row["quantity"])
        image = row["image"]

        # Insert category into the Category table (if it doesn't already exist)
        if category_name not in unique_categories:
            unique_categories.add(category_name)
            cursor.execute(
                """
                INSERT INTO orders_api_category (name)
                VALUES (%s)
                ON CONFLICT (name) DO NOTHING
                RETURNING id
                """,
                (category_name,),
            )
            result = cursor.fetchone()

            if result is None:
                # If no new row was inserted, fetch the existing ID
                cursor.execute(
                    "SELECT id FROM orders_api_category WHERE name = %s",
                    (category_name,),
                )
                result = cursor.fetchone()

            if result is None:
                raise ValueError(f"Category ID not found for category: {category_name}")
            category_id = result[0]

            print(f"Category '{category_name}' has ID: {category_id}")
        else:
            # Fetch the ID for the already processed category
            cursor.execute(
                "SELECT id FROM orders_api_category WHERE name = %s", (category_name,)
            )
            result = cursor.fetchone()
            if result is None:
                raise ValueError(f"Category ID not found for category: {category_name}")
            category_id = result[0]

        # Insert product into the Product table
        cursor.execute(
            """
            INSERT INTO orders_api_product (
                name, product_url, cost_price, price, category_id,
                reviews, stars, is_best_seller, quantity, image
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                name,
                product_url,
                cost_price,
                price,
                category_id,
                reviews,
                stars,
                is_best_seller,
                quantity,
                image,
            ),
        )

# Commit changes and close the connection
conn.commit()
cursor.close()
conn.close()

print("Data successfully inserted!")
