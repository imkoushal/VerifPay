import { useRef, useState } from 'react'
import AnalyseInput from './components/AnalyseInput'
import VerdictCard from './components/VerdictCard'
import ExplanationPanel from './components/ExplanationPanel'
import ScanningLoader from './components/ScanningLoader'
import TelegramSection from './components/TelegramSection'
import { analyseText } from './api'

function Header() {
  return (
    <header className="border-b border-line">
      <div className="mx-auto flex max-w-3xl items-center justify-between px-5 py-5 sm:px-6">
        <div className="flex items-center gap-2.5">
          <svg viewBox="0 0 24 24" className="h-6 w-6 text-white" fill="none" aria-hidden="true">
            <path
              d="M12 2.5 4.5 5.8v5.4c0 4.6 3.2 8.9 7.5 10.3 4.3-1.4 7.5-5.7 7.5-10.3V5.8L12 2.5Z"
              stroke="currentColor"
              strokeWidth="1.6"
              strokeLinejoin="round"
            />
            <path
              d="m8.8 12 2.2 2.2 4.2-4.4"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          <span className="text-[15px] font-bold tracking-tight">VerifPay</span>
        </div>
        <span className="text-xs text-faint">Fraud detection for India</span>
      </div>
    </header>
  )
}

function ErrorMessage({ message, onRetry }) {
  return (
    <div
      role="alert"
      className="animate-rise rounded-2xl border border-danger/30 bg-danger/5 px-5 py-5 sm:px-7"
    >
      <h2 className="text-sm font-semibold text-danger">Analysis failed</h2>
      <p className="mt-1.5 text-sm leading-relaxed text-white/80">{message}</p>
      <button
        type="button"
        onClick={onRetry}
        className="mt-4 rounded-lg border border-line px-4 py-2 text-sm font-medium
                   text-white transition-colors hover:border-white/30"
      >
        Try again
      </button>
    </div>
  )
}

export default function App() {
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const lastTextRef = useRef('')
  const resultsRef = useRef(null)

  async function handleAnalyse(text) {
    lastTextRef.current = text
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const data = await analyseText(text)
      setResult(data)
      // Bring the verdict into view on phones, where it lands below the fold.
      requestAnimationFrame(() => {
        resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      })
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-ink">
      <Header />

      <main className="mx-auto max-w-3xl px-5 pb-20 sm:px-6">
        {/* Hero */}
        <section className="pt-14 pb-8 text-center sm:pt-20 sm:pb-10">
          <h1 className="text-4xl font-bold tracking-tight text-balance sm:text-5xl">
            Is this message safe?
          </h1>
          <p className="mx-auto mt-4 max-w-xl text-[15px] leading-relaxed text-pretty text-muted sm:text-base">
            AI-powered fraud detection for Indian consumers — paste any message, link, or UPI
            request.
          </p>
        </section>

        <AnalyseInput onAnalyse={handleAnalyse} loading={loading} />

        {/* Results */}
        <div ref={resultsRef} className="mt-8 space-y-5 scroll-mt-6">
          {loading && <ScanningLoader />}
          {error && !loading && (
            <ErrorMessage message={error} onRetry={() => handleAnalyse(lastTextRef.current)} />
          )}
          {result && !loading && (
            <>
              <VerdictCard result={result} />
              <ExplanationPanel result={result} />
            </>
          )}
        </div>

        <div className="mt-16 sm:mt-20">
          <TelegramSection />
        </div>

        <footer className="mt-14 border-t border-line pt-6 text-center">
          <p className="text-xs leading-relaxed text-faint">
            VerifPay gives an automated assessment and can be wrong. Never share OTPs, card numbers
            or UPI PINs with anyone. To report fraud, call the national cybercrime helpline{' '}
            <span className="font-medium text-muted">1930</span>.
          </p>
        </footer>
      </main>
    </div>
  )
}
