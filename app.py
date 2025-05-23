from flask import Flask, jsonify, request, render_template, session # Ensure session is imported
import sqlite3 # Add this import
import pandas as pd # Add this import
import os # For secret_key
from datetime import timedelta # For session lifetime

app = Flask(__name__)
# For production, FLASK_SECRET_KEY should be a strong, persistent random string.
# If FLASK_SECRET_KEY is not set, os.urandom(24) is used as a fallback (suitable for dev).
app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))
app.permanent_session_lifetime = timedelta(days=7) # Optional: Configure session lifetime

DATABASE_NAME = 'store.db' # Add this line

# Function to get a database connection (will be used by API endpoints later)
def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row # This allows accessing columns by name
    return conn

@app.route('/')
def home():
    # return "Welcome to the Minecraft Store! (Placeholder)" # Old line
    return render_template('home.html') # New line

@app.route('/admin/upload')
def admin_upload_page():
    return render_template('admin_upload.html')

@app.route('/cart')
def cart_page():
    return render_template('cart.html')

@app.route('/checkout')
def checkout_page():
    return render_template('checkout.html')

# Add a simple test route to check database (optional, can be removed later)
@app.route('/test_db')
def test_db():
    try:
        conn = get_db_connection()
        # Check if the products table exists
        table_exists = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='products';").fetchone()
        conn.close()
        if table_exists:
            return "Database connection successful and 'products' table exists."
        else:
            return "Database connection successful but 'products' table does NOT exist."
    except Exception as e:
        return f"Database connection failed: {str(e)}"

# POST /api/products
@app.route('/api/products', methods=['POST'])
def add_product():
    data = request.get_json()
    if not data or 'name' not in data or 'price' not in data:
        return jsonify({'error': 'Missing required fields: name and price'}), 400

    name = data['name']
    description = data.get('description')
    price = data['price']
    image_url = data.get('image_url')
    stock_quantity = data.get('stock_quantity', 0)

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO products (name, description, price, image_url, stock_quantity) VALUES (?, ?, ?, ?, ?)",
                       (name, description, price, image_url, stock_quantity))
        product_id = cursor.lastrowid
        conn.commit()
        
        created_product = {
            'id': product_id,
            'name': name,
            'description': description,
            'price': price,
            'image_url': image_url,
            'stock_quantity': stock_quantity
        }
        # Important: Close connection after all operations for this request are done
        conn.close() 
        return jsonify(created_product), 201
    except sqlite3.Error as e:
        if conn: conn.close()
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    except Exception as e:
        if conn: conn.close()
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500

# GET /api/products
@app.route('/api/products', methods=['GET'])
def get_products():
    try:
        conn = get_db_connection()
        products_cursor = conn.execute("SELECT * FROM products")
        products = [dict(row) for row in products_cursor.fetchall()]
        conn.close()
        return jsonify(products)
    except sqlite3.Error as e:
        if conn: conn.close()
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    except Exception as e:
        if conn: conn.close()
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500

# GET /api/products/<int:product_id>
@app.route('/api/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    try:
        conn = get_db_connection()
        product_cursor = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        product = product_cursor.fetchone()
        conn.close()
        if product is None:
            return jsonify({'error': 'Product not found'}), 404
        return jsonify(dict(product))
    except sqlite3.Error as e:
        if conn: conn.close()
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    except Exception as e:
        if conn: conn.close()
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500

# PUT /api/products/<int:product_id>
@app.route('/api/products/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided for update'}), 400
    
    conn = None # Initialize conn to None for broader scope in try/except/finally
    try:
        conn = get_db_connection()
        # First, check if product exists
        product_cursor = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        product = product_cursor.fetchone()

        if product is None:
            conn.close()
            return jsonify({'error': 'Product not found'}), 404

        current_product = dict(product)
        
        # Ensure name and price are present if they are being updated, or retain old values
        name = data.get('name', current_product['name'])
        price = data.get('price', current_product['price'])

        if not name or price is None: # Check for empty name or None price
             conn.close()
             return jsonify({'error': 'Name and price are required and cannot be empty'}), 400
        
        updated_product_data = {
            'name': name,
            'description': data.get('description', current_product['description']),
            'price': price,
            'image_url': data.get('image_url', current_product['image_url']),
            'stock_quantity': data.get('stock_quantity', current_product['stock_quantity'])
        }

        sql = """UPDATE products SET 
                 name = ?, description = ?, price = ?, image_url = ?, stock_quantity = ?
                 WHERE id = ?"""
        conn.execute(sql, (updated_product_data['name'], updated_product_data['description'], 
                           updated_product_data['price'], updated_product_data['image_url'],
                           updated_product_data['stock_quantity'], product_id))
        conn.commit()
        
        # Return the updated product data including its ID
        response_data = {'id': product_id, **updated_product_data}
        conn.close()
        return jsonify(response_data)

    except sqlite3.Error as e:
        if conn: conn.close()
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    except Exception as e:
        if conn: conn.close()
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500

# DELETE /api/products/<int:product_id>
@app.route('/api/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    conn = None # Initialize conn to None
    try:
        conn = get_db_connection()
        # Check if product exists before deleting
        product_cursor = conn.execute("SELECT id FROM products WHERE id = ?", (product_id,))
        product = product_cursor.fetchone()
        
        if product is None:
            conn.close()
            return jsonify({'error': 'Product not found'}), 404

        conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Product deleted successfully'}), 200 # Standard success
    except sqlite3.Error as e:
        if conn: conn.close()
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    except Exception as e:
        if conn: conn.close()
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500

@app.route('/api/products/search', methods=['GET'])
def search_products():
    query = request.args.get('q', '').strip()

    # Optional: Handle very short queries or empty queries if specific behavior is desired.
    # For example, if query is empty, could return all products or an empty list.
    # if not query:
    #     return jsonify([]) # Return empty list if query is empty

    conn = None 
    try:
        conn = get_db_connection()
        search_term = f"%{query}%"
        
        products_cursor = conn.execute(
            "SELECT * FROM products WHERE name LIKE ? OR description LIKE ?", 
            (search_term, search_term)
        )
        products = [dict(row) for row in products_cursor.fetchall()]
        # Connection is closed after fetching and before returning
        conn.close() 
        conn = None # Indicate connection is closed for the finally block

        return jsonify(products)

    except sqlite3.Error as e:
        # Log error e server-side if possible
        # conn might be None if get_db_connection() failed, or already closed.
        return jsonify({'error': f'Database search error: {str(e)}'}), 500
    except Exception as e:
        # Log error e server-side if possible
        return jsonify({'error': f'An unexpected error occurred during search: {str(e)}'}), 500
    finally:
        if conn: # Only try to close if it wasn't set to None (i.e., closed successfully in try)
            conn.close()

ALLOWED_EXTENSIONS = {'xlsx'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/upload_products_excel', methods=['POST'])
def upload_products_excel():
    if 'excel_file' not in request.files:
        return jsonify({'error': 'No excel_file part'}), 400
    
    file = request.files['excel_file']
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if not file or not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed or missing. Only .xlsx is accepted.'}), 400

    conn = None # Initialize for finally block
    try:
        # Try reading the file into a pandas DataFrame
        df = pd.read_excel(file.stream)
    except Exception as e:
        return jsonify({'error': f'Failed to read Excel: {str(e)}'}), 400

    added_count = 0
    updated_count = 0
    row_errors = []
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        for index, row in df.iterrows():
            row_number = index + 2  # Excel rows are typically 1-indexed, plus header
            
            current_row_name_for_error = row.get('Name', 'N/A') # For error reporting if name is missing

            try:
                name = row.get('Name')
                price_val = row.get('Price')

                # Validation for Name
                if pd.isna(name) or str(name).strip() == '':
                    row_errors.append(f"Row {row_number}: 'Name' is missing or empty.")
                    continue # Skip to the next row
                name = str(name).strip()
                current_row_name_for_error = name # Update for more specific error reporting

                # Validation for Price
                if pd.isna(price_val):
                    row_errors.append(f"Row {row_number}: 'Price' is missing for product '{name}'.")
                    continue
                try:
                    price = float(price_val)
                except ValueError:
                    row_errors.append(f"Row {row_number}: 'Price' for '{name}' ('{price_val}') is not a valid number.")
                    continue

                # Process Optional Fields (Stock Quantity, Description, Image URL)
                stock_q_val = row.get('Stock Quantity')
                if pd.isna(stock_q_val) or str(stock_q_val).strip() == '':
                    stock_quantity = 0
                else:
                    try:
                        stock_quantity = int(float(stock_q_val)) # float conversion handles "10.0" then int
                    except ValueError:
                        row_errors.append(f"Row {row_number}: 'Stock Quantity' for '{name}' ('{stock_q_val}') is not a valid integer.")
                        continue
                
                desc_val = row.get('Description')
                description = str(desc_val).strip() if not pd.isna(desc_val) else None
                
                img_val = row.get('Image URL')
                image_url = str(img_val).strip() if not pd.isna(img_val) else None

                # Database Operations
                cursor.execute("SELECT id FROM products WHERE name = ?", (name,))
                existing_product = cursor.fetchone()

                if existing_product:
                    cursor.execute("""UPDATE products SET description = ?, price = ?, image_url = ?, stock_quantity = ?
                                      WHERE id = ?""", 
                                   (description, price, image_url, stock_quantity, existing_product['id']))
                    updated_count += 1
                else:
                    cursor.execute("""INSERT INTO products (name, description, price, image_url, stock_quantity)
                                      VALUES (?, ?, ?, ?, ?)""", 
                                   (name, description, price, image_url, stock_quantity))
                    added_count += 1
            
            except KeyError as e: # Catches missing columns in the Excel file
                # This error means the Excel sheet itself doesn't have an expected column header.
                # It's a structural issue with the file, so it might be better to stop processing.
                # For now, we'll record it as a row error and continue to see if other rows are okay,
                # but this could be changed to a more global error.
                row_errors.append(f"Row {row_number}: Missing expected column in Excel: {str(e)}. Required columns include 'Name', 'Price'.")
                # If a critical column like 'Name' or 'Price' is what's missing, then the row processing would have failed earlier.
                # This specific KeyError here implies an optional column might be missing, or an issue with .get() if not used properly.
                # However, the current structure uses .get() which should prevent KeyErrors for optional fields.
                # This catch might be for unexpected KeyErrors if direct access `row['Column']` was used somewhere.
                # Given the use of .get(), a KeyError here is less likely unless it's from a malformed DataFrame.
                # Let's refine the error message to be more general.
                row_errors.append(f"Row {row_number}: Column access error: {str(e)}. Ensure Excel has 'Name' and 'Price' columns.")

            except Exception as e: # Catches other errors for this specific row
                row_errors.append(f"Row {row_number}: Error processing product '{current_row_name_for_error}': {str(e)}")
        
        # After iterating through all rows
        if row_errors:
            conn.rollback() # Rollback if any row had an error
            return jsonify({'error': 'Errors occurred during processing. No products were imported or updated due to issues in specific rows.', 'details': row_errors}), 400
        else:
            conn.commit() # Commit only if all rows were processed successfully
            return jsonify({'message': 'Excel processed successfully.', 'added': added_count, 'updated': updated_count}), 200

    except Exception as e: # Catches errors from the main try block (e.g., db connection, initial df read)
        if conn:
            conn.rollback() # Ensure rollback on unexpected errors during the transaction phase
        # This error is for issues outside the row-by-row processing, e.g., database connection failure
        return jsonify({'error': f'An unexpected server error occurred: {str(e)}'}), 500
    finally:
        if conn:
            conn.close() # Always close the connection

@app.route('/api/cart/add', methods=['POST'])
def add_to_cart():
    data = request.get_json()
    if not data or 'product_id' not in data or 'quantity' not in data:
        return jsonify({'error': 'Missing product_id or quantity'}), 400

    try:
        product_id = int(data['product_id'])
        quantity = int(data['quantity'])
        if quantity <= 0:
            return jsonify({'error': 'Quantity must be positive'}), 400
    except ValueError:
        return jsonify({'error': 'Invalid product_id or quantity format'}), 400

    conn = None # Initialize conn for broader scope
    product = None
    try:
        conn = get_db_connection()
        product_cursor = conn.execute("SELECT id, name, price, image_url FROM products WHERE id = ?", (product_id,))
        product = product_cursor.fetchone()
    except sqlite3.Error as e:
        # Log the error e server-side
        if conn: conn.close() # Ensure connection is closed on DB error
        return jsonify({'error': f'Database error while fetching product: {str(e)}'}), 500
    finally:
        if conn and product is None: # Close connection if product not found or other early exit in try
            conn.close()
        elif conn and product is not None: # Or just ensure it's closed if product was found
             conn.close()


    if not product:
        return jsonify({'error': 'Product not found'}), 404

    # Initialize cart if it doesn't exist
    if 'cart' not in session:
        session['cart'] = {}
    
    cart = session['cart']
    product_id_str = str(product_id) # Use string keys for session cart items

    if product_id_str in cart:
        # Ensure quantity is a number before adding
        cart[product_id_str]['quantity'] = int(cart[product_id_str].get('quantity', 0)) + quantity
    else:
        cart[product_id_str] = {
            'id': product['id'], # Storing id can be useful on frontend
            'name': product['name'],
            'price': product['price'],
            'quantity': quantity,
            'image_url': product['image_url']
        }
    
    session.permanent = True # Make the session permanent as configured by app.permanent_session_lifetime
    session.modified = True # Mark session as modified to ensure it's saved
    
    return jsonify({'message': 'Product added to cart successfully!', 'cart': session['cart']}), 200

@app.route('/api/cart', methods=['GET'])
def view_cart():
    cart_items = session.get('cart', {}) # Default to an empty dict if 'cart' not in session
    
    total_price = 0.0 # Ensure float for price calculation
    total_items = 0
    
    for item_id, item_details in cart_items.items():
        # Defensive: check if price and quantity exist and are numbers
        price = item_details.get('price', 0)
        quantity = item_details.get('quantity', 0)
        
        if not isinstance(price, (int, float)): price = 0.0
        if not isinstance(quantity, int): quantity = 0

        total_price += price * quantity
        total_items += quantity
    
    return jsonify({
        'cart_items': cart_items, 
        'total_items': total_items,
        'total_price': round(total_price, 2)
    })

@app.route('/api/cart/update/<product_id_str>', methods=['PUT'])
def update_cart_item(product_id_str):
    if 'cart' not in session or product_id_str not in session['cart']:
        return jsonify({'error': 'Item not found in cart'}), 404

    data = request.get_json()
    if not data or 'quantity' not in data:
        return jsonify({'error': 'Missing quantity'}), 400

    try:
        quantity = int(data['quantity'])
        if quantity <= 0:
            # If quantity is 0 or less, it implies removing the item.
            # For this implementation, we will remove it directly.
            # Alternative: return error and require using DELETE endpoint.
            del session['cart'][product_id_str]
            session.modified = True
            message = 'Item quantity updated to 0 and removed from cart.'
        else:
            session['cart'][product_id_str]['quantity'] = quantity
            session.modified = True
            message = 'Cart item quantity updated.'

    except ValueError:
        return jsonify({'error': 'Invalid quantity format. Must be an integer.'}), 400
    
    # Recalculate totals for the response
    current_cart = session.get('cart', {})
    total_price = 0.0
    total_items = 0
    for item_id, item_details in current_cart.items():
        price = item_details.get('price', 0)
        qty = item_details.get('quantity', 0)
        if not isinstance(price, (int, float)): price = 0.0
        if not isinstance(qty, int): qty = 0
        total_price += price * qty
        total_items += qty

    return jsonify({
        'message': message, 
        'cart_items': current_cart,
        'total_items': total_items,
        'total_price': round(total_price, 2)
    }), 200

@app.route('/api/cart/remove/<product_id_str>', methods=['DELETE'])
def remove_from_cart(product_id_str):
    if 'cart' not in session or product_id_str not in session['cart']:
        return jsonify({'error': 'Item not found in cart'}), 404

    del session['cart'][product_id_str]
    session.modified = True

    # Recalculate totals for the response
    current_cart = session.get('cart', {})
    total_price = 0.0
    total_items = 0
    for item_id, item_details in current_cart.items():
        price = item_details.get('price', 0)
        qty = item_details.get('quantity', 0)
        if not isinstance(price, (int, float)): price = 0.0
        if not isinstance(qty, int): qty = 0
        total_price += price * qty
        total_items += qty
        
    return jsonify({
        'message': 'Item removed from cart.', 
        'cart_items': current_cart,
        'total_items': total_items,
        'total_price': round(total_price, 2)
    }), 200

@app.route('/api/cart/clear', methods=['POST'])
def clear_cart(): # Renamed function to avoid conflict with any potential 'clear_cart' import/variable
    if 'cart' in session: # Check if cart exists before trying to pop
        session.pop('cart', None) # Remove cart from session; None if not found (though 'in' check handles this)
        session.modified = True
    
    # Return the state of an empty cart
    return jsonify({
        'message': 'Cart cleared successfully.', 
        'cart_items': {}, 
        'total_items': 0,
        'total_price': 0.0
    }), 200

@app.route('/api/checkout/place_order', methods=['POST'])
def place_order():
    data = request.get_json()
    if not data or not data.get('customer_name') or not data.get('customer_email'):
        return jsonify({'error': 'Missing customer name or email'}), 400
    
    customer_name = data['customer_name']
    customer_email = data['customer_email']

    cart = session.get('cart', {})
    if not cart:
        return jsonify({'error': 'Your cart is empty. Cannot place order.'}), 400

    total_amount = 0.0 # Ensure float
    for item_id_str, item_details in cart.items():
        try:
            # Validate that price and quantity are numbers
            price = float(item_details['price'])
            quantity = int(item_details['quantity'])
            if price < 0 or quantity < 0: # Basic validation
                return jsonify({'error': f"Invalid price or quantity for item {item_id_str}."}), 400
            total_amount += price * quantity
        except (ValueError, TypeError, KeyError) as e:
            # Log the problematic item_details for server-side diagnosis
            print(f"Error processing cart item {item_id_str}: {item_details}. Error: {e}")
            return jsonify({'error': f"Invalid data for item {item_id_str} in cart."}), 500
    total_amount = round(total_amount, 2)

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Insert into orders table
        cursor.execute(
            "INSERT INTO orders (customer_name, customer_email, total_amount) VALUES (?, ?, ?)",
            (customer_name, customer_email, total_amount)
        )
        order_id = cursor.lastrowid

        # Insert into order_items table
        for item_id_str, item_details in cart.items():
            # Ensure item_details['id'] contains the numeric product ID,
            # item_details['price'] is the price per item,
            # and item_details['quantity'] is the quantity.
            product_actual_id = int(item_details['id']) # The original product ID
            item_price = float(item_details['price'])
            item_quantity = int(item_details['quantity'])
            
            cursor.execute(
                "INSERT INTO order_items (order_id, product_id, quantity, price_per_item) VALUES (?, ?, ?, ?)",
                (order_id, product_actual_id, item_quantity, item_price)
            )
        
        conn.commit()

        # Clear the cart from session
        session.pop('cart', None)
        session.modified = True
        # Frontend should call updateCartCountDisplay() upon successful response

        return jsonify({
            'message': 'Order placed successfully!',
            'order_id': order_id,
            'customer_name': customer_name,
            'total_amount': total_amount
        }), 201

    except sqlite3.Error as e:
        if conn: conn.rollback()
        # Log e for server diagnosis (e.g., print(f"DB Error: {e}"))
        return jsonify({'error': f'Database error placing order: {str(e)}'}), 500
    except Exception as e:
        if conn: conn.rollback()
        # Log e for server diagnosis (e.g., print(f"Unexpected Error: {e}"))
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    # To ensure the database is created when the app starts for the first time (development)
    # In a production environment, you'd run database_setup.py separately.
    from database_setup import setup_database
    setup_database()
    # Development server configuration
    port = int(os.environ.get('PORT', 5000)) # Use PORT env var if available, else default to 5000
    app.run(host='0.0.0.0', port=port, debug=True)
