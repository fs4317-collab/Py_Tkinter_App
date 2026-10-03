import tkinter as tk
from tkinter import messagebox, filedialog
import mysql.connector
import csv
import os
import re
from datetime import datetime

# ============================================================
# Database connection
# ============================================================

def connect_db():
    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="YOUR PASSWORD"
    )

    cursor = db.cursor()
    cursor.execute(
        "CREATE DATABASE IF NOT EXISTS repair_parts_inventory"
    )
    cursor.close()
    db.close()

    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="YOUR PASSWORD",
        database="repair_parts_inventory"
    )

# ============================================================
# Material Number Cleaning
# ============================================================

def clean_scanned_material(value):
    if value is None:
        return ""

    value = str(value)
    value = value.replace("\r", "")
    value = value.replace("\n", "")
    value = value.replace("\t", "")

    return value.strip()


def normalize_material(value):
    if value is None:
        return ""

    value = str(value).strip().upper()

    return re.sub(
        r"[^A-Z0-9]",
        "",
        value
    )

# ============================================================
# Resolve Scanned Material Number
# ============================================================

def resolve_material_number(cursor, scanned_material):
    scanned_material = clean_scanned_material(
        scanned_material
    )

    if not scanned_material:
        return None, "EMPTY"

    cursor.execute(
        """
        SELECT Material
        FROM master_parts_inventory
        WHERE Material = %s
        """,
        (scanned_material,)
    )

    result = cursor.fetchone()

    if result:
        return result[0], "EXACT"

    normalized_scan = normalize_material(
        scanned_material
    )

    if not normalized_scan:
        return None, "NOT_FOUND"

    cursor.execute(
        """
        SELECT Material
        FROM master_parts_inventory
        """
    )

    materials = cursor.fetchall()
    normalized_matches = []

    for row in materials:
        database_material = str(
            row[0]
        ).strip()

        normalized_database_material = normalize_material(
            database_material
        )

        if (
            normalized_database_material
            and normalized_database_material == normalized_scan
        ):
            normalized_matches.append(
                database_material
            )

    if len(normalized_matches) == 1:
        return normalized_matches[0], "NORMALIZED"

    if len(normalized_matches) > 1:
        return normalized_matches, "AMBIGUOUS"

    possible_matches = []

    for row in materials:
        database_material = str(
            row[0]
        ).strip()

        normalized_database_material = normalize_material(
            database_material
        )

        if len(normalized_database_material) < 4:
            continue

        if normalized_database_material in normalized_scan:
            possible_matches.append(
                database_material
            )

    possible_matches = list(
        dict.fromkeys(possible_matches)
    )

    if len(possible_matches) == 0:
        return None, "NOT_FOUND"

    if len(possible_matches) == 1:
        return possible_matches[0], "CONTAINED"

    return possible_matches, "AMBIGUOUS"

# ============================================================
# Display Scanner Match Error
# ============================================================

def show_material_match_error(
    scanned_material,
    resolved_material,
    match_type
):
    if match_type == "EMPTY":
        messagebox.showwarning(
            "Missing Material",
            "Please enter or scan a material number."
        )
        return

    if match_type == "NOT_FOUND":
        messagebox.showerror(
            "Part Not Found",
            f"The scanned material could not be matched "
            f"to the master parts catalog.\n\n"
            f"Scanned value:\n{scanned_material}\n\n"
            f"Please verify the material number."
        )
        return

    if match_type == "AMBIGUOUS":
        possible = "\n".join(
            str(x)
            for x in resolved_material
        )

        messagebox.showerror(
            "Multiple Parts Found",
            f"The scanner value matches more than one "
            f"material number.\n\n"
            f"Scanned value:\n{scanned_material}\n\n"
            f"Possible matches:\n{possible}\n\n"
            f"The transaction was NOT completed."
        )

# ============================================================
# Create Inventory Table
# ============================================================

def create_inventory_table(cursor):
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS inventory (
            Material VARCHAR(50) NOT NULL,
            Description VARCHAR(255),
            Price DECIMAL(12,2),
            In_Stock INT NOT NULL DEFAULT 0,
            PRIMARY KEY (Material),
            FOREIGN KEY (Material)
                REFERENCES master_parts_inventory(Material)
        )
        """
    )

# ============================================================
# Create Machine Usage Table
# ============================================================

def create_machine_usage_table(cursor):
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS machine_parts_usage (
            Material VARCHAR(50) NOT NULL,
            Description VARCHAR(255),
            Price DECIMAL(12,2),
            Machine_1 INT NOT NULL DEFAULT 0,
            Machine_2 INT NOT NULL DEFAULT 0,
            PRIMARY KEY (Material),
            FOREIGN KEY (Material)
                REFERENCES master_parts_inventory(Material)
        )
        """
    )
    
# ============================================================
# Add Inventory
# ============================================================

def add_inventory():
    scanned_material = clean_scanned_material(
        material_entry.get()
    )

    if not scanned_material:
        messagebox.showwarning(
            "Missing Material",
            "Please enter or scan a material number."
        )
        return

    db = None
    cursor = None

    try:
        db = connect_db()
        cursor = db.cursor()

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = 'repair_parts_inventory'
            AND table_name = 'master_parts_inventory'
            """
        )

        if cursor.fetchone()[0] == 0:
            messagebox.showerror(
                "Master Table Missing",
                "The master_parts_inventory table does not exist.\n\n"
                "Please import the Master Parts CSV first."
            )
            return

        create_inventory_table(cursor)

        material, match_type = resolve_material_number(
            cursor,
            scanned_material
        )

        if match_type in (
            "EMPTY",
            "NOT_FOUND",
            "AMBIGUOUS"
        ):
            show_material_match_error(
                scanned_material,
                material,
                match_type
            )
            return

        cursor.execute(
            """
            SELECT
                Material,
                Description,
                Price
            FROM master_parts_inventory
            WHERE Material = %s
            """,
            (material,)
        )

        master_part = cursor.fetchone()

        if not master_part:
            messagebox.showerror(
                "Part Not Found",
                f"Material {material} was not found "
                "in the master parts catalog."
            )
            return

        cursor.execute(
            """
            SELECT In_Stock
            FROM inventory
            WHERE Material = %s
            """,
            (material,)
        )

        existing = cursor.fetchone()

        if existing:
            cursor.execute(
                """
                UPDATE inventory
                SET In_Stock = In_Stock + 1
                WHERE Material = %s
                """,
                (material,)
            )

            new_stock = existing[0] + 1

        else:
            cursor.execute(
                """
                INSERT INTO inventory
                (
                    Material,
                    Description,
                    Price,
                    In_Stock
                )
                VALUES (%s, %s, %s, 1)
                """,
                master_part
            )

            new_stock = 1

        db.commit()

        if scanned_material != material:
            scan_message = (
                f"Scanned:\n{scanned_material}\n\n"
                f"Matched Material:\n{material}\n\n"
            )
        else:
            scan_message = (
                f"Material:\n{material}\n\n"
            )

        messagebox.showinfo(
            "Inventory Updated",
            scan_message
            + f"Description:\n{master_part[1]}\n\n"
            + f"Price: ${float(master_part[2]):,.2f}\n"
            + f"Quantity in Stock: {new_stock}"
        )

        material_entry.delete(0, tk.END)
        material_entry.focus()

    except mysql.connector.Error as err:
        if db:
            db.rollback()

        messagebox.showerror(
            "Database Error",
            f"Database error:\n\n{err}"
        )

    except Exception as err:
        if db:
            db.rollback()

        messagebox.showerror(
            "Error",
            f"An error occurred:\n\n{err}"
        )

    finally:
        if cursor:
            cursor.close()

        if db:
            db.close()
            
# ============================================================
# Remove Inventory
# ============================================================

def remove_inventory():
    scanned_material = clean_scanned_material(
        material_entry.get()
    )

    if not scanned_material:
        messagebox.showwarning(
            "Missing Material",
            "Please enter or scan a material number."
        )
        return

    db = None
    cursor = None

    try:
        db = connect_db()
        cursor = db.cursor()

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = 'repair_parts_inventory'
            AND table_name = 'inventory'
            """
        )

        if cursor.fetchone()[0] == 0:
            messagebox.showerror(
                "Inventory Missing",
                "The inventory table does not exist yet."
            )
            return

        material, match_type = resolve_material_number(
            cursor,
            scanned_material
        )

        if match_type in (
            "EMPTY",
            "NOT_FOUND",
            "AMBIGUOUS"
        ):
            show_material_match_error(
                scanned_material,
                material,
                match_type
            )
            return

        cursor.execute(
            """
            SELECT
                Material,
                Description,
                Price,
                In_Stock
            FROM inventory
            WHERE Material = %s
            FOR UPDATE
            """,
            (material,)
        )

        inventory_part = cursor.fetchone()

        if not inventory_part:
            messagebox.showerror(
                "Part Not Found",
                f"Material {material} is not currently "
                "in inventory."
            )
            return

        material_no = inventory_part[0]
        description = inventory_part[1]
        price = inventory_part[2]
        current_stock = inventory_part[3]

        if current_stock <= 0:
            messagebox.showwarning(
                "No Inventory Available",
                f"Material {material} currently has "
                "0 items in stock.\n\n"
                "Nothing was removed."
            )
            return

        cursor.execute(
            """
            UPDATE inventory
            SET In_Stock = In_Stock - 1
            WHERE Material = %s
            AND In_Stock > 0
            """,
            (material,)
        )

        if cursor.rowcount != 1:
            raise Exception(
                "Inventory could not be updated."
            )

        db.commit()

        remaining_stock = current_stock - 1

        if scanned_material != material:
            scan_message = (
                f"Scanned:\n{scanned_material}\n\n"
                f"Matched Material:\n{material}\n\n"
            )
        else:
            scan_message = (
                f"Material:\n{material}\n\n"
            )

        messagebox.showinfo(
            "Inventory Removed",
            scan_message
            + f"Description:\n{description}\n\n"
            + f"Price: ${float(price):,.2f}\n"
            + f"Remaining Inventory: {remaining_stock}"
        )

        material_entry.delete(0, tk.END)
        material_entry.focus()

    except mysql.connector.Error as err:
        if db:
            db.rollback()

        messagebox.showerror(
            "Database Error",
            f"Database error:\n\n{err}"
        )

    except Exception as err:
        if db:
            db.rollback()

        messagebox.showerror(
            "Error",
            f"An error occurred:\n\n{err}"
        )

    finally:
        if cursor:
            cursor.close()

        if db:
            db.close()

# ============================================================
# Clear Inventory
# ============================================================

def clear_inventory():
    confirm = messagebox.askyesno(
        "Confirm Clear Inventory",
        "Are you sure you want to clear all inventory?\n\n"
        "This will completely erase current inventory records.\n\n"
        "The master parts catalog and machine usage table "
        "will NOT be affected.\n\n"
        "This action cannot be undone.",
        icon="warning"
    )

    if not confirm:
        return

    db = None
    cursor = None

    try:
        db = connect_db()
        cursor = db.cursor()

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = 'repair_parts_inventory'
            AND table_name = 'inventory'
            """
        )

        if cursor.fetchone()[0] == 0:
            messagebox.showinfo(
                "Clear Inventory",
                "The inventory table does not exist yet."
            )
            return

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM inventory
            """
        )

        record_count = cursor.fetchone()[0]

        if record_count == 0:
            messagebox.showinfo(
                "Clear Inventory",
                "Inventory is already empty."
            )
            return

        cursor.execute(
            """
            DELETE FROM inventory
            """
        )

        db.commit()

        messagebox.showinfo(
            "Inventory Cleared",
            f"{record_count} inventory records were deleted.\n\n"
            "The inventory table structure was preserved.\n"
            "The master parts catalog was not changed.\n"
            "Machine usage records were not changed."
        )

        material_entry.delete(0, tk.END)
        material_entry.focus()

    except mysql.connector.Error as err:
        if db:
            db.rollback()

        messagebox.showerror(
            "Database Error",
            f"Database error while clearing inventory:\n\n{err}"
        )

    except Exception as err:
        if db:
            db.rollback()

        messagebox.showerror(
            "Clear Inventory Error",
            f"Could not clear inventory:\n\n{err}"
        )

    finally:
        if cursor:
            cursor.close()

        if db:
            db.close()


# ============================================================
# Clear Machine Usage
# ============================================================

def clear_machine_usage():
    confirm = messagebox.askyesno(
        "Confirm Clear Machine Usage",
        "Are you sure you want to clear all machine usage records?\n\n"
        "This will erase all Machine 1 and Machine 2 usage records.\n\n"
        "The master parts catalog and inventory will NOT be affected.\n\n"
        "This action cannot be undone.",
        icon="warning"
    )

    if not confirm:
        return

    db = None
    cursor = None

    try:
        db = connect_db()
        cursor = db.cursor()

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = 'repair_parts_inventory'
            AND table_name = 'machine_parts_usage'
            """
        )

        if cursor.fetchone()[0] == 0:
            messagebox.showinfo(
                "Clear Machine Usage",
                "The machine usage table does not exist yet."
            )
            return

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM machine_parts_usage
            """
        )

        record_count = cursor.fetchone()[0]

        if record_count == 0:
            messagebox.showinfo(
                "Clear Machine Usage",
                "Machine usage is already empty."
            )
            return

        cursor.execute(
            """
            DELETE FROM machine_parts_usage
            """
        )

        db.commit()

        messagebox.showinfo(
            "Machine Usage Cleared",
            f"{record_count} machine usage records were deleted.\n\n"
            "The machine usage table structure was preserved.\n"
            "The master parts catalog was not changed.\n"
            "Inventory was not changed."
        )

        material_entry.delete(0, tk.END)
        material_entry.focus()

    except mysql.connector.Error as err:
        if db:
            db.rollback()

        messagebox.showerror(
            "Database Error",
            f"Database error while clearing machine usage:\n\n{err}"
        )

    except Exception as err:
        if db:
            db.rollback()

        messagebox.showerror(
            "Clear Machine Usage Error",
            f"Could not clear machine usage:\n\n{err}"
        )

    finally:
        if cursor:
            cursor.close()

        if db:
            db.close()
         
# ============================================================
# Clean Price
# ============================================================

def clean_price(value):
    if value is None:
        return 0.00

    value = str(value).strip()

    if not value:
        return 0.00

    value = value.replace("$", "")
    value = value.replace(",", "")

    try:
        return float(value)
    except ValueError:
        return 0.00


# ============================================================
# Import Master Parts CSV
# Required columns: Material, Description, Price
# ============================================================

def import_csv():
    file_path = filedialog.askopenfilename(
        title="Select Master Parts CSV",
        filetypes=[
            ("CSV Files", "*.csv"),
            ("All Files", "*.*")
        ]
    )

    if not file_path:
        return

    db = None
    cursor = None

    try:
        with open(
            file_path,
            mode="r",
            newline="",
            encoding="utf-8-sig"
        ) as file:
            reader = csv.reader(file)
            rows = list(reader)

        if not rows:
            messagebox.showerror(
                "Import Error",
                "The selected CSV file is empty."
            )
            return

        # Find the row containing the required headers.
        header_index = None

        for i, row in enumerate(rows):
            headers = [
                str(value).strip().lower()
                for value in row
            ]

            if (
                "material" in headers
                and "description" in headers
                and "price" in headers
            ):
                header_index = i
                break

        if header_index is None:
            messagebox.showerror(
                "Import Error",
                "Could not find the required columns.\n\n"
                "The CSV must contain:\n"
                "Material, Description, Price"
            )
            return

        headers = [
            str(value).strip().lower()
            for value in rows[header_index]
        ]

        material_index = headers.index("material")
        description_index = headers.index("description")
        price_index = headers.index("price")

        new_parts = {}

        for row in rows[header_index + 1:]:
            if len(row) <= max(
                material_index,
                description_index,
                price_index
            ):
                continue

            material = str(
                row[material_index]
            ).strip()

            if not material:
                continue

            if material in new_parts:
                continue

            description = str(
                row[description_index]
            ).strip()

            price = clean_price(
                row[price_index]
            )

            new_parts[material] = (
                description,
                price
            )

        if not new_parts:
            messagebox.showerror(
                "Import Error",
                "No valid material numbers were found "
                "in the CSV."
            )
            return

        db = connect_db()
        cursor = db.cursor()

        # Create master table if it does not exist.
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS master_parts_inventory (
                Material VARCHAR(50) NOT NULL,
                Description VARCHAR(255),
                Price DECIMAL(12,2),
                PRIMARY KEY (Material)
            )
            """
        )

        create_inventory_table(cursor)
        create_machine_usage_table(cursor)

        # Get materials currently referenced by inventory.
        cursor.execute(
            """
            SELECT Material
            FROM inventory
            """
        )

        inventory_materials = {
            row[0]
            for row in cursor.fetchall()
        }

        # Get materials currently referenced by usage.
        cursor.execute(
            """
            SELECT Material
            FROM machine_parts_usage
            """
        )

        usage_materials = {
            row[0]
            for row in cursor.fetchall()
        }

        # Get current master catalog.
        cursor.execute(
            """
            SELECT Material
            FROM master_parts_inventory
            """
        )

        existing_master = {
            row[0]
            for row in cursor.fetchall()
        }

        inserted_count = 0
        updated_count = 0

        # Insert or update master parts.
        for material, values in new_parts.items():
            description = values[0]
            price = values[1]

            if material in existing_master:
                cursor.execute(
                    """
                    UPDATE master_parts_inventory
                    SET Description = %s,
                        Price = %s
                    WHERE Material = %s
                    """,
                    (
                        description,
                        price,
                        material
                    )
                )

                updated_count += 1

            else:
                cursor.execute(
                    """
                    INSERT INTO master_parts_inventory
                    (
                        Material,
                        Description,
                        Price
                    )
                    VALUES (%s, %s, %s)
                    """,
                    (
                        material,
                        description,
                        price
                    )
                )

                inserted_count += 1

        # Protect materials currently used by inventory
        # or the usage table.
        protected_materials = (
            inventory_materials
            | usage_materials
        )

        deleted_count = 0
        protected_count = 0

        # Remove obsolete master records only when they
        # are not referenced by another table.
        for material in existing_master:
            if material in new_parts:
                continue

            if material in protected_materials:
                protected_count += 1
                continue

            cursor.execute(
                """
                DELETE FROM master_parts_inventory
                WHERE Material = %s
                """,
                (material,)
            )

            deleted_count += 1

        db.commit()

        messagebox.showinfo(
            "Import Complete",
            "Master Parts CSV imported successfully.\n\n"
            f"Parts processed: {len(new_parts)}\n"
            f"New parts: {inserted_count}\n"
            f"Updated parts: {updated_count}\n"
            f"Old unused parts removed: {deleted_count}\n"
            f"Referenced parts preserved: {protected_count}\n\n"
            "CSV columns:\n"
            "Material, Description, Price"
        )

        material_entry.delete(0, tk.END)
        material_entry.focus()

    except mysql.connector.Error as err:
        if db:
            db.rollback()

        messagebox.showerror(
            "Database Error",
            f"Database error during import:\n\n{err}"
        )

    except Exception as err:
        if db:
            db.rollback()

        messagebox.showerror(
            "Import Error",
            f"Could not import the CSV file:\n\n{err}"
        )

    finally:
        if cursor:
            cursor.close()

        if db:
            db.close()
            
# ============================================================
# Use Part on Machine 1 or Machine 2
# ============================================================

def use_part(machine):
    scanned_material = clean_scanned_material(
        material_entry.get()
    )

    if not scanned_material:
        messagebox.showwarning(
            "Missing Material",
            "Please enter or scan a material number."
        )
        return

    if machine not in (1, 2):
        messagebox.showerror(
            "Machine Error",
            "Invalid machine selection."
        )
        return

    db = None
    cursor = None

    try:
        db = connect_db()
        cursor = db.cursor()

        # Check that inventory table exists.
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = 'repair_parts_inventory'
            AND table_name = 'inventory'
            """
        )

        if cursor.fetchone()[0] == 0:
            messagebox.showerror(
                "Inventory Missing",
                "The inventory table does not exist yet."
            )
            return

        create_machine_usage_table(cursor)

        # Resolve scanned material number.
        material, match_type = resolve_material_number(
            cursor,
            scanned_material
        )

        if match_type in (
            "EMPTY",
            "NOT_FOUND",
            "AMBIGUOUS"
        ):
            show_material_match_error(
                scanned_material,
                material,
                match_type
            )
            return

        # Get inventory information and lock the row.
        cursor.execute(
            """
            SELECT
                Material,
                Description,
                Price,
                In_Stock
            FROM inventory
            WHERE Material = %s
            FOR UPDATE
            """,
            (material,)
        )

        inventory_part = cursor.fetchone()

        if not inventory_part:
            messagebox.showerror(
                "Part Not Found",
                f"Material {material} is not currently "
                "in inventory."
            )
            return

        material_no = inventory_part[0]
        description = inventory_part[1]
        price = inventory_part[2]
        current_stock = inventory_part[3]

        if current_stock <= 0:
            messagebox.showwarning(
                "Out of Stock",
                f"Material {material} has no "
                "inventory remaining."
            )
            return

        # Check whether the material already has
        # a machine usage record.
        cursor.execute(
            """
            SELECT
                Machine_1,
                Machine_2
            FROM machine_parts_usage
            WHERE Material = %s
            FOR UPDATE
            """,
            (material,)
        )

        usage = cursor.fetchone()

        # Create usage record if this is the first use.
        if usage is None:
            cursor.execute(
                """
                INSERT INTO machine_parts_usage
                (
                    Material,
                    Description,
                    Price,
                    Machine_1,
                    Machine_2
                )
                VALUES (%s, %s, %s, 0, 0)
                """,
                (
                    material_no,
                    description,
                    price
                )
            )

            machine_1_count = 0
            machine_2_count = 0

        else:
            machine_1_count = usage[0]
            machine_2_count = usage[1]

        # Record usage for Machine 1.
        if machine == 1:
            machine_1_count += 1

            cursor.execute(
                """
                UPDATE machine_parts_usage
                SET Machine_1 = %s,
                    Description = %s,
                    Price = %s
                WHERE Material = %s
                """,
                (
                    machine_1_count,
                    description,
                    price,
                    material_no
                )
            )

            machine_name = "Machine 1"
            machine_count = machine_1_count

        # Record usage for Machine 2.
        else:
            machine_2_count += 1

            cursor.execute(
                """
                UPDATE machine_parts_usage
                SET Machine_2 = %s,
                    Description = %s,
                    Price = %s
                WHERE Material = %s
                """,
                (
                    machine_2_count,
                    description,
                    price,
                    material_no
                )
            )

            machine_name = "Machine 2"
            machine_count = machine_2_count

        # Remove one item from inventory.
        cursor.execute(
            """
            UPDATE inventory
            SET In_Stock = In_Stock - 1
            WHERE Material = %s
            AND In_Stock > 0
            """,
            (material,)
        )

        if cursor.rowcount != 1:
            raise Exception(
                "Inventory could not be updated."
            )

        db.commit()

        remaining_stock = current_stock - 1

        # Build scanner information for confirmation.
        if scanned_material != material:
            scan_message = (
                f"Scanned:\n{scanned_material}\n\n"
                f"Matched Material:\n{material}\n\n"
            )
        else:
            scan_message = (
                f"Material:\n{material}\n\n"
            )

        messagebox.showinfo(
            "Part Usage Recorded",
            scan_message
            + f"Description:\n{description}\n\n"
            + f"Used on: {machine_name}\n\n"
            + f"{machine_name} Total Used: {machine_count}\n\n"
            + f"Remaining Inventory: {remaining_stock}"
        )

        material_entry.delete(0, tk.END)
        material_entry.focus()

    except mysql.connector.Error as err:
        if db:
            db.rollback()

        messagebox.showerror(
            "Database Error",
            f"Database error:\n\n{err}"
        )

    except Exception as err:
        if db:
            db.rollback()

        messagebox.showerror(
            "Usage Error",
            f"Could not record machine usage:\n\n{err}"
        )

    finally:
        if cursor:
            cursor.close()

        if db:
            db.close()

# ============================================================
# Report Folder
# ============================================================

def get_report_folder():
    try:
        import ctypes
        from ctypes import wintypes

        CSIDL_DESKTOPDIRECTORY = 0x0010
        SHGFP_TYPE_CURRENT = 0

        buffer = ctypes.create_unicode_buffer(
            wintypes.MAX_PATH
        )

        ctypes.windll.shell32.SHGetFolderPathW(
            None,
            CSIDL_DESKTOPDIRECTORY,
            None,
            SHGFP_TYPE_CURRENT,
            buffer
        )

        desktop = buffer.value

        if not desktop:
            desktop = os.path.join(
                os.path.expanduser("~"),
                "Desktop"
            )

    except Exception:
        desktop = os.path.join(
            os.path.expanduser("~"),
            "Desktop"
        )

    report_folder = os.path.join(
        desktop,
        "Parts Inventory Quarterly Reports"
    )

    os.makedirs(
        report_folder,
        exist_ok=True
    )

    return report_folder


# ============================================================
# Get Quarter
# ============================================================

def get_quarter(month):
    if month <= 3:
        return "Q1"

    if month <= 6:
        return "Q2"

    if month <= 9:
        return "Q3"

    return "Q4"


# ============================================================
# Create Inventory CSV Report
# Only includes parts priced at $100 or more
# ============================================================

def create_inventory_report():
    db = None
    cursor = None

    try:
        db = connect_db()
        cursor = db.cursor()

        # Check whether inventory table exists.
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = 'repair_parts_inventory'
            AND table_name = 'inventory'
            """
        )

        if cursor.fetchone()[0] == 0:
            messagebox.showwarning(
                "Inventory Report",
                "The inventory table does not exist yet."
            )
            return

        # Only include parts with a price of $100 or more.
        cursor.execute(
            """
            SELECT
                Material,
                Description,
                Price,
                In_Stock
            FROM inventory
            WHERE Price >= 100
            ORDER BY Material
            """
        )

        rows = cursor.fetchall()

        if not rows:
            messagebox.showinfo(
                "Inventory Report",
                "There are no inventory items with "
                "a price of $100 or more."
            )
            return

        now = datetime.now()
        quarter = get_quarter(now.month)

        date_text = now.strftime("%Y-%m-%d")
        time_text = now.strftime("%H-%M-%S")

        file_name = (
            f"Inventory_Report_{quarter}_"
            f"{date_text}_{time_text}.csv"
        )

        report_folder = get_report_folder()

        file_path = os.path.join(
            report_folder,
            file_name
        )

        with open(
            file_path,
            mode="w",
            newline="",
            encoding="utf-8-sig"
        ) as file:
            writer = csv.writer(file)

            # Report information.
            writer.writerow(
                ["Inventory Report"]
            )

            writer.writerow(
                ["Date", now.strftime("%Y-%m-%d")]
            )

            writer.writerow(
                ["Time", now.strftime("%H:%M:%S")]
            )

            writer.writerow(
                ["Quarter", quarter]
            )

            writer.writerow([])

            # Column headers.
            writer.writerow(
                [
                    "Material",
                    "Description",
                    "Price",
                    "In Stock",
                    "Inventory Value"
                ]
            )

            total_inventory_value = 0

            for row in rows:
                material = row[0]
                description = row[1]
                price = float(row[2] or 0)
                in_stock = int(row[3] or 0)

                inventory_value = (
                    price * in_stock
                )

                total_inventory_value += (
                    inventory_value
                )

                writer.writerow(
                    [
                        material,
                        description,
                        f"{price:.2f}",
                        in_stock,
                        f"{inventory_value:.2f}"
                    ]
                )

            writer.writerow([])

            writer.writerow(
                [
                    "",
                    "",
                    "",
                    "Total Inventory Value",
                    f"{total_inventory_value:.2f}"
                ]
            )

        messagebox.showinfo(
            "Inventory Report Created",
            "Inventory CSV report created successfully.\n\n"
            f"Quarter: {quarter}\n"
            f"Items: {len(rows)}\n"
            "Minimum Price: $100.00\n\n"
            f"Saved to:\n{file_path}"
        )

    except mysql.connector.Error as err:
        messagebox.showerror(
            "Database Error",
            f"Database error while creating report:\n\n{err}"
        )

    except Exception as err:
        messagebox.showerror(
            "Report Error",
            f"Could not create inventory report:\n\n{err}"
        )

    finally:
        if cursor:
            cursor.close()

        if db:
            db.close()


# ============================================================
# Create Machine Usage CSV Report
# ============================================================

def create_machine_usage_report():
    db = None
    cursor = None

    try:
        db = connect_db()
        cursor = db.cursor()

        # Check whether machine usage table exists.
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = 'repair_parts_inventory'
            AND table_name = 'machine_parts_usage'
            """
        )

        if cursor.fetchone()[0] == 0:
            messagebox.showwarning(
                "Machine Usage Report",
                "The machine usage table does not exist yet."
            )
            return

        cursor.execute(
            """
            SELECT
                Material,
                Description,
                Price,
                Machine_1,
                Machine_2
            FROM machine_parts_usage
            ORDER BY Material
            """
        )

        rows = cursor.fetchall()

        if not rows:
            messagebox.showinfo(
                "Machine Usage Report",
                "There are no machine usage records."
            )
            return

        now = datetime.now()
        quarter = get_quarter(now.month)

        date_text = now.strftime("%Y-%m-%d")
        time_text = now.strftime("%H-%M-%S")

        file_name = (
            f"Machine_Usage_Report_{quarter}_"
            f"{date_text}_{time_text}.csv"
        )

        report_folder = get_report_folder()

        file_path = os.path.join(
            report_folder,
            file_name
        )

        with open(
            file_path,
            mode="w",
            newline="",
            encoding="utf-8-sig"
        ) as file:
            writer = csv.writer(file)

            # Report information.
            writer.writerow(
                ["Machine Parts Usage Report"]
            )

            writer.writerow(
                ["Date", now.strftime("%Y-%m-%d")]
            )

            writer.writerow(
                ["Time", now.strftime("%H:%M:%S")]
            )

            writer.writerow(
                ["Quarter", quarter]
            )

            writer.writerow([])

            # Column headers.
            writer.writerow(
                [
                    "Material",
                    "Description",
                    "Price",
                    "Machine 1",
                    "Machine 2",
                    "Total Used"
                ]
            )

            total_machine_1 = 0
            total_machine_2 = 0
            total_used = 0

            for row in rows:
                material = row[0]
                description = row[1]
                price = float(row[2] or 0)
                machine_1 = int(row[3] or 0)
                machine_2 = int(row[4] or 0)

                row_total = (
                    machine_1 + machine_2
                )

                total_machine_1 += machine_1
                total_machine_2 += machine_2
                total_used += row_total

                writer.writerow(
                    [
                        material,
                        description,
                        f"{price:.2f}",
                        machine_1,
                        machine_2,
                        row_total
                    ]
                )

            writer.writerow([])

            writer.writerow(
                [
                    "",
                    "",
                    "",
                    total_machine_1,
                    total_machine_2,
                    total_used
                ]
            )

        messagebox.showinfo(
            "Machine Usage Report Created",
            "Machine usage CSV report created successfully.\n\n"
            f"Quarter: {quarter}\n"
            f"Records: {len(rows)}\n"
            f"Total Parts Used: {total_used}\n\n"
            f"Saved to:\n{file_path}"
        )

    except mysql.connector.Error as err:
        messagebox.showerror(
            "Database Error",
            f"Database error while creating report:\n\n{err}"
        )

    except Exception as err:
        messagebox.showerror(
            "Report Error",
            f"Could not create machine usage report:\n\n{err}"
        )

    finally:
        if cursor:
            cursor.close()

        if db:
            db.close()
            
# ============================================================
# Main Tkinter Window
# ============================================================

root = tk.Tk()
root.title("Parts Inventory Management System")
root.geometry("600x600")
root.resizable(False, False)

# ============================================================
# Professional Blue Color Palette
# ============================================================

BG_COLOR = "#EAF2F8"
HEADER_COLOR = "#1F4E78"
PRIMARY_BLUE = "#5B9BD5"
SECONDARY_BLUE = "#9DC3E6"
LIGHT_BLUE = "#D9EAF7"
DARK_BLUE = "#2F75B5"
TEXT_COLOR = "#1F1F1F"
WHITE = "#FFFFFF"

root.configure(bg=BG_COLOR)


# ============================================================
# Header
# ============================================================

header_frame = tk.Frame(
    root,
    bg=HEADER_COLOR,
    height=75
)

header_frame.pack(
    fill="x"
)

header_frame.pack_propagate(False)

title_label = tk.Label(
    header_frame,
    text="Parts Inventory Management",
    font=("Segoe UI", 20, "bold"),
    bg=HEADER_COLOR,
    fg=WHITE
)

title_label.pack(
    side="left",
    padx=20,
    pady=20
)


# ============================================================
# Import Master Parts CSV Button
# ============================================================

import_button = tk.Button(
    header_frame,
    text="Import Master Parts\nInventory",
    command=import_csv,
    font=("Segoe UI", 9, "bold"),
    bg=SECONDARY_BLUE,
    fg=TEXT_COLOR,
    activebackground=LIGHT_BLUE,
    activeforeground=TEXT_COLOR,
    relief="raised",
    bd=4,
    cursor="hand2",
    padx=18,
    pady=6
)

import_button.pack(
    side="right",
    padx=12,
    pady=8
)

# ============================================================
# Main Content Frame
# ============================================================

main_frame = tk.Frame(
    root,
    bg=BG_COLOR
)

main_frame.pack(
    fill="both",
    expand=True,
    padx=30,
    pady=20
)


# ============================================================
# Material Number Entry
# ============================================================

material_label = tk.Label(
    main_frame,
    text="Material Number",
    font=("Segoe UI", 12, "bold"),
    bg=BG_COLOR,
    fg=TEXT_COLOR
)

material_label.pack(
    pady=(5, 5)
)

material_entry = tk.Entry(
    main_frame,
    font=("Segoe UI", 14),
    justify="center",
    relief="sunken",
    bd=3,
    width=30
)

material_entry.pack(
    pady=(0, 18)
)

material_entry.focus()


# ============================================================
# 3D Button Helper
# ============================================================

def create_3d_button(
    parent,
    text,
    command,
    bg=PRIMARY_BLUE,
    width=24
):
    button = tk.Button(
        parent,
        text=text,
        command=command,
        font=("Segoe UI", 10, "bold"),
        bg=bg,
        fg=TEXT_COLOR,
        activebackground=LIGHT_BLUE,
        activeforeground=TEXT_COLOR,
        width=width,
        relief="raised",
        bd=5,
        cursor="hand2",
        pady=5
    )

    return button


# ============================================================
# Inventory Buttons
# ============================================================

inventory_frame = tk.Frame(
    main_frame,
    bg=BG_COLOR
)

inventory_frame.pack(
    pady=5
)

add_button = create_3d_button(
    inventory_frame,
    "Add Inventory",
    add_inventory,
    SECONDARY_BLUE
)

add_button.grid(
    row=0,
    column=0,
    padx=6,
    pady=5
)

remove_button = create_3d_button(
    inventory_frame,
    "Remove Inventory",
    remove_inventory,
    SECONDARY_BLUE
)

remove_button.grid(
    row=0,
    column=1,
    padx=6,
    pady=5
)


# ============================================================
# Machine Usage Buttons
# ============================================================

machine_frame = tk.Frame(
    main_frame,
    bg=BG_COLOR
)

machine_frame.pack(
    pady=5
)

machine_1_button = create_3d_button(
    machine_frame,
    "Use - Machine 1",
    lambda: use_part(1),
    PRIMARY_BLUE
)

machine_1_button.grid(
    row=0,
    column=0,
    padx=6,
    pady=5
)

machine_2_button = create_3d_button(
    machine_frame,
    "Use - Machine 2",
    lambda: use_part(2),
    PRIMARY_BLUE
)

machine_2_button.grid(
    row=0,
    column=1,
    padx=6,
    pady=5
)


# ============================================================
# Clear Buttons
# ============================================================

clear_frame = tk.Frame(
    main_frame,
    bg=BG_COLOR
)

clear_frame.pack(
    pady=5
)

clear_inventory_button = create_3d_button(
    clear_frame,
    "Clear Inventory",
    clear_inventory,
    LIGHT_BLUE
)

clear_inventory_button.grid(
    row=0,
    column=0,
    padx=6,
    pady=5
)

clear_usage_button = create_3d_button(
    clear_frame,
    "Clear Machine Usage",
    clear_machine_usage,
    LIGHT_BLUE
)

clear_usage_button.grid(
    row=0,
    column=1,
    padx=6,
    pady=5
)


# ============================================================
# Report Section
# ============================================================

report_label = tk.Label(
    main_frame,
    text="Reports",
    font=("Segoe UI", 12, "bold"),
    bg=BG_COLOR,
    fg=HEADER_COLOR
)

report_label.pack(
    pady=(15, 5)
)

report_frame = tk.Frame(
    main_frame,
    bg=BG_COLOR
)

report_frame.pack(
    pady=5
)

inventory_report_button = create_3d_button(
    report_frame,
    "Create Inventory Report",
    create_inventory_report,
    DARK_BLUE
)

inventory_report_button.configure(
    fg=WHITE
)

inventory_report_button.grid(
    row=0,
    column=0,
    padx=6,
    pady=5
)

usage_report_button = create_3d_button(
    report_frame,
    "Create Machine Usage Report",
    create_machine_usage_report,
    DARK_BLUE
)

usage_report_button.configure(
    fg=WHITE
)

usage_report_button.grid(
    row=0,
    column=1,
    padx=6,
    pady=5
)


# ============================================================
# Enter Key Support
# ============================================================

def enter_key_pressed(event):
    add_inventory()


material_entry.bind(
    "<Return>",
    enter_key_pressed
)


# ============================================================
# Footer
# ============================================================

footer_frame = tk.Frame(
    root,
    bg=HEADER_COLOR,
    height=35
)

footer_frame.pack(
    fill="x",
    side="bottom"
)

footer_frame.pack_propagate(False)

footer_label = tk.Label(
    footer_frame,
    text="Inventory and Machine Parts Tracking System",
    font=("Segoe UI", 9),
    bg=HEADER_COLOR,
    fg=WHITE
)

footer_label.pack(
    pady=8
)


# ============================================================
# Start Application
# ============================================================

root.mainloop()
