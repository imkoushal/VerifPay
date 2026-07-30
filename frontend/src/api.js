/**
 * VerifPay API client.
 *
 * Talks to the FastAPI backend's POST /analyse endpoint. The backend enforces
 * a 30/minute per-IP rate limit and optionally an X-API-Key header, so both of
 * those failure modes get their own message rather than a generic error.
 */

const API_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/+$/, '')
const API_KEY = import.meta.env.VITE_API_KEY || ''

/** Matches AnalyseRequest.text max_length on the backend. */
export const MAX_TEXT_LENGTH = 5000

/** Backend rejects requests that take longer than this to reach us. */
const REQUEST_TIMEOUT_MS = 45000

function buildHeaders() {
  const headers = { 'Content-Type': 'application/json' }
  if (API_KEY) headers['X-API-Key'] = API_KEY
  return headers
}

async function readError(response) {
  // FastAPI returns {detail: ...}; slowapi's 429 returns {error: ...}.
  try {
    const body = await response.json()
    if (typeof body?.detail === 'string') return body.detail
    if (Array.isArray(body?.detail)) return body.detail[0]?.msg || 'Invalid request.'
    if (typeof body?.error === 'string') return body.error
  } catch {
    /* body was not JSON — fall through to the status-based message */
  }
  return null
}

/**
 * Analyse a suspicious message.
 * @param {string} text
 * @returns {Promise<object>} AnalyseResponse
 */
export async function analyseText(text) {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)

  let response
  try {
    response = await fetch(`${API_URL}/analyse`, {
      method: 'POST',
      headers: buildHeaders(),
      body: JSON.stringify({ text }),
      signal: controller.signal,
    })
  } catch (err) {
    if (err.name === 'AbortError') {
      throw new Error('The analysis took too long to respond. Please try again.')
    }
    throw new Error(
      `Could not reach the VerifPay backend at ${API_URL}. Check that the server is running.`,
    )
  } finally {
    clearTimeout(timeout)
  }

  if (!response.ok) {
    const detail = await readError(response)
    if (response.status === 429) {
      throw new Error(detail || 'Too many requests. Please wait a minute and try again.')
    }
    if (response.status === 401) {
      throw new Error(detail || 'This VerifPay instance requires an API key.')
    }
    throw new Error(detail || `Analysis failed (HTTP ${response.status}).`)
  }

  return response.json()
}
