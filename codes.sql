-- Create Database
CREATE DATABASE IF NOT EXISTS mdb;
USE mdb;

-- Create Tables
CREATE TABLE IF NOT EXISTS Admin (
    admin_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS Supplier (
    supplier_id INT AUTO_INCREMENT PRIMARY KEY,
    s_name VARCHAR(100) NOT NULL,
    contact VARCHAR(50),
    s_address TEXT
);

CREATE TABLE IF NOT EXISTS Product (
    product_id INT AUTO_INCREMENT PRIMARY KEY,
    p_name VARCHAR(100) NOT NULL,
    category VARCHAR(50),
    stock_quantity INT DEFAULT 0,
    supplier_id INT,
    FOREIGN KEY (supplier_id) REFERENCES Supplier(supplier_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Medicine (
    medicine_id INT AUTO_INCREMENT PRIMARY KEY,
    m_name VARCHAR(100) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    product_id INT,
    FOREIGN KEY (product_id) REFERENCES Product(product_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Customer (
    customer_id INT AUTO_INCREMENT PRIMARY KEY,
    c_name VARCHAR(100) NOT NULL,
    contact VARCHAR(50),
    c_address TEXT
);

CREATE TABLE IF NOT EXISTS Purchase_Order (
    order_id INT AUTO_INCREMENT PRIMARY KEY,
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_amount DECIMAL(10,2) NOT NULL,
    customer_id INT,
    quantity INT DEFAULT 0,
    FOREIGN KEY (customer_id) REFERENCES Customer(customer_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS MedicineLog (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    action_type VARCHAR(10),
    medicine_id INT,
    m_name VARCHAR(100),
    price DECIMAL(10,2),
    product_id INT,
    action_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create Triggers
DELIMITER //

CREATE TRIGGER after_medicine_update
AFTER UPDATE ON Medicine
FOR EACH ROW
BEGIN
    INSERT INTO MedicineLog (action_type, medicine_id, m_name, price, product_id)
    VALUES ('UPDATE', OLD.medicine_id, OLD.m_name, OLD.price, OLD.product_id);
END//

-- Create Stored Procedures
CREATE PROCEDURE GetTableRowCounts()
BEGIN
    SELECT 'Medicine' as table_name, COUNT(*) as record_count FROM Medicine
    UNION ALL
    SELECT 'Supplier', COUNT(*) FROM Supplier
    UNION ALL
    SELECT 'Product', COUNT(*) FROM Product
    UNION ALL
    SELECT 'Customer', COUNT(*) FROM Customer
    UNION ALL
    SELECT 'Purchase_Order', COUNT(*) FROM Purchase_Order;
END//

DELIMITER ;

-- Sample Queries for Reports

-- 1. Supplier Summary (Join Query)
SELECT Supplier.s_name, COUNT(Product.product_id) AS total_products
FROM Supplier
JOIN Product ON Supplier.supplier_id = Product.supplier_id
GROUP BY Supplier.s_name;

-- 2. Premium Suppliers (Nested Query)
SELECT Supplier.s_name, COUNT(Product.product_id) AS total_products
FROM Supplier
JOIN Product ON Supplier.supplier_id = Product.supplier_id
WHERE Product.product_id IN (
    SELECT product_id 
    FROM Medicine 
    WHERE price > (SELECT AVG(price) FROM Medicine)
)
GROUP BY Supplier.s_name;

-- 3. Category-wise Price Average (Aggregate Query)
SELECT category, AVG(Medicine.price) AS avg_price
FROM Product
JOIN Medicine ON Product.product_id = Medicine.product_id
GROUP BY category;

-- Sample Data Insertion

-- Insert Suppliers
INSERT INTO Supplier (s_name, contact, s_address) VALUES
('MedSupply Corp', '+1-123-456-7890', '123 Supply Street, Medical District'),
('PharmaCare Ltd', '+1-234-567-8901', '456 Pharma Avenue, Health City');

-- Insert Products
INSERT INTO Product (p_name, category, stock_quantity, supplier_id) VALUES
('Generic Medicine', 'General', 100, 1),
('Pain Relief', 'Analgesics', 150, 1),
('Antibiotics', 'Prescription', 75, 2);

-- Insert Medicines
INSERT INTO Medicine (m_name, price, product_id) VALUES
('Paracetamol', 9.99, 1),
('Ibuprofen', 12.99, 2),
('Amoxicillin', 24.99, 3);

-- Insert Customers
INSERT INTO Customer (c_name, contact, c_address) VALUES
('John Doe', '+1-345-678-9012', '789 Patient Road'),
('Jane Smith', '+1-456-789-0123', '321 Customer Lane');

-- Insert Purchase Orders
INSERT INTO Purchase_Order (total_amount, customer_id, quantity) VALUES
(49.95, 1, 5),
(129.90, 2, 10);

-- Additional Useful Queries

-- 1. View Low Stock Products
CREATE VIEW low_stock_products AS
SELECT p_name, category, stock_quantity
FROM Product
WHERE stock_quantity < 50;

-- 2. View Total Sales by Customer
CREATE VIEW customer_sales AS
SELECT 
    c.c_name,
    COUNT(po.order_id) as total_orders,
    SUM(po.total_amount) as total_spent
FROM Customer c
LEFT JOIN Purchase_Order po ON c.customer_id = po.customer_id
GROUP BY c.customer_id, c.c_name;

-- 3. View Medicine Stock Value
CREATE VIEW medicine_stock_value AS
SELECT 
    m.m_name,
    m.price,
    p.stock_quantity,
    (m.price * p.stock_quantity) as total_value
FROM Medicine m
JOIN Product p ON m.product_id = p.product_id;

-- 4. Index for Better Performance
CREATE INDEX idx_medicine_price ON Medicine(price);
CREATE INDEX idx_product_category ON Product(category);
CREATE INDEX idx_supplier_name ON Supplier(s_name);s