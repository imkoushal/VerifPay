/**
 * Badge showing the fraud category returned by the backend.
 * Fraud type strings mirror the FraudType enum in app/models/schemas.py.
 */

const FRAUD_TYPES = {
  PHISHING: { label: 'Phishing', hint: 'Fake link built to steal your credentials' },
  FAKE_KYC: { label: 'Fake KYC', hint: 'Fake KYC or PAN expiry threat' },
  UPI_MANIPULATION: { label: 'UPI Fraud', hint: 'Fraudulent UPI collect or payment request' },
  CARD_SCAM: { label: 'Card Scam', hint: 'Fake card offer or card-blocking threat' },
  OTP_FRAUD: { label: 'OTP Fraud', hint: 'Attempt to extract your OTP' },
  INVESTMENT_SCAM: { label: 'Investment Scam', hint: 'Fake investment, lottery or prize scheme' },
  SAFE: { label: 'No Fraud Detected', hint: 'No known fraud pattern matched' },
}

export default function FraudTypeBadge({ fraudType }) {
  const meta = FRAUD_TYPES[fraudType] || {
    label: String(fraudType || 'Unknown').replace(/_/g, ' '),
    hint: '',
  }
  const isSafe = fraudType === 'SAFE'

  return (
    <span
      title={meta.hint}
      className={[
        'inline-flex items-center gap-2 rounded-full border px-3 py-1',
        'text-xs font-semibold tracking-wide uppercase',
        isSafe
          ? 'border-safe/40 bg-safe/10 text-safe'
          : 'border-danger/40 bg-danger/10 text-danger',
      ].join(' ')}
    >
      <span
        aria-hidden="true"
        className={`h-1.5 w-1.5 rounded-full ${isSafe ? 'bg-safe' : 'bg-danger'}`}
      />
      {meta.label}
    </span>
  )
}
