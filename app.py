import streamlit as st
import mysql.connector
from mysql.connector import Error
import hashlib
import pandas as pd
import matplotlib.pyplot as plt

# =====================================================
# BACKGROUND
# =====================================================
def set_background_from_url():
    bg_url = "https://as1.ftcdn.net/v2/jpg/09/62/34/24/1000_F_962342401_7qC0xdyxBY8BvWbBtsWCmfUMiA2uyTe6.jpg"
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("{bg_url}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

set_background_from_url()

# =====================================================
# DATABASE CONNECTION (SAFE)
# =====================================================
@st.cache_resource
def create_connection():
    try:
        connection = mysql.connector.connect(
            host="mysql-2a0dc9ac-ganjiveeresh09-b774.h.aivencloud.com",
            port=20508,   # must be int
            user="avnadmin",
            password="AVNS_5Opa9v9Cu_ZOaO4dm1R",
            database="mdb",
            ssl_disabled=False
        )
        return connection if connection.is_connected() else None

    except Error as e:
        st.error(f"Error connecting to database: {e}")
        return None

# =====================================================
# AUTHENTICATION
# =====================================================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_admin_credentials(username, password):
    conn = create_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT 1 FROM Admin WHERE username=%s AND password=%s",
                (username, hash_password(password))
            )
            return cur.fetchone() is not None
        finally:
            cur.close()
    return False

def add_admin(username, password):
    conn = create_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO Admin (username, password) VALUES (%s,%s)",
                (username, hash_password(password))
            )
            conn.commit()
        finally:
            cur.close()

def admin_login_signup():
    st.title("Admin Login / Signup")
    action = st.radio("Choose Action", ["Login", "Signup"])
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button(action):
        if action == "Login":
            if check_admin_credentials(username, password):
                st.session_state.logged_in = True
                st.success("Welcome to Medicine Supply Management System 💊")
            else:
                st.error("Invalid credentials")
        else:
            add_admin(username, password)
            st.success("Account created. Please login.")

# =====================================================
# DASHBOARD (COUNT QUERY)
# =====================================================
def count_records(table):
    conn = create_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            return cur.fetchone()[0]
        finally:
            cur.close()
    return 0

def show_dashboard():
    st.header("📊 Dashboard - Record Overview")

    col1, col2, col3 = st.columns(3)
    col1.metric("Medicines", count_records("Medicine"))
    col2.metric("Suppliers", count_records("Supplier"))
    col3.metric("Products", count_records("Product"))

    col4, col5 = st.columns(2)
    col4.metric("Customers", count_records("Customer"))
    col5.metric("Purchase Orders", count_records("Purchase_Order"))

    data = {
        "Table": ["Medicine", "Supplier", "Product", "Customer", "Purchase Order"],
        "Count": [
            count_records("Medicine"),
            count_records("Supplier"),
            count_records("Product"),
            count_records("Customer"),
            count_records("Purchase_Order")
        ]
    }

    df = pd.DataFrame(data)
    st.bar_chart(df.set_index("Table"))

# =====================================================
# PROCEDURE DASHBOARD
# =====================================================
def get_table_row_counts():
    conn = create_connection()
    if conn:
        try:
            cur = conn.cursor(dictionary=True)
            cur.callproc("GetTableRowCounts")
            for result in cur.stored_results():
                return result.fetchall()
        finally:
            cur.close()
    return []

def procedure_dashboard():
    st.header("📋 Procedure-Based Table Counts")
    data = get_table_row_counts()
    if data:
        st.table(pd.DataFrame(data))
    else:
        st.info("No data returned")

# =====================================================
# REPORTS (JOIN / NESTED / AGGREGATE)
# =====================================================
def reports():
    st.header("📈 Analytical Reports")
    choice = st.selectbox(
        "Select Report Type",
        ["Supplier Summary", "Premium Suppliers", "Category-wise Price Average"]
    )

    conn = create_connection()
    if not conn:
        return

    cur = conn.cursor()

    if choice == "Supplier Summary":
        cur.execute("""
            SELECT s.s_name, COUNT(p.product_id)
            FROM Supplier s
            JOIN Product p ON s.supplier_id=p.supplier_id
            GROUP BY s.s_name
        """)
        st.table(pd.DataFrame(cur.fetchall(), columns=["Supplier", "Products"]))

    elif choice == "Premium Suppliers":
        cur.execute("""
            SELECT s.s_name, COUNT(p.product_id)
            FROM Supplier s
            JOIN Product p ON s.supplier_id=p.supplier_id
            WHERE p.product_id IN (
                SELECT product_id FROM Medicine
                WHERE price > (SELECT AVG(price) FROM Medicine)
            )
            GROUP BY s.s_name
        """)
        st.table(pd.DataFrame(cur.fetchall(), columns=["Supplier", "Products"]))

    else:
        cur.execute("""
            SELECT category, AVG(m.price)
            FROM Product p
            JOIN Medicine m ON p.product_id=m.product_id
            GROUP BY category
        """)
        st.table(pd.DataFrame(cur.fetchall(), columns=["Category", "Avg Price"]))

    cur.close()

# =====================================================
# GENERIC CRUD TEMPLATE
# =====================================================
def crud_operations(entity, insert_fn, get_fn, update_fn, delete_fn, fields):
    st.header(f"{entity} Management")
    action = st.radio("Action", ["Add", "View", "Update", "Delete"])

    if action == "Add":
        data = {}
        for f, t in fields.items():
            data[f] = st.text_input(f) if t == "str" else st.number_input(f, min_value=0)
        if st.button(f"Add {entity}"):
            insert_fn(**data)

    elif action == "View":
        st.table(get_fn())

    elif action == "Update":
        rid = st.number_input(f"{entity} ID", min_value=1)
        data = {}
        for f, t in fields.items():
            data[f] = st.text_input(f) if t == "str" else st.number_input(f, min_value=0)
        if st.button("Update"):
            update_fn(rid, **data)

    else:
        rid = st.number_input(f"{entity} ID", min_value=1)
        if st.button("Delete"):
            delete_fn(rid)

# =====================================================
# MEDICINE CRUD
# =====================================================
def insert_medicine(m_name, price, product_id):
    conn = create_connection()
    if conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO Medicine (m_name, price, product_id) VALUES (%s,%s,%s)",
            (m_name, price, product_id)
        )
        conn.commit()
        cur.close()

def get_medicines():
    conn = create_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM Medicine")
    data = cur.fetchall()
    cur.close()
    return data

def update_medicine(mid, m_name, price, product_id):
    conn = create_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE Medicine SET m_name=%s, price=%s, product_id=%s WHERE medicine_id=%s",
        (m_name, price, product_id, mid)
    )
    conn.commit()
    cur.close()

def delete_medicine(mid):
    conn = create_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM Medicine WHERE medicine_id=%s", (mid,))
    conn.commit()
    cur.close()

# =====================================================
# SUPPLIER / PRODUCT / CUSTOMER / PURCHASE ORDER CRUD
# (UNCHANGED LOGIC, SAFE CURSORS)
# =====================================================
def insert_supplier(s_name, contact, s_address):
    conn = create_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO Supplier VALUES (NULL,%s,%s,%s)", (s_name, contact, s_address))
    conn.commit()
    cur.close()

def get_suppliers():
    conn = create_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM Supplier")
    data = cur.fetchall()
    cur.close()
    return data

def update_supplier(supplier_id, s_name, contact, s_address):
    conn = create_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE Supplier SET s_name=%s, contact=%s, s_address=%s WHERE supplier_id=%s",
        (s_name, contact, s_address, supplier_id)
    )
    conn.commit()
    cur.close()

def delete_supplier(supplier_id):
    conn = create_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM Supplier WHERE supplier_id=%s", (supplier_id,))
    conn.commit()
    cur.close()

# =====================================================
# LOGOUT & MAIN
# =====================================================
def logout():
    st.session_state.clear()
    st.experimental_rerun()

def main():
    st.title("💊 Medicine Supply 🚛 Management System")

    if "logged_in" not in st.session_state:
        admin_login_signup()
        return

    menu = st.sidebar.selectbox(
        "Menu",
        ["Dashboard", "Procedure Dashboard", "Medicine", "Supplier", "Reports"]
    )

    if st.sidebar.button("Logout"):
        logout()

    if menu == "Dashboard":
        show_dashboard()
    elif menu == "Procedure Dashboard":
        procedure_dashboard()
    elif menu == "Medicine":
        crud_operations(
            "Medicine",
            insert_medicine,
            get_medicines,
            update_medicine,
            delete_medicine,
            {"m_name": "str", "price": "int", "product_id": "int"}
        )
    elif menu == "Supplier":
        crud_operations(
            "Supplier",
            insert_supplier,
            get_suppliers,
            update_supplier,
            delete_supplier,
            {"s_name": "str", "contact": "str", "s_address": "str"}
        )
    else:
        reports()

    st.sidebar.markdown(
        "[Instagram – Designer](https://www.instagram.com/_veeresh_ganji_/)"
    )

if __name__ == "__main__":
    main()

