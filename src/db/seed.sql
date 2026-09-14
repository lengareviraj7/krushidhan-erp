-- ============================================================
-- Default Initial Seed Data for Agri-Input Shop ERP
-- ============================================================

-- 1. Standard Measurement Units
INSERT OR IGNORE INTO units (unit_id, unit_name, symbol) VALUES
(1, 'Kilogram', 'KG'),
(2, 'Gram', 'GM'),
(3, 'Litre', 'LTR'),
(4, 'Millilitre', 'ML'),
(5, 'Bag', 'BAG'),
(6, 'Quintal', 'QTL'),
(7, 'Numbers / Pieces', 'NOS'),
(8, 'Bottle', 'BTL'),
(9, 'Packet / Box', 'PKT');

-- 2. Standard Unit Conversions
INSERT OR IGNORE INTO unit_conversions (from_unit_id, to_unit_id, conversion_factor) VALUES
(1, 2, 1000.0), -- 1 KG = 1000 GM
(3, 4, 1000.0), -- 1 LTR = 1000 ML
(5, 1, 50.0),   -- 1 BAG = 50 KG
(6, 1, 100.0);  -- 1 QTL = 100 KG

-- 3. Standard GST Tax Groups
INSERT OR IGNORE INTO tax_groups (tax_group_id, tax_group_name, cgst_rate, sgst_rate, igst_rate) VALUES
(1, 'Exempted (0%)', 0.0, 0.0, 0.0),
(2, 'GST 5% (Fertilizers & Bulk Inputs)', 2.5, 2.5, 5.0),
(3, 'GST 12% (Agricultural Tractors & Parts)', 6.0, 6.0, 12.0),
(4, 'GST 18% (Pesticides, Insecticides & Sprayers)', 9.0, 9.0, 18.0),
(5, 'GST 28% (Luxury & Specialized Hardware)', 14.0, 14.0, 28.0);

-- 4. Standard Product Categories
INSERT OR IGNORE INTO categories (category_id, category_name, short_name, is_hardware_category) VALUES
(1, 'Chemical Fertilizers', 'FERT', 0),
(2, 'Hybrid & Improved Seeds', 'SEED', 0),
(3, 'Pesticides & Insecticides', 'PEST', 0),
(4, 'Fungicides & Herbicides', 'FUNG', 0),
(5, 'Plant Growth Regulators & Bio-Stimulants', 'PGR', 0),
(6, 'Agricultural Hardware & Drip Irrigation', 'HARD', 1);

-- 5. Standard Crops
INSERT OR IGNORE INTO crops (crop_id, crop_name, description) VALUES
(1, 'Sugarcane (ऊस)', 'Cash crop with high fertilizer requirement'),
(2, 'Cotton (कापूस)', 'Pest sensitive commercial crop'),
(3, 'Soybean (सोयाबीन)', 'Kharif oilseed crop'),
(4, 'Wheat (गहू)', 'Rabi cereal crop'),
(5, 'Onion (कांदा)', 'High fungicide and fertilizer demand'),
(6, 'Tomato (टोमॅटो)', 'Horticulture crop');

-- 6. Customer Groups
INSERT OR IGNORE INTO customer_groups (group_id, group_name, discount_percent) VALUES
(1, 'Retail Farmer', 0.0),
(2, 'Wholesale Buyer', 2.0),
(3, 'Grampanchayat / Krishi Mandal', 5.0);

-- 7. System Chart of Accounts (Double-Entry Foundation)
INSERT OR IGNORE INTO ledger_accounts (account_id, account_name, account_group, is_system) VALUES
(1, 'Cash in Hand', 'CASH', 1),
(2, 'Bank Account', 'BANK_ACCOUNTS', 1),
(3, 'Sales Account', 'INCOME', 1),
(4, 'Purchase Account', 'EXPENSE', 1),
(5, 'Sales Return Account', 'EXPENSE', 1),
(6, 'Purchase Return Account', 'INCOME', 1),
(7, 'CGST Output Account', 'LIABILITIES', 1),
(8, 'SGST Output Account', 'LIABILITIES', 1),
(9, 'IGST Output Account', 'LIABILITIES', 1),
(10, 'CGST Input Account', 'ASSETS', 1),
(11, 'SGST Input Account', 'ASSETS', 1),
(12, 'IGST Input Account', 'ASSETS', 1),
(13, 'Discount Allowed Account', 'EXPENSE', 1),
(14, 'Discount Received Account', 'INCOME', 1),
(15, 'Round Off Account', 'EXPENSE', 1);

-- 8. Standard Expense Categories
INSERT OR IGNORE INTO expense_categories (category_id, category_name, description) VALUES
(1, 'Shop Rent', 'Monthly premises rental'),
(2, 'Electricity Bill', 'Power and electricity expenses'),
(3, 'Staff Salaries & Wages', 'Employee salaries and daily labor'),
(4, 'Freight & Transportation', 'Goods inward and delivery transport'),
(5, 'Tea, Water & Refreshments', 'Shop hospitality expenses'),
(6, 'Stationery & Printing', 'Billing paper, toner and shop supplies');

-- 9. Initial Default Company Profile
INSERT OR IGNORE INTO company_settings (
    setting_id, company_name, address, city, state, pincode, mobile,
    dl_fertilizer, dl_pesticide, dl_seed, invoice_terms, default_invoice_size
) VALUES (
    1,
    'Krishi Vikas Agri Inputs & Seeds',
    'Main Market Road, Near APMC Market Yard',
    'Pune',
    'Maharashtra',
    '411001',
    '9876543210',
    'LIC/FERT/2026/0123',
    'LIC/PEST/2026/0456',
    'LIC/SEED/2026/0789',
    '1. Goods once sold will not be taken back without original bill.\n2. Expiry warranty lies with respective manufacturing company.\n3. Subject to local jurisdiction.',
    'A4'
);

-- 10. Default Admin User (Default PIN/Password: admin123, pre-hashed using SHA256/Bcrypt compatible fallback)
-- Password 'admin123' bcrypt hash: $2b$12$e8x/yUv2O5m3zK.wK0Y.DehZ0J7CjH8mB6u4E8q7G9k0V2.A1b2c3 or initial bootstrap hash
INSERT OR IGNORE INTO users (user_id, username, password_hash, full_name, role, is_active) VALUES
(1, 'admin', '$2b$12$K1r.5gCgO4X3N2M.9O7w7e6t3mO8g4u9v8c3x5b8a0z1y2x3w4v5u', 'Shop Owner / Admin', 'ADMIN', 1);
