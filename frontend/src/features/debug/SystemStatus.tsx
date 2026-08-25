import { useEffect, useState } from 'react'

import { api, type Health } from '../../api/client'
import { Wordmark } from '../../components/Wordmark'

/** Diagnostics screen, reachable only at /_stato — not linked from the app.
 *
 * Left outside the session gate on purpose. Signing in needs the database, so
 * requiring a session here would hide the page exactly when the database is the
 * thing that broke. The disclosure worry is handled in the endpoint instead:
 * /api/health fills in `detail` only when something is wrong, and never carries
 * a connection string or a single row of domain data.
 */

type Probe =
  | { state: 'loading' }
  | { state: 'loaded'; health: Health }
  | { state: 'failed'; message: string }

export function SystemStatus() {
  const [probe, setProbe] = useState<Probe>({ state: 'loading' })

  useEffect(() => {
    let active = true

    api
      .health()
      .then((health) => {
        if (active) setProbe({ state: 'loaded', health })
      })
      .catch((error: unknown) => {
        if (active) {
          setProbe({
            state: 'failed',
            message: error instanceof Error ? error.message : 'Errore sconosciuto',
          })
        }
      })

    return () => {
      active = false
    }
  }, [])

  return (
    <div className="min-h-full bg-bg-app px-4 py-8 sm:px-6">
      <div className="mx-auto flex w-full max-w-[560px] flex-col gap-3">
        <Wordmark />

        <section className="rounded-card border border-border-soft bg-surface-card p-5 shadow-card">
          <h1 className="font-display text-title text-ink-1">Stato del sistema</h1>
          <p className="mt-1 text-caption text-ink-2">
            Pagina di diagnostica · non raggiungibile dall'app
          </p>

          <div className="mt-5 flex flex-col gap-2">
            <StatusRow label="Frontend" value="ok" detail="React · Vite · Tailwind" />
            <ApiRows probe={probe} />
          </div>
        </section>

        <DesignSystem />
      </div>
    </div>
  )
}

function ApiRows({ probe }: { probe: Probe }) {
  if (probe.state === 'loading') {
    return (
      <>
        <StatusRow label="API" value="pending" detail="Verifico…" />
        <StatusRow label="Database" value="pending" detail="Verifico…" />
      </>
    )
  }

  if (probe.state === 'failed') {
    return (
      <>
        <StatusRow label="API" value="error" detail={probe.message} />
        <StatusRow label="Database" value="pending" detail="Non verificabile" />
      </>
    )
  }

  const { health } = probe
  const databaseLabels: Record<Health['database'], string> = {
    ok: 'Connesso',
    unreachable: 'Non raggiungibile',
    not_configured: 'DATABASE_URL non configurata',
  }

  return (
    <>
      <StatusRow label="API" value="ok" detail={`FastAPI · ambiente ${health.environment}`} />
      <StatusRow
        label="Database"
        value={health.database === 'ok' ? 'ok' : 'error'}
        detail={databaseLabels[health.database]}
      />
      {health.database !== 'ok' && health.detail ? (
        <p className="mt-1 rounded-control bg-surface-card-2 px-3 py-2.5 text-caption text-ink-2">
          {health.detail}
        </p>
      ) : null}
    </>
  )
}

type Value = 'ok' | 'error' | 'pending'

function StatusRow({ label, value, detail }: { label: string; value: Value; detail: string }) {
  return (
    <div className="flex items-center gap-3 rounded-control border border-border-soft px-3 py-2.5">
      <StatusDot value={value} />
      <span className="text-body font-medium text-ink-1">{label}</span>
      <span className="ml-auto truncate text-caption text-ink-2" title={detail}>
        {detail}
      </span>
    </div>
  )
}

/* A filled dot, not an icon: DESIGN.md prescribes Lucide and forbids hand-drawn
   SVGs, and Lucide is not a dependency until M1. A dot needs neither. */
function StatusDot({ value }: { value: Value }) {
  const tone =
    value === 'ok'
      ? 'bg-accent-dim text-accent'
      : value === 'error'
        ? 'bg-danger-dim text-danger'
        : 'bg-surface-card-2 text-ink-3'

  const label = value === 'ok' ? 'ok' : value === 'error' ? 'errore' : 'in corso'

  return (
    <span
      className={`grid size-6 shrink-0 place-items-center rounded-pill ${tone}`}
      role="img"
      aria-label={label}
    >
      <span className="size-2 rounded-pill bg-current" />
    </span>
  )
}

/* Renders the tokens straight from tokens.css: if a swatch looks wrong here,
   tokens.css has drifted from docs/design/DESIGN.md. */
function DesignSystem() {
  const money = [
    { name: 'entrata', className: 'bg-money-income' },
    { name: 'uscita', className: 'bg-money-expense' },
    { name: 'trasferimento', className: 'bg-money-transfer' },
    { name: 'rettifica', className: 'bg-money-adjustment' },
  ]

  const series = [
    'bg-chart-1',
    'bg-chart-2',
    'bg-chart-3',
    'bg-chart-4',
    'bg-chart-5',
    'bg-chart-6',
  ]

  return (
    <section className="rounded-card border border-border-soft bg-surface-card p-5 shadow-card">
      <h2 className="font-display text-heading text-ink-1">Design system</h2>
      <p className="mt-1 text-caption text-ink-2">
        Token da docs/design/DESIGN.md · Space Grotesk e Instrument Sans
      </p>

      <p className="num mt-4 text-hero text-ink-1">1.234,56 €</p>

      <p className="mt-4 text-micro uppercase text-ink-3">I colori del denaro</p>
      <div className="mt-2 flex gap-2">
        {money.map((swatch) => (
          <div key={swatch.name} className="flex flex-1 flex-col gap-1.5">
            <div className={`h-10 rounded-control ${swatch.className}`} />
            <span className="text-micro uppercase text-ink-3">{swatch.name}</span>
          </div>
        ))}
      </div>

      <p className="mt-4 text-micro uppercase text-ink-3">Serie dei grafici</p>
      <div className="mt-2 flex gap-2">
        {series.map((className) => (
          <div key={className} className={`h-6 flex-1 rounded-control ${className}`} />
        ))}
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-2">
        <button
          type="button"
          className="rounded-pill bg-accent px-4 py-2.5 text-body font-medium text-ink-on-accent shadow-glow-accent"
        >
          Azione primaria
        </button>
        <button
          type="button"
          className="rounded-pill border border-border-strong px-4 py-2.5 text-body text-ink-1"
        >
          Secondaria
        </button>
        <span className="rounded-pill bg-surface-card-2 px-3 py-2 text-caption text-ink-2">
          Chip
        </span>
      </div>
    </section>
  )
}
