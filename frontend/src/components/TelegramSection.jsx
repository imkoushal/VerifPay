import { QRCodeSVG } from 'qrcode.react'

const BOT_URL = import.meta.env.VITE_TELEGRAM_BOT_URL || 'https://t.me/VerifPayBot'

/**
 * Bottom section pointing users at the Telegram bot (Phase 4), which accepts
 * forwarded messages and voice notes without any signup.
 */
export default function TelegramSection() {
  return (
    <section className="rounded-2xl border border-line bg-surface px-6 py-8 sm:px-10 sm:py-10">
      <div className="flex flex-col items-center gap-8 sm:flex-row sm:items-center sm:justify-between">
        <div className="max-w-md text-center sm:text-left">
          <h2 className="text-xl font-bold tracking-tight text-white sm:text-2xl">
            Check scams straight from Telegram
          </h2>
          <p className="mt-3 text-[15px] leading-relaxed text-muted">
            Forward any suspicious SMS, WhatsApp message or link to the VerifPay bot and get the
            same verdict in seconds. You can even forward a voice note of a scam call — it gets
            transcribed and analysed automatically.
          </p>
          <p className="mt-3 text-sm text-faint">No app download. No signup. Works on any phone.</p>

          <a
            href={BOT_URL}
            target="_blank"
            rel="noreferrer noopener"
            className="mt-5 inline-flex items-center gap-2 rounded-xl bg-white px-5 py-3
                       text-sm font-semibold text-ink transition-colors hover:bg-white/85"
          >
            Open in Telegram
            <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" fill="none" aria-hidden="true">
              <path
                d="M4 12 12 4M6 4h6v6"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </a>
        </div>

        <div className="shrink-0 rounded-2xl bg-white p-4">
          <QRCodeSVG value={BOT_URL} size={148} level="M" marginSize={0} />
          <p className="mt-3 text-center text-xs font-medium text-neutral-600">Scan to open bot</p>
        </div>
      </div>
    </section>
  )
}
