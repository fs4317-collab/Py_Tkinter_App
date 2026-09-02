# Py_Tkinter_App

Copyright © 2026 Felix Soto Toro. All rights reserved.  
This project is provided for viewing and portfolio purposes only. No permission is granted to copy, modify, distribute, or use this code without prior written permission.

---

A Python/Tkinter inventory management application designed to simplify the tracking of machine parts and maintenance inventory. The application uses MySQL to manage part information and inventory levels, supports scanning or entering part numbers, adding and removing stock, and recording parts used on Machine 1 or Machine 2. It provides a simple interface for maintaining accurate, real-time inventory records and helps reduce manual tracking during equipment maintenance.

## Application Interface & Workflow Demonstration

Below is a visual walkthrough showing how the Tkinter application interacts directly with the MySQL database when executing common barcode operations.

### Initial System Setup

The main Tkinter application interface provides a single entry point for scanning or typing part numbers, accompanied by dedicated action controls:

*(Tkinter Application Interface Screenshot)*

Before taking any action, consider the initial baseline records across both database tables:
* **`parts_inventory` Table:** Part `100005` (**Conveyor Drive Motor**) starts with **5 units** in stock.
* **`parts_usage` Table:** The `Machine_1` and `Machine_2` usage columns for all parts read **0**.

*(Initial `parts_inventory` Table Screenshot)*  
*(Initial `parts_usage` Table Screenshot)*

---

### Step 1: Adding Inventory via Barcode Scanner

Using the connected USB barcode scanner, part number `100005` is scanned into the application's input field. Clicking the **Add Inventory** button executes the database transaction.

1. Scan part number **`100005`**.
2. Click **Add Inventory**.
3. A confirmation **Success** message box appears.

*(Add Inventory "Success" Popup Screenshot)*

#### Inventory Verification
Checking the `parts_inventory` table shows that the inventory count for the **Conveyor Drive Motor** has increased from **5 to 6**.

*(`parts_inventory` Table Updated to 6 Screenshot)*

---

### Step 2: Logging Part Consumption on Machine 1

To log part utilization during maintenance, we scan part number **`100005`** again and allocate it to **Machine 1**.

1. Scan part number **`100005`**.
2. Click **Use - Machine 1**.
3. A confirmation **Success** message box appears.

*(Machine 1 Usage "Success" Popup Screenshot)*

#### Dual Table Database Update
The operation updates two database tables in real time:

1. **Usage Table Updated:** The `Machine_1` column on the **Conveyor Drive Motor** row updates from **0 to 1**.
   *(`parts_usage` Table Updated Screenshot)*

2. **Inventory Stock Deducted:** Simultaneously, available stock for the **Conveyor Drive Motor** in `parts_inventory` decrements from **6 back to 5**.
   *(`parts_inventory` Table Updated to 5 Screenshot)*
pip install mysql-connector-python
