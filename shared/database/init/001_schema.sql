-- ═══════════════════════════════════════════════════════════════════════════════
-- HAMPSTEAD RENOVATIONS - 3-AGENT AI SYSTEM
-- Database Schema - PostgreSQL 15+
-- ═══════════════════════════════════════════════════════════════════════════════
--
-- This schema provides local data persistence for the AI system, complementing
-- HubSpot CRM data with operational data that needs faster access or isn't
-- suitable for CRM storage.
--
-- Run order:
-- 1. 001_schema.sql (this file)
-- 2. 002_seed.sql (initial data)
-- 3. 003_functions.sql (stored procedures)
--
-- ═══════════════════════════════════════════════════════════════════════════════

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For fuzzy text search

-- Set timezone
SET timezone = 'Europe/London';

-- ─────────────────────────────────────────────────────────────────────────────────
-- ENUM TYPES
-- ─────────────────────────────────────────────────────────────────────────────────

CREATE TYPE service_type AS ENUM (
    'kitchen-extension',
    'loft-conversion',
    'bathroom',
    'full-renovation',
    'basement',
    'maintenance',
    'structural',
    'planning-only',
    'other'
);

CREATE TYPE property_type AS ENUM (
    'flat',
    'terraced',
    'semi-detached',
    'detached',
    'mansion-block',
    'period-conversion',
    'mews',
    'unknown'
);

CREATE TYPE budget_band AS ENUM (
    'under-15k',
    '15k-40k',
    '40k-100k',
    '100k-250k',
    'over-250k',
    'unknown'
);

CREATE TYPE timeline_category AS ENUM (
    'urgent',
    'soon',
    'planning',
    'future',
    'exploring',
    'unknown'
);

CREATE TYPE lead_priority AS ENUM (
    'hot',
    'warm',
    'cool',
    'cold'
);

CREATE TYPE lead_source AS ENUM (
    'whatsapp',
    'website',
    'phone',
    'email',
    'referral',
    'google-ads',
    'houzz',
    'instagram',
    'other'
);

CREATE TYPE deal_stage AS ENUM (
    'new',
    'contacted',
    'survey-scheduled',
    'survey-completed',
    'quote-sent',
    'negotiation',
    'contract-sent',
    'won',
    'lost'
);

CREATE TYPE document_type AS ENUM (
    'quote',
    'contract',
    'invoice',
    'receipt',
    'certificate',
    'drawing',
    'photo',
    'other'
);

CREATE TYPE conversation_channel AS ENUM (
    'whatsapp',
    'email',
    'phone',
    'sms',
    'web-chat'
);

CREATE TYPE message_direction AS ENUM (
    'inbound',
    'outbound'
);

-- ─────────────────────────────────────────────────────────────────────────────────
-- LEADS TABLE
-- Primary table for lead data - mirrors HubSpot but allows faster local queries
-- ─────────────────────────────────────────────────────────────────────────────────

CREATE TABLE leads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- External IDs
    hubspot_contact_id VARCHAR(50) UNIQUE,
    hubspot_deal_id VARCHAR(50),
    
    -- Contact Information
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    full_name VARCHAR(200) GENERATED ALWAYS AS (
        COALESCE(first_name, '') || ' ' || COALESCE(last_name, '')
    ) STORED,
    email VARCHAR(255),
    phone VARCHAR(20),
    phone_normalised VARCHAR(20),  -- E.164 format (+447XXXXXXXXX)
    
    -- Property Information
    postcode VARCHAR(10),
    postcode_area VARCHAR(5),  -- e.g., NW3, NW11
    area_name VARCHAR(100),
    property_type property_type DEFAULT 'unknown',
    property_style VARCHAR(50),  -- victorian, edwardian, etc.
    conservation_area VARCHAR(10) DEFAULT 'unknown',
    listed_building BOOLEAN DEFAULT FALSE,
    
    -- Project Information
    service_type service_type DEFAULT 'other',
    service_description TEXT,
    budget_band budget_band DEFAULT 'unknown',
    budget_mentioned VARCHAR(100),  -- Customer's exact words
    timeline_category timeline_category DEFAULT 'unknown',
    timeline_stated VARCHAR(200),
    specific_requirements JSONB DEFAULT '[]'::jsonb,
    
    -- Qualification
    lead_score INTEGER CHECK (lead_score >= 0 AND lead_score <= 100),
    priority lead_priority DEFAULT 'cool',
    source lead_source DEFAULT 'website',
    
    -- UTM Tracking
    utm_source VARCHAR(100),
    utm_medium VARCHAR(100),
    utm_campaign VARCHAR(100),
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    deal_stage deal_stage DEFAULT 'new',
    
    -- AI Processing
    ai_qualification_data JSONB,
    ai_confidence DECIMAL(3, 2),
    
    -- GDPR
    marketing_consent BOOLEAN DEFAULT FALSE,
    consent_timestamp TIMESTAMP WITH TIME ZONE,
    data_retention_date DATE,  -- When to delete if inactive
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(100) DEFAULT 'system',
    
    -- Constraints
    CONSTRAINT valid_email CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
    CONSTRAINT valid_phone CHECK (phone_normalised IS NULL OR phone_normalised ~ '^\+44[0-9]{10}$')
);

-- Indexes for leads
CREATE INDEX idx_leads_hubspot_contact ON leads(hubspot_contact_id);
CREATE INDEX idx_leads_hubspot_deal ON leads(hubspot_deal_id);
CREATE INDEX idx_leads_email ON leads(email);
CREATE INDEX idx_leads_phone ON leads(phone_normalised);
CREATE INDEX idx_leads_postcode_area ON leads(postcode_area);
CREATE INDEX idx_leads_priority ON leads(priority);
CREATE INDEX idx_leads_deal_stage ON leads(deal_stage);
CREATE INDEX idx_leads_created ON leads(created_at DESC);
CREATE INDEX idx_leads_score ON leads(lead_score DESC);
CREATE INDEX idx_leads_active ON leads(is_active) WHERE is_active = TRUE;

-- Full text search index
CREATE INDEX idx_leads_fulltext ON leads USING gin(
    to_tsvector('english', COALESCE(full_name, '') || ' ' || COALESCE(email, '') || ' ' || COALESCE(postcode, ''))
);

-- ─────────────────────────────────────────────────────────────────────────────────
-- QUOTES TABLE
-- ─────────────────────────────────────────────────────────────────────────────────

CREATE TABLE quotes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    quote_number VARCHAR(20) UNIQUE NOT NULL,  -- HR-YYMMDD-XXXX
    
    -- Relationships
    lead_id UUID REFERENCES leads(id) ON DELETE SET NULL,
    hubspot_deal_id VARCHAR(50),
    
    -- Quote Details
    service_type service_type,
    property_type property_type,
    project_description TEXT,
    
    -- Amounts (stored in pence for precision)
    subtotal_pence BIGINT NOT NULL,
    vat_rate DECIMAL(4, 2) DEFAULT 20.00,
    vat_pence BIGINT NOT NULL,
    total_pence BIGINT NOT NULL,
    
    -- Validity
    valid_from DATE DEFAULT CURRENT_DATE,
    valid_until DATE,
    
    -- Timeline
    estimated_duration_weeks INTEGER,
    earliest_start_date DATE,
    
    -- Document Storage
    pdf_url TEXT,
    pdf_s3_key VARCHAR(255),
    cover_letter TEXT,
    
    -- Status
    status VARCHAR(20) DEFAULT 'draft' CHECK (status IN ('draft', 'sent', 'viewed', 'accepted', 'rejected', 'expired', 'superseded')),
    
    -- Tracking
    sent_at TIMESTAMP WITH TIME ZONE,
    viewed_at TIMESTAMP WITH TIME ZONE,
    viewed_count INTEGER DEFAULT 0,
    accepted_at TIMESTAMP WITH TIME ZONE,
    rejected_at TIMESTAMP WITH TIME ZONE,
    rejection_reason TEXT,
    
    -- Version Control
    version INTEGER DEFAULT 1,
    parent_quote_id UUID REFERENCES quotes(id),
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(100) DEFAULT 'system'
);

-- Indexes for quotes
CREATE INDEX idx_quotes_number ON quotes(quote_number);
CREATE INDEX idx_quotes_lead ON quotes(lead_id);
CREATE INDEX idx_quotes_status ON quotes(status);
CREATE INDEX idx_quotes_valid_until ON quotes(valid_until);
CREATE INDEX idx_quotes_created ON quotes(created_at DESC);

-- ─────────────────────────────────────────────────────────────────────────────────
-- QUOTE LINE ITEMS TABLE
-- ─────────────────────────────────────────────────────────────────────────────────

CREATE TABLE quote_line_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    quote_id UUID NOT NULL REFERENCES quotes(id) ON DELETE CASCADE,
    
    -- Item Details
    category VARCHAR(20) CHECK (category IN ('labour', 'materials', 'plant', 'fees', 'contingency')),
    description TEXT NOT NULL,
    notes TEXT,
    
    -- Quantities
    quantity DECIMAL(10, 2) NOT NULL,
    unit VARCHAR(20),  -- sqm, item, hours, days, etc.
    
    -- Pricing (pence)
    unit_price_pence BIGINT NOT NULL,
    total_pence BIGINT NOT NULL,
    
    -- Optional breakdown
    breakdown JSONB,  -- For complex items with sub-components
    
    -- Display
    sort_order INTEGER DEFAULT 0,
    is_optional BOOLEAN DEFAULT FALSE,
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for line items
CREATE INDEX idx_line_items_quote ON quote_line_items(quote_id);
CREATE INDEX idx_line_items_category ON quote_line_items(category);

-- ─────────────────────────────────────────────────────────────────────────────────
-- CONVERSATIONS TABLE
-- Stores all customer communication history
-- ─────────────────────────────────────────────────────────────────────────────────

CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Relationships
    lead_id UUID REFERENCES leads(id) ON DELETE SET NULL,
    
    -- Message Details
    channel conversation_channel NOT NULL,
    direction message_direction NOT NULL,
    
    -- External IDs
    external_message_id VARCHAR(100),  -- WhatsApp message ID, email message ID, etc.
    thread_id VARCHAR(100),  -- For grouping related messages
    
    -- Content
    content TEXT,
    content_html TEXT,  -- For emails
    subject VARCHAR(500),  -- For emails
    
    -- Media
    has_media BOOLEAN DEFAULT FALSE,
    media_type VARCHAR(50),  -- audio, image, document
    media_url TEXT,
    media_s3_key VARCHAR(255),
    
    -- AI Processing
    ai_summary TEXT,
    ai_sentiment VARCHAR(20),  -- positive, neutral, negative
    ai_intent VARCHAR(50),  -- enquiry, follow-up, complaint, etc.
    ai_extracted_data JSONB,
    
    -- For outbound messages
    template_used VARCHAR(100),
    
    -- Status
    status VARCHAR(20) DEFAULT 'delivered' CHECK (status IN ('pending', 'sent', 'delivered', 'read', 'failed')),
    error_message TEXT,
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE
);

-- Indexes for conversations
CREATE INDEX idx_conversations_lead ON conversations(lead_id);
CREATE INDEX idx_conversations_channel ON conversations(channel);
CREATE INDEX idx_conversations_direction ON conversations(direction);
CREATE INDEX idx_conversations_thread ON conversations(thread_id);
CREATE INDEX idx_conversations_created ON conversations(created_at DESC);
CREATE INDEX idx_conversations_external ON conversations(external_message_id);

-- ─────────────────────────────────────────────────────────────────────────────────
-- DOCUMENTS TABLE
-- Tracks all generated documents
-- ─────────────────────────────────────────────────────────────────────────────────

CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Relationships
    lead_id UUID REFERENCES leads(id) ON DELETE SET NULL,
    quote_id UUID REFERENCES quotes(id) ON DELETE SET NULL,
    
    -- Document Details
    document_type document_type NOT NULL,
    document_number VARCHAR(50),  -- e.g., INV-2024-001
    title VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- File Storage
    file_name VARCHAR(255),
    file_size_bytes BIGINT,
    mime_type VARCHAR(100),
    s3_bucket VARCHAR(100),
    s3_key VARCHAR(255) NOT NULL,
    s3_url TEXT,
    presigned_url TEXT,
    presigned_url_expires_at TIMESTAMP WITH TIME ZONE,
    
    -- Version Control
    version INTEGER DEFAULT 1,
    is_current BOOLEAN DEFAULT TRUE,
    parent_document_id UUID REFERENCES documents(id),
    
    -- Status
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('draft', 'active', 'superseded', 'archived', 'deleted')),
    
    -- Access Tracking
    view_count INTEGER DEFAULT 0,
    last_viewed_at TIMESTAMP WITH TIME ZONE,
    download_count INTEGER DEFAULT 0,
    last_downloaded_at TIMESTAMP WITH TIME ZONE,
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(100) DEFAULT 'system'
);

-- Indexes for documents
CREATE INDEX idx_documents_lead ON documents(lead_id);
CREATE INDEX idx_documents_quote ON documents(quote_id);
CREATE INDEX idx_documents_type ON documents(document_type);
CREATE INDEX idx_documents_number ON documents(document_number);
CREATE INDEX idx_documents_current ON documents(is_current) WHERE is_current = TRUE;

-- ─────────────────────────────────────────────────────────────────────────────────
-- SURVEYS TABLE
-- Tracks scheduled site surveys
-- ─────────────────────────────────────────────────────────────────────────────────

CREATE TABLE surveys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Relationships
    lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    
    -- Scheduling
    scheduled_date DATE NOT NULL,
    scheduled_time TIME NOT NULL,
    duration_minutes INTEGER DEFAULT 30,
    
    -- Calendar Integration
    calendar_event_id VARCHAR(255),
    calendar_provider VARCHAR(50) DEFAULT 'microsoft',  -- microsoft, google
    
    -- Location
    address TEXT,
    postcode VARCHAR(10),
    access_notes TEXT,
    parking_notes TEXT,
    
    -- Assignment
    assigned_to VARCHAR(100) DEFAULT 'ross',
    
    -- Status
    status VARCHAR(20) DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'confirmed', 'completed', 'cancelled', 'no-show', 'rescheduled')),
    
    -- Confirmation
    confirmation_sent_at TIMESTAMP WITH TIME ZONE,
    reminder_sent_at TIMESTAMP WITH TIME ZONE,
    confirmed_by_customer BOOLEAN DEFAULT FALSE,
    
    -- Outcome
    completed_at TIMESTAMP WITH TIME ZONE,
    outcome_notes TEXT,
    quote_to_follow BOOLEAN,
    
    -- Rescheduling
    rescheduled_from_id UUID REFERENCES surveys(id),
    cancellation_reason TEXT,
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for surveys
CREATE INDEX idx_surveys_lead ON surveys(lead_id);
CREATE INDEX idx_surveys_date ON surveys(scheduled_date);
CREATE INDEX idx_surveys_status ON surveys(status);
CREATE INDEX idx_surveys_assigned ON surveys(assigned_to);

-- ─────────────────────────────────────────────────────────────────────────────────
-- AUDIT LOG TABLE
-- ─────────────────────────────────────────────────────────────────────────────────

CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- What changed
    entity_type VARCHAR(50) NOT NULL,  -- leads, quotes, documents, etc.
    entity_id UUID,
    action VARCHAR(50) NOT NULL,  -- create, update, delete, view, etc.
    
    -- Who made the change
    actor VARCHAR(100),
    actor_type VARCHAR(20),  -- user, system, api, workflow
    
    -- Change details
    old_values JSONB,
    new_values JSONB,
    changed_fields TEXT[],
    
    -- Context
    ip_address INET,
    user_agent TEXT,
    request_id VARCHAR(100),
    workflow_id VARCHAR(100),
    
    -- Timestamp
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for audit log
CREATE INDEX idx_audit_entity ON audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_action ON audit_log(action);
CREATE INDEX idx_audit_actor ON audit_log(actor);
CREATE INDEX idx_audit_created ON audit_log(created_at DESC);

-- Partition audit log by month for better performance
-- CREATE TABLE audit_log_y2024m12 PARTITION OF audit_log
--     FOR VALUES FROM ('2024-12-01') TO ('2025-01-01');

-- ─────────────────────────────────────────────────────────────────────────────────
-- WORKFLOW EXECUTIONS TABLE
-- Tracks n8n workflow executions for debugging
-- ─────────────────────────────────────────────────────────────────────────────────

CREATE TABLE workflow_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Workflow Details
    workflow_name VARCHAR(255) NOT NULL,
    workflow_id VARCHAR(100),
    execution_id VARCHAR(100),
    
    -- Related Entities
    lead_id UUID REFERENCES leads(id) ON DELETE SET NULL,
    
    -- Execution Details
    trigger_type VARCHAR(50),  -- webhook, schedule, manual
    trigger_data JSONB,
    
    -- Status
    status VARCHAR(20) DEFAULT 'running' CHECK (status IN ('running', 'success', 'error', 'cancelled')),
    error_message TEXT,
    error_stack TEXT,
    
    -- Timing
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_ms INTEGER,
    
    -- Output
    output_data JSONB
);

-- Indexes
CREATE INDEX idx_workflow_executions_workflow ON workflow_executions(workflow_name);
CREATE INDEX idx_workflow_executions_lead ON workflow_executions(lead_id);
CREATE INDEX idx_workflow_executions_status ON workflow_executions(status);
CREATE INDEX idx_workflow_executions_started ON workflow_executions(started_at DESC);

-- ─────────────────────────────────────────────────────────────────────────────────
-- FUNCTIONS & TRIGGERS
-- ─────────────────────────────────────────────────────────────────────────────────

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at trigger to relevant tables
CREATE TRIGGER update_leads_updated_at
    BEFORE UPDATE ON leads
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_quotes_updated_at
    BEFORE UPDATE ON quotes
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_surveys_updated_at
    BEFORE UPDATE ON surveys
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Function to generate quote number
CREATE OR REPLACE FUNCTION generate_quote_number()
RETURNS VARCHAR(20) AS $$
DECLARE
    today_date VARCHAR(6);
    sequence_num INTEGER;
    new_number VARCHAR(20);
BEGIN
    today_date := TO_CHAR(CURRENT_DATE, 'YYMMDD');
    
    SELECT COALESCE(MAX(
        CAST(SUBSTRING(quote_number FROM 'HR-' || today_date || '-(\d{4})') AS INTEGER)
    ), 0) + 1
    INTO sequence_num
    FROM quotes
    WHERE quote_number LIKE 'HR-' || today_date || '-%';
    
    new_number := 'HR-' || today_date || '-' || LPAD(sequence_num::TEXT, 4, '0');
    
    RETURN new_number;
END;
$$ LANGUAGE plpgsql;

-- Function to normalise phone numbers
CREATE OR REPLACE FUNCTION normalise_uk_phone(phone VARCHAR)
RETURNS VARCHAR AS $$
DECLARE
    clean_phone VARCHAR;
BEGIN
    -- Remove all non-digits
    clean_phone := REGEXP_REPLACE(phone, '[^0-9]', '', 'g');
    
    -- Handle different formats
    IF clean_phone LIKE '44%' THEN
        clean_phone := '+' || clean_phone;
    ELSIF clean_phone LIKE '0%' THEN
        clean_phone := '+44' || SUBSTRING(clean_phone FROM 2);
    ELSIF LENGTH(clean_phone) = 10 THEN
        clean_phone := '+44' || clean_phone;
    END IF;
    
    RETURN clean_phone;
END;
$$ LANGUAGE plpgsql;

-- Trigger to normalise phone on insert/update
CREATE OR REPLACE FUNCTION normalise_lead_phone()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.phone IS NOT NULL THEN
        NEW.phone_normalised := normalise_uk_phone(NEW.phone);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER normalise_lead_phone_trigger
    BEFORE INSERT OR UPDATE OF phone ON leads
    FOR EACH ROW
    EXECUTE FUNCTION normalise_lead_phone();

-- Function to extract postcode area
CREATE OR REPLACE FUNCTION extract_postcode_area(postcode VARCHAR)
RETURNS VARCHAR AS $$
BEGIN
    RETURN UPPER(REGEXP_REPLACE(
        SPLIT_PART(UPPER(TRIM(postcode)), ' ', 1),
        '([A-Z]{1,2})(\d{1,2})[A-Z]?',
        '\1\2'
    ));
END;
$$ LANGUAGE plpgsql;

-- Trigger to extract postcode area
CREATE OR REPLACE FUNCTION set_postcode_area()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.postcode IS NOT NULL THEN
        NEW.postcode_area := extract_postcode_area(NEW.postcode);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_lead_postcode_area
    BEFORE INSERT OR UPDATE OF postcode ON leads
    FOR EACH ROW
    EXECUTE FUNCTION set_postcode_area();

-- ─────────────────────────────────────────────────────────────────────────────────
-- VIEWS
-- ─────────────────────────────────────────────────────────────────────────────────

-- Active leads dashboard view
CREATE OR REPLACE VIEW v_active_leads AS
SELECT 
    l.id,
    l.full_name,
    l.email,
    l.phone,
    l.postcode_area,
    l.service_type,
    l.budget_band,
    l.lead_score,
    l.priority,
    l.deal_stage,
    l.source,
    l.created_at,
    l.updated_at,
    EXTRACT(EPOCH FROM (NOW() - l.updated_at)) / 86400 AS days_since_activity,
    COUNT(DISTINCT c.id) AS message_count,
    COUNT(DISTINCT q.id) AS quote_count,
    MAX(c.created_at) AS last_message_at
FROM leads l
LEFT JOIN conversations c ON c.lead_id = l.id
LEFT JOIN quotes q ON q.lead_id = l.id
WHERE l.is_active = TRUE
GROUP BY l.id
ORDER BY 
    CASE l.priority 
        WHEN 'hot' THEN 1 
        WHEN 'warm' THEN 2 
        WHEN 'cool' THEN 3 
        ELSE 4 
    END,
    l.lead_score DESC;

-- Pipeline summary view
CREATE OR REPLACE VIEW v_pipeline_summary AS
SELECT 
    deal_stage,
    priority,
    COUNT(*) AS lead_count,
    SUM(CASE budget_band 
        WHEN 'under-15k' THEN 10000
        WHEN '15k-40k' THEN 27500
        WHEN '40k-100k' THEN 70000
        WHEN '100k-250k' THEN 175000
        WHEN 'over-250k' THEN 350000
        ELSE 50000
    END) AS estimated_value,
    AVG(lead_score) AS avg_score
FROM leads
WHERE is_active = TRUE
GROUP BY deal_stage, priority
ORDER BY 
    CASE deal_stage
        WHEN 'new' THEN 1
        WHEN 'contacted' THEN 2
        WHEN 'survey-scheduled' THEN 3
        WHEN 'survey-completed' THEN 4
        WHEN 'quote-sent' THEN 5
        WHEN 'negotiation' THEN 6
        WHEN 'contract-sent' THEN 7
        ELSE 8
    END;

-- Quotes pending view
CREATE OR REPLACE VIEW v_quotes_pending AS
SELECT 
    q.id,
    q.quote_number,
    q.total_pence / 100.0 AS total_gbp,
    q.status,
    q.valid_until,
    q.sent_at,
    q.viewed_count,
    l.full_name,
    l.email,
    l.postcode_area,
    q.service_type,
    EXTRACT(EPOCH FROM (NOW() - q.sent_at)) / 86400 AS days_since_sent,
    q.valid_until - CURRENT_DATE AS days_until_expiry
FROM quotes q
JOIN leads l ON l.id = q.lead_id
WHERE q.status IN ('sent', 'viewed')
ORDER BY q.valid_until ASC;

-- ─────────────────────────────────────────────────────────────────────────────────
-- GRANTS (adjust as needed for your setup)
-- ─────────────────────────────────────────────────────────────────────────────────

-- Grant usage on sequences
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO hampstead;

-- Grant table permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO hampstead;

-- Grant view permissions
GRANT SELECT ON v_active_leads TO hampstead;
GRANT SELECT ON v_pipeline_summary TO hampstead;
GRANT SELECT ON v_quotes_pending TO hampstead;

-- ─────────────────────────────────────────────────────────────────────────────────
-- COMMENTS
-- ─────────────────────────────────────────────────────────────────────────────────

COMMENT ON TABLE leads IS 'Primary lead/customer data - syncs with HubSpot';
COMMENT ON TABLE quotes IS 'Generated quotes with PDF storage';
COMMENT ON TABLE quote_line_items IS 'Individual line items for each quote';
COMMENT ON TABLE conversations IS 'All customer communication across channels';
COMMENT ON TABLE documents IS 'All generated documents (quotes, contracts, invoices)';
COMMENT ON TABLE surveys IS 'Scheduled and completed site surveys';
COMMENT ON TABLE audit_log IS 'Comprehensive audit trail for all changes';
COMMENT ON TABLE workflow_executions IS 'n8n workflow execution tracking';

COMMENT ON COLUMN leads.phone_normalised IS 'E.164 format phone number for consistent matching';
COMMENT ON COLUMN leads.ai_qualification_data IS 'Full AI qualification response JSON';
COMMENT ON COLUMN quotes.total_pence IS 'Amount stored in pence to avoid floating point issues';
