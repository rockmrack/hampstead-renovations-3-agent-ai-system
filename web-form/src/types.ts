// Lead Form Types
export interface LeadFormData {
  // Contact Information
  firstName: string
  lastName: string
  email: string
  phone: string
  preferredContact: 'phone' | 'email' | 'whatsapp'
  
  // Property Details
  postcode: string
  propertyType: PropertyType
  propertyAge: PropertyAge
  
  // Project Details
  serviceType: ServiceType[]
  projectDescription: string
  timeline: ProjectTimeline
  budgetRange: BudgetRange
  
  // Additional Info
  conservationArea: boolean | null
  planningRequired: boolean | null
  howDidYouHear: ReferralSource
  marketingConsent: boolean
}

export type PropertyType = 
  | 'detached'
  | 'semi-detached'
  | 'terraced'
  | 'flat'
  | 'maisonette'
  | 'townhouse'
  | 'period'
  | 'new-build'

export type PropertyAge = 
  | 'pre-1900'
  | '1900-1930'
  | '1930-1960'
  | '1960-1990'
  | '1990-2010'
  | 'post-2010'

export type ServiceType = 
  | 'kitchen'
  | 'bathroom'
  | 'loft-conversion'
  | 'extension'
  | 'basement'
  | 'full-refurbishment'
  | 'structural'
  | 'electrical'
  | 'plumbing'
  | 'flooring'
  | 'painting-decorating'
  | 'other'

export type ProjectTimeline = 
  | 'asap'
  | '1-3-months'
  | '3-6-months'
  | '6-12-months'
  | 'planning-stage'

export type BudgetRange = 
  | 'under-25k'
  | '25k-50k'
  | '50k-100k'
  | '100k-200k'
  | '200k-500k'
  | 'over-500k'
  | 'not-sure'

export type ReferralSource = 
  | 'google'
  | 'social-media'
  | 'referral'
  | 'local-advertising'
  | 'houzz'
  | 'checkatrade'
  | 'other'

// Form Step Types
export interface FormStep {
  id: number
  title: string
  description: string
  fields: (keyof LeadFormData)[]
}

// API Response Types
export interface SubmitLeadResponse {
  success: boolean
  leadId?: string
  message: string
}

// UI State Types
export interface FormState {
  currentStep: number
  isSubmitting: boolean
  submitError: string | null
  isSuccess: boolean
}

// Display Options
export const PROPERTY_TYPES: Record<PropertyType, string> = {
  'detached': 'Detached House',
  'semi-detached': 'Semi-Detached House',
  'terraced': 'Terraced House',
  'flat': 'Flat/Apartment',
  'maisonette': 'Maisonette',
  'townhouse': 'Townhouse',
  'period': 'Period Property',
  'new-build': 'New Build',
}

export const PROPERTY_AGES: Record<PropertyAge, string> = {
  'pre-1900': 'Victorian/Edwardian (Pre-1900)',
  '1900-1930': '1900-1930',
  '1930-1960': '1930-1960',
  '1960-1990': '1960-1990',
  '1990-2010': '1990-2010',
  'post-2010': 'Post-2010',
}

export const SERVICE_TYPES: Record<ServiceType, { label: string; icon: string; description: string }> = {
  'kitchen': { 
    label: 'Kitchen Renovation', 
    icon: '🍳',
    description: 'Complete kitchen design and installation'
  },
  'bathroom': { 
    label: 'Bathroom Renovation', 
    icon: '🚿',
    description: 'Bathroom design, refurbishment, and installation'
  },
  'loft-conversion': { 
    label: 'Loft Conversion', 
    icon: '🏠',
    description: 'Transform your loft into living space'
  },
  'extension': { 
    label: 'House Extension', 
    icon: '🏗️',
    description: 'Ground floor, side, or rear extensions'
  },
  'basement': { 
    label: 'Basement Conversion', 
    icon: '⬇️',
    description: 'Basement excavation and conversion'
  },
  'full-refurbishment': { 
    label: 'Full Refurbishment', 
    icon: '🔨',
    description: 'Complete property renovation'
  },
  'structural': { 
    label: 'Structural Work', 
    icon: '🧱',
    description: 'Walls, load-bearing alterations, underpinning'
  },
  'electrical': { 
    label: 'Electrical', 
    icon: '⚡',
    description: 'Rewiring and electrical installations'
  },
  'plumbing': { 
    label: 'Plumbing & Heating', 
    icon: '🔧',
    description: 'Central heating, boilers, plumbing'
  },
  'flooring': { 
    label: 'Flooring', 
    icon: '🪵',
    description: 'Wood, tile, carpet, and underfloor heating'
  },
  'painting-decorating': { 
    label: 'Painting & Decorating', 
    icon: '🎨',
    description: 'Interior and exterior decoration'
  },
  'other': { 
    label: 'Other', 
    icon: '📝',
    description: 'Something else - tell us in the description'
  },
}

export const TIMELINES: Record<ProjectTimeline, string> = {
  'asap': 'As soon as possible',
  '1-3-months': 'Within 1-3 months',
  '3-6-months': 'Within 3-6 months',
  '6-12-months': 'Within 6-12 months',
  'planning-stage': 'Just exploring options',
}

export const BUDGET_RANGES: Record<BudgetRange, string> = {
  'under-25k': 'Under £25,000',
  '25k-50k': '£25,000 - £50,000',
  '50k-100k': '£50,000 - £100,000',
  '100k-200k': '£100,000 - £200,000',
  '200k-500k': '£200,000 - £500,000',
  'over-500k': 'Over £500,000',
  'not-sure': 'Not sure yet',
}

export const REFERRAL_SOURCES: Record<ReferralSource, string> = {
  'google': 'Google Search',
  'social-media': 'Social Media (Instagram, Facebook)',
  'referral': 'Friend/Family Referral',
  'local-advertising': 'Local Advertising',
  'houzz': 'Houzz',
  'checkatrade': 'Checkatrade',
  'other': 'Other',
}

// Postcode Validation
export const COVERED_POSTCODES = ['NW1', 'NW2', 'NW3', 'NW5', 'NW6', 'NW8', 'NW10', 'NW11', 'N6', 'N2', 'N10', 'N12', 'W9', 'W11', 'WC1']
