import { useState } from 'react'
import { ChartColumn, House, Landmark, Plus, Receipt, Tags, User } from 'lucide-react'
import { NavLink, Outlet } from 'react-router'

import { Wordmark } from '../../components/Wordmark'
import { TransactionSheet } from '../transactions/TransactionSheet'

/** The frame every signed-in screen sits in.
 *
 * Five sections, and the profile is not one of them:
 *
 * - **Mobile**: the five sit in the tab bar as icons only — five words on a
 *   390px screen crowd the row and get truncated anyway. The profile moves to a
 *   fixed button top right, which is where you look for "me" on a phone and
 *   which buys the fifth tab back for Categorie.
 * - **Desktop**: the sidebar lists all six, profile included and last. There is
 *   room, and a floating button in a corner would be a second route to the same
 *   screen.
 *
 * ⚠️ One entry point per screen, per platform. The profile is top right on a
 * phone and in the sidebar on a desktop — never both at once.
 */

const SECTIONS = [
  { to: '/riepilogo', label: 'Riepilogo', Icon: House },
  { to: '/movimenti', label: 'Movimenti', Icon: Receipt },
  { to: '/conti', label: 'Conti', Icon: Landmark },
  { to: '/categorie', label: 'Categorie', Icon: Tags },
  { to: '/analisi', label: 'Analisi', Icon: ChartColumn },
]

const PROFILE = { to: '/profilo', label: 'Profilo', Icon: User }

export function AppShell() {
  // The sheet lives here rather than on a page: the + has to work from every
  // section, and recording a spend must not cost a navigation there and back.
  const [recording, setRecording] = useState(false)

  return (
    <div className="min-h-full bg-bg-app">
      <Sidebar />
      <MobileHeader />

      {/* The margin clears the fixed sidebar; the inner box is what gets
          centred, so the content sits in the middle of the space that is
          actually left rather than in the middle of the window. On mobile the
          top padding clears the header and the bottom one the tab bar with the
          button floating above it. */}
      <main className="pb-28 pt-20 sm:ml-[212px] sm:pb-12 sm:pt-10">
        {/* ⚠️ Twelve on a phone, not sixteen. On 390px every pixel of margin
            is a pixel the name of a movement does not get, and the names were
            being truncated with empty space next to them. Desktop keeps its
            room: there the width is not scarce. */}
        <div className="mx-auto w-full max-w-[900px] px-3 sm:px-8">
          <Outlet />
        </div>
      </main>

      <AddButton onClick={() => setRecording(true)} />
      <TabBar />

      {recording ? <TransactionSheet movement={null} onClose={() => setRecording(false)} /> : null}
    </div>
  )
}

function Sidebar() {
  return (
    <aside className="fixed inset-y-0 left-0 hidden w-[212px] flex-col gap-1 border-r border-border-soft bg-bg-raise px-3 py-6 sm:flex">
      <div className="px-3 pb-4">
        <Wordmark />
      </div>

      {[...SECTIONS, PROFILE].map(({ to, label, Icon }) => (
        <NavLink key={to} to={to} className={sidebarLink}>
          <Icon size={20} strokeWidth={2} aria-hidden />
          {label}
        </NavLink>
      ))}
    </aside>
  )
}

function sidebarLink({ isActive }: { isActive: boolean }): string {
  return [
    'flex items-center gap-3 rounded-control px-3 py-2.5 text-body transition-colors duration-200',
    isActive
      ? 'bg-surface-selected text-accent'
      : 'text-ink-2 hover:bg-surface-hover hover:text-ink-1',
  ].join(' ')
}

/** Phone only: the wordmark, and the way to the profile.
 *
 * Fixed, because it is the one control that has to be reachable from every
 * screen without scrolling back to the top of a long list of movements.
 */
function MobileHeader() {
  return (
    <header className="fixed inset-x-0 top-0 z-30 flex h-14 items-center justify-between border-b border-border-soft bg-bg-raise/90 px-4 backdrop-blur-[12px] sm:hidden">
      <Wordmark />

      <NavLink
        to={PROFILE.to}
        aria-label={PROFILE.label}
        title={PROFILE.label}
        className={({ isActive }) =>
          [
            'grid size-10 place-items-center rounded-pill transition-colors duration-200',
            isActive ? 'bg-surface-selected text-accent' : 'text-ink-2 hover:bg-surface-hover',
          ].join(' ')
        }
      >
        <PROFILE.Icon size={22} strokeWidth={2} aria-hidden />
      </NavLink>
    </header>
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
 * Sits above the tab bar on mobile and bottom-right on desktop, and opens the
 * sheet over whatever you were looking at.
 */
function AddButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label="Aggiungi un movimento"
      title="Aggiungi un movimento"
      className="fixed bottom-20 right-4 z-40 grid size-14 place-items-center rounded-pill bg-accent text-ink-on-accent shadow-glow-accent transition-colors duration-200 hover:bg-accent-hover active:bg-accent-press sm:bottom-8 sm:right-8"
    >
      <Plus size={26} strokeWidth={2} aria-hidden />
    </button>
  )
}
