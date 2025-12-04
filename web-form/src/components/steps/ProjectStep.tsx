import { useFormContext } from 'react-hook-form'
import type { LeadFormData, ServiceType } from '../../types'
import { SERVICE_TYPES } from '../../types'

export function ProjectStep() {
  const { register, watch, setValue, formState: { errors } } = useFormContext<LeadFormData>()
  const selectedServices = watch('serviceType') || []

  const toggleService = (service: ServiceType) => {
    const current = selectedServices || []
    if (current.includes(service)) {
      setValue('serviceType', current.filter(s => s !== service), { shouldValidate: true })
    } else {
      setValue('serviceType', [...current, service], { shouldValidate: true })
    }
  }

  return (
    <div className="space-y-6">
      {/* Service Selection */}
      <div>
        <label className="input-label">
          What services are you interested in? <span className="text-red-500">*</span>
        </label>
        <p className="text-sm text-hampstead-500 mb-3">Select all that apply</p>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {Object.entries(SERVICE_TYPES).map(([value, { label, icon, description }]) => {
            const isSelected = selectedServices.includes(value as ServiceType)
            return (
              <button
                key={value}
                type="button"
                onClick={() => toggleService(value as ServiceType)}
                className={`service-card text-left ${isSelected ? 'selected' : ''}`}
              >
                <div className="text-2xl">{icon}</div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-hampstead-800">{label}</p>
                  <p className="text-sm text-hampstead-500 truncate">{description}</p>
                </div>
                <div className={`flex-shrink-0 w-5 h-5 rounded border-2 flex items-center justify-center transition-colors ${
                  isSelected ? 'bg-gold-500 border-gold-500' : 'border-hampstead-300'
                }`}>
                  {isSelected && (
                    <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  )}
                </div>
              </button>
            )
          })}
        </div>
        
        {/* Hidden input for form validation */}
        <input type="hidden" {...register('serviceType')} />
        
        {errors.serviceType && (
          <p className="input-error mt-2">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            {errors.serviceType.message}
          </p>
        )}
      </div>

      {/* Project Description */}
      <div>
        <label htmlFor="projectDescription" className="input-label">
          Tell us about your project <span className="text-red-500">*</span>
        </label>
        <textarea
          id="projectDescription"
          rows={5}
          className={`input-field resize-none ${errors.projectDescription ? 'error' : ''}`}
          placeholder="Please describe what you'd like to achieve. Include any specific requirements, styles you like, or challenges you're facing with your current space..."
          {...register('projectDescription')}
        />
        <p className="text-xs text-hampstead-500 mt-1">
          The more detail you provide, the more accurate our initial assessment will be.
        </p>
        {errors.projectDescription && (
          <p className="input-error">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            {errors.projectDescription.message}
          </p>
        )}
      </div>

      {/* Selected Services Summary */}
      {selectedServices.length > 0 && (
        <div className="bg-gold-50 border border-gold-200 rounded-lg p-4">
          <p className="text-sm font-medium text-gold-800 mb-2">
            Selected Services ({selectedServices.length})
          </p>
          <div className="flex flex-wrap gap-2">
            {selectedServices.map((service) => (
              <span
                key={service}
                className="inline-flex items-center gap-1 px-3 py-1 bg-white rounded-full text-sm text-hampstead-700 border border-gold-300"
              >
                {SERVICE_TYPES[service].icon} {SERVICE_TYPES[service].label}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
