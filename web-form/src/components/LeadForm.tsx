import { useState } from 'react'
import { useForm, FormProvider } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { motion, AnimatePresence } from 'framer-motion'
import { z } from 'zod'
import type { LeadFormData, FormStep } from '../types'
import { COVERED_POSTCODES } from '../types'
import { StepIndicator } from './StepIndicator'
import { ContactStep } from './steps/ContactStep'
import { PropertyStep } from './steps/PropertyStep'
import { ProjectStep } from './steps/ProjectStep'
import { DetailsStep } from './steps/DetailsStep'

// UK phone regex - allows various formats
const ukPhoneRegex = /^(?:(?:\+44)|(?:0))(?:\s?\d){9,10}$/

// UK postcode regex
const ukPostcodeRegex = /^[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}$/i

// Form validation schema
const leadFormSchema = z.object({
  firstName: z.string().min(2, 'First name must be at least 2 characters'),
  lastName: z.string().min(2, 'Last name must be at least 2 characters'),
  email: z.string().email('Please enter a valid email address'),
  phone: z.string().regex(ukPhoneRegex, 'Please enter a valid UK phone number'),
  preferredContact: z.enum(['phone', 'email', 'whatsapp']),
  postcode: z.string()
    .regex(ukPostcodeRegex, 'Please enter a valid UK postcode')
    .refine((val) => {
      const area = val.replace(/\s/g, '').match(/^([A-Z]{1,2}\d)/i)?.[1]?.toUpperCase()
      return area && COVERED_POSTCODES.some(pc => area.startsWith(pc.replace(/\d+$/, '')) || pc === area)
    }, 'Sorry, we currently only serve North West London (NW1-NW11, N2, N6, N10, N12, W9, W11)'),
  propertyType: z.enum(['detached', 'semi-detached', 'terraced', 'flat', 'maisonette', 'townhouse', 'period', 'new-build']),
  propertyAge: z.enum(['pre-1900', '1900-1930', '1930-1960', '1960-1990', '1990-2010', 'post-2010']),
  serviceType: z.array(z.enum([
    'kitchen', 'bathroom', 'loft-conversion', 'extension', 'basement',
    'full-refurbishment', 'structural', 'electrical', 'plumbing',
    'flooring', 'painting-decorating', 'other'
  ])).min(1, 'Please select at least one service'),
  projectDescription: z.string().min(20, 'Please provide more detail about your project (at least 20 characters)'),
  timeline: z.enum(['asap', '1-3-months', '3-6-months', '6-12-months', 'planning-stage']),
  budgetRange: z.enum(['under-25k', '25k-50k', '50k-100k', '100k-200k', '200k-500k', 'over-500k', 'not-sure']),
  conservationArea: z.boolean().nullable(),
  planningRequired: z.boolean().nullable(),
  howDidYouHear: z.enum(['google', 'social-media', 'referral', 'local-advertising', 'houzz', 'checkatrade', 'other']),
  marketingConsent: z.boolean(),
})

const FORM_STEPS: FormStep[] = [
  {
    id: 1,
    title: 'Your Details',
    description: 'How can we reach you?',
    fields: ['firstName', 'lastName', 'email', 'phone', 'preferredContact'],
  },
  {
    id: 2,
    title: 'Your Property',
    description: 'Tell us about your property',
    fields: ['postcode', 'propertyType', 'propertyAge'],
  },
  {
    id: 3,
    title: 'Your Project',
    description: 'What would you like us to do?',
    fields: ['serviceType', 'projectDescription'],
  },
  {
    id: 4,
    title: 'Final Details',
    description: 'A few more questions',
    fields: ['timeline', 'budgetRange', 'conservationArea', 'planningRequired', 'howDidYouHear', 'marketingConsent'],
  },
]

interface LeadFormProps {
  onSuccess: (firstName: string, leadId?: string) => void
}

export function LeadForm({ onSuccess }: LeadFormProps) {
  const [currentStep, setCurrentStep] = useState(1)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  const methods = useForm<LeadFormData>({
    resolver: zodResolver(leadFormSchema),
    mode: 'onBlur',
    defaultValues: {
      firstName: '',
      lastName: '',
      email: '',
      phone: '',
      preferredContact: 'phone',
      postcode: '',
      propertyType: undefined,
      propertyAge: undefined,
      serviceType: [],
      projectDescription: '',
      timeline: undefined,
      budgetRange: undefined,
      conservationArea: null,
      planningRequired: null,
      howDidYouHear: undefined,
      marketingConsent: false,
    },
  })

  const { handleSubmit, trigger, formState: { errors } } = methods

  const currentStepData = FORM_STEPS[currentStep - 1]

  const validateCurrentStep = async (): Promise<boolean> => {
    const fieldsToValidate = currentStepData.fields as (keyof LeadFormData)[]
    return await trigger(fieldsToValidate)
  }

  const goToNextStep = async () => {
    const isValid = await validateCurrentStep()
    if (isValid && currentStep < FORM_STEPS.length) {
      setCurrentStep(prev => prev + 1)
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }
  }

  const goToPrevStep = () => {
    if (currentStep > 1) {
      setCurrentStep(prev => prev - 1)
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }
  }

  const onSubmit = async (data: LeadFormData) => {
    setIsSubmitting(true)
    setSubmitError(null)

    try {
      const webhookUrl = import.meta.env.VITE_WEBHOOK_URL || '/api/webhook/web-lead'
      
      const response = await fetch(webhookUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...data,
          source: 'web-form',
          submittedAt: new Date().toISOString(),
          userAgent: navigator.userAgent,
          referrer: document.referrer,
        }),
      })

      if (!response.ok) {
        throw new Error('Failed to submit form. Please try again.')
      }

      const result = await response.json()
      onSuccess(data.firstName, result.leadId)
    } catch {
      setSubmitError('Something went wrong. Please try again or contact us directly.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const slideVariants = {
    enter: (direction: number) => ({
      x: direction > 0 ? 100 : -100,
      opacity: 0,
    }),
    center: {
      x: 0,
      opacity: 1,
    },
    exit: (direction: number) => ({
      x: direction < 0 ? 100 : -100,
      opacity: 0,
    }),
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="card p-6 md:p-8"
    >
      {/* Header */}
      <div className="text-center mb-8">
        <h1 className="text-2xl md:text-3xl font-serif font-bold text-navy-900 mb-2">
          Get Your Free Quote
        </h1>
        <p className="text-hampstead-600">
          Tell us about your project and we'll get back to you within 24 hours
        </p>
      </div>

      {/* Step Indicator */}
      <StepIndicator 
        steps={FORM_STEPS} 
        currentStep={currentStep} 
      />

      {/* Form */}
      <FormProvider {...methods}>
        <form onSubmit={handleSubmit(onSubmit)} noValidate>
          <AnimatePresence mode="wait" custom={currentStep}>
            <motion.div
              key={currentStep}
              custom={currentStep}
              variants={slideVariants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{ duration: 0.3, ease: 'easeInOut' }}
            >
              {/* Step Title */}
              <div className="mb-6">
                <h2 className="text-xl font-semibold text-navy-800">
                  {currentStepData.title}
                </h2>
                <p className="text-hampstead-500 text-sm">
                  {currentStepData.description}
                </p>
              </div>

              {/* Step Content */}
              {currentStep === 1 && <ContactStep />}
              {currentStep === 2 && <PropertyStep />}
              {currentStep === 3 && <ProjectStep />}
              {currentStep === 4 && <DetailsStep />}
            </motion.div>
          </AnimatePresence>

          {/* Error Message */}
          {submitError && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6"
            >
              <p className="flex items-center gap-2">
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
                {submitError}
              </p>
            </motion.div>
          )}

          {/* Navigation Buttons */}
          <div className="flex justify-between items-center mt-8 pt-6 border-t border-hampstead-100">
            {currentStep > 1 ? (
              <button
                type="button"
                onClick={goToPrevStep}
                className="btn-outline"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
                Back
              </button>
            ) : (
              <div />
            )}

            {currentStep < FORM_STEPS.length ? (
              <button
                type="button"
                onClick={goToNextStep}
                className="btn-primary"
              >
                Continue
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>
            ) : (
              <button
                type="submit"
                disabled={isSubmitting}
                className="btn-primary"
              >
                {isSubmitting ? (
                  <>
                    <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    Submitting...
                  </>
                ) : (
                  <>
                    Submit Enquiry
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </>
                )}
              </button>
            )}
          </div>
        </form>
      </FormProvider>

      {/* Trust Badges */}
      <div className="mt-8 pt-6 border-t border-hampstead-100">
        <div className="flex flex-wrap justify-center items-center gap-6 text-hampstead-400 text-sm">
          <div className="flex items-center gap-2">
            <svg className="w-5 h-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M2.166 4.999A11.954 11.954 0 0010 1.944 11.954 11.954 0 0017.834 5c.11.65.166 1.32.166 2.001 0 5.225-3.34 9.67-8 11.317C5.34 16.67 2 12.225 2 7c0-.682.057-1.35.166-2.001zm11.541 3.708a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            SSL Secured
          </div>
          <div className="flex items-center gap-2">
            <svg className="w-5 h-5 text-gold-500" fill="currentColor" viewBox="0 0 20 20">
              <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
            </svg>
            5-Star Reviews
          </div>
          <div className="flex items-center gap-2">
            <svg className="w-5 h-5 text-navy-500" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M6.267 3.455a3.066 3.066 0 001.745-.723 3.066 3.066 0 013.976 0 3.066 3.066 0 001.745.723 3.066 3.066 0 012.812 2.812c.051.643.304 1.254.723 1.745a3.066 3.066 0 010 3.976 3.066 3.066 0 00-.723 1.745 3.066 3.066 0 01-2.812 2.812 3.066 3.066 0 00-1.745.723 3.066 3.066 0 01-3.976 0 3.066 3.066 0 00-1.745-.723 3.066 3.066 0 01-2.812-2.812 3.066 3.066 0 00-.723-1.745 3.066 3.066 0 010-3.976 3.066 3.066 0 00.723-1.745 3.066 3.066 0 012.812-2.812zm7.44 5.252a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            FMB Member
          </div>
          <div className="flex items-center gap-2">
            <svg className="w-5 h-5 text-navy-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            24hr Response
          </div>
        </div>
      </div>
    </motion.div>
  )
}
