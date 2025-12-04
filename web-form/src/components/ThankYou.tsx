import { motion } from 'framer-motion'

interface ThankYouProps {
  firstName: string
  leadId?: string
  onReset: () => void
}

export function ThankYou({ firstName, leadId, onReset }: ThankYouProps) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ duration: 0.3 }}
      className="text-center py-12"
    >
      {/* Success Icon */}
      <motion.div
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
        className="mx-auto w-24 h-24 bg-green-100 rounded-full flex items-center justify-center mb-6"
      >
        <svg 
          className="w-12 h-12 text-green-600" 
          fill="none" 
          stroke="currentColor" 
          viewBox="0 0 24 24"
        >
          <motion.path
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ delay: 0.4, duration: 0.5 }}
            strokeLinecap="round" 
            strokeLinejoin="round" 
            strokeWidth={2} 
            d="M5 13l4 4L19 7" 
          />
        </svg>
      </motion.div>
      
      {/* Thank You Message */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
      >
        <h1 className="text-3xl md:text-4xl font-serif font-bold text-navy-900 mb-4">
          Thank You, {firstName}!
        </h1>
        <p className="text-lg text-hampstead-600 max-w-md mx-auto mb-6">
          We've received your enquiry and one of our renovation specialists will be in touch within 24 hours.
        </p>
      </motion.div>
      
      {/* Reference Number */}
      {leadId && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="bg-hampstead-100 rounded-lg px-6 py-4 inline-block mb-8"
        >
          <p className="text-sm text-hampstead-500 mb-1">Your Reference Number</p>
          <p className="text-xl font-mono font-bold text-navy-800">{leadId}</p>
        </motion.div>
      )}
      
      {/* What's Next */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
        className="bg-white rounded-xl shadow-md border border-hampstead-100 p-6 max-w-lg mx-auto mb-8"
      >
        <h2 className="font-semibold text-navy-800 mb-4">What Happens Next?</h2>
        <div className="space-y-4 text-left">
          <div className="flex gap-4">
            <div className="flex-shrink-0 w-8 h-8 bg-gold-100 rounded-full flex items-center justify-center">
              <span className="text-gold-700 font-bold text-sm">1</span>
            </div>
            <div>
              <p className="font-medium text-hampstead-800">Review Your Project</p>
              <p className="text-sm text-hampstead-500">We'll review your requirements and assess the scope of work.</p>
            </div>
          </div>
          <div className="flex gap-4">
            <div className="flex-shrink-0 w-8 h-8 bg-gold-100 rounded-full flex items-center justify-center">
              <span className="text-gold-700 font-bold text-sm">2</span>
            </div>
            <div>
              <p className="font-medium text-hampstead-800">Initial Consultation</p>
              <p className="text-sm text-hampstead-500">We'll call to discuss your project in detail and answer any questions.</p>
            </div>
          </div>
          <div className="flex gap-4">
            <div className="flex-shrink-0 w-8 h-8 bg-gold-100 rounded-full flex items-center justify-center">
              <span className="text-gold-700 font-bold text-sm">3</span>
            </div>
            <div>
              <p className="font-medium text-hampstead-800">Site Visit</p>
              <p className="text-sm text-hampstead-500">We'll arrange a free, no-obligation site visit to assess your property.</p>
            </div>
          </div>
          <div className="flex gap-4">
            <div className="flex-shrink-0 w-8 h-8 bg-gold-100 rounded-full flex items-center justify-center">
              <span className="text-gold-700 font-bold text-sm">4</span>
            </div>
            <div>
              <p className="font-medium text-hampstead-800">Detailed Quote</p>
              <p className="text-sm text-hampstead-500">Receive a comprehensive quote tailored to your specific requirements.</p>
            </div>
          </div>
        </div>
      </motion.div>
      
      {/* Contact Options */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6 }}
        className="flex flex-col sm:flex-row gap-4 justify-center items-center"
      >
        <a 
          href="tel:+442071234567"
          className="btn-primary"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
          </svg>
          Call Us Now
        </a>
        <a 
          href="https://wa.me/447700123456"
          target="_blank"
          rel="noopener noreferrer"
          className="btn-secondary"
        >
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/>
          </svg>
          WhatsApp Us
        </a>
        <button 
          onClick={onReset}
          className="btn-outline"
        >
          Submit Another Enquiry
        </button>
      </motion.div>
    </motion.div>
  )
}
