import { useFormContext } from 'react-hook-form'
import type { LeadFormData } from '../../types'
import { PROPERTY_TYPES, PROPERTY_AGES } from '../../types'

export function PropertyStep() {
  const { register, formState: { errors } } = useFormContext<LeadFormData>()

  return (
    <div className="space-y-6">
      {/* Postcode */}
      <div>
        <label htmlFor="postcode" className="input-label">
          Property Postcode <span className="text-red-500">*</span>
        </label>
        <input
          id="postcode"
          type="text"
          autoComplete="postal-code"
          className={`input-field ${errors.postcode ? 'error' : ''}`}
          placeholder="NW3 4HT"
          {...register('postcode')}
        />
        <p className="text-xs text-hampstead-500 mt-1">
          We serve North West London: NW1-NW11, N2, N6, N10, N12, W9, W11
        </p>
        {errors.postcode && (
          <p className="input-error">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            {errors.postcode.message}
          </p>
        )}
      </div>

      {/* Property Type */}
      <div>
        <label className="input-label">
          Property Type <span className="text-red-500">*</span>
        </label>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {Object.entries(PROPERTY_TYPES).map(([value, label]) => (
            <label
              key={value}
              className="relative flex items-center justify-center p-3 bg-white border border-hampstead-200 rounded-lg cursor-pointer hover:border-gold-400 transition-colors has-[:checked]:border-gold-500 has-[:checked]:bg-gold-50 has-[:checked]:ring-2 has-[:checked]:ring-gold-500 text-center"
            >
              <input
                type="radio"
                value={value}
                className="sr-only"
                {...register('propertyType')}
              />
              <span className="text-sm font-medium text-hampstead-700">{label}</span>
            </label>
          ))}
        </div>
        {errors.propertyType && (
          <p className="input-error">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            Please select a property type
          </p>
        )}
      </div>

      {/* Property Age */}
      <div>
        <label className="input-label">
          Property Age <span className="text-red-500">*</span>
        </label>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {Object.entries(PROPERTY_AGES).map(([value, label]) => (
            <label
              key={value}
              className="relative flex items-center justify-center p-3 bg-white border border-hampstead-200 rounded-lg cursor-pointer hover:border-gold-400 transition-colors has-[:checked]:border-gold-500 has-[:checked]:bg-gold-50 has-[:checked]:ring-2 has-[:checked]:ring-gold-500 text-center"
            >
              <input
                type="radio"
                value={value}
                className="sr-only"
                {...register('propertyAge')}
              />
              <span className="text-sm font-medium text-hampstead-700">{label}</span>
            </label>
          ))}
        </div>
        {errors.propertyAge && (
          <p className="input-error">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            Please select the age of your property
          </p>
        )}
      </div>

      {/* Info Box */}
      <div className="bg-navy-50 border border-navy-200 rounded-lg p-4">
        <div className="flex gap-3">
          <svg className="w-5 h-5 text-navy-600 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
          </svg>
          <div>
            <p className="text-sm text-navy-800 font-medium">Why does property age matter?</p>
            <p className="text-sm text-navy-600 mt-1">
              Older properties often require specialist approaches, especially in conservation areas like Hampstead. 
              Knowing your property age helps us provide more accurate quotes and identify any additional considerations.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
