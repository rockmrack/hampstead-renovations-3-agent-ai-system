/**
 * Hampstead Renovations - Lead Intake API Service
 * 
 * This module handles all communication with the Lead Intake API backend.
 * It includes retry logic, error handling, and type safety.
 */

import type { LeadFormData } from '../types'

// ═══════════════════════════════════════════════════════════════════════════════
// CONFIGURATION
// ═══════════════════════════════════════════════════════════════════════════════

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8004'
const MAX_RETRIES = 3
const RETRY_DELAY_MS = 1000

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export interface LeadSubmissionResponse {
  success: boolean
  leadId: string
  message: string
  score?: number
  priority?: string
  estimatedCallback?: string
}

export interface ApiError {
  error: string
  detail?: string
  code?: string
  statusCode: number
}

export interface ProjectType {
  id: string
  name: string
  description: string
}

export interface LeadSource {
  id: string
  name: string
}

// ═══════════════════════════════════════════════════════════════════════════════
// UTILITIES
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Sleep utility for retry delays
 */
const sleep = (ms: number): Promise<void> => 
  new Promise(resolve => setTimeout(resolve, ms))

/**
 * Exponential backoff delay calculator
 */
const getRetryDelay = (attempt: number): number => 
  RETRY_DELAY_MS * Math.pow(2, attempt)

/**
 * Check if error is retryable (network errors, 5xx server errors)
 */
const isRetryableError = (error: unknown): boolean => {
  if (error instanceof TypeError) {
    // Network error (fetch failed)
    return true
  }
  if (error instanceof ApiResponseError) {
    // Retry on server errors (5xx), not client errors (4xx)
    return error.statusCode >= 500
  }
  return false
}

// ═══════════════════════════════════════════════════════════════════════════════
// ERROR CLASSES
// ═══════════════════════════════════════════════════════════════════════════════

export class ApiResponseError extends Error {
  statusCode: number
  detail?: string
  code?: string

  constructor(message: string, statusCode: number, detail?: string, code?: string) {
    super(message)
    this.name = 'ApiResponseError'
    this.statusCode = statusCode
    this.detail = detail
    this.code = code
  }
}

export class ValidationError extends Error {
  fields: Record<string, string[]>

  constructor(message: string, fields: Record<string, string[]>) {
    super(message)
    this.name = 'ValidationError'
    this.fields = fields
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// API CLIENT
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Make an API request with retry logic
 */
async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {},
  retries: number = MAX_RETRIES
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`
  
  const defaultHeaders: HeadersInit = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  }

  const config: RequestInit = {
    ...options,
    headers: {
      ...defaultHeaders,
      ...options.headers,
    },
  }

  let lastError: Error | null = null
  
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const response = await fetch(url, config)
      
      // Handle non-OK responses
      if (!response.ok) {
        let errorData: ApiError
        
        try {
          errorData = await response.json()
        } catch {
          errorData = {
            error: `Request failed with status ${response.status}`,
            statusCode: response.status,
          }
        }
        
        // Handle validation errors (422)
        if (response.status === 422 && errorData.detail) {
          throw new ValidationError(
            'Validation failed',
            typeof errorData.detail === 'object' ? errorData.detail : {}
          )
        }
        
        throw new ApiResponseError(
          errorData.error || `Request failed with status ${response.status}`,
          response.status,
          typeof errorData.detail === 'string' ? errorData.detail : undefined,
          errorData.code
        )
      }
      
      // Parse successful response
      const data = await response.json()
      return data as T
      
    } catch (error) {
      lastError = error as Error
      
      // Don't retry validation errors or client errors
      if (!isRetryableError(error)) {
        throw error
      }
      
      // If we have more retries, wait and try again
      if (attempt < retries) {
        const delay = getRetryDelay(attempt)
        console.warn(`API request failed, retrying in ${delay}ms (attempt ${attempt + 1}/${retries})`)
        await sleep(delay)
      }
    }
  }
  
  // All retries exhausted
  throw lastError || new Error('Request failed after all retries')
}

// ═══════════════════════════════════════════════════════════════════════════════
// API METHODS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Submit a new lead from the web form
 */
export async function submitLead(formData: LeadFormData): Promise<LeadSubmissionResponse> {
  // Transform form data to API format
  const payload = {
    // Contact info
    first_name: formData.firstName,
    last_name: formData.lastName,
    email: formData.email,
    phone: formData.phone,
    preferred_contact: formData.preferredContact,
    
    // Property info
    postcode: formData.postcode.toUpperCase().replace(/\s+/g, ' ').trim(),
    property_type: formData.propertyType,
    property_age: formData.propertyAge,
    
    // Project info
    project_types: formData.serviceType,
    project_description: formData.projectDescription,
    
    // Additional details
    timeline: formData.timeline,
    budget_range: formData.budgetRange,
    conservation_area: formData.conservationArea,
    planning_required: formData.planningRequired,
    
    // Source tracking
    source: 'web-form',
    how_did_you_hear: formData.howDidYouHear,
    marketing_consent: formData.marketingConsent,
    
    // Metadata
    submitted_at: new Date().toISOString(),
    user_agent: navigator.userAgent,
    referrer: document.referrer || undefined,
    page_url: window.location.href,
  }
  
  return apiRequest<LeadSubmissionResponse>('/leads', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

/**
 * Check API health status
 */
export async function checkHealth(): Promise<{ status: string; timestamp: string }> {
  return apiRequest<{ status: string; timestamp: string }>('/health')
}

/**
 * Get available project types
 */
export async function getProjectTypes(): Promise<ProjectType[]> {
  const response = await apiRequest<{ project_types: ProjectType[] }>('/project-types')
  return response.project_types
}

/**
 * Get available lead sources
 */
export async function getLeadSources(): Promise<LeadSource[]> {
  const response = await apiRequest<{ sources: LeadSource[] }>('/lead-sources')
  return response.sources
}

/**
 * Get lead status by ID (for tracking)
 */
export async function getLeadStatus(leadId: string): Promise<{
  id: string
  status: string
  created_at: string
  estimated_callback?: string
}> {
  return apiRequest(`/leads/${leadId}`)
}

// ═══════════════════════════════════════════════════════════════════════════════
// REACT HOOK HELPERS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Format API error for display
 */
export function formatApiError(error: unknown): string {
  if (error instanceof ValidationError) {
    const fieldErrors = Object.entries(error.fields)
      .map(([field, errors]) => `${field}: ${errors.join(', ')}`)
      .join('; ')
    return `Please check your input: ${fieldErrors}`
  }
  
  if (error instanceof ApiResponseError) {
    switch (error.statusCode) {
      case 400:
        return error.detail || 'Invalid request. Please check your information.'
      case 401:
      case 403:
        return 'Access denied. Please refresh the page and try again.'
      case 404:
        return 'Service not found. Please try again later.'
      case 429:
        return 'Too many requests. Please wait a moment and try again.'
      case 500:
      case 502:
      case 503:
        return 'Our service is temporarily unavailable. Please try again in a few minutes.'
      default:
        return error.message || 'An unexpected error occurred.'
    }
  }
  
  if (error instanceof TypeError && error.message.includes('fetch')) {
    return 'Unable to connect to our service. Please check your internet connection.'
  }
  
  if (error instanceof Error) {
    return error.message
  }
  
  return 'An unexpected error occurred. Please try again.'
}
