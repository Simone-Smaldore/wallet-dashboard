import { CategoriesTab } from './CategoriesTab'

/** The two lists you file movements under.
 *
 * A section of its own since M2's review: on a phone it earns the tab the
 * profile gave up, and on a desktop it is one sidebar entry instead of half a
 * screen hidden behind a switch.
 */
export function CategoriesPage() {
  return (
    <div className="flex flex-col gap-4">
      <h1 className="font-display text-title text-ink-1">Categorie</h1>
      <CategoriesTab />
    </div>
  )
}
