import { useState } from 'react'
import type { FormEvent } from 'react'

import { useQuery } from '../../api/cache'
import { api, type Savings } from '../../api/client'
import { Button } from '../../components/Button'
import { Dropdown } from '../../components/Dropdown'
import { Field } from '../../components/Field'
import { Sheet } from '../../components/Sheet'
import { formatMoney, parseAmountField } from '../../lib/money'

/** How much you mean to put aside, and what counts as a salary.
 *
 * The two live in the same sheet because neither works without the other: a
 * target with no salary to judge it against has nothing to say, and naming the
 * salary without a target measures a stretch against nothing.
 *
 * ⚠️ The amount is kept as a string while it is typed and turned into cents
 * only on save — like every other amount here, and for the same reason:
 * `type="number"` refills an emptied box with 0, and multiplying a parsed float
 * by 100 loses a cent on most of the amounts anyone types.
 *
 * ⚠️ Clearing the box removes the target rather than setting it to zero. "I
 * don't want a goal" and "my goal is nothing" are different statements, and the
 * card shows a different thing for each.
 */
export function SavingsTargetSheet({
  savings,
  onClose,
}: {
  savings: Savings
  onClose: () => void
}) {
  const categories = useQuery('/api/categories', api.categories)

  const [amount, setAmount] = useState(
    savings.target_cents === null
      ? ''
      : formatMoney(savings.target_cents, { symbol: false }),
  )
  const [salaryId, setSalaryId] = useState<number | null>(savings.salary_category_id)
  const [error, setError] = useState<string | null>(null)

  // ⚠️ Income categories only. A spending category here would make every cycle
  // start on a grocery run — the server refuses it too, this just never offers
  // the mistake.
  const income = (categories.data ?? []).filter(
    (category) => category.kind === 'income' && !category.is_archived,
  )

  async function save(event: FormEvent) {
    event.preventDefault()
    setError(null)

    const emptied = amount.trim() === ''
    const parsed = emptied ? null : parseAmountField(amount)

    if (parsed && parsed.error) {
      setError(parsed.error)
      return
    }
    if (parsed && parsed.cents !== null && parsed.cents < 0) {
      setError('Un obiettivo negativo non vuol dire niente')
      return
    }

    try {
      await api.updateHousehold({
        monthly_savings_target_cents: parsed ? parsed.cents : null,
        salary_category_id: salaryId,
      })
      onClose()
    } catch {
      // The box keeps what was typed: the worst thing this app can do is make
      // you write an amount twice.
      setError('Non è stato possibile salvare. Riprova.')
    }
  }

  return (
    <Sheet title="Obiettivo di risparmio" onClose={onClose}>
      <form onSubmit={save} className="flex flex-col gap-4">
        <Field
          label="Da uno stipendio al successivo metto da parte"
          inputMode="decimal"
          autoFocus
          value={amount}
          onChange={(event) => setAmount(event.target.value)}
          placeholder="0,00"
          hint="Lascia vuoto per non avere un obiettivo."
          error={error}
        />

        <div className="flex flex-col gap-1.5">
          <p className="text-caption text-ink-2">Qual è lo stipendio</p>
          <Dropdown
            placeholder="Scegli la categoria"
            value={salaryId}
            onChange={setSalaryId}
            groups={[{ label: 'Entrate', options: income.map(toOption) }]}
          />
          <p className="text-caption text-ink-3">
            Ogni entrata in questa categoria apre un nuovo ciclo. Se ne arriva una seconda
            nello stesso mese — la tredicesima, degli arretrati — si somma a quello in
            corso invece di spezzarlo in due.
          </p>
        </div>

        <p className="text-caption text-ink-3">
          Il conto va da uno stipendio al successivo, non dal primo del mese: quello che
          conta è se lo stipendio di novembre c'era ancora quando è arrivato quello di
          dicembre. I trasferimenti fra i tuoi conti non contano — spostare i soldi non è
          metterli da parte.
        </p>

        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Annulla
          </Button>
          <Button type="submit">Salva</Button>
        </div>
      </form>
    </Sheet>
  )
}

function toOption(category: { id: number; name: string; color: string }) {
  return { value: category.id, label: category.name, color: category.color }
}
