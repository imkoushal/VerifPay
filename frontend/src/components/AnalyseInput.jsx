import { useState } from 'react'
import { MAX_TEXT_LENGTH } from '../api'

const EXAMPLES = [
  'Your SBI account KYC has expired. Update immediately at http://sbi-kyc-update.xyz or your account will be blocked within 24 hours.',
  'Congratulations! Your number won Rs 25 lakh in the KBC lottery. Share your Aadhaar and bank details to claim.',
  'HDFC Bank: Rs 2,499 debited from a/c XX1234 on 12-Jul for card purchase. Not you? Call 18002586161.',
]

export default function AnalyseInput({ onAnalyse, loading }) {
  const [text, setText] = useState('')

  const trimmed = text.trim()
  const tooLong = text.length > MAX_TEXT_LENGTH
  const canSubmit = trimmed.length > 0 && !tooLong && !loading

  function handleSubmit(event) {
    event.preventDefault()
    if (canSubmit) onAnalyse(trimmed)
  }

  function handleKeyDown(event) {
    // Ctrl/Cmd+Enter submits — the textarea is large, so Enter must stay a newline.
    if ((event.metaKey || event.ctrlKey) && event.key === 'Enter' && canSubmit) {
      event.preventDefault()
      onAnalyse(trimmed)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <div className="rounded-2xl border border-line bg-surface p-2 focus-within:border-white/25 transition-colors">
        <label htmlFor="message" className="sr-only">
          Suspicious message, link or UPI request
        </label>
        <textarea
          id="message"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading}
          rows={6}
          spellCheck="false"
          placeholder="Paste the message, link or UPI request here…"
          className="w-full resize-y bg-transparent px-4 py-3 text-base leading-relaxed
                     text-white placeholder:text-faint focus:outline-none disabled:opacity-50
                     sm:text-lg"
        />

        <div className="flex flex-col gap-3 border-t border-line px-4 pt-3 pb-1 sm:flex-row sm:items-center sm:justify-between">
          <span className={`text-xs ${tooLong ? 'text-danger' : 'text-faint'}`}>
            {tooLong
              ? `${text.length.toLocaleString()} / ${MAX_TEXT_LENGTH.toLocaleString()} — too long to analyse`
              : `${text.length.toLocaleString()} / ${MAX_TEXT_LENGTH.toLocaleString()} characters`}
          </span>

          <button
            type="submit"
            disabled={!canSubmit}
            className="w-full rounded-xl bg-white px-6 py-3 text-sm font-semibold text-ink
                       transition-colors hover:bg-white/85 disabled:cursor-not-allowed
                       disabled:bg-white/20 disabled:text-white/40 sm:w-auto"
          >
            {loading ? 'Analysing…' : 'Analyse'}
          </button>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <span className="text-xs text-faint">Try an example:</span>
        {EXAMPLES.map((example, i) => (
          <button
            key={i}
            type="button"
            disabled={loading}
            onClick={() => setText(example)}
            className="rounded-lg border border-line px-3 py-1.5 text-xs text-muted
                       transition-colors hover:border-white/25 hover:text-white
                       disabled:cursor-not-allowed disabled:opacity-40"
          >
            {['Fake KYC SMS', 'Lottery scam', 'Real bank alert'][i]}
          </button>
        ))}
      </div>
    </form>
  )
}
