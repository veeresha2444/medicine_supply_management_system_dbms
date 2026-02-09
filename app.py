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
# DATABASE CONNECTION
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
        cur = conn.cursor()
        cur.execute(
            "SELECT 1 FROM admin WHERE username=%s AND password=%s",
            (username, hash_password(password))
        )
        result = cur.fetchone()
        cur.close()
        return result is not None
    return False

def add_admin(username, password):
    conn = create_connection()
    if conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO admin (username, password) VALUES (%s,%s)",
            (username, hash_password(password))
        )
        conn.commit()
        cur.close()

def admin_login_signup():
    st.title("Admin Login / Signup")
    choice = st.radio("Choose Action", ["Login", "Signup"])
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button(choice):
        if choice == "Login":
            if check_admin_credentials(username, password):
                st.session_state.logged_in = True
                st.success("Welcome to Medicine Supply Management System 💊")
            else:
                st.error("Invalid username or password")
        else:
            add_admin(username, password)
            st.success("Account created. Please login.")

# =====================================================
# DASHBOARD
# =====================================================
def count_records(table):
    conn = create_connection()
    if conn:
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        cur.close()
        return count
    return 0

def show_dashboard():
    st.header("📊 Dashboard Overview")

    col1, col2, col3 = st.columns(3)
    col1.metric("Medicines", count_records("medicine"))
    col2.metric("Suppliers", count_records("supplier"))
    col3.metric("Products", count_records("product"))

    col4, col5 = st.columns(2)
    col4.metric("Customers", count_records("customer"))
    col5.metric("Orders", count_records("purchase_order"))

# =====================================================
# PROCEDURE DASHBOARD
# =====================================================
def get_table_row_counts():
    conn = create_connection()
    if conn:
        cur = conn.cursor(dictionary=True)
        cur.callproc("GetTableRowCounts")
        for result in cur.stored_results():
            data = result.fetchall()
        cur.close()
        return data
    return []

def procedure_dashboard():
    st.subheader("📊 Stored Procedure Dashboard")
    data = get_table_row_counts()
    if data:
        st.table(pd.DataFrame(data))
    else:
        st.info("No data returned")

# =====================================================
# REPORTS
# =====================================================
def reports():
    st.header("📈 Analytical Reports")
    option = st.selectbox(
        "Select Report",
        ["Supplier Summary", "Premium Suppliers", "Category-wise Price Average"]
    )

    conn = create_connection()
    if not conn:
        return
    cur = conn.cursor()

    if option == "Supplier Summary":
        cur.execute("""
            SELECT s.s_name, COUNT(p.product_id)
            FROM supplier s
            JOIN product p ON s.supplier_id=p.supplier_id
            GROUP BY s.s_name
        """)
        st.table(pd.DataFrame(cur.fetchall(), columns=["Supplier", "Products"]))

    elif option == "Premium Suppliers":
        cur.execute("""
            SELECT s.s_name, COUNT(p.product_id)
            FROM supplier s
            JOIN product p ON s.supplier_id=p.supplier_id
            WHERE p.product_id IN (
                SELECT product_id FROM medicine
                WHERE price > (SELECT AVG(price) FROM medicine)
            )
            GROUP BY s.s_name
        """)
        st.table(pd.DataFrame(cur.fetchall(), columns=["Supplier", "Products"]))

    else:
        cur.execute("""
            SELECT category, AVG(m.price)
            FROM product p
            JOIN medicine m ON p.product_id=m.product_id
            GROUP BY category
        """)
        st.table(pd.DataFrame(cur.fetchall(), columns=["Category", "Avg Price"]))

    cur.close()

# =====================================================
# MEDICINE CRUD
# =====================================================
def medicine_crud():
    st.subheader("Medicine Management")
    action = st.radio("Action", ["Add", "View", "Update", "Delete"])

    conn = create_connection()
    if not conn:
        return
    cur = conn.cursor()

    if action == "Add":
        name = st.text_input("Medicine Name")
        price = st.number_input("Price", min_value=0.0)
        pid = st.number_input("Product ID", min_value=1)
        if st.button("Add Medicine"):
            cur.execute(
                "INSERT INTO medicine (m_name, price, product_id) VALUES (%s,%s,%s)",
                (name, price, pid)
            )
            conn.commit()
            st.success("Medicine added")

    elif action == "View":
        cur.execute("SELECT * FROM medicine")
        st.table(cur.fetchall())

    elif action == "Update":
        mid = st.number_input("Medicine ID", min_value=1)
        name = st.text_input("New Name")
        price = st.number_input("New Price", min_value=0.0)
        pid = st.number_input("New Product ID", min_value=1)
        if st.button("Update Medicine"):
            cur.execute(
                "UPDATE medicine SET m_name=%s, price=%s, product_id=%s WHERE medicine_id=%s",
                (name, price, pid, mid)
            )
            conn.commit()
            st.success("Medicine updated")

    else:
        mid = st.number_input("Medicine ID", min_value=1)
        if st.button("Delete Medicine"):
            cur.execute(
                "DELETE FROM medicine WHERE medicine_id=%s",
                (mid,)
            )
            conn.commit()
            st.success("Medicine deleted")

    cur.close()

# =====================================================
# LOGOUT
# =====================================================
def logout():
    st.session_state.clear()
    st.experimental_rerun()

# =====================================================
# MAIN
# =====================================================
def main():
    st.title("💊 Medicine Supply 🚛 Management System")

    if "logged_in" not in st.session_state:
        admin_login_signup()
        return

    menu = st.sidebar.selectbox(
        "Menu",
        ["Dashboard", "Procedure Dashboard", "Medicine", "Reports"]
    )

    if st.sidebar.button("Logout"):
        logout()

    if menu == "Dashboard":
        show_dashboard()
    elif menu == "Procedure Dashboard":
        procedure_dashboard()
    elif menu == "Medicine":
        medicine_crud()
    else:
        reports()

    st.sidebar.markdown(
        "[Instagram – Designer](https://www.instagram.com/_veeresh_ganji_/)"
    )

if __name__ == "__main__":
    main()
