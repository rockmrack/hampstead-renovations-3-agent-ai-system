-- =============================================================================
-- Hampstead Renovations - Database Seed Data
-- =============================================================================
-- This file seeds the database with initial data for testing and development.
-- Run after 001_schema.sql
-- =============================================================================

-- =============================================================================
-- SERVICE CATALOG SEED DATA
-- =============================================================================

INSERT INTO service_catalog (category, name, description, unit, base_price, tier, active) VALUES
-- Kitchen Services - Essential
('kitchen', 'Kitchen Cabinet Installation', 'Supply and fit standard kitchen cabinets', 'linear_meter', 450.00, 'essential', true),
('kitchen', 'Worktop Installation', 'Supply and fit laminate worktops', 'linear_meter', 180.00, 'essential', true),
('kitchen', 'Kitchen Tiling', 'Standard ceramic tile splashback installation', 'sqm', 65.00, 'essential', true),
('kitchen', 'Kitchen Plumbing', 'Basic sink and tap installation', 'unit', 350.00, 'essential', true),
('kitchen', 'Kitchen Electrical', 'Standard socket and lighting installation', 'unit', 280.00, 'essential', true),

-- Kitchen Services - Premium
('kitchen', 'Premium Cabinet Installation', 'Supply and fit handleless soft-close cabinets', 'linear_meter', 750.00, 'premium', true),
('kitchen', 'Quartz Worktop Installation', 'Supply and fit quartz composite worktops', 'linear_meter', 420.00, 'premium', true),
('kitchen', 'Premium Kitchen Tiling', 'Designer tile splashback with LED accent', 'sqm', 120.00, 'premium', true),
('kitchen', 'Premium Plumbing', 'Designer tap and undermount sink installation', 'unit', 650.00, 'premium', true),

-- Kitchen Services - Luxury
('kitchen', 'Bespoke Cabinet Installation', 'Handcrafted bespoke cabinetry', 'linear_meter', 1200.00, 'luxury', true),
('kitchen', 'Marble Worktop Installation', 'Natural marble worktop with waterfall edges', 'linear_meter', 850.00, 'luxury', true),
('kitchen', 'Luxury Kitchen Tiling', 'Natural stone or designer statement tiles', 'sqm', 220.00, 'luxury', true),

-- Bathroom Services - Essential
('bathroom', 'Bathroom Suite Installation', 'Supply and fit standard bathroom suite', 'unit', 1200.00, 'essential', true),
('bathroom', 'Bathroom Tiling', 'Standard ceramic floor and wall tiles', 'sqm', 55.00, 'essential', true),
('bathroom', 'Bathroom Plumbing', 'Standard plumbing connections', 'unit', 400.00, 'essential', true),
('bathroom', 'Bathroom Electrical', 'Extractor fan and lighting installation', 'unit', 320.00, 'essential', true),

-- Bathroom Services - Premium
('bathroom', 'Premium Bathroom Suite', 'Designer bathroom suite with concealed cistern', 'unit', 2500.00, 'premium', true),
('bathroom', 'Premium Bathroom Tiling', 'Large format porcelain tiles with underfloor heating prep', 'sqm', 95.00, 'premium', true),
('bathroom', 'Wet Room Installation', 'Full wet room with linear drain', 'unit', 3500.00, 'premium', true),
('bathroom', 'Premium Bathroom Electrical', 'LED mirror and heated towel rail installation', 'unit', 550.00, 'premium', true),

-- Bathroom Services - Luxury
('bathroom', 'Luxury Bathroom Suite', 'Premium brand bathroom with freestanding bath', 'unit', 5500.00, 'luxury', true),
('bathroom', 'Luxury Bathroom Tiling', 'Natural stone with bespoke patterns', 'sqm', 180.00, 'luxury', true),
('bathroom', 'Steam Room Installation', 'Full steam room with controls', 'unit', 8500.00, 'luxury', true),

-- Extension Services
('extension', 'Single Storey Extension', 'Ground floor extension (price per sqm)', 'sqm', 1800.00, 'premium', true),
('extension', 'Double Storey Extension', 'Two storey extension (price per sqm)', 'sqm', 1500.00, 'premium', true),
('extension', 'Wrap Around Extension', 'L-shaped rear and side extension', 'sqm', 1900.00, 'premium', true),
('extension', 'Glass Extension', 'Structural glass extension', 'sqm', 2800.00, 'luxury', true),

-- Loft Conversion Services
('loft_conversion', 'Velux Loft Conversion', 'Basic loft conversion with Velux windows', 'sqm', 1200.00, 'essential', true),
('loft_conversion', 'Dormer Loft Conversion', 'Rear dormer loft conversion', 'sqm', 1500.00, 'premium', true),
('loft_conversion', 'L-Shaped Dormer', 'L-shaped rear dormer conversion', 'sqm', 1700.00, 'premium', true),
('loft_conversion', 'Mansard Loft Conversion', 'Full mansard conversion', 'sqm', 2200.00, 'luxury', true),

-- Flooring Services
('flooring', 'Laminate Flooring', 'Supply and fit laminate flooring', 'sqm', 35.00, 'essential', true),
('flooring', 'Engineered Wood Flooring', 'Supply and fit engineered wood', 'sqm', 75.00, 'premium', true),
('flooring', 'Solid Hardwood Flooring', 'Supply and fit solid hardwood', 'sqm', 120.00, 'luxury', true),
('flooring', 'Natural Stone Flooring', 'Supply and fit natural stone tiles', 'sqm', 150.00, 'luxury', true),
('flooring', 'Underfloor Heating', 'Electric underfloor heating system', 'sqm', 85.00, 'premium', true),

-- Electrical Services
('electrical', 'Consumer Unit Upgrade', 'Full consumer unit replacement', 'unit', 650.00, 'essential', true),
('electrical', 'Full Rewire', 'Complete house rewire (per bedroom)', 'unit', 1200.00, 'essential', true),
('electrical', 'Smart Home Installation', 'Basic smart lighting and controls', 'unit', 800.00, 'premium', true),
('electrical', 'Full Smart Home System', 'Complete home automation system', 'unit', 3500.00, 'luxury', true),

-- Plumbing Services
('plumbing', 'Boiler Installation', 'Standard combi boiler installation', 'unit', 2500.00, 'essential', true),
('plumbing', 'Premium Boiler Installation', 'Premium brand boiler with smart controls', 'unit', 3800.00, 'premium', true),
('plumbing', 'Central Heating Install', 'Full central heating system (per radiator)', 'unit', 450.00, 'essential', true),
('plumbing', 'Underfloor Heating Water', 'Water-based underfloor heating', 'sqm', 120.00, 'premium', true),

-- Painting & Decorating
('painting', 'Standard Room Painting', 'Walls and ceiling painting (per room)', 'unit', 350.00, 'essential', true),
('painting', 'Premium Room Painting', 'Premium paint with full prep work', 'unit', 550.00, 'premium', true),
('painting', 'Feature Wall Installation', 'Decorative wallpaper or texture', 'unit', 400.00, 'premium', true),
('painting', 'Bespoke Decorating', 'Custom decorative finishes', 'unit', 850.00, 'luxury', true);

-- =============================================================================
-- LOCATION MULTIPLIERS
-- =============================================================================

INSERT INTO location_multipliers (postcode_prefix, area_name, multiplier, notes) VALUES
('NW3', 'Hampstead', 1.25, 'Premium London location'),
('NW6', 'West Hampstead', 1.20, 'Prime North West London'),
('NW11', 'Golders Green', 1.15, 'Affluent residential area'),
('N2', 'East Finchley', 1.10, 'Good residential area'),
('N6', 'Highgate', 1.25, 'Premium village location'),
('N10', 'Muswell Hill', 1.15, 'Popular family area'),
('NW1', 'Camden / Regents Park', 1.20, 'Central location premium'),
('NW8', 'St Johns Wood', 1.30, 'Prime London location'),
('W1', 'West End', 1.35, 'Central London premium'),
('SW3', 'Chelsea', 1.35, 'Prime London location'),
('SW7', 'South Kensington', 1.30, 'Premium area'),
('W11', 'Notting Hill', 1.25, 'Fashionable West London'),
('EC1', 'Clerkenwell', 1.15, 'City fringe area'),
('DEFAULT', 'Standard London', 1.00, 'Base rate for other areas');

-- =============================================================================
-- SAMPLE STAFF DATA (Development Only)
-- =============================================================================

INSERT INTO staff (email, name, role, department, phone, active) VALUES
('james.wilson@hampsteadrenovations.co.uk', 'James Wilson', 'director', 'management', '+44 20 7123 4567', true),
('sarah.johnson@hampsteadrenovations.co.uk', 'Sarah Johnson', 'sales_manager', 'sales', '+44 20 7123 4568', true),
('michael.chen@hampsteadrenovations.co.uk', 'Michael Chen', 'project_manager', 'operations', '+44 20 7123 4569', true),
('emma.brown@hampsteadrenovations.co.uk', 'Emma Brown', 'sales_rep', 'sales', '+44 20 7123 4570', true),
('david.smith@hampsteadrenovations.co.uk', 'David Smith', 'estimator', 'operations', '+44 20 7123 4571', true);

-- =============================================================================
-- SAMPLE LEAD SOURCES
-- =============================================================================

INSERT INTO lead_sources (source_name, source_type, attribution_model, active) VALUES
('Website Form', 'organic', 'first_touch', true),
('Google Ads', 'paid', 'last_touch', true),
('Facebook Ads', 'paid', 'last_touch', true),
('Houzz', 'referral', 'first_touch', true),
('Checkatrade', 'referral', 'first_touch', true),
('MyBuilder', 'referral', 'first_touch', true),
('Word of Mouth', 'referral', 'first_touch', true),
('Previous Client', 'referral', 'first_touch', true),
('Trade Partner', 'referral', 'first_touch', true),
('Local Advertising', 'paid', 'first_touch', true),
('Voicemail', 'organic', 'first_touch', true),
('WhatsApp', 'organic', 'first_touch', true);

-- =============================================================================
-- SAMPLE CUSTOMERS (Development/Testing Only)
-- =============================================================================

INSERT INTO customers (first_name, last_name, email, phone, address_line1, address_line2, city, postcode, source, lifecycle_stage, created_at) VALUES
('John', 'Smith', 'john.smith@example.com', '+44 7700 900001', '42 Hampstead High Street', NULL, 'London', 'NW3 1QE', 'Website Form', 'lead', NOW() - INTERVAL '30 days'),
('Emma', 'Johnson', 'emma.j@example.com', '+44 7700 900002', '15 Flask Walk', 'Flat 3', 'London', 'NW3 1HJ', 'Google Ads', 'qualified', NOW() - INTERVAL '25 days'),
('Michael', 'Williams', 'mwilliams@example.com', '+44 7700 900003', '88 Heath Street', NULL, 'London', 'NW3 1DN', 'Houzz', 'opportunity', NOW() - INTERVAL '20 days'),
('Sarah', 'Brown', 'sarah.brown@example.com', '+44 7700 900004', '23 Church Row', NULL, 'London', 'NW3 6UP', 'Word of Mouth', 'customer', NOW() - INTERVAL '90 days'),
('David', 'Taylor', 'dtaylor@example.com', '+44 7700 900005', '56 Rosslyn Hill', 'Garden Flat', 'London', 'NW3 1ND', 'Checkatrade', 'lead', NOW() - INTERVAL '5 days'),
('Lisa', 'Anderson', 'lisa.a@example.com', '+44 7700 900006', '12 Fitzjohns Avenue', NULL, 'London', 'NW3 5LT', 'Facebook Ads', 'qualified', NOW() - INTERVAL '15 days'),
('James', 'Thomas', 'jthomas@example.com', '+44 7700 900007', '78 Frognal', NULL, 'London', 'NW3 6XD', 'MyBuilder', 'lead', NOW() - INTERVAL '3 days'),
('Rachel', 'Jackson', 'rachel.j@example.com', '+44 7700 900008', '34 Arkwright Road', 'Flat 2B', 'London', 'NW3 6BH', 'Previous Client', 'customer', NOW() - INTERVAL '180 days');

-- =============================================================================
-- SAMPLE PROJECTS (Development/Testing Only)
-- =============================================================================

INSERT INTO projects (customer_id, project_type, tier, title, description, address_line1, city, postcode, estimated_sqm, status, estimated_start_date, estimated_duration_weeks, created_at) VALUES
(1, 'kitchen', 'premium', 'Complete Kitchen Renovation', 'Full kitchen remodel with new cabinets, quartz worktops, and integrated appliances', '42 Hampstead High Street', 'London', 'NW3 1QE', 18.5, 'quoted', NOW() + INTERVAL '30 days', 6, NOW() - INTERVAL '28 days'),
(2, 'bathroom', 'luxury', 'Master Bathroom Renovation', 'Luxury bathroom with freestanding bath and walk-in shower', '15 Flask Walk', 'London', 'NW3 1HJ', 12.0, 'quoted', NOW() + INTERVAL '45 days', 4, NOW() - INTERVAL '23 days'),
(3, 'extension', 'premium', 'Rear Extension Project', 'Single storey rear extension with bi-fold doors', '88 Heath Street', 'London', 'NW3 1DN', 25.0, 'in_progress', NOW() - INTERVAL '30 days', 12, NOW() - INTERVAL '60 days'),
(4, 'full_renovation', 'premium', 'Full House Renovation', 'Complete renovation including kitchen, 2 bathrooms, and rewiring', '23 Church Row', 'London', 'NW3 6UP', 145.0, 'completed', NOW() - INTERVAL '120 days', 16, NOW() - INTERVAL '200 days'),
(5, 'loft_conversion', 'essential', 'Velux Loft Conversion', 'Basic loft conversion with Velux windows and ensuite', '56 Rosslyn Hill', 'London', 'NW3 1ND', 35.0, 'lead', NULL, 8, NOW() - INTERVAL '4 days'),
(6, 'kitchen', 'essential', 'Kitchen Refresh', 'Cabinet replacement and new worktops', '12 Fitzjohns Avenue', 'London', 'NW3 5LT', 14.0, 'quoted', NOW() + INTERVAL '20 days', 3, NOW() - INTERVAL '12 days');

-- =============================================================================
-- SAMPLE QUOTES (Development/Testing Only)
-- =============================================================================

INSERT INTO quotes (project_id, quote_number, version, tier, subtotal, discount_amount, discount_percentage, vat_amount, total, valid_until, status, pdf_url, notes, created_at) VALUES
(1, 'QTE-2024-000001', 1, 'premium', 28500.00, 1425.00, 5.0, 5415.00, 32490.00, NOW() + INTERVAL '30 days', 'sent', 's3://hampstead-documents/quotes/QTE-2024-000001.pdf', 'Premium kitchen package with Caesarstone worktops', NOW() - INTERVAL '27 days'),
(2, 'QTE-2024-000002', 1, 'luxury', 18500.00, 0.00, 0.0, 3700.00, 22200.00, NOW() + INTERVAL '30 days', 'sent', 's3://hampstead-documents/quotes/QTE-2024-000002.pdf', 'Luxury bathroom with Villeroy & Boch suite', NOW() - INTERVAL '22 days'),
(3, 'QTE-2024-000003', 2, 'premium', 67500.00, 3375.00, 5.0, 12825.00, 76950.00, NOW() - INTERVAL '45 days', 'accepted', 's3://hampstead-documents/quotes/QTE-2024-000003.pdf', 'Revised quote with larger extension footprint', NOW() - INTERVAL '55 days'),
(4, 'QTE-2023-000042', 1, 'premium', 142000.00, 14200.00, 10.0, 25560.00, 153360.00, NOW() - INTERVAL '180 days', 'accepted', 's3://hampstead-documents/quotes/QTE-2023-000042.pdf', 'Full renovation - returning client discount applied', NOW() - INTERVAL '195 days'),
(6, 'QTE-2024-000004', 1, 'essential', 9800.00, 0.00, 0.0, 1960.00, 11760.00, NOW() + INTERVAL '30 days', 'draft', NULL, 'Basic kitchen refresh package', NOW() - INTERVAL '10 days');

-- =============================================================================
-- SAMPLE CONTRACTS (Development/Testing Only)
-- =============================================================================

INSERT INTO contracts (project_id, quote_id, contract_number, contract_type, total_value, deposit_amount, deposit_percentage, payment_schedule, status, signed_date, pdf_url, created_at) VALUES
(3, 3, 'CTR-2024-000001', 'fixed_price', 76950.00, 15390.00, 20.0, '{"stages": ["deposit", "foundation", "structure", "completion"]}', 'active', NOW() - INTERVAL '40 days', 's3://hampstead-documents/contracts/CTR-2024-000001.pdf', NOW() - INTERVAL '42 days'),
(4, 4, 'CTR-2023-000015', 'fixed_price', 153360.00, 30672.00, 20.0, '{"stages": ["deposit", "strip_out", "first_fix", "second_fix", "completion"]}', 'completed', NOW() - INTERVAL '175 days', 's3://hampstead-documents/contracts/CTR-2023-000015.pdf', NOW() - INTERVAL '180 days');

-- =============================================================================
-- SAMPLE INVOICES (Development/Testing Only)
-- =============================================================================

INSERT INTO invoices (contract_id, invoice_number, invoice_type, description, subtotal, vat_amount, total, due_date, status, paid_date, pdf_url, created_at) VALUES
(1, 'INV-2024-000001', 'deposit', 'Project deposit - 20%', 12825.00, 2565.00, 15390.00, NOW() - INTERVAL '30 days', 'paid', NOW() - INTERVAL '35 days', 's3://hampstead-documents/invoices/INV-2024-000001.pdf', NOW() - INTERVAL '40 days'),
(1, 'INV-2024-000002', 'stage', 'Foundation stage complete', 19237.50, 3847.50, 23085.00, NOW() - INTERVAL '10 days', 'paid', NOW() - INTERVAL '8 days', 's3://hampstead-documents/invoices/INV-2024-000002.pdf', NOW() - INTERVAL '15 days'),
(1, 'INV-2024-000003', 'stage', 'Structure stage complete', 19237.50, 3847.50, 23085.00, NOW() + INTERVAL '14 days', 'sent', NULL, 's3://hampstead-documents/invoices/INV-2024-000003.pdf', NOW() - INTERVAL '2 days'),
(2, 'INV-2023-000045', 'deposit', 'Project deposit - 20%', 25560.00, 5112.00, 30672.00, NOW() - INTERVAL '170 days', 'paid', NOW() - INTERVAL '168 days', 's3://hampstead-documents/invoices/INV-2023-000045.pdf', NOW() - INTERVAL '175 days'),
(2, 'INV-2023-000058', 'final', 'Final payment - project complete', 102240.00, 20448.00, 122688.00, NOW() - INTERVAL '85 days', 'paid', NOW() - INTERVAL '82 days', 's3://hampstead-documents/invoices/INV-2023-000058.pdf', NOW() - INTERVAL '90 days');

-- =============================================================================
-- SAMPLE COMMUNICATIONS (Development/Testing Only)
-- =============================================================================

INSERT INTO communications (customer_id, project_id, channel, direction, subject, content, sentiment, ai_processed, created_at) VALUES
(1, 1, 'email', 'inbound', 'Kitchen renovation inquiry', 'Hi, I am interested in renovating my kitchen. The current layout is quite dated and I would like a modern open-plan design with an island.', 'positive', true, NOW() - INTERVAL '30 days'),
(1, 1, 'email', 'outbound', 'RE: Kitchen renovation inquiry', 'Thank you for your inquiry. I would be delighted to arrange a site visit to discuss your kitchen renovation project. Would Tuesday at 10am work for you?', 'positive', false, NOW() - INTERVAL '29 days'),
(2, 2, 'whatsapp', 'inbound', NULL, 'Just following up on the bathroom quote. Are the tiles included in the price?', 'neutral', true, NOW() - INTERVAL '20 days'),
(3, 3, 'email', 'outbound', 'Project update - Week 3', 'Dear Mr Williams, I am pleased to report that the foundation work is now complete and has passed building control inspection. We are on schedule to begin the structural phase next week.', 'positive', false, NOW() - INTERVAL '7 days'),
(5, 5, 'voicemail', 'inbound', 'Voicemail transcription', 'Hi, this is David Taylor calling about a loft conversion. I live in Hampstead and want to add a bedroom and ensuite. Please call me back on 07700 900005. Thanks.', 'positive', true, NOW() - INTERVAL '5 days');

-- =============================================================================
-- SAMPLE LEADS FOR AI SCORING (Development/Testing Only)
-- =============================================================================

INSERT INTO leads (customer_id, source_id, status, score, score_breakdown, budget_range, timeline, project_interest, notes, assigned_to, created_at) VALUES
(1, 1, 'qualified', 85, '{"budget": 25, "timeline": 20, "engagement": 20, "location": 20}', '25000-50000', '1-3_months', 'kitchen', 'High-value kitchen project in prime Hampstead location. Very engaged prospect.', 2, NOW() - INTERVAL '28 days'),
(2, 2, 'qualified', 78, '{"budget": 22, "timeline": 18, "engagement": 20, "location": 18}', '15000-25000', '1-3_months', 'bathroom', 'Luxury bathroom renovation. Good location in Flask Walk.', 2, NOW() - INTERVAL '23 days'),
(5, 1, 'new', 62, '{"budget": 18, "timeline": 15, "engagement": 14, "location": 15}', '25000-50000', '3-6_months', 'loft_conversion', 'Loft conversion inquiry via voicemail. Good location, timeline flexible.', NULL, NOW() - INTERVAL '4 days'),
(6, 4, 'contacted', 55, '{"budget": 15, "timeline": 12, "engagement": 13, "location": 15}', '10000-15000', '1-3_months', 'kitchen', 'Kitchen refresh project. Facebook lead, lower budget tier.', 4, NOW() - INTERVAL '12 days'),
(7, 6, 'new', 48, '{"budget": 12, "timeline": 10, "engagement": 11, "location": 15}', 'unknown', 'flexible', 'general', 'New MyBuilder inquiry. Needs qualification call.', NULL, NOW() - INTERVAL '2 days');

-- =============================================================================
-- SAMPLE SURVEY RESPONSES (Development/Testing Only)
-- =============================================================================

INSERT INTO surveys (project_id, customer_id, survey_type, overall_rating, quality_rating, communication_rating, timeliness_rating, value_rating, would_recommend, testimonial, submitted_at) VALUES
(4, 4, 'post_completion', 5, 5, 5, 4, 5, true, 'Absolutely fantastic work from start to finish. The team at Hampstead Renovations transformed our home beyond our expectations. James and his team were professional, communicative, and delivered outstanding quality. Highly recommend!', NOW() - INTERVAL '75 days');

-- =============================================================================
-- GRANT PERMISSIONS
-- =============================================================================

-- Ensure the application user has necessary permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO hampstead;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO hampstead;

-- =============================================================================
-- REFRESH MATERIALIZED VIEWS (if any exist)
-- =============================================================================

-- Note: Add REFRESH MATERIALIZED VIEW commands here if materialized views are created

-- =============================================================================
-- COMPLETION MESSAGE
-- =============================================================================

DO $$
BEGIN
    RAISE NOTICE '=============================================================================';
    RAISE NOTICE 'Hampstead Renovations - Database Seed Complete';
    RAISE NOTICE '=============================================================================';
    RAISE NOTICE 'Seeded data includes:';
    RAISE NOTICE '  - Service catalog entries: %', (SELECT COUNT(*) FROM service_catalog);
    RAISE NOTICE '  - Location multipliers: %', (SELECT COUNT(*) FROM location_multipliers);
    RAISE NOTICE '  - Staff members: %', (SELECT COUNT(*) FROM staff);
    RAISE NOTICE '  - Sample customers: %', (SELECT COUNT(*) FROM customers);
    RAISE NOTICE '  - Sample projects: %', (SELECT COUNT(*) FROM projects);
    RAISE NOTICE '  - Sample quotes: %', (SELECT COUNT(*) FROM quotes);
    RAISE NOTICE '=============================================================================';
END $$;
