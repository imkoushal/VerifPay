import { useEffect, useState } from 'react'

/**
 * Loading state shown while /analyse runs. The backend chains four services,
 * so the steps advance on a timer to show what is happening rather than
 * claiming real per-stage progress.
 */
const STEPS = [
  'Running 5-model ensemble',
  'Checking links against phishing databases',
  'Matching known fraud patterns',
  'Generating explanation',
]

export default function ScanningLoader() {
  const [step, setStep] = useState(0)

  useEffect(() => {
    const id = setInterval(() => {
      setStep((current) => Math.min(current + 1, STEPS.length - 1))
    }, 1600)
    return () => clearInterval(id)
  }, [])

  return (
    <section
      aria-live="polite"
      aria-busy="true"
      className="animate-rise overflow-hidden rounded-2xl border border-line bg-surface"
    >
      {/* Scanning beam */}
      <div className="relative h-28 overflow-hidden border-b border-line bg-elevated sm:h-32">
        <div
          aria-hidden="true"
          className="absolute inset-x-0 top-0 h-px animate-scan bg-gradient-to-r
                     from-transparent via-white/70 to-transparent"
        />
        <div
          aria-hidden="true"
          className="absolute inset-0 opacity-[0.07]"
          style={{
            backgroundImage:
              'repeating-linear-gradient(0deg, #fff 0 1px, transparent 1px 8px)',
          }}
        />
        <div className="relative flex h-full items-center justify-center">
          <p className="text-sm font-medium tracking-wide text-white/70">Analysing message…</p>
        </div>
      </div>

      <ol className="space-y-3 px-5 py-5 sm:px-7">
        {STEPS.map((label, i) => (
          <li key={label} className="flex items-center gap-3 text-sm">
            <span
              aria-hidden="true"
              className={`h-1.5 w-1.5 rounded-full ${
                i < step ? 'bg-safe' : i === step ? 'animate-pulse-dot bg-white' : 'bg-white/20'
              }`}
            />
            <span className={i <= step ? 'text-white/85' : 'text-faint'}>{label}</span>
          </li>
        ))}
      </ol>
    </section>
  )
}
