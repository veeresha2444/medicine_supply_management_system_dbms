import streamlit as st
import mysql.connector
from mysql.connector import Error
import hashlib
import matplotlib.pyplot as plt
import pandas as pd
import psycopg2
from psycopg2 import sql

# Function to create a database connection
@st.cache_resource
def create_connection():
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="Veeresh@123",
            database="mdb"
        )
        return connection if connection.is_connected() else None
    except Error as e:
        st.error(f"Error connecting to database: {e}")
        return None
        return connection if connection.is_connected() else None
    except Error as e:
        st.error(f"Error connecting to MySQL database: {e}")
        return None

# Admin login and signup
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_admin_credentials(username, password):
    connection = create_connection()
    if connection:
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM Admin WHERE username = %s AND password = %s",
                       (username, hash_password(password)))
        return cursor.fetchone() is not None

def add_admin(username, password):
    connection = create_connection()
    if connection:
        cursor = connection.cursor()
        cursor.execute("INSERT INTO Admin (username, password) VALUES (%s, %s)",
                       (username, hash_password(password)))
        connection.commit()
        cursor.close()

def admin_login_signup():
    st.title("Admin Login / Signup")
    choice = st.radio("Choose Action", ["Login", "Signup"])
    username, password = st.text_input("Username"), st.text_input("Password", type="password")
    if st.button(choice):
        if choice == "Login" and check_admin_credentials(username, password):
            st.success("Great 🥰Welcome to medicine supply management system😊!")
            st.session_state.logged_in = True
        elif choice == "Signup":
            add_admin(username, password)
            st.success("Account created! Please login.")
        else:
            st.error("Invalid credentials or action.")
            
# Function to count records in each table
def count_records(table_name):
    connection = create_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            return count
        except Error as e:
            st.error(f"Error counting records in {table_name}: {e}")
            return 0
        finally:
            cursor.close()
    return 0

# Dashboard function
def show_dashboard():
    st.header("📊 Dashboard - Overview of Records")

    # Get counts for each table
    medicine_count = count_records("Medicine")
    supplier_count = count_records("Supplier")
    product_count = count_records("Product")
    customer_count = count_records("Customer")
    purchase_order_count = count_records("Purchase_Order")

    # Display counts as metrics
    st.subheader("Record Counts")
    col1, col2, col3 = st.columns(3)
    col1.metric("Medicines", medicine_count)
    col2.metric("Suppliers", supplier_count)
    col3.metric("Products", product_count)

    col4, col5 = st.columns(2)
    col4.metric("Customers", customer_count)
    col5.metric("Purchase Orders", purchase_order_count)

    # Optional: Visualizations (e.g., bar chart)
    st.subheader("📊 Record Distribution")
    data = {
        "Table": ["Medicine", "Supplier", "Product", "Customer", "Purchase Order"],
        "Count": [medicine_count, supplier_count, product_count, customer_count, purchase_order_count]
    }
    chart_data = pd.DataFrame(data)
    st.bar_chart(chart_data.set_index("Table"))


# procedure query
def get_table_row_counts():
    connection = create_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.callproc('GetTableRowCounts')
            for result in cursor.stored_results():
                table_counts = result.fetchall()  # Get all rows from the procedure
            return table_counts
        except Error as e:
            st.error(f"Error fetching table counts: {e}")
            return []
        finally:
            cursor.close()


def dashboard():
    st.title("Database Dashboard 📊")
    
    # Get table counts
    table_counts = get_table_row_counts()
    
    if table_counts:
        st.subheader("Table Overview")
        st.write("Below is the count of records in each table using procedure query:")

        # Create a DataFrame for better display
        import pandas as pd
        df = pd.DataFrame(table_counts)
        st.table(df)
    else:
        st.info("No data available or error in fetching table counts.")


# join nested and aggregate querys
def reports():
    st.header("📊 Analytical Reports")
    report_choice = st.selectbox("Select Report Type", ["Supplier Summary", "Premium Suppliers", "Category-wise Price Average"])

    connection = create_connection()
    if connection:
        cursor = connection.cursor()

        # Supplier Summary (Join Query)
        if report_choice == "Supplier Summary":
            st.subheader("Total Products Per Supplier")
            query = """
            SELECT Supplier.s_name, COUNT(Product.product_id) AS total_products
            FROM Supplier
            JOIN Product ON Supplier.supplier_id = Product.supplier_id
            GROUP BY Supplier.s_name;
            """
            cursor.execute(query)
            results = cursor.fetchall()
            if results:
                df = pd.DataFrame(results, columns=["Supplier Name", "Total Products"])
                st.table(df)
            else:
                st.info("No data available.")

        # Premium Suppliers (Nested Query)
        elif report_choice == "Premium Suppliers":
            st.subheader("Suppliers with Premium Products")
            query = """
            SELECT Supplier.s_name, COUNT(Product.product_id) AS total_products
            FROM Supplier
            JOIN Product ON Supplier.supplier_id = Product.supplier_id
            WHERE Product.product_id IN (
                SELECT product_id FROM Medicine WHERE price > (SELECT AVG(price) FROM Medicine)
            )
            GROUP BY Supplier.s_name;
            """
            cursor.execute(query)
            results = cursor.fetchall()
            if results:
                df = pd.DataFrame(results, columns=["Supplier Name", "Total Products"])
                st.table(df)
            else:
                st.info("No suppliers found with premium products.")

        # Category-wise Price Average (Aggregate Query)
        elif report_choice == "Category-wise Price Average":
            st.subheader("Average Medicine Price by Category")
            query = """
            SELECT category, AVG(Medicine.price) AS avg_price
            FROM Product
            JOIN Medicine ON Product.product_id = Medicine.product_id
            GROUP BY category;
            """
            cursor.execute(query)
            results = cursor.fetchall()
            if results:
                df = pd.DataFrame(results, columns=["Category", "Average Price"])
                st.table(df)
            else:
                st.info("No data available.")

        cursor.close()  
        

        
# CRUD Templates to reduce redundancy
def crud_operations(entity_name, insert_func, get_func, update_func, delete_func, fields):
    st.header(f"{entity_name} Management")
    action = st.radio("Select Action", ["Add", "View", "Update", "Delete"])

    if action == "Add":
        inputs = {field: st.text_input(field) if type_ == 'str' else st.number_input(field, min_value=0) 
                  for field, type_ in fields.items()}
        if st.button(f"Add {entity_name}"):
            insert_func(**inputs)

    elif action == "View":
        records = get_func()
        st.table(records)

    elif action == "Update":
        record_id = st.number_input(f"{entity_name} ID to Update", min_value=1)
        inputs = {field: st.text_input(field) if type_ == 'str' else st.number_input(field, min_value=0) 
                  for field, type_ in fields.items()}
        if st.button(f"Update {entity_name}"):
            update_func(record_id, **inputs)

    elif action == "Delete":
        record_id = st.number_input(f"{entity_name} ID to Delete", min_value=1)
        if st.button(f"Delete {entity_name}"):
            delete_func(record_id)

# CRUD Functions for Medicine

# Insert new medicine
def insert_medicine(m_name, price, product_id):
    connection = create_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("INSERT INTO Medicine (m_name, price, product_id) VALUES (%s, %s, %s)", 
                           (m_name, price, product_id))
            connection.commit()
            st.success("Medicine added successfully!")
        except Error as e:
            st.error(f"Error inserting medicine: {e}")
        finally:
            cursor.close()

# Get all medicines
def get_medicines():
    connection = create_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT * FROM Medicine")
            medicines = cursor.fetchall()
            return medicines
        except Error as e:
            st.error(f"Error fetching medicines: {e}")
            return []
        finally:
            cursor.close()

# Create a trigger for logging updates on the Medicine table            
def create_trigger(connection):
    try:
        cursor = connection.cursor()
        trigger_query = """                 CREATE TRIGGER after_medicine_update
        AFTER UPDATE ON Medicine
        FOR EACH ROW
        BEGIN
            INSERT INTO MedicineLog (action_type, medicine_id, m_name, price, product_id)
            VALUES ('UPDATE', OLD.medicine_id, OLD.m_name, OLD.price, OLD.product_id);
        END;
        """
        cursor.execute("DROP TRIGGER IF EXISTS after_medicine_update;")
        cursor.execute(trigger_query)
        connection.commit()
        cursor.close()
    except Error as e:
        st.error(f"Error creating trigger: {e}")
        
        


def update_medicine(medicine_id, m_name, price, product_id):
    connection = create_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("UPDATE Medicine SET m_name = %s, price = %s, product_id = %s WHERE medicine_id = %s",
                           (m_name, price, product_id, medicine_id))
            connection.commit()
            st.success("Medicine updated successfully!")
        except Error as e:
            st.error(f"Error updating medicine: {e}")
        finally:
            cursor.close()

# Delete medicine
def delete_medicine(medicine_id):
    connection = create_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("DELETE FROM Medicine WHERE medicine_id = %s", (medicine_id,))
            connection.commit()
            st.success("Medicine deleted successfully!")
        except Error as e:
            st.error(f"Error deleting medicine: {e}")
        finally:
            cursor.close()



#Trigger query          
def create_medicine_update_trigger():
    connection = create_connection()
    if connection:
        try:
            cursor = connection.cursor()
            trigger_query = """
            CREATE TRIGGER after_medicine_update
            AFTER UPDATE ON Medicine
            FOR EACH ROW
            BEGIN
                INSERT INTO MedicineLog (action_type, medicine_id, m_name, price, product_id, action_time)
                VALUES ('UPDATE', OLD.medicine_id, OLD.m_name, OLD.price, OLD.product_id, NOW());
            END;
            """
            cursor.execute("DROP TRIGGER IF EXISTS after_medicine_update;")
            cursor.execute(trigger_query)
            connection.commit()
            st.success("Trigger for Medicine updates created successfully!")
        except Error as e:
            st.error(f"Error creating trigger: {e}")
        finally:
            cursor.close()
  

# Medicine Management UI
def medicine_management():
    st.header("Medicine Management")

    # Sidebar for choosing CRUD operations
    operation = st.sidebar.selectbox("Select Operation", ["Add Medicine", "Update Medicine", "Delete Medicine", "View Medicines"])

    if operation == "Add Medicine":
        st.subheader("Add New Medicine")
        m_name = st.text_input("Medicine Name")
        price = st.number_input("Price", min_value=0.0)
        product_id = st.number_input("Product ID", min_value=1)
        
        if st.button("Add Medicine"):
            if m_name and price and product_id:
                insert_medicine(m_name, price, product_id)
            else:
                st.warning("Please fill in all fields")

    elif operation == "Update Medicine":
        st.subheader("Update Existing Medicine")
        medicine_id = st.number_input("Enter Medicine ID to Update", min_value=1)
        if medicine_id:
            connection = create_connection()
            if connection:
                cursor = connection.cursor()
                cursor.execute("SELECT * FROM Medicine WHERE medicine_id = %s", (medicine_id,))
                medicine = cursor.fetchone()
                if medicine:
                    m_name = st.text_input("Medicine Name", value=medicine[1])  # Assuming 1 is the index for m_name
                    price = st.number_input("Price", value=medicine[2], min_value=0.0)  # Assuming 2 is the index for price
                    product_id = st.number_input("Product ID", value=medicine[3], min_value=1)  # Assuming 3 is the index for product_id

                    if st.button("Update Medicine"):
                        update_medicine(medicine_id, m_name, price, product_id)
                else:
                    st.error("No medicine found with this ID.")
                cursor.close()

    elif operation == "Delete Medicine":
        st.subheader("Delete Medicine")
        medicine_id = st.number_input("Enter Medicine ID to Delete", min_value=1)
        
        if st.button("Delete Medicine"):
            if medicine_id:
                delete_medicine(medicine_id)
            else:
                st.warning("Please enter a valid Medicine ID")

    elif operation == "View Medicines":
        st.subheader("List of All Medicines")
        medicines = get_medicines()
        if medicines:
            for medicine in medicines:
                st.write(f"ID: {medicine[0]}, Name: {medicine[1]}, Price: {medicine[2]}, Product ID: {medicine[3]}")
        else:
            st.info("No medicines found")


# Similar CRUD operations for Supplier, Product, Customer, and Purchase Order
# Define only the `insert`, `get`, `update`, and `delete` functions for each of these entities
def insert_supplier(s_name, contact, s_address):
    connection = create_connection()
    cursor = connection.cursor()
    cursor.execute("INSERT INTO Supplier (s_name, contact, s_address) VALUES (%s, %s, %s)", 
                   (s_name, contact, s_address))
    connection.commit()
    cursor.close()

def get_suppliers():
    connection = create_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM Supplier")
    suppliers = cursor.fetchall()
    cursor.close()
    return suppliers

def update_supplier(supplier_id, s_name, contact, s_address):
    connection = create_connection()
    cursor = connection.cursor()
    cursor.execute("UPDATE Supplier SET s_name = %s, contact = %s, s_address = %s WHERE supplier_id = %s",
                   (s_name, contact, s_address, supplier_id))
    connection.commit()
    cursor.close()

def delete_supplier(supplier_id):
    connection = create_connection()
    cursor = connection.cursor()
    cursor.execute("DELETE FROM Supplier WHERE supplier_id = %s", (supplier_id,))
    connection.commit()
    cursor.close()
    
    
# Add a new product
def insert_product(p_name, category, stock_quantity, supplier_id):
    connection = create_connection()
    if connection:
        cursor = connection.cursor()
        query = "INSERT INTO Product (p_name, category, stock_quantity, supplier_id) VALUES (%s, %s, %s, %s)"
        cursor.execute(query, (p_name, category, stock_quantity, supplier_id))
        connection.commit()
        cursor.close()

# Retrieve all products
def get_products():
    connection = create_connection()
    if connection:
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM Product")
        products = cursor.fetchall()
        cursor.close()
        return products

# Update a product record
def update_product(product_id, p_name, category, stock_quantity, supplier_id):
    connection = create_connection()
    if connection:
        cursor = connection.cursor()
        query = "UPDATE Product SET p_name = %s, category = %s, stock_quantity = %s, supplier_id = %s WHERE product_id = %s"
        cursor.execute(query, (p_name, category, stock_quantity, supplier_id, product_id))
        connection.commit()
        cursor.close()

# Delete a product
def delete_product(product_id):
    connection = create_connection()
    if connection:
        cursor = connection.cursor()
        query = "DELETE FROM Product WHERE product_id = %s"
        cursor.execute(query, (product_id,))
        connection.commit()
        cursor.close()


# Add a new customer
def insert_customer(c_name, contact, c_address):
    connection = create_connection()
    if connection:
        cursor = connection.cursor()
        query = "INSERT INTO Customer (c_name, contact, c_address) VALUES (%s, %s, %s)"
        cursor.execute(query, (c_name, contact, c_address))
        connection.commit()
        cursor.close()

# Retrieve all customers
def get_customers():
    connection = create_connection()
    if connection:
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM Customer")
        customers = cursor.fetchall()
        cursor.close()
        return customers

# Update a customer record
def update_customer(customer_id, c_name, contact, c_address):
    connection = create_connection()
    if connection:
        cursor = connection.cursor()
        query = "UPDATE Customer SET c_name = %s, contact = %s, c_address = %s WHERE customer_id = %s"
        cursor.execute(query, (c_name, contact, c_address, customer_id))
        connection.commit()
        cursor.close()

# Delete a customer
def delete_customer(customer_id):
    connection = create_connection()
    if connection:
        cursor = connection.cursor()
        query = "DELETE FROM Customer WHERE customer_id = %s"
        cursor.execute(query, (customer_id,))
        connection.commit()
        cursor.close()

def insert_purchase_order(total_amount, customer_id, quantity=0):
    """
    Inserts a new purchase order into the database with total_amount, customer_id, and optional quantity.
    """
    connection = create_connection()
    if connection:
        cursor = connection.cursor()
        # Ensure that the quantity is passed correctly, default is 0 if not provided.
        query = "INSERT INTO Purchase_Order (total_amount, customer_id, quantity) VALUES (%s, %s, %s)"
        cursor.execute(query, (total_amount, customer_id, quantity))
        connection.commit()
        cursor.close()


# Retrieve all purchase orders
def get_purchase_orders():
    """
    Retrieves all purchase orders from the database.
    """
    connection = create_connection()
    if connection:
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM Purchase_Order")
        purchase_orders = cursor.fetchall()
        cursor.close()
        return purchase_orders


# Update a purchase order
def update_purchase_order(order_id, total_amount, customer_id, quantity=None):
    """
    Updates an existing purchase order with new total_amount, customer_id, and optionally quantity.
    """
    connection = create_connection()
    if connection:
        cursor = connection.cursor()
        # Prepare the update query with quantity if provided
        if quantity is not None:
            query = "UPDATE Purchase_Order SET total_amount = %s, customer_id = %s, quantity = %s WHERE order_id = %s"
            cursor.execute(query, (total_amount, customer_id, quantity, order_id))
        else:
            query = "UPDATE Purchase_Order SET total_amount = %s, customer_id = %s WHERE order_id = %s"
            cursor.execute(query, (total_amount, customer_id, order_id))
        connection.commit()
        cursor.close()


# Delete a purchase order
def delete_purchase_order(order_id):
    """
    Deletes a purchase order from the database based on the given order_id.
    """
    connection = create_connection()
    if connection:
        cursor = connection.cursor()
        query = "DELETE FROM Purchase_Order WHERE order_id = %s"
        cursor.execute(query, (order_id,))
        connection.commit()
        cursor.close()

        
# Function to log out the admin
def logout():
    if "logged_in" in st.session_state:
        del st.session_state["logged_in"]
    st.success("Logged out successfully ! 🥰Have nice day😊")
    



# Similar CRUD functions for Product, Customer, Purchase Order (not shown here to save space)

# Streamlit UI for CRUD Operations
def main():
    st.title("Medicine 💊 Supply 🚛 Management System")

    if "logged_in" not in st.session_state:
        admin_login_signup()
    elif st.session_state.logged_in:
        menu = ["Dashboard", "Medicine", "Supplier", "Product", "Customer", "Purchase Order", "Reports"]
        choice = st.sidebar.selectbox("Select a category", menu)
        
        # Show logout button
        if st.button("Logout"):
            logout()
            
        if choice == "Reports":
            reports()
           

        if choice == "Dashboard":
            show_dashboard()  # Call the dashboard function    
            
        if choice == "Dashboard":
            dashboard()
        else:
            fields_dict = {
                "Medicine": {"m_name": 'str', "price": 'float', "product_id": 'int'},
                "Supplier": {"s_name": 'str', "contact": 'str', "s_address": 'str'},
                "Product": {"p_name": 'str', "category": 'str', "stock_quantity": 'int', "supplier_id": 'int'},
                "Customer": {"c_name": 'str', "contact": 'str', "c_address": 'str'},
                "Purchase Order": {"total_amount": 'float', "customer_id": 'int'}
            }

            crud_dict = {
                "Medicine": (insert_medicine, get_medicines, update_medicine, delete_medicine),
                "Supplier": (insert_supplier, get_suppliers, update_supplier, delete_supplier),
                "Product": (insert_product, get_products, update_product, delete_product),
                "Customer": (insert_customer, get_customers, update_customer, delete_customer),
                "Purchase Order": (insert_purchase_order, get_purchase_orders, update_purchase_order, delete_purchase_order)
            }
            
            if choice in crud_dict:
                crud_operations(choice, *crud_dict[choice], fields_dict[choice])
            
            
   
  

   
        
        # Adding a clickable URL that opens a profile
        st.sidebar.markdown("""
            [Insta_profiles of Designer](https://www.instagram.com/_veeresh_ganji_/?next=%2F)
        """)
  
        


if __name__ == "__main__":
    create_medicine_update_trigger()  # Ensure the trigger exists
    main()
