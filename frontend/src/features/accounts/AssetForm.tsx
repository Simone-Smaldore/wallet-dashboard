import { useState } from 'react'
import type { FormEvent } from 'react'

import {
  api,
  ASSET_KINDS,
  type Asset,
  type AssetKind,
  type PriceBasis,
  type PriceSource,
} from '../../api/client'
import { Button } from '../../components/Button'
import { Dropdown } from '../../components/Dropdown'
import { Field } from '../../components/Field'
import { Sheet } from '../../components/Sheet'
import { formatMoney } from '../../lib/money'
import { formatDayShort } from '../../lib/period'

const KIND_LABELS: Record<AssetKind, string> = {
  etf: 'ETF',
  obbligazione: 'Obbligazione',
  crypto: 'Crypto',
  altro: 'Altro',
}

/** ⚠️ The kind decides how the price is read, so choosing it is not cosmetic.
 *
 * A bond quotes as a percentage of its nominal; everything else quotes per
 * unit. Setting the two together means one fewer thing to get wrong, and the
 * form still shows which convention is in force. */
const DEFAULTS: Record<AssetKind, { basis: PriceBasis; source: PriceSource }> = {
  etf: { basis: 'per_unit', source: 'borsa_italiana' },
  obbligazione: { basis: 'percent_of_nominal', source: 'borsa_italiana' },
  crypto: { basis: 'per_unit', source: 'coingecko' },
  altro: { basis: 'per_unit', source: 'manual' },
}

const SOURCE_LABELS: Record<PriceSource, string> = {
  borsa_italiana: 'Borsa Italiana (ISIN)',
  coingecko: 'CoinGecko (id moneta)',
  manual: 'A mano',
}

const QUANTITY_HINT: Record<PriceBasis, string> = {
  per_unit: 'Quante quote, o quante monete.',
  percent_of_nominal:
    "Il valore nominale in euro. ⚠️ Un'obbligazione si quota in percentuale del nominale: 10.000 € a 55,78 valgono 5.578 €.",
}

/** Add or correct a holding.
 *
 * ⚠️ The "prova adesso" is the point of this form, not a nicety. A mistyped
 * ISIN fails silently for weeks: nothing errors, the nightly job simply finds
 * no price, and you notice because a number never moved. Asking the source now,
 * while the field is still under your eyes, is the only cheap moment to find
 * out.
 */
export function AssetForm({
  asset,
  accountId,
  onClose,
}: {
  asset: Asset | null
  accountId: number
  onClose: () => void
}) {
  const [name, setName] = useState(asset?.name ?? '')
  const [kind, setKind] = useState<AssetKind>(asset?.kind ?? 'etf')
  const [quantity, setQuantity] = useState(asset?.quantity ?? '')
  const [reference, setReference] = useState(asset?.source_ref ?? '')
  const [source, setSource] = useState<PriceSource>(asset?.source ?? 'borsa_italiana')
  const [basis, setBasis] = useState<PriceBasis>(asset?.price_basis ?? 'per_unit')

  const [probe, setProbe] = useState<string | null>(null)
  const [probing, setProbing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function chooseKind(next: AssetKind) {
    setKind(next)
    // Only for a new one: changing the kind of an existing holding must not
    // quietly rewrite a convention somebody set on purpose.
    if (asset === null) {
      setBasis(DEFAULTS[next].basis)
      setSource(DEFAULTS[next].source)
    }
  }

  async function tryPrice() {
    setProbe(null)
    setProbing(true)
    try {
      const result = await api.probePrice({
        source,
        source_ref: reference.trim(),
        kind,
        price_basis: basis,
        quantity: quantity.trim() || undefined,
      })
      setProbe(
        result.found
          ? `${formatMoney(result.unit_price_cents ?? 0)} al ${formatDayShort(result.date ?? '')}` +
            (result.value_cents !== null
              ? ` · in tutto ${formatMoney(result.value_cents)}`
              : '')
          : 'Nessun prezzo: controlla il riferimento.',
      )
    } catch {
      setProbe('Non sono riuscito a chiedere il prezzo.')
    } finally {
      setProbing(false)
    }
  }

  async function save(event: FormEvent) {
    event.preventDefault()
    setError(null)

    if (!name.trim()) return setError('Manca il nome')
    if (!Number(quantity)) return setError('Manca la quantità')

    const body = {
      name: name.trim(),
      kind,
      quantity: quantity.trim(),
      price_basis: basis,
      source,
      source_ref: reference.trim() || null,
    }

    try {
      if (asset) await api.updateAsset(asset.id, body)
      else await api.createAsset({ ...body, account_id: accountId })
      onClose()
    } catch (cause) {
      // The form keeps what was typed: an ISIN is not something to write twice.
      setError(cause instanceof Error ? cause.message : 'Non è stato possibile salvare.')
    }
  }

  return (
    <Sheet title={asset ? 'Modifica asset' : 'Nuovo asset'} onClose={onClose}>
      <form onSubmit={save} className="flex flex-col gap-4">
        <Field
          label="Nome"
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="iShares Core MSCI World"
          autoFocus
        />

        <div className="flex flex-col gap-1.5">
          <span className="text-caption text-ink-2">Tipo</span>
          <div className="flex flex-wrap gap-2">
            {ASSET_KINDS.map((option) => (
              <button
                key={option}
                type="button"
                onClick={() => chooseKind(option)}
                className={[
                  'min-h-9 rounded-pill border px-3 text-caption transition-colors duration-200',
                  option === kind
                    ? 'border-accent bg-accent-dim text-accent'
                    : 'border-border-soft text-ink-2 hover:bg-surface-hover',
                ].join(' ')}
              >
                {KIND_LABELS[option]}
              </button>
            ))}
          </div>
        </div>

        <Field
          label="Quantità"
          inputMode="decimal"
          value={quantity}
          onChange={(event) => setQuantity(event.target.value)}
          placeholder="0"
          hint={QUANTITY_HINT[basis]}
        />

        <div className="flex flex-col gap-1.5">
          <span className="text-caption text-ink-2">Prezzo da</span>
          <Dropdown
            placeholder="Scegli la fonte"
            value={source}
            onChange={(value) => value && setSource(value)}
            groups={[
              {
                label: 'Fonti',
                options: (['borsa_italiana', 'coingecko', 'manual'] as PriceSource[]).map(
                  (value) => ({ value, label: SOURCE_LABELS[value] }),
                ),
              },
            ]}
          />
        </div>

        {source === 'manual' ? (
          <p className="text-caption text-ink-3">
            Nessuno andrà a cercare il prezzo: il valore lo aggiorni tu con la
            riconciliazione del conto.
          </p>
        ) : (
          <>
            <Field
              label={source === 'coingecko' ? 'Id della moneta' : 'ISIN'}
              value={reference}
              onChange={(event) => setReference(event.target.value)}
              placeholder={source === 'coingecko' ? 'bitcoin' : 'IE00B4L5Y983'}
            />

            <div className="flex items-center gap-3">
              <Button
                type="button"
                variant="secondary"
                onClick={() => void tryPrice()}
                disabled={probing || !reference.trim()}
              >
                {probing ? 'Chiedo…' : 'Prova adesso'}
              </Button>
              {probe ? <p className="num text-caption text-ink-2">{probe}</p> : null}
            </div>
          </>
        )}

        {error ? <p className="text-caption text-danger">{error}</p> : null}

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
