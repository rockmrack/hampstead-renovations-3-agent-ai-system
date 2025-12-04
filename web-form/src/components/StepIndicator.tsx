import type { FormStep } from '../types'

interface StepIndicatorProps {
  steps: FormStep[]
  currentStep: number
}

export function StepIndicator({ steps, currentStep }: StepIndicatorProps) {
  return (
    <div className="mb-8">
      {/* Progress Bar */}
      <div className="progress-bar mb-6">
        <div 
          className="progress-bar-fill" 
          style={{ width: `${((currentStep - 1) / (steps.length - 1)) * 100}%` }}
        />
      </div>
      
      {/* Step Indicators */}
      <div className="flex justify-between">
        {steps.map((step) => (
          <div 
            key={step.id}
            className="flex flex-col items-center"
          >
            <div 
              className={`step-indicator ${
                step.id < currentStep 
                  ? 'completed' 
                  : step.id === currentStep 
                    ? 'active' 
                    : 'upcoming'
              }`}
            >
              {step.id < currentStep ? (
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
              ) : (
                step.id
              )}
            </div>
            <span 
              className={`mt-2 text-xs font-medium hidden sm:block ${
                step.id <= currentStep ? 'text-navy-700' : 'text-hampstead-400'
              }`}
            >
              {step.title}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
