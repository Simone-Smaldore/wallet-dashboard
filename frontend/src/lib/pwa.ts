/** Whether we are running as an installed app rather than in a browser tab.
 *
 * This matters for exactly one thing, and it is not cosmetic. On iOS an app
 * added to the home screen gets its own storage, separate from Safari's. The
 * magic link in the email opens in Safari, so the session cookie is set there
 * and the installed app stays signed out — with no address bar to paste the
 * link into, it would be unusable.
 *
 * So in standalone the login screen offers a way to hand the token over
 * directly. In a tab that would be noise: tapping the link works.
 *
 * `display-mode: standalone` is the standard; `navigator.standalone` is the
 * older iOS-only flag, kept because it is the platform this exists for.
 */

interface IosNavigator extends Navigator {
  standalone?: boolean
}

export function isStandalone(): boolean {
  if (window.matchMedia('(display-mode: standalone)').matches) return true
  if (window.matchMedia('(display-mode: fullscreen)').matches) return true
  return (navigator as IosNavigator).standalone === true
}

/** Pull the single-use token out of whatever got pasted.
 *
 * ⚠️ **What you copy is almost never the link that was sent.** Gmail rewrites
 * every link into `https://www.google.com/url?q=<il link, codificato>&source=…`,
 * so the token is not in the query string at all — it is inside another URL,
 * percent-encoded, inside a parameter called `q`. Other clients add tracking
 * parameters, or wrap it differently, or paste it inside a sentence.
 *
 * Reading only `?token=` off the top-level URL was therefore wrong for the most
 * common case there is, and the screen then blamed the token — "already used" —
 * for a link it had simply failed to read. A wrong diagnosis is worse than no
 * diagnosis: it sends you to ask for another link, which fails the same way.
 *
 * So the last step is a plain search for `token=` anywhere in the text, after
 * decoding. It accepts the whole link, a wrapped link, a bare token, or a link
 * with words around it — all of which are things a person reasonably ends up
 * with on the clipboard.
 */
export function tokenFromPaste(value: string): string | null {
  const text = value.trim()
  if (!text) return null

  // A bare token: one opaque run of URL-safe characters, no spaces.
  if (/^[\w-]{16,}$/.test(text)) return text

  // Decode as far as it goes: Gmail's wrapper hides the real URL one level
  // down, and some clients manage two.
  let decoded = text
  for (let round = 0; round < 3; round += 1) {
    const next = safeDecode(decoded)
    if (next === decoded) break
    decoded = next
  }

  const match = /[?&]token=([\w-]{16,})/.exec(decoded)
  return match ? match[1] : null
}

function safeDecode(value: string): string {
  try {
    return decodeURIComponent(value)
  } catch {
    // A stray % that is not an escape. Whatever is there is what we search.
    return value
  }
}
