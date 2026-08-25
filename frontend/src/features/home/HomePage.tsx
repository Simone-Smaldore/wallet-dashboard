import { Wordmark } from '../../components/Wordmark'

/** Placeholder for the walking skeleton.
 *
 * M0 proves the stack, not the product: there is nothing to show yet because
 * there is nothing to record into. The real home — balances, recent movements,
 * the month's saving target — arrives with M4, and everything before it needs
 * accounts and transactions to exist first.
 */
export function HomePage() {
  return (
    <div className="min-h-full bg-bg-app px-4 py-10">
      <div className="mx-auto flex w-full max-w-[520px] flex-col gap-5">
        <Wordmark />

        <section className="rounded-card border border-border-soft bg-surface-card p-5 shadow-card">
          <h1 className="font-display text-title text-ink-1">In costruzione</h1>
          <p className="mt-2 text-body text-ink-2">
            Questo è lo scheletro dell'app: c'è l'impalcatura, non ancora il prodotto. Si
            comincia dall'accesso, poi conti e categorie, poi i movimenti.
          </p>
        </section>
      </div>
    </div>
  )
}
