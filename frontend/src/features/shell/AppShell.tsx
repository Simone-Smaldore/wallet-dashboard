import { ChartColumn, House, Landmark, Plus, Receipt, User } from 'lucide-react'
import { NavLink, Outlet, useNavigate } from 'react-router'

import { Wordmark } from '../../components/Wordmark'

/** The frame every signed-in screen sits in.
 *
 * Mobile: five tabs pinned to the bottom — icons only, no captions — plus the
 * add button floating above them on the right. Five labels on a 390px screen
 * crowd the row and get truncated anyway; five destinations are learnt on the
 * first use, and the name is still there for a screen reader.
 *
 * ⚠️ The add button is not one of the tabs, and that is the point. DESIGN.md
 * originally put it in the middle of a four-tab bar; with the profile taking a
 * fifth tab there was no middle left. Floating it keeps both: five destinations
 * *and* a fixed home for the one action that has to cost three taps — the whole
 * app depends on recording a spend being frictionless.
 */

const SECTIONS = [
  { to: '/riepilogo', label: 'Riepilogo', Icon: House },
  { to: '/movimenti', label: 'Movimenti', Icon: Receipt },
  { to: '/conti', label: 'Conti', Icon: Landmark },
  { to: '/analisi', label: 'Analisi', Icon: ChartColumn },
  { to: '/profilo', label: 'Profilo', Icon: User },
]

export function AppShell() {
  return (
    <div className="min-h-full bg-bg-app">
      <Sidebar />

      {/* pb-28 on mobile clears the tab bar and the button above it. */}
      <main className="mx-auto w-full max-w-[720px] px-4 pb-28 pt-6 sm:pl-[248px] sm:pr-6 sm:pb-10">
        <Outlet />
      </main>

      <AddButton />
      <TabBar />
    </div>
  )
}

function Sidebar() {
  return (
    <aside className="fixed inset-y-0 left-0 hidden w-[212px] flex-col gap-1 border-r border-border-soft bg-bg-raise px-3 py-6 sm:flex">
      <div className="px-3 pb-4">
        <Wordmark />
      </div>

      {SECTIONS.map(({ to, label, Icon }) => (
        <NavLink
          key={to}
          to={to}
          className={({ isActive }) =>
            [
              'flex items-center gap-3 rounded-control px-3 py-2.5 text-body transition-colors duration-200',
              isActive
                ? 'bg-surface-selected text-accent'
                : 'text-ink-2 hover:bg-surface-hover hover:text-ink-1',
            ].join(' ')
          }
        >
          <Icon size={20} strokeWidth={2} aria-hidden />
          {label}
        </NavLink>
      ))}
    </aside>
  )
}

function TabBar() {
  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-30 flex h-16 border-t border-border-soft bg-bg-raise/90 backdrop-blur-[12px] sm:hidden"
      aria-label="Sezioni"
    >
      {SECTIONS.map(({ to, label, Icon }) => (
        <NavLink
          key={to}
          to={to}
          aria-label={label}
          title={label}
          className={({ isActive }) =>
            [
              'flex flex-1 items-center justify-center transition-colors duration-200',
              isActive ? 'text-accent' : 'text-ink-3',
            ].join(' ')
          }
        >
          <Icon size={26} strokeWidth={2} aria-hidden />
        </NavLink>
      ))}
    </nav>
  )
}

/** The one action with a permanent place on the screen.
 *
 * Sits above the tab bar on mobile and bottom-right on desktop. Does nothing
 * yet: the form arrives with M3, and until then saying so is more honest than
 * hiding the button and rebuilding the layout later.
 */
function AddButton() {
  const navigate = useNavigate()

  return (
    <button
      type="button"
      onClick={() => void navigate('/movimenti/nuovo')}
      aria-label="Aggiungi un movimento"
      className="fixed bottom-20 right-4 z-40 grid size-14 place-items-center rounded-pill bg-accent text-ink-on-accent shadow-glow-accent transition-colors duration-200 hover:bg-accent-hover active:bg-accent-press sm:bottom-8 sm:right-8"
    >
      <Plus size={26} strokeWidth={2} aria-hidden />
    </button>
  )
}
