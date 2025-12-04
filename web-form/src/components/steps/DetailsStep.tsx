import { useFormContext } from 'react-hook-form'
import type { LeadFormData } from '../../types'
import { TIMELINES, BUDGET_RANGES, REFERRAL_SOURCES } from '../../types'

export function DetailsStep() {
  const { register, watch, setValue, formState: { errors } } = useFormContext<LeadFormData>()
  
  const conservationArea = watch('conservationArea')
  const planningRequired = watch('planningRequired')

  return (
    <div className="space-y-6">
      {/* Timeline */}
      <div>
        <label className="input-label">
          When would you like to start? <span className="text-red-500">*</span>
        </label>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {Object.entries(TIMELINES).map(([value, label]) => (
            <label
              key={value}
              className="relative flex items-center p-3 bg-white border border-hampstead-200 rounded-lg cursor-pointer hover:border-gold-400 transition-colors has-[:checked]:border-gold-500 has-[:checked]:bg-gold-50 has-[:checked]:ring-2 has-[:checked]:ring-gold-500"
            >
              <input
                type="radio"
                value={value}
                className="sr-only"
                {...register('timeline')}
              />
              <span className="text-sm font-medium text-hampstead-700">{label}</span>
            </label>
          ))}
        </div>
        {errors.timeline && (
          <p className="input-error">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            Please select a timeline
          </p>
        )}
      </div>

      {/* Budget Range */}
      <div>
        <label className="input-label">
          Approximate Budget Range <span className="text-red-500">*</span>
        </label>
        <p className="text-sm text-hampstead-500 mb-3">This helps us understand the scope of your project</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {Object.entries(BUDGET_RANGES).map(([value, label]) => (
            <label
              key={value}
              className="relative flex items-center justify-center p-3 bg-white border border-hampstead-200 rounded-lg cursor-pointer hover:border-gold-400 transition-colors has-[:checked]:border-gold-500 has-[:checked]:bg-gold-50 has-[:checked]:ring-2 has-[:checked]:ring-gold-500 text-center"
            >
              <input
                type="radio"
                value={value}
                className="sr-only"
                {...register('budgetRange')}
              />
              <span className="text-sm font-medium text-hampstead-700">{label}</span>
            </label>
          ))}
        </div>
        {errors.budgetRange && (
          <p className="input-error">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            Please select a budget range
          </p>
        )}
      </div>

      {/* Conservation Area & Planning */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <label className="input-label">
            Is your property in a conservation area?
          </label>
          <div className="flex gap-3">
            {[
              { value: true, label: 'Yes' },
              { value: false, label: 'No' },
              { value: null, label: 'Not Sure' },
            ].map((option) => (
              <button
                key={String(option.value)}
                type="button"
                onClick={() => setValue('conservationArea', option.value, { shouldValidate: true })}
                className={`flex-1 py-2 px-4 rounded-lg border-2 font-medium transition-colors ${
                  conservationArea === option.value
                    ? 'border-gold-500 bg-gold-50 text-gold-700'
                    : 'border-hampstead-200 text-hampstead-600 hover:border-hampstead-300'
                }`}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="input-label">
            Do you think you'll need planning permission?
          </label>
          <div className="flex gap-3">
            {[
              { value: true, label: 'Yes' },
              { value: false, label: 'No' },
              { value: null, label: 'Not Sure' },
            ].map((option) => (
              <button
                key={String(option.value)}
                type="button"
                onClick={() => setValue('planningRequired', option.value, { shouldValidate: true })}
                className={`flex-1 py-2 px-4 rounded-lg border-2 font-medium transition-colors ${
                  planningRequired === option.value
                    ? 'border-gold-500 bg-gold-50 text-gold-700'
                    : 'border-hampstead-200 text-hampstead-600 hover:border-hampstead-300'
                }`}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* How did you hear about us */}
      <div>
        <label htmlFor="howDidYouHear" className="input-label">
          How did you hear about us? <span className="text-red-500">*</span>
        </label>
        <select
          id="howDidYouHear"
          className={`input-field ${errors.howDidYouHear ? 'error' : ''}`}
          {...register('howDidYouHear')}
        >
          <option value="">Select an option...</option>
          {Object.entries(REFERRAL_SOURCES).map(([value, label]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>
        {errors.howDidYouHear && (
          <p className="input-error">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            Please let us know how you found us
          </p>
        )}
      </div>

      {/* Marketing Consent */}
      <div className="bg-hampstead-50 rounded-lg p-4">
        <label className="flex items-start gap-3 cursor-pointer">
          <input
            type="checkbox"
            className="checkbox-custom mt-0.5"
            {...register('marketingConsent')}
          />
          <div>
            <span className="text-sm text-hampstead-700">
              I'd like to receive occasional updates about special offers, renovation tips, and project showcases from Hampstead Renovations.
            </span>
            <p className="text-xs text-hampstead-500 mt-1">
              You can unsubscribe at any time. We never share your information with third parties.
            </p>
          </div>
        </label>
      </div>

      {/* Privacy Note */}
      <div className="text-xs text-hampstead-500 text-center">
        By submitting this form, you agree to our{' '}
        <a href="#" className="text-navy-600 hover:underline">Privacy Policy</a>
        {' '}and{' '}
        <a href="#" className="text-navy-600 hover:underline">Terms of Service</a>.
      </div>
    </div>
  )
}
