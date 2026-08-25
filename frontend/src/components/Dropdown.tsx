import { useEffect, useRef, useState } from 'react'
import { Check, ChevronDown } from 'lucide-react'

import { categoryColorClasses } from './CategoryIcon'

/** A picker with a panel we actually draw.
 *
 * ⚠️ Not a native `<select>`, and the reason is narrow: the popup a `<select>`
 * opens is rendered by the operating system, so it cannot be rounded, tinted or
 * grouped the way the rest of the app is — the closed control would follow
 * DESIGN.md and the open one would be a grey Windows rectangle.
 *
 * What that costs is keyboard behaviour a native select gives for free, so it
 * is implemented here rather than skipped: arrows move, Enter picks, Escape
 * closes, and a click anywhere else closes too.
 */

export type Option<T> = {
  value: T
  label: string
  /** Optional colour token (`chart-3`) for a leading dot. */
  color?: string
}

export type Group<T> = {
  label: string
  options: Option<T>[]
}

export function Dropdown<T extends string | number>({
  placeholder,
  value,
  groups,
  onChange,
}: {
  /** Shown when nothing is chosen, and as the accessible name. */
  placeholder: string
  value: T | null
  groups: Group<T>[]
  onChange: (value: T | null) => void
}) {
  const [open, setOpen] = useState(false)
  const container = useRef<HTMLDivElement>(null)

  const all = groups.flatMap((group) => group.options)
  const chosen = all.find((option) => option.value === value) ?? null

  useEffect(() => {
    if (!open) return

    const onPointerDown = (event: PointerEvent) => {
      if (!container.current?.contains(event.target as Node)) setOpen(false)
    }
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false)
    }

    document.addEventListener('pointerdown', onPointerDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('pointerdown', onPointerDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  function move(step: number) {
    if (all.length === 0) return
    const current = all.findIndex((option) => option.value === value)
    const next = Math.min(Math.max(current + step, 0), all.length - 1)
    onChange(all[current === -1 && step > 0 ? 0 : next].value)
  }

  return (
    <div ref={container} className="relative">
      <button
        type="button"
        onClick={() => setOpen((was) => !was)}
        onKeyDown={(event) => {
          if (event.key === 'ArrowDown') {
            event.preventDefault()
            if (open) move(1)
            else setOpen(true)
          }
          if (event.key === 'ArrowUp') {
            event.preventDefault()
            move(-1)
          }
        }}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={placeholder}
        className={[
          'flex min-h-9 items-center gap-1.5 rounded-pill border px-3 text-caption transition-colors duration-200',
          chosen
            ? 'border-accent bg-accent-dim text-accent'
            : 'border-border-soft text-ink-2 hover:bg-surface-hover',
        ].join(' ')}
      >
        {chosen?.color ? <Dot color={chosen.color} /> : null}
        {chosen?.label ?? placeholder}
        <ChevronDown size={15} strokeWidth={2} aria-hidden />
      </button>

      {open ? (
        <div
          role="listbox"
          aria-label={placeholder}
          className="absolute left-0 top-[calc(100%+6px)] z-40 max-h-72 w-56 overflow-y-auto rounded-card border border-border-soft bg-bg-raise p-1.5 shadow-card"
        >
          <Row
            label={placeholder}
            selected={value === null}
            onClick={() => {
              onChange(null)
              setOpen(false)
            }}
          />

          {groups.map((group) => (
            <div key={group.label} role="group" aria-label={group.label}>
              {/* The heading earns its place when there is more than one group:
                  spending and income categories must never read as one list. */}
              {groups.length > 1 ? (
                <p className="px-3 pb-1 pt-2.5 text-micro uppercase text-ink-3">
                  {group.label}
                </p>
              ) : null}

              {group.options.map((option) => (
                <Row
                  key={String(option.value)}
                  label={option.label}
                  color={option.color}
                  selected={option.value === value}
                  onClick={() => {
                    onChange(option.value)
                    setOpen(false)
                  }}
                />
              ))}
            </div>
          ))}
        </div>
      ) : null}
    </div>
  )
}

function Row({
  label,
  color,
  selected,
  onClick,
}: {
  label: string
  color?: string
  selected: boolean
  onClick: () => void
}) {
  return (
    <button
      type="button"
      role="option"
      aria-selected={selected}
      onClick={onClick}
      className={[
        'flex w-full items-center gap-2 rounded-control px-3 py-2 text-left text-body transition-colors duration-200',
        selected ? 'bg-surface-selected text-accent' : 'text-ink-1 hover:bg-surface-hover',
      ].join(' ')}
    >
      {color ? <Dot color={color} /> : null}
      <span className="min-w-0 flex-1 truncate">{label}</span>
      {selected ? <Check size={16} strokeWidth={2} aria-hidden /> : null}
    </button>
  )
}

/** The colour classes come from CategoryIcon, which is the one place that knows
 *  the palette: two copies would drift the day an eleventh colour arrives. */
function Dot({ color }: { color: string }) {
  return (
    <span
      className={`size-2.5 shrink-0 rounded-pill ${categoryColorClasses(color).dot}`}
      aria-hidden
    />
  )
}
