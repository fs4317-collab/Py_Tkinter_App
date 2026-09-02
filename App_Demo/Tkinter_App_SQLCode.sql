USE inventory_repair_parts;

-- ============================================
-- Table 1: Parts Inventory
-- ============================================

CREATE TABLE parts_inventory (
    Siemens_PN INT PRIMARY KEY,
    Description VARCHAR(255),
    Inventory INT NOT NULL DEFAULT 0
);


-- ============================================
-- Table 2: Parts Usage
-- ============================================

CREATE TABLE parts_usage (
    Siemens_PN INT PRIMARY KEY,
    Description VARCHAR(255),
    Machine_1 INT NOT NULL DEFAULT 0,
    Machine_2 INT NOT NULL DEFAULT 0,

    CONSTRAINT fk_parts_usage_inventory
        FOREIGN KEY (Siemens_PN)
        REFERENCES parts_inventory(Siemens_PN)
);

USE inventory_repair_parts;


-- ============================================
-- Insert 10 Parts into parts_inventory
-- ============================================

INSERT INTO parts_inventory (Part_NO, Description, Inventory)
VALUES
(100001, 'Conveyor Drive Belt', 10),
(100002, 'Conveyor Roller Bearing', 15),
(100003, 'Conveyor Idler Roller', 12),
(100004, 'Proximity Sensor', 8),
(100005, 'Conveyor Drive Motor', 5),
(100006, 'Drive Sprocket', 7),
(100007, 'Conveyor Drive Pulley', 6),
(100008, 'Emergency Stop Switch', 10),
(100009, 'Conveyor Chain', 9),
(100010, 'Photoelectric Sensor', 8);


-- ============================================
-- Insert the SAME 10 Parts into parts_usage
-- ============================================

INSERT INTO parts_usage (Part_NO, Description, Machine_1, Machine_2)
VALUES
(100001, 'Conveyor Drive Belt', 0, 0),
(100002, 'Conveyor Roller Bearing', 0, 0),
(100003, 'Conveyor Idler Roller', 0, 0),
(100004, 'Proximity Sensor', 0, 0),
(100005, 'Conveyor Drive Motor', 0, 0),
(100006, 'Drive Sprocket', 0, 0),
(100007, 'Conveyor Drive Pulley', 0, 0),
(100008, 'Emergency Stop Switch', 0, 0),
(100009, 'Conveyor Chain', 0, 0),
(100010, 'Photoelectric Sensor', 0, 0);
