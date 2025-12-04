-- =============================================================================
-- Hampstead Renovations - Database Functions & Stored Procedures
-- =============================================================================
-- This file contains utility functions, triggers, and stored procedures
-- Run after 001_schema.sql and 002_seed.sql
-- =============================================================================

-- =============================================================================
-- UTILITY FUNCTIONS
-- =============================================================================

-- Function to generate quote numbers
CREATE OR REPLACE FUNCTION generate_quote_number()
RETURNS TEXT AS $$
DECLARE
    year_part TEXT;
    seq_num INTEGER;
    quote_num TEXT;
BEGIN
    year_part := TO_CHAR(CURRENT_DATE, 'YYYY');
    
    SELECT COALESCE(MAX(CAST(SUBSTRING(quote_number FROM 10) AS INTEGER)), 0) + 1
    INTO seq_num
    FROM quotes
    WHERE quote_number LIKE 'QTE-' || year_part || '-%';
    
    quote_num := 'QTE-' || year_part || '-' || LPAD(seq_num::TEXT, 6, '0');
    
    RETURN quote_num;
END;
$$ LANGUAGE plpgsql;

-- Function to generate contract numbers
CREATE OR REPLACE FUNCTION generate_contract_number()
RETURNS TEXT AS $$
DECLARE
    year_part TEXT;
    seq_num INTEGER;
    contract_num TEXT;
BEGIN
    year_part := TO_CHAR(CURRENT_DATE, 'YYYY');
    
    SELECT COALESCE(MAX(CAST(SUBSTRING(contract_number FROM 10) AS INTEGER)), 0) + 1
    INTO seq_num
    FROM contracts
    WHERE contract_number LIKE 'CTR-' || year_part || '-%';
    
    contract_num := 'CTR-' || year_part || '-' || LPAD(seq_num::TEXT, 6, '0');
    
    RETURN contract_num;
END;
$$ LANGUAGE plpgsql;

-- Function to generate invoice numbers
CREATE OR REPLACE FUNCTION generate_invoice_number()
RETURNS TEXT AS $$
DECLARE
    year_part TEXT;
    seq_num INTEGER;
    invoice_num TEXT;
BEGIN
    year_part := TO_CHAR(CURRENT_DATE, 'YYYY');
    
    SELECT COALESCE(MAX(CAST(SUBSTRING(invoice_number FROM 10) AS INTEGER)), 0) + 1
    INTO seq_num
    FROM invoices
    WHERE invoice_number LIKE 'INV-' || year_part || '-%';
    
    invoice_num := 'INV-' || year_part || '-' || LPAD(seq_num::TEXT, 6, '0');
    
    RETURN invoice_num;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- LEAD SCORING FUNCTION
-- =============================================================================

CREATE OR REPLACE FUNCTION calculate_lead_score(
    p_budget_range TEXT,
    p_timeline TEXT,
    p_project_type TEXT,
    p_postcode TEXT,
    p_engagement_level INTEGER DEFAULT 10
)
RETURNS TABLE (
    total_score INTEGER,
    score_breakdown JSONB
) AS $$
DECLARE
    budget_score INTEGER := 0;
    timeline_score INTEGER := 0;
    project_score INTEGER := 0;
    location_score INTEGER := 0;
    engagement_score INTEGER := 0;
    location_multiplier DECIMAL(3,2) := 1.0;
    postcode_prefix TEXT;
BEGIN
    -- Budget scoring (max 25 points)
    CASE p_budget_range
        WHEN '100000+' THEN budget_score := 25;
        WHEN '75000-100000' THEN budget_score := 23;
        WHEN '50000-75000' THEN budget_score := 20;
        WHEN '25000-50000' THEN budget_score := 17;
        WHEN '15000-25000' THEN budget_score := 14;
        WHEN '10000-15000' THEN budget_score := 10;
        WHEN 'under_10000' THEN budget_score := 5;
        ELSE budget_score := 8;
    END CASE;
    
    -- Timeline scoring (max 20 points)
    CASE p_timeline
        WHEN 'immediate' THEN timeline_score := 20;
        WHEN '1-3_months' THEN timeline_score := 18;
        WHEN '3-6_months' THEN timeline_score := 14;
        WHEN '6-12_months' THEN timeline_score := 10;
        WHEN 'flexible' THEN timeline_score := 12;
        ELSE timeline_score := 8;
    END CASE;
    
    -- Project type scoring (max 20 points)
    CASE p_project_type
        WHEN 'full_renovation' THEN project_score := 20;
        WHEN 'extension' THEN project_score := 18;
        WHEN 'loft_conversion' THEN project_score := 17;
        WHEN 'kitchen' THEN project_score := 15;
        WHEN 'bathroom' THEN project_score := 12;
        WHEN 'flooring' THEN project_score := 8;
        WHEN 'painting' THEN project_score := 6;
        ELSE project_score := 10;
    END CASE;
    
    -- Location scoring (max 20 points) - based on postcode
    postcode_prefix := UPPER(SPLIT_PART(TRIM(p_postcode), ' ', 1));
    
    -- Get location multiplier
    SELECT COALESCE(lm.multiplier, 1.0)
    INTO location_multiplier
    FROM location_multipliers lm
    WHERE lm.postcode_prefix = postcode_prefix
    LIMIT 1;
    
    -- Convert multiplier to score (1.0 = 15, 1.35 = 20, 0.8 = 10)
    location_score := LEAST(20, GREATEST(5, ROUND((location_multiplier - 0.8) / 0.55 * 15 + 5)::INTEGER));
    
    -- Engagement scoring (max 15 points) - passed as parameter
    engagement_score := LEAST(15, GREATEST(0, p_engagement_level));
    
    -- Return results
    total_score := budget_score + timeline_score + project_score + location_score + engagement_score;
    score_breakdown := jsonb_build_object(
        'budget', budget_score,
        'timeline', timeline_score,
        'project', project_score,
        'location', location_score,
        'engagement', engagement_score
    );
    
    RETURN NEXT;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- PRICING CALCULATION FUNCTION
-- =============================================================================

CREATE OR REPLACE FUNCTION calculate_project_price(
    p_project_type TEXT,
    p_tier TEXT,
    p_sqm DECIMAL,
    p_postcode TEXT
)
RETURNS TABLE (
    base_price DECIMAL(12,2),
    location_adjusted DECIMAL(12,2),
    vat_amount DECIMAL(12,2),
    total_price DECIMAL(12,2),
    price_breakdown JSONB
) AS $$
DECLARE
    base_rate DECIMAL(12,2);
    multiplier DECIMAL(3,2) := 1.0;
    postcode_prefix TEXT;
    subtotal DECIMAL(12,2);
    vat_rate DECIMAL(4,3) := 0.20;
BEGIN
    -- Get base rate from service catalog
    SELECT COALESCE(AVG(sc.base_price), 100.00)
    INTO base_rate
    FROM service_catalog sc
    WHERE sc.category = p_project_type
      AND sc.tier = p_tier
      AND sc.active = true;
    
    -- Get location multiplier
    postcode_prefix := UPPER(SPLIT_PART(TRIM(p_postcode), ' ', 1));
    
    SELECT COALESCE(lm.multiplier, 1.0)
    INTO multiplier
    FROM location_multipliers lm
    WHERE lm.postcode_prefix = postcode_prefix
       OR lm.postcode_prefix = 'DEFAULT'
    ORDER BY CASE WHEN lm.postcode_prefix = 'DEFAULT' THEN 1 ELSE 0 END
    LIMIT 1;
    
    -- Calculate prices
    base_price := base_rate * p_sqm;
    location_adjusted := ROUND(base_price * multiplier, 2);
    vat_amount := ROUND(location_adjusted * vat_rate, 2);
    total_price := location_adjusted + vat_amount;
    
    -- Build breakdown
    price_breakdown := jsonb_build_object(
        'base_rate_per_sqm', base_rate,
        'sqm', p_sqm,
        'base_total', base_price,
        'location_multiplier', multiplier,
        'postcode_prefix', postcode_prefix,
        'subtotal', location_adjusted,
        'vat_rate', vat_rate,
        'vat', vat_amount,
        'total', total_price
    );
    
    RETURN NEXT;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- PROJECT TIMELINE ESTIMATION
-- =============================================================================

CREATE OR REPLACE FUNCTION estimate_project_timeline(
    p_project_type TEXT,
    p_tier TEXT,
    p_sqm DECIMAL
)
RETURNS TABLE (
    estimated_weeks INTEGER,
    breakdown JSONB
) AS $$
DECLARE
    base_weeks INTEGER;
    tier_multiplier DECIMAL(3,2);
    size_factor DECIMAL(3,2);
BEGIN
    -- Base weeks by project type
    CASE p_project_type
        WHEN 'full_renovation' THEN base_weeks := 12;
        WHEN 'extension' THEN base_weeks := 10;
        WHEN 'loft_conversion' THEN base_weeks := 8;
        WHEN 'kitchen' THEN base_weeks := 4;
        WHEN 'bathroom' THEN base_weeks := 3;
        WHEN 'flooring' THEN base_weeks := 1;
        WHEN 'painting' THEN base_weeks := 1;
        WHEN 'electrical' THEN base_weeks := 2;
        WHEN 'plumbing' THEN base_weeks := 2;
        ELSE base_weeks := 4;
    END CASE;
    
    -- Tier multiplier (luxury takes longer due to bespoke work)
    CASE p_tier
        WHEN 'essential' THEN tier_multiplier := 0.9;
        WHEN 'premium' THEN tier_multiplier := 1.0;
        WHEN 'luxury' THEN tier_multiplier := 1.3;
        ELSE tier_multiplier := 1.0;
    END CASE;
    
    -- Size factor (larger projects take longer)
    IF p_sqm <= 10 THEN
        size_factor := 0.8;
    ELSIF p_sqm <= 25 THEN
        size_factor := 1.0;
    ELSIF p_sqm <= 50 THEN
        size_factor := 1.2;
    ELSIF p_sqm <= 100 THEN
        size_factor := 1.5;
    ELSE
        size_factor := 2.0;
    END IF;
    
    -- Calculate estimated weeks
    estimated_weeks := CEIL(base_weeks * tier_multiplier * size_factor);
    
    -- Build breakdown
    breakdown := jsonb_build_object(
        'base_weeks', base_weeks,
        'tier_multiplier', tier_multiplier,
        'size_factor', size_factor,
        'calculated_weeks', estimated_weeks,
        'assumptions', jsonb_build_object(
            'includes_planning', p_project_type IN ('extension', 'loft_conversion'),
            'working_days_per_week', 5,
            'contingency_buffer', '10%'
        )
    );
    
    RETURN NEXT;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- CUSTOMER LIFETIME VALUE CALCULATION
-- =============================================================================

CREATE OR REPLACE FUNCTION calculate_customer_ltv(p_customer_id INTEGER)
RETURNS TABLE (
    total_revenue DECIMAL(12,2),
    project_count INTEGER,
    average_project_value DECIMAL(12,2),
    first_project_date TIMESTAMP,
    last_project_date TIMESTAMP,
    customer_tenure_days INTEGER,
    ltv_score INTEGER
) AS $$
BEGIN
    SELECT 
        COALESCE(SUM(i.total), 0),
        COUNT(DISTINCT p.id),
        COALESCE(AVG(q.total), 0),
        MIN(p.created_at),
        MAX(p.created_at),
        EXTRACT(DAY FROM NOW() - MIN(p.created_at))::INTEGER,
        CASE 
            WHEN COALESCE(SUM(i.total), 0) >= 100000 THEN 100
            WHEN COALESCE(SUM(i.total), 0) >= 50000 THEN 80
            WHEN COALESCE(SUM(i.total), 0) >= 25000 THEN 60
            WHEN COALESCE(SUM(i.total), 0) >= 10000 THEN 40
            ELSE 20
        END
    INTO 
        total_revenue,
        project_count,
        average_project_value,
        first_project_date,
        last_project_date,
        customer_tenure_days,
        ltv_score
    FROM customers c
    LEFT JOIN projects p ON p.customer_id = c.id
    LEFT JOIN quotes q ON q.project_id = p.id AND q.status = 'accepted'
    LEFT JOIN contracts ct ON ct.project_id = p.id
    LEFT JOIN invoices i ON i.contract_id = ct.id AND i.status = 'paid'
    WHERE c.id = p_customer_id
    GROUP BY c.id;
    
    RETURN NEXT;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- DASHBOARD STATISTICS FUNCTIONS
-- =============================================================================

-- Get sales pipeline summary
CREATE OR REPLACE FUNCTION get_pipeline_summary()
RETURNS TABLE (
    stage TEXT,
    count INTEGER,
    total_value DECIMAL(12,2),
    avg_value DECIMAL(12,2)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        q.status::TEXT as stage,
        COUNT(*)::INTEGER as count,
        COALESCE(SUM(q.total), 0) as total_value,
        COALESCE(AVG(q.total), 0) as avg_value
    FROM quotes q
    WHERE q.created_at >= NOW() - INTERVAL '90 days'
    GROUP BY q.status
    ORDER BY 
        CASE q.status
            WHEN 'draft' THEN 1
            WHEN 'sent' THEN 2
            WHEN 'viewed' THEN 3
            WHEN 'accepted' THEN 4
            WHEN 'rejected' THEN 5
            WHEN 'expired' THEN 6
        END;
END;
$$ LANGUAGE plpgsql;

-- Get monthly revenue trend
CREATE OR REPLACE FUNCTION get_revenue_trend(p_months INTEGER DEFAULT 12)
RETURNS TABLE (
    month TEXT,
    revenue DECIMAL(12,2),
    invoice_count INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        TO_CHAR(DATE_TRUNC('month', i.paid_date), 'YYYY-MM') as month,
        COALESCE(SUM(i.total), 0) as revenue,
        COUNT(*)::INTEGER as invoice_count
    FROM invoices i
    WHERE i.status = 'paid'
      AND i.paid_date >= NOW() - (p_months || ' months')::INTERVAL
    GROUP BY DATE_TRUNC('month', i.paid_date)
    ORDER BY DATE_TRUNC('month', i.paid_date);
END;
$$ LANGUAGE plpgsql;

-- Get lead source performance
CREATE OR REPLACE FUNCTION get_lead_source_performance()
RETURNS TABLE (
    source_name TEXT,
    lead_count INTEGER,
    qualified_count INTEGER,
    conversion_rate DECIMAL(5,2),
    total_value DECIMAL(12,2)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ls.source_name,
        COUNT(l.id)::INTEGER as lead_count,
        COUNT(l.id) FILTER (WHERE l.status IN ('qualified', 'converted'))::INTEGER as qualified_count,
        ROUND(
            COUNT(l.id) FILTER (WHERE l.status IN ('qualified', 'converted'))::DECIMAL 
            / NULLIF(COUNT(l.id), 0) * 100, 
            2
        ) as conversion_rate,
        COALESCE(SUM(q.total) FILTER (WHERE q.status = 'accepted'), 0) as total_value
    FROM lead_sources ls
    LEFT JOIN leads l ON l.source_id = ls.id
    LEFT JOIN customers c ON c.id = l.customer_id
    LEFT JOIN projects p ON p.customer_id = c.id
    LEFT JOIN quotes q ON q.project_id = p.id
    WHERE ls.active = true
    GROUP BY ls.id, ls.source_name
    ORDER BY lead_count DESC;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- TRIGGERS
-- =============================================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at trigger to all tables with that column
DO $$
DECLARE
    t TEXT;
BEGIN
    FOR t IN 
        SELECT table_name 
        FROM information_schema.columns 
        WHERE column_name = 'updated_at' 
          AND table_schema = 'public'
    LOOP
        EXECUTE format('
            DROP TRIGGER IF EXISTS update_%I_updated_at ON %I;
            CREATE TRIGGER update_%I_updated_at
            BEFORE UPDATE ON %I
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
        ', t, t, t, t);
    END LOOP;
END $$;

-- =============================================================================
-- INDEXES FOR PERFORMANCE
-- =============================================================================

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_leads_score ON leads(score DESC);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
CREATE INDEX IF NOT EXISTS idx_quotes_status_created ON quotes(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_invoices_status_due ON invoices(status, due_date);
CREATE INDEX IF NOT EXISTS idx_customers_lifecycle ON customers(lifecycle_stage);
CREATE INDEX IF NOT EXISTS idx_communications_customer ON communications(customer_id, created_at DESC);

-- =============================================================================
-- COMPLETION MESSAGE
-- =============================================================================

DO $$
BEGIN
    RAISE NOTICE '=============================================================================';
    RAISE NOTICE 'Hampstead Renovations - Database Functions Installed';
    RAISE NOTICE '=============================================================================';
    RAISE NOTICE 'Functions created:';
    RAISE NOTICE '  - generate_quote_number()';
    RAISE NOTICE '  - generate_contract_number()';
    RAISE NOTICE '  - generate_invoice_number()';
    RAISE NOTICE '  - calculate_lead_score()';
    RAISE NOTICE '  - calculate_project_price()';
    RAISE NOTICE '  - estimate_project_timeline()';
    RAISE NOTICE '  - calculate_customer_ltv()';
    RAISE NOTICE '  - get_pipeline_summary()';
    RAISE NOTICE '  - get_revenue_trend()';
    RAISE NOTICE '  - get_lead_source_performance()';
    RAISE NOTICE '=============================================================================';
END $$;
