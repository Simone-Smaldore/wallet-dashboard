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

export function MovimentiPage() {
  return (
    <EmptyState title="Movimenti">
      L'elenco di tutto quello che entra ed esce, con i filtri per periodo, conto e
      categoria. Arriva con M3.
    </EmptyState>
  )
}

export function ContiPage() {
  return (
    <EmptyState title="Conti">
      I tuoi conti e i loro saldi, più le categorie di spesa e di entrata. Arriva con M2 —
      è il prossimo passo.
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

export function NuovoMovimentoPage() {
  return (
    <EmptyState title="Aggiungi un movimento">
      Importo, categoria, salva. È la schermata più importante dell'app e arriva con M3,
      insieme ai conti su cui registrare.
    </EmptyState>
  )
}
