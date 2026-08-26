import { useState } from 'react'
import { Archive, ArchiveRestore, Pencil, Plus } from 'lucide-react'

import { api, type Category, type CategoryKind } from '../../api/client'
import { useQuery } from '../../api/cache'
import { Button } from '../../components/Button'
import { CategoryIcon } from '../../components/CategoryIcon'
import { IconButton } from '../../components/IconButton'
import { EmptyState } from '../../components/EmptyState'
import { CategoryForm } from './CategoryForm'

/** ⚠️ Two lists, never interleaved.
 *
 * "Stipendio" has no business among the spending categories, and the separation
 * on screen is the same one the database enforces: uniqueness is per sign, so
 * "Regalo" can legitimately exist on both sides — a present you bought, and
 * money someone gave you.
 *
 * Cards in a grid rather than one long list: a category is an icon, a colour and
 * a word, which is a tile and not a row. It also fills the width instead of
 * leaving two thirds of a desktop screen empty next to a column of names.
 */
export function CategoriesTab() {
  const { data, error, refetch } = useQuery('/api/categories', api.categories)
  const [editing, setEditing] = useState<Category | null>(null)
  const [creating, setCreating] = useState<CategoryKind | null>(null)

  // No `loading` guard: categories are names, and a name remembered from the
  // last session is still that name. If there is nothing at all yet the two
  // groups draw their own empty state, which is the honest thing to show.
  if (error && !data) {
    return (
      <EmptyState title="Non riesco a leggere le categorie">
        {error.message}
        <Button variant="secondary" onClick={refetch} className="mt-4">
          Riprova
        </Button>
      </EmptyState>
    )
  }

  const categories = data ?? []

  return (
    <div className="flex flex-col gap-6">
      <CategoryGroup
        title="Uscite"
        kind="expense"
        categories={categories.filter((category) => category.kind === 'expense')}
        onEdit={setEditing}
        onCreate={() => setCreating('expense')}
      />

      <CategoryGroup
        title="Entrate"
        kind="income"
        categories={categories.filter((category) => category.kind === 'income')}
        onEdit={setEditing}
        onCreate={() => setCreating('income')}
      />

      {creating ? (
        <CategoryForm
          category={null}
          kind={creating}
          onClose={() => setCreating(null)}
          onSaved={() => setCreating(null)}
        />
      ) : null}

      {editing ? (
        <CategoryForm
          category={editing}
          kind={editing.kind}
          onClose={() => setEditing(null)}
          onSaved={() => setEditing(null)}
        />
      ) : null}
    </div>
  )
}

function CategoryGroup({
  title,
  kind,
  categories,
  onEdit,
  onCreate,
}: {
  title: string
  kind: CategoryKind
  categories: Category[]
  onEdit: (category: Category) => void
  onCreate: () => void
}) {
  return (
    <section className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-micro uppercase text-ink-3">{title}</h2>
        <button
          type="button"
          onClick={onCreate}
          className="flex items-center gap-1.5 rounded-pill px-3 py-1.5 text-caption text-ink-2 transition-colors duration-200 hover:bg-surface-hover hover:text-ink-1"
        >
          <Plus size={16} strokeWidth={2} aria-hidden />
          {kind === 'expense' ? 'Nuova uscita' : 'Nuova entrata'}
        </button>
      </div>

      {categories.length === 0 ? (
        <EmptyState
          title={`Nessuna categoria di ${kind === 'expense' ? 'uscita' : 'entrata'}`}
        />
      ) : (
        <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {categories.map((category) => (
            <CategoryCard
              key={category.id}
              category={category}
              onEdit={() => onEdit(category)}
            />
          ))}
        </ul>
      )}
    </section>
  )
}

function CategoryCard({
  category,
  onEdit,
}: {
  category: Category
  onEdit: () => void
}) {
  async function toggleArchive() {
    // Archived, never deleted: past movements point at it and the month-on-month
    // comparison reads it.
    await api.updateCategory(category.id, { is_archived: !category.is_archived })
  }

  return (
    <li
      className={[
        'flex items-center gap-3 rounded-card border border-border-soft bg-surface-card px-4 py-3',
        category.is_archived ? 'opacity-55' : '',
      ].join(' ')}
    >
      <CategoryIcon icon={category.icon} color={category.color} />

      <div className="min-w-0 flex-1">
        <p className="truncate text-body text-ink-1">{category.name}</p>
        {category.is_archived ? <p className="text-caption text-ink-3">Archiviata</p> : null}
      </div>

      <div className="flex shrink-0">
        <IconButton label={`Modifica ${category.name}`} onClick={onEdit} Icon={Pencil} />
        <IconButton
          label={
            category.is_archived
              ? `Ripristina ${category.name}`
              : `Archivia ${category.name}`
          }
          onClick={() => void toggleArchive()}
          Icon={category.is_archived ? ArchiveRestore : Archive}
        />
      </div>
    </li>
  )
}
