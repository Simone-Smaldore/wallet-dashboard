/** Money on the client. Mirror of backend/app/domain/money.py.
 *
 * ⚠️ Amounts are integers in cents, here as everywhere. Summing them in
 * JavaScript is exact — numbers are float64 but represent integers exactly up
 * to 2^53, which in cents is ninety thousand billion euro — so the frontend is
 * allowed to add them up. What it is not allowed to do is divide before the
 * very last step: the moment you divide you are holding a float, and the reason
 * for the whole representation is gone.
 *
 * ⚠️ The word "cents" never reaches the user. It is internal: you write
 * `12,50` and you read `12,50 €`.
 */

const CENTS_PER_EURO = 100

/** `1.234` and `1.234.567`: dots as thousands separators and nothing else. */
const THOUSANDS_ONLY = /^\d{1,3}(\.\d{3})+$/
const DIGITS = /^\d+$/

export class InvalidAmount extends Error {}

/** Cents to Italian text: `1.234,56 €`.
 *
 * ⚠️ The division by 100 happens here and only here. */
export function formatMoney(cents: number, options: { symbol?: boolean } = {}): string {
  const { symbol = true } = options
  const sign = cents < 0 ? '-' : ''
  const absolute = Math.abs(cents)
  const whole = Math.trunc(absolute / CENTS_PER_EURO)
  const decimals = absolute % CENTS_PER_EURO

  const grouped = whole.toLocaleString('it-IT')
  const text = `${sign}${grouped},${String(decimals).padStart(2, '0')}`
  return symbol ? `${text} €` : text
}

/** Turn what a person typed into cents.
 *
 * ⚠️ Deliberately not `parseFloat(text) * 100`. In binary floating point
 * `19.99 * 100` is `1998.9999999999998`, so truncating loses a cent on prices
 * ending in 99 — most of them — quietly and only sometimes, which is the worst
 * way to be wrong about money. This works on the digits.
 *
 * The comma is unambiguous in Italian. The dot is not: `1.234` is one thousand
 * two hundred and thirty-four, `12.50` is twelve euro fifty, and both get
 * typed. A string made only of well-formed thousands groups reads as thousands;
 * anything else treats the last dot as the decimal separator.
 */
export function parseAmount(text: string): number {
  let cleaned = text.trim().replace(/ /g, ' ').replace(/\s/g, '')
  if (!cleaned) throw new InvalidAmount("Manca l'importo")

  cleaned = cleaned.replace(/€$/, '').trim()

  let sign = 1
  if (cleaned.startsWith('-') || cleaned.startsWith('+')) {
    sign = cleaned.startsWith('-') ? -1 : 1
    cleaned = cleaned.slice(1)
  }
  if (!cleaned) throw new InvalidAmount(`Importo non valido: ${text}`)

  const [wholeText, decimalsText] = split(cleaned, text)

  if (wholeText && !DIGITS.test(wholeText)) {
    throw new InvalidAmount(`Importo non valido: ${text}`)
  }
  if (!wholeText && !decimalsText) {
    throw new InvalidAmount(`Importo non valido: ${text}`)
  }

  const whole = wholeText ? Number(wholeText) : 0
  // "12,5" means fifty cents, not five.
  const decimals = decimalsText ? Number(decimalsText.padEnd(2, '0')) : 0

  return sign * (whole * CENTS_PER_EURO + decimals)
}

function split(cleaned: string, original: string): [string, string] {
  if (cleaned.includes(',')) {
    const at = cleaned.lastIndexOf(',')
    const whole = cleaned.slice(0, at)
    if (whole.includes(',')) throw new InvalidAmount(`Importo non valido: ${original}`)
    return [whole.replaceAll('.', ''), checkedDecimals(cleaned.slice(at + 1), original)]
  }

  if (!cleaned.includes('.')) return [cleaned, '']

  if (THOUSANDS_ONLY.test(cleaned)) return [cleaned.replaceAll('.', ''), '']

  const at = cleaned.lastIndexOf('.')
  return [
    checkedWhole(cleaned.slice(0, at), original),
    checkedDecimals(cleaned.slice(at + 1), original),
  ]
}

function checkedWhole(whole: string, original: string): string {
  if (!whole) return ''
  if (DIGITS.test(whole) || THOUSANDS_ONLY.test(whole)) return whole.replaceAll('.', '')
  throw new InvalidAmount(`Importo non valido: ${original}`)
}

/** Two decimals is the whole precision this app has. Three would mean an amount
 *  that cannot be stored without rounding, and rounding what someone typed
 *  under their fingers is what this codebase refuses to do. */
function checkedDecimals(decimals: string, original: string): string {
  if (!DIGITS.test(decimals) || decimals.length > 2) {
    throw new InvalidAmount(`Importo non valido: ${original}`)
  }
  return decimals
}

/** Validate a field without correcting it while it is being typed.
 *
 * Returns the value in cents, or an error message to show under the box. An
 * empty box is an error, never zero: it means the person has not said yet.
 */
export function parseAmountField(
  text: string,
  options: { allowEmpty?: boolean } = {},
): { cents: number; error: null } | { cents: null; error: string } {
  if (!text.trim()) {
    return options.allowEmpty
      ? { cents: 0, error: null }
      : { cents: null, error: "Manca l'importo" }
  }
  try {
    return { cents: parseAmount(text), error: null }
  } catch {
    return { cents: null, error: 'Importo non valido' }
  }
}
