import { useEffect, useState } from 'react'
import FraudTypeBadge from './FraudTypeBadge'

function ShieldIcon({ className }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className} aria-hidden="true">
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
  )
}

function AlertIcon({ className }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className} aria-hidden="true">
      <path
        d="M12 2.5 4.5 5.8v5.4c0 4.6 3.2 8.9 7.5 10.3 4.3-1.4 7.5-5.7 7.5-10.3V5.8L12 2.5Z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      <path d="M12 8v4.4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <circle cx="12" cy="15.8" r="1.05" fill="currentColor" />
    </svg>
  )
}

/** Confidence meter — fills on mount so the number lands with a bit of weight. */
function ConfidenceMeter({ value, suspicious }) {
  const percent = Math.round((value ?? 0) * 100)
  const [width, setWidth] = useState(0)

  useEffect(() => {
    const frame = requestAnimationFrame(() => setWidth(percent))
    return () => cancelAnimationFrame(frame)
  }, [percent])

  return (
    <div>
      <div className="mb-2 flex items-baseline justify-between">
        <span className="text-xs font-medium tracking-wide text-muted uppercase">Confidence</span>
        <span className="text-sm font-semibold tabular-nums text-white">{percent}%</span>
      </div>
      <div
        role="meter"
        aria-valuenow={percent}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Detection confidence"
        className="h-2 w-full overflow-hidden rounded-full bg-white/10"
      >
        <div
          className={`h-full rounded-full transition-[width] duration-700 ease-out ${
            suspicious ? 'bg-danger' : 'bg-safe'
          }`}
          style={{ width: `${width}%` }}
        />
      </div>
    </div>
  )
}

export default function VerdictCard({ result }) {
  const suspicious = result.verdict === 'suspicious'
  const Icon = suspicious ? AlertIcon : ShieldIcon
  const flaggedUrls = (result.url_checks || []).filter((check) => check.is_phishing)

  return (
    <section
      aria-live="polite"
      className={`animate-rise overflow-hidden rounded-2xl border bg-surface ${
        suspicious ? 'border-danger/35' : 'border-safe/35'
      }`}
    >
      {/* Verdict banner */}
      <div
        className={`flex items-center gap-4 px-5 py-5 sm:px-7 ${
          suspicious ? 'bg-danger/10' : 'bg-safe/10'
        }`}
      >
        <Icon className={`h-9 w-9 shrink-0 ${suspicious ? 'text-danger' : 'text-safe'}`} />
        <div className="min-w-0">
          <h2
            className={`text-xl font-bold tracking-tight sm:text-2xl ${
              suspicious ? 'text-danger' : 'text-safe'
            }`}
          >
            {suspicious ? 'Suspicious' : 'Looks Safe'}
          </h2>
          <p className="mt-0.5 text-sm text-muted">
            {suspicious
              ? 'Do not click any links or share details from this message.'
              : 'No fraud pattern matched — stay alert if anything still feels off.'}
          </p>
        </div>
      </div>

      <div className="space-y-5 px-5 py-5 sm:px-7">
        <div className="flex flex-wrap items-center gap-3">
          <FraudTypeBadge fraudType={result.fraud_type} />
        </div>

        <ConfidenceMeter value={result.confidence} suspicious={suspicious} />

        {result.confidence_reason && (
          <p className="text-sm leading-relaxed text-muted">{result.confidence_reason}</p>
        )}

        {flaggedUrls.length > 0 && (
          <div className="rounded-xl border border-danger/30 bg-danger/5 p-4">
            <h3 className="mb-2 text-xs font-semibold tracking-wide text-danger uppercase">
              {flaggedUrls.length === 1 ? 'Dangerous link found' : 'Dangerous links found'}
            </h3>
            <ul className="space-y-2">
              {flaggedUrls.map((check, i) => (
                <li key={i} className="text-sm">
                  {/* Rendered as plain text, never as an anchor — this URL is hostile. */}
                  <span className="block break-all font-mono text-xs text-white/90">
                    {check.url}
                  </span>
                  <span className="text-xs text-muted">
                    Flagged by {check.source.replace(/_/g, ' ')}
                    {check.threat_type && check.threat_type !== 'none'
                      ? ` — ${check.threat_type.replace(/_/g, ' ').toLowerCase()}`
                      : ''}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </section>
  )
}
