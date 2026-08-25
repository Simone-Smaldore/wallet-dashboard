import { AccountsTab } from './AccountsTab'

/** Where the money sits.
 *
 * Categories used to share this screen behind a two-way switch. They are their
 * own section now: both are registries you set up once and then pick from, but
 * they are looked for at different moments — a balance while you wonder how much
 * is left, a category while you tidy up.
 */
export function AccountsPage() {
  return (
    <div className="flex flex-col gap-4">
      <h1 className="font-display text-title text-ink-1">Conti</h1>
      <AccountsTab />
    </div>
  )
}
