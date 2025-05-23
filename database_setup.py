import sqlite3

DATABASE_NAME = 'store.db'

def create_connection():
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
    except sqlite3.Error as e:
        print(e)
    return conn

def create_table(conn, create_table_sql):
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
    except sqlite3.Error as e:
        print(e)

def setup_database():
    sql_create_products_table = """ CREATE TABLE IF NOT EXISTS products (
                                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                                        name TEXT NOT NULL,
                                        description TEXT,
                                        price REAL NOT NULL,
                                        image_url TEXT,
                                        stock_quantity INTEGER NOT NULL DEFAULT 0
                                    ); """

    conn = create_connection()

    if conn is not None:
        create_table(conn, sql_create_products_table)
        print(f"Table 'products' configured.")

        sql_create_orders_table = """ CREATE TABLE IF NOT EXISTS orders (
                                          id INTEGER PRIMARY KEY AUTOINCREMENT,
                                          customer_name TEXT NOT NULL,
                                          customer_email TEXT NOT NULL,
                                          total_amount REAL NOT NULL,
                                          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                                      ); """
        create_table(conn, sql_create_orders_table)
        print(f"Table 'orders' configured.")

        sql_create_order_items_table = """ CREATE TABLE IF NOT EXISTS order_items (
                                               id INTEGER PRIMARY KEY AUTOINCREMENT,
                                               order_id INTEGER NOT NULL,
                                               product_id INTEGER NOT NULL,
                                               quantity INTEGER NOT NULL,
                                               price_per_item REAL NOT NULL,
                                               FOREIGN KEY (order_id) REFERENCES orders (id),
                                               FOREIGN KEY (product_id) REFERENCES products (id) 
                                           ); """
        create_table(conn, sql_create_order_items_table)
        print(f"Table 'order_items' configured.")
        
        print(f"Database {DATABASE_NAME} all tables configured.")
        conn.close()
    else:
        print("Error! cannot create the database connection.")

if __name__ == '__main__':
    setup_database()
