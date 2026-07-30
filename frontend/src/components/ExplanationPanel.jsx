/**
 * Renders the LLM-generated explanation: why the verdict was reached,
 * the specific red flags, and the single recommended action.
 */
export default function ExplanationPanel({ result }) {
  const suspicious = result.verdict === 'suspicious'
  const redFlags = result.red_flags || []

  return (
    <section className="animate-rise space-y-6 rounded-2xl border border-line bg-surface px-5 py-6 sm:px-7">
      <div>
        <h3 className="mb-2 text-xs font-semibold tracking-wide text-muted uppercase">
          Why this verdict
        </h3>
        <p className="text-[15px] leading-relaxed text-white/90">{result.explanation}</p>
      </div>

      {redFlags.length > 0 && (
        <div>
          <h3 className="mb-3 text-xs font-semibold tracking-wide text-muted uppercase">
            {suspicious ? 'Red flags detected' : 'What we checked'}
          </h3>
          <ul className="space-y-2.5">
            {redFlags.map((flag, i) => (
              <li key={i} className="flex gap-3 text-[15px] leading-relaxed text-white/85">
                <span
                  aria-hidden="true"
                  className={`mt-2 h-1.5 w-1.5 shrink-0 rounded-full ${
                    suspicious ? 'bg-danger' : 'bg-safe'
                  }`}
                />
                <span>{flag}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {result.recommended_action && (
        <div
          className={`rounded-xl border px-4 py-4 ${
            suspicious ? 'border-danger/30 bg-danger/5' : 'border-safe/30 bg-safe/5'
          }`}
        >
          <h3
            className={`mb-1.5 text-xs font-semibold tracking-wide uppercase ${
              suspicious ? 'text-danger' : 'text-safe'
            }`}
          >
            What you should do
          </h3>
          <p className="text-[15px] leading-relaxed font-medium text-white">
            {result.recommended_action}
          </p>
        </div>
      )}
    </section>
  )
}
