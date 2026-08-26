import { useState } from 'react'
import type { FormEvent } from 'react'

import { useQuery } from '../../api/cache'
import { api, type Asset } from '../../api/client'
import { Button } from '../../components/Button'
import { Dropdown } from '../../components/Dropdown'
import { Field } from '../../components/Field'
import { Sheet } from '../../components/Sheet'
import { parseAmountField } from '../../lib/money'
import { today } from '../../lib/period'

/** Ho comprato: quante quote in più, e quanto sono costate.
 *
 * ⚠️ **The gesture that happens every month**, and it is two facts at once: the
 * money leaves a bank account, the holding grows. They go in one request so
 * neither can land alone — money moved with no shares to show for it would make
 * the gain fiction, and nothing would look wrong.
 *
 * ⚠️ **The quantity is added, not replaced.** Making you type the new total
 * would be making you do arithmetic, which is the one thing this app is for.
 */
export function BuySheet({ asset, onClose }: { asset: Asset; onClose: () => void }) {
  const accounts = useQuery('/api/accounts', api.accounts)

  const [quantity, setQuantity] = useState('')
  const [amount, setAmount] = useState('')
  const [from, setFrom] = useState<number | null>(null)
  const [date, setDate] = useState(() => today())
  const [error, setError] = useState<string | null>(null)

  // Where the money can come from: anywhere that is not the holding's own home.
  const sources = (accounts.data?.accounts ?? []).filter(
    (account) => !account.is_archived && account.id !== asset.account_id,
  )

  async function save(event: FormEvent) {
    event.preventDefault()
    setError(null)

    if (!Number(quantity)) return setError('Quante quote hai comprato?')
    if (from === null) return setError('Da quale conto sono usciti i soldi?')

    const paid = parseAmountField(amount)
    if (paid.cents === null) return setError(paid.error)

    try {
      await api.buyAsset(asset.id, {
        quantity: quantity.trim(),
        amount_cents: paid.cents,
        from_account_id: from,
        date,
      })
      onClose()
    } catch (cause) {
      // The sheet keeps what was typed: nobody should have to find their
      // contract note twice.
      setError(cause instanceof Error ? cause.message : 'Non è stato possibile salvare.')
    }
  }

  return (
    <Sheet title={`Ho comprato ${asset.name}`} onClose={onClose}>
      <form onSubmit={save} className="flex flex-col gap-4">
        <Field
          label="Quante ne hai comprate"
          inputMode="decimal"
          autoFocus
          value={quantity}
          onChange={(event) => setQuantity(event.target.value)}
          placeholder="0,4"
          hint={`Si sommano alle ${asset.quantity} che hai già.`}
        />

        <Field
          label="Quanto hai pagato"
          inputMode="decimal"
          value={amount}
          onChange={(event) => setAmount(event.target.value)}
          placeholder="80,00"
          hint="Commissioni comprese: è quello che è uscito dal conto."
        />

        <div className="flex flex-col gap-1.5">
          <p className="text-caption text-ink-2">Da quale conto</p>
          <Dropdown
            placeholder="Scegli il conto"
            value={from}
            onChange={setFrom}
            groups={[
              {
                label: 'Conti',
                options: sources.map((account) => ({
                  value: account.id,
                  label: account.name,
                })),
              },
            ]}
          />
        </div>

        <Field
          label="Data"
          type="date"
          value={date}
          onChange={(event) => setDate(event.target.value)}
        />

        <p className="text-caption text-ink-3">
          ⚠️ È un trasferimento, non una spesa: il patrimonio non cala e le uscite non lo
          vedono. Il budget del mese però sì — quei soldi dal conto sono usciti davvero.
        </p>

        {error ? <p className="text-caption text-danger">{error}</p> : null}

        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Annulla
          </Button>
          <Button type="submit">Registra</Button>
        </div>
      </form>
    </Sheet>
  )
}
