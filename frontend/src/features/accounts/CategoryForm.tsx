import { useState } from 'react'
import type { FormEvent } from 'react'

import {
  api,
  CATEGORY_COLORS,
  type Category,
  type CategoryColor,
  type CategoryKind,
} from '../../api/client'
import { Button } from '../../components/Button'
import { ChevronLeft, ChevronRight } from 'lucide-react'

import {
  CATEGORY_ICONS,
  ICON_GROUPS,
  categoryColorClasses,
} from '../../components/CategoryIcon'
import { Field } from '../../components/Field'
import { IconButton } from '../../components/IconButton'
import { Sheet } from '../../components/Sheet'

export function CategoryForm({
  category,
  kind,
  onClose,
  onSaved,
}: {
  category: Category | null
  kind: CategoryKind
  onClose: () => void
  onSaved: () => void
}) {
  const editing = category !== null

  const [name, setName] = useState(category?.name ?? '')
  const [color, setColor] = useState<CategoryColor>(category?.color ?? 'chart-1')
  const [icon, setIcon] = useState(category?.icon ?? 'ShoppingCart')
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setSaving(true)
    try {
      if (editing) await api.updateCategory(category.id, { name: name.trim(), color, icon })
      // ⚠️ The sign is set at creation and never again: movements already point
      // at the category, and flipping it would move past amounts from one side
      // of every chart to the other.
      else await api.createCategory({ name: name.trim(), kind, color, icon })
      onSaved()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Non è stato possibile salvare')
    } finally {
      setSaving(false)
    }
  }

  const title = editing
    ? 'Modifica categoria'
    : kind === 'expense'
      ? 'Nuova categoria di uscita'
      : 'Nuova categoria di entrata'

  return (
    <Sheet title={title} onClose={onClose}>
      <form onSubmit={submit} className="flex flex-col gap-4">
        <Field
          label="Nome"
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="Spesa"
          autoFocus
          required
        />

        <div className="flex flex-col gap-1.5">
          <span className="text-caption text-ink-2">Colore</span>
          <div className="flex flex-wrap gap-2">
            {CATEGORY_COLORS.map((option) => {
              const { text, tint } = categoryColorClasses(option)
              const active = option === color
              return (
                <button
                  key={option}
                  type="button"
                  onClick={() => setColor(option)}
                  aria-label={`Colore ${option}`}
                  title={`Colore ${option}`}
                  aria-pressed={active}
                  className={[
                    'grid size-10 place-items-center rounded-pill border-2 transition-colors duration-200',
                    tint,
                    active ? 'border-current' : 'border-transparent',
                    text,
                  ].join(' ')}
                >
                  <span className="size-4 rounded-pill bg-current" />
                </button>
              )
            })}
          </div>
        </div>

        <IconPicker value={icon} onChange={setIcon} />

        {error ? <p className="text-caption text-danger">{error}</p> : null}

        <div className="flex gap-2">
          <Button type="submit" disabled={saving}>
            {saving ? 'Salvo…' : 'Salva'}
          </Button>
          <Button type="button" variant="ghost" onClick={onClose}>
            Annulla
          </Button>
        </div>
      </form>
    </Sheet>
  )
}

/** Fifty-six icons, eight at a time, in themed pages.
 *
 * ⚠️ The arrows move between *groups*, not between numbered pages: "Casa" tells
 * you where you are and roughly what is next, which "pagina 3 di 7" never does.
 * The picker opens on the group the current icon belongs to, so editing a
 * category does not drop you somewhere unrelated.
 */
function IconPicker({
  value,
  onChange,
}: {
  value: string
  onChange: (icon: string) => void
}) {
  const [page, setPage] = useState(() =>
    Math.max(
      0,
      ICON_GROUPS.findIndex((group) => group.icons.includes(value)),
    ),
  )
  const group = ICON_GROUPS[page]
  const elsewhere = ICON_GROUPS.find((candidate) => candidate.icons.includes(value))

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between gap-2">
        <span className="text-caption text-ink-2">Icona</span>

        <div className="flex items-center gap-1">
          <IconButton
            label="Gruppo precedente"
            onClick={() => setPage((current) => Math.max(0, current - 1))}
            disabled={page === 0}
            Icon={ChevronLeft}
            iconSize={16}
          />

          <span className="min-w-[7.5rem] text-center text-caption text-ink-2">
            {group.label}
          </span>

          <IconButton
            label="Gruppo successivo"
            onClick={() =>
              setPage((current) => Math.min(ICON_GROUPS.length - 1, current + 1))
            }
            disabled={page === ICON_GROUPS.length - 1}
            Icon={ChevronRight}
            iconSize={16}
          />
        </div>
      </div>

      <div className="grid grid-cols-4 gap-2 sm:grid-cols-8">
        {group.icons.map((option) => {
          const Icon = CATEGORY_ICONS[option]
          const active = option === value
          return (
            <button
              key={option}
              type="button"
              onClick={() => onChange(option)}
              aria-label={option}
              title={option}
              aria-pressed={active}
              className={[
                'grid aspect-square place-items-center rounded-control border transition-colors duration-200',
                active
                  ? 'border-accent bg-accent-dim text-accent'
                  : 'border-border-soft text-ink-2 hover:bg-surface-hover',
              ].join(' ')}
            >
              <Icon size={20} strokeWidth={2} aria-hidden />
            </button>
          )
        })}
      </div>

      {/* The chosen icon can live on a page you are not looking at; saying so
          beats leaving you wondering whether the click registered. */}
      {elsewhere && elsewhere !== group ? (
        <p className="text-caption text-ink-3">Scelta nel gruppo {elsewhere.label}.</p>
      ) : null}
    </div>
  )
}
