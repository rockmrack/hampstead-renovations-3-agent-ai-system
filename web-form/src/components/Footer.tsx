export function Footer() {
  const currentYear = new Date().getFullYear()
  
  return (
    <footer className="bg-navy-900 text-white py-8">
      <div className="container mx-auto px-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* Company Info */}
          <div>
            <h3 className="font-serif text-lg font-bold mb-3">Hampstead Renovations</h3>
            <p className="text-navy-300 text-sm leading-relaxed">
              Premium residential renovation services serving Hampstead, Belsize Park, 
              and surrounding North West London areas for over 15 years.
            </p>
          </div>
          
          {/* Service Areas */}
          <div>
            <h4 className="font-semibold mb-3">Areas We Serve</h4>
            <div className="grid grid-cols-2 gap-1 text-sm text-navy-300">
              <span>NW3 - Hampstead</span>
              <span>NW6 - Kilburn</span>
              <span>NW11 - Golders Green</span>
              <span>NW8 - St John's Wood</span>
              <span>N6 - Highgate</span>
              <span>NW1 - Camden</span>
            </div>
          </div>
          
          {/* Contact */}
          <div>
            <h4 className="font-semibold mb-3">Contact Us</h4>
            <div className="space-y-2 text-sm text-navy-300">
              <p className="flex items-center gap-2">
                <svg className="w-4 h-4 text-gold-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
                </svg>
                020 7123 4567
              </p>
              <p className="flex items-center gap-2">
                <svg className="w-4 h-4 text-gold-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
                hello@hampsteadrenovations.co.uk
              </p>
              <p className="flex items-center gap-2">
                <svg className="w-4 h-4 text-gold-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Mon-Fri: 8am-6pm, Sat: 9am-2pm
              </p>
            </div>
          </div>
        </div>
        
        {/* Bottom Bar */}
        <div className="border-t border-navy-800 mt-8 pt-6 flex flex-col md:flex-row justify-between items-center gap-4 text-sm text-navy-400">
          <p>© {currentYear} Hampstead Renovations Ltd. All rights reserved.</p>
          <div className="flex items-center gap-4">
            <a href="#" className="hover:text-gold-400 transition-colors">Privacy Policy</a>
            <a href="#" className="hover:text-gold-400 transition-colors">Terms of Service</a>
          </div>
        </div>
      </div>
    </footer>
  )
}
