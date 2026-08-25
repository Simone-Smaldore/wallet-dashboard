import { EmptyState } from '../../components/EmptyState'

/** The rooms that exist but are still empty.
 *
 * Each one says what will be there and when, rather than pretending. A screen
 * that shows a plausible-looking zero is worse than one that admits it has
 * nothing: the first is a number you might believe.
 */

export function RiepilogoPage() {
  return (
    <EmptyState title="Riepilogo">
      Qui vedrai quanto c'è su ogni conto, il totale, e gli ultimi movimenti. Arriva con
      M4, quando ci saranno movimenti da riassumere.
    </EmptyState>
  )
}

export function AnalisiPage() {
  return (
    <EmptyState title="Analisi">
      Dove finiscono i soldi: per categoria, mese per mese, e il patrimonio nel tempo.
      Arriva con M4.
    </EmptyState>
  )
}
