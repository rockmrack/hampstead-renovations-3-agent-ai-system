import { useFormContext } from 'react-hook-form'
import type { LeadFormData } from '../../types'

export function ContactStep() {
  const { register, formState: { errors } } = useFormContext<LeadFormData>()

  return (
    <div className="space-y-6">
      {/* Name Fields */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label htmlFor="firstName" className="input-label">
            First Name <span className="text-red-500">*</span>
          </label>
          <input
            id="firstName"
            type="text"
            autoComplete="given-name"
            className={`input-field ${errors.firstName ? 'error' : ''}`}
            placeholder="John"
            {...register('firstName')}
          />
          {errors.firstName && (
            <p className="input-error">
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
              {errors.firstName.message}
            </p>
          )}
        </div>
        
        <div>
          <label htmlFor="lastName" className="input-label">
            Last Name <span className="text-red-500">*</span>
          </label>
          <input
            id="lastName"
            type="text"
            autoComplete="family-name"
            className={`input-field ${errors.lastName ? 'error' : ''}`}
            placeholder="Smith"
            {...register('lastName')}
          />
          {errors.lastName && (
            <p className="input-error">
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
              {errors.lastName.message}
            </p>
          )}
        </div>
      </div>

      {/* Email */}
      <div>
        <label htmlFor="email" className="input-label">
          Email Address <span className="text-red-500">*</span>
        </label>
        <input
          id="email"
          type="email"
          autoComplete="email"
          className={`input-field ${errors.email ? 'error' : ''}`}
          placeholder="john.smith@example.com"
          {...register('email')}
        />
        {errors.email && (
          <p className="input-error">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            {errors.email.message}
          </p>
        )}
      </div>

      {/* Phone */}
      <div>
        <label htmlFor="phone" className="input-label">
          Phone Number <span className="text-red-500">*</span>
        </label>
        <input
          id="phone"
          type="tel"
          autoComplete="tel"
          className={`input-field ${errors.phone ? 'error' : ''}`}
          placeholder="07700 123456 or +44 7700 123456"
          {...register('phone')}
        />
        {errors.phone && (
          <p className="input-error">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            {errors.phone.message}
          </p>
        )}
      </div>

      {/* Preferred Contact Method */}
      <div>
        <label className="input-label">
          Preferred Contact Method <span className="text-red-500">*</span>
        </label>
        <div className="grid grid-cols-3 gap-3">
          {[
            { value: 'phone', label: 'Phone', icon: '📞' },
            { value: 'email', label: 'Email', icon: '📧' },
            { value: 'whatsapp', label: 'WhatsApp', icon: '💬' },
          ].map((option) => (
            <label
              key={option.value}
              className="relative flex items-center justify-center gap-2 p-3 bg-white border border-hampstead-200 rounded-lg cursor-pointer hover:border-gold-400 transition-colors has-[:checked]:border-gold-500 has-[:checked]:bg-gold-50 has-[:checked]:ring-2 has-[:checked]:ring-gold-500"
            >
              <input
                type="radio"
                value={option.value}
                className="sr-only"
                {...register('preferredContact')}
              />
              <span className="text-lg">{option.icon}</span>
              <span className="text-sm font-medium text-hampstead-700">{option.label}</span>
            </label>
          ))}
        </div>
        {errors.preferredContact && (
          <p className="input-error">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            {errors.preferredContact.message}
          </p>
        )}
      </div>
    </div>
  )
}
