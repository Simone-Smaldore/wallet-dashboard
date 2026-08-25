/** The product mark. There is no logo file: DESIGN.md specifies a typographic
 *  wordmark, "Wallet." in Space Grotesk 600 with the full stop in the accent. */
export function Wordmark() {
  return (
    <span className="font-display text-title font-semibold text-ink-1">
      Wallet<span className="text-accent">.</span>
    </span>
  )
}
