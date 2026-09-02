import tkinter as tk
from tkinter import messagebox
import mysql.connector


# Database connection
def connect_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Periquitos2!!",
        database="inventory_repair_parts"
    )


# Add one part to inventory
def add_inventory():

    part_number = entry.get().strip()

    if not part_number:
        messagebox.showerror("Error", "Scan a part number.")
        return

    try:
        db = connect_db()
        cursor = db.cursor()

        # Check that the part exists
        cursor.execute(
            "SELECT Part_NO FROM parts_inventory WHERE Part_NO = %s",
            (part_number,)
        )

        if cursor.fetchone() is None:
            messagebox.showerror(
                "Error",
                "Part number does not exist in inventory."
            )
            cursor.close()
            db.close()
            return

        # Add 1 to inventory
        cursor.execute(
            """
            UPDATE parts_inventory
            SET Inventory = Inventory + 1
            WHERE Part_NO = %s
            """,
            (part_number,)
        )

        db.commit()

        messagebox.showinfo(
            "Success",
            f"Part {part_number} added to inventory."
        )

        entry.delete(0, tk.END)
        entry.focus()

        cursor.close()
        db.close()

    except mysql.connector.Error as error:
        messagebox.showerror(
            "Database Error",
            str(error)
        )


# Use part on a machine
def use_part(machine):

    part_number = entry.get().strip()

    if not part_number:
        messagebox.showerror("Error", "Scan a part number.")
        return

    try:
        db = connect_db()
        cursor = db.cursor()

        # Check inventory
        cursor.execute(
            """
            SELECT Inventory
            FROM parts_inventory
            WHERE Part_NO = %s
            """,
            (part_number,)
        )

        result = cursor.fetchone()

        if result is None:
            messagebox.showerror(
                "Error",
                "Part number does not exist."
            )
            cursor.close()
            db.close()
            return

        # Make sure inventory is available
        if result[0] <= 0:
            messagebox.showerror(
                "Error",
                "No inventory available for this part."
            )
            cursor.close()
            db.close()
            return

        # Remove 1 from inventory
        cursor.execute(
            """
            UPDATE parts_inventory
            SET Inventory = Inventory - 1
            WHERE Part_NO = %s
            """,
            (part_number,)
        )

        # Add 1 to the selected machine
        if machine == 1:

            cursor.execute(
                """
                UPDATE parts_usage
                SET Machine_1 = Machine_1 + 1
                WHERE Part_NO = %s
                """,
                (part_number,)
            )

        else:

            cursor.execute(
                """
                UPDATE parts_usage
                SET Machine_2 = Machine_2 + 1
                WHERE Part_NO = %s
                """,
                (part_number,)
            )

        # Both changes happen together
        db.commit()

        messagebox.showinfo(
            "Success",
            f"Part {part_number} used on Machine {machine}."
        )

        entry.delete(0, tk.END)
        entry.focus()

        cursor.close()
        db.close()

    except mysql.connector.Error as error:
        db.rollback()

        messagebox.showerror(
            "Database Error",
            str(error)
        )

        cursor.close()
        db.close()


# -----------------------------
# Tkinter window
# -----------------------------

root = tk.Tk()

root.title("Inventory Parts")
root.geometry("400x250")


# One text entry
entry = tk.Entry(
    root,
    font=("Arial", 18),
    width=25
)

entry.pack(pady=20)

entry.focus()


# Buttons
tk.Button(
    root,
    text="Add Inventory",
    width=20,
    command=add_inventory
).pack(pady=5)


tk.Button(
    root,
    text="Use - Machine 1",
    width=20,
    command=lambda: use_part(1)
).pack(pady=5)


tk.Button(
    root,
    text="Use - Machine 2",
    width=20,
    command=lambda: use_part(2)
).pack(pady=5)


root.mainloop()