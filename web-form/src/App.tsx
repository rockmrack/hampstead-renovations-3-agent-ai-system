import { useState } from 'react'
import { AnimatePresence } from 'framer-motion'
import { LeadForm } from './components/LeadForm'
import { ThankYou } from './components/ThankYou'
import { Header } from './components/Header'
import { Footer } from './components/Footer'

function App() {
  const [isSubmitted, setIsSubmitted] = useState(false)
  const [submittedData, setSubmittedData] = useState<{
    firstName: string
    leadId?: string
  } | null>(null)

  const handleSuccess = (firstName: string, leadId?: string) => {
    setSubmittedData({ firstName, leadId })
    setIsSubmitted(true)
    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const handleReset = () => {
    setIsSubmitted(false)
    setSubmittedData(null)
  }

  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      
      <main className="flex-1 py-8 md:py-12">
        <div className="container mx-auto px-4 max-w-4xl">
          <AnimatePresence mode="wait">
            {isSubmitted && submittedData ? (
              <ThankYou
                key="thank-you"
                firstName={submittedData.firstName}
                leadId={submittedData.leadId}
                onReset={handleReset}
              />
            ) : (
              <LeadForm key="lead-form" onSuccess={handleSuccess} />
            )}
          </AnimatePresence>
        </div>
      </main>
      
      <Footer />
    </div>
  )
}

export default App
