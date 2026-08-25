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
 * Accepts the whole link or the bare token, because both are things a person
 * reasonably ends up with on the clipboard.
 */
export function tokenFromPaste(value: string): string | null {
  const text = value.trim()
  if (!text) return null

  try {
    const fromUrl = new URL(text).searchParams.get('token')
    if (fromUrl) return fromUrl.trim()
  } catch {
    // Not a URL. Falls through to treating it as the token itself.
  }

  // A bare token: one opaque run of URL-safe characters, no spaces.
  return /^[\w-]{16,}$/.test(text) ? text : null
}
