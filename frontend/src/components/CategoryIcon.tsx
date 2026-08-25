import {
  Baby,
  Banknote,
  BookOpen,
  Bus,
  Car,
  Coffee,
  Dumbbell,
  Ellipsis,
  Film,
  Fuel,
  Gift,
  GraduationCap,
  HeartPulse,
  House,
  PawPrint,
  Pill,
  Plane,
  Repeat,
  Shirt,
  ShoppingCart,
  Smartphone,
  UtensilsCrossed,
  Wifi,
  Wrench,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

/** The curated icon set, mirrored from domain/vocabulary.py.
 *
 * Imported one by one rather than as a namespace so the bundle carries these
 * twenty-four and not the other fifteen hundred. The backend refuses a name
 * outside this list, which is what stops a category from rendering as nothing.
 */
export const CATEGORY_ICONS: Record<string, LucideIcon> = {
  ShoppingCart,
  House,
  Car,
  UtensilsCrossed,
  Coffee,
  HeartPulse,
  Pill,
  Dumbbell,
  Shirt,
  Gift,
  Plane,
  Bus,
  Fuel,
  Wrench,
  Smartphone,
  Wifi,
  Repeat,
  BookOpen,
  GraduationCap,
  Film,
  PawPrint,
  Baby,
  Banknote,
  Ellipsis,
}

export const CATEGORY_ICON_NAMES = Object.keys(CATEGORY_ICONS)

/** Colour tokens carry the name, not the value: `chart-3`, never a hex.
 *
 * Tailwind needs the class to appear literally somewhere to generate it, so the
 * six are written out here instead of built with a template string. */
const COLOR_CLASSES: Record<string, { text: string; tint: string }> = {
  'chart-1': { text: 'text-chart-1', tint: 'bg-chart-1/15' },
  'chart-2': { text: 'text-chart-2', tint: 'bg-chart-2/15' },
  'chart-3': { text: 'text-chart-3', tint: 'bg-chart-3/15' },
  'chart-4': { text: 'text-chart-4', tint: 'bg-chart-4/15' },
  'chart-5': { text: 'text-chart-5', tint: 'bg-chart-5/15' },
  'chart-6': { text: 'text-chart-6', tint: 'bg-chart-6/15' },
}

export function categoryColorClasses(color: string) {
  return COLOR_CLASSES[color] ?? COLOR_CLASSES['chart-1']
}

/** A category's badge: the icon on a tint of its colour, in a round container.
 *
 * Round because DESIGN.md gives categories the round container and transfers
 * the square one — the shape itself says which of the two you are looking at.
 */
export function CategoryIcon({
  icon,
  color,
  size = 20,
}: {
  icon: string
  color: string
  size?: number
}) {
  const Icon = CATEGORY_ICONS[icon] ?? Ellipsis
  const { text, tint } = categoryColorClasses(color)

  return (
    <span
      className={`grid size-10 shrink-0 place-items-center rounded-pill ${tint} ${text}`}
      aria-hidden
    >
      <Icon size={size} strokeWidth={2} />
    </span>
  )
}
