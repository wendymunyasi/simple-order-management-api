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

# Insert data into the table
with open(CSV_FILE_PATH, "r", encoding="utf-8") as file:
    reader = csv.DictReader(file)
    for row in reader:
        name = row["name"]
        price = float(row["price"])
        cursor.execute(
            "INSERT INTO orders_api_product (name, price) VALUES (%s, %s)",
            (name, price),
        )

# Commit changes and close the connection
conn.commit()
cursor.close()
conn.close()

print("Data successfully inserted!")
