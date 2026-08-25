import {
  Baby,
  Banknote,
  Beer,
  Bike,
  BookOpen,
  Briefcase,
  Bus,
  Cake,
  Camera,
  Car,
  Coffee,
  Coins,
  CreditCard,
  Droplet,
  Dumbbell,
  Ellipsis,
  Film,
  Flame,
  Fuel,
  Gamepad2,
  Gift,
  Glasses,
  GraduationCap,
  Hammer,
  Heart,
  HeartPulse,
  House,
  Key,
  Laptop,
  Music,
  Package,
  Palette,
  ParkingCircle,
  PawPrint,
  PiggyBank,
  Pill,
  Pizza,
  Plane,
  Repeat,
  Scissors,
  Shirt,
  ShoppingBag,
  ShoppingCart,
  Smartphone,
  Sofa,
  Sparkles,
  Stethoscope,
  Store,
  Ticket,
  Train,
  TrendingUp,
  Umbrella,
  UtensilsCrossed,
  Wifi,
  Wrench,
  Zap,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

/** The curated icon set, mirrored from domain/vocabulary.py.
 *
 * Imported one by one rather than as a namespace so the bundle carries these
 * fifty-six and not the other fifteen hundred. The backend refuses a name
 * outside this list, which is what stops a category from rendering as nothing.
 *
 * ⚠️ Grouped by theme, and the groups are what the picker pages through: eight
 * at a time with the group's name on screen. "Casa" tells you where you are in
 * a way "pagina 3 di 7" never will.
 */
export const ICON_GROUPS: { label: string; icons: string[] }[] = [
  { label: 'Casa', icons: ['House', 'Key', 'Zap', 'Droplet', 'Flame', 'Wifi', 'Sofa', 'Hammer'] },
  {
    label: 'Spesa e cibo',
    icons: ['ShoppingCart', 'ShoppingBag', 'UtensilsCrossed', 'Coffee', 'Pizza', 'Beer', 'Cake', 'Store'],
  },
  {
    label: 'Trasporti',
    icons: ['Car', 'Bus', 'Train', 'Bike', 'Fuel', 'Plane', 'ParkingCircle', 'Ticket'],
  },
  {
    label: 'Salute e cura',
    icons: ['HeartPulse', 'Pill', 'Stethoscope', 'Dumbbell', 'Scissors', 'Glasses', 'Baby', 'PawPrint'],
  },
  {
    label: 'Svago',
    icons: ['Film', 'Music', 'Gamepad2', 'Camera', 'BookOpen', 'GraduationCap', 'Palette', 'Sparkles'],
  },
  {
    label: 'Soldi e lavoro',
    icons: ['Banknote', 'Coins', 'PiggyBank', 'CreditCard', 'Briefcase', 'Laptop', 'TrendingUp', 'Repeat'],
  },
  {
    label: 'Altro',
    icons: ['Gift', 'Smartphone', 'Wrench', 'Package', 'Umbrella', 'Heart', 'Shirt', 'Ellipsis'],
  },
]

export const CATEGORY_ICONS: Record<string, LucideIcon> = {
  House,
  Key,
  Zap,
  Droplet,
  Flame,
  Wifi,
  Sofa,
  Hammer,
  ShoppingCart,
  ShoppingBag,
  UtensilsCrossed,
  Coffee,
  Pizza,
  Beer,
  Cake,
  Store,
  Car,
  Bus,
  Train,
  Bike,
  Fuel,
  Plane,
  ParkingCircle,
  Ticket,
  HeartPulse,
  Pill,
  Stethoscope,
  Dumbbell,
  Scissors,
  Glasses,
  Baby,
  PawPrint,
  Film,
  Music,
  Gamepad2,
  Camera,
  BookOpen,
  GraduationCap,
  Palette,
  Sparkles,
  Banknote,
  Coins,
  PiggyBank,
  CreditCard,
  Briefcase,
  Laptop,
  TrendingUp,
  Repeat,
  Gift,
  Smartphone,
  Wrench,
  Package,
  Umbrella,
  Heart,
  Shirt,
  Ellipsis,
}

/** Colour tokens carry the name, not the value: `chart-3`, never a hex.
 *
 * ⚠️ Tailwind needs the class to appear literally somewhere to generate it, so
 * the ten are written out here instead of built with a template string. The
 * first six are also the chart series; seven to ten exist only for categories.
 */
const COLOR_CLASSES: Record<string, { text: string; tint: string; dot: string }> = {
  'chart-1': { text: 'text-chart-1', tint: 'bg-chart-1/15', dot: 'bg-chart-1' },
  'chart-2': { text: 'text-chart-2', tint: 'bg-chart-2/15', dot: 'bg-chart-2' },
  'chart-3': { text: 'text-chart-3', tint: 'bg-chart-3/15', dot: 'bg-chart-3' },
  'chart-4': { text: 'text-chart-4', tint: 'bg-chart-4/15', dot: 'bg-chart-4' },
  'chart-5': { text: 'text-chart-5', tint: 'bg-chart-5/15', dot: 'bg-chart-5' },
  'chart-6': { text: 'text-chart-6', tint: 'bg-chart-6/15', dot: 'bg-chart-6' },
  'chart-7': { text: 'text-chart-7', tint: 'bg-chart-7/15', dot: 'bg-chart-7' },
  'chart-8': { text: 'text-chart-8', tint: 'bg-chart-8/15', dot: 'bg-chart-8' },
  'chart-9': { text: 'text-chart-9', tint: 'bg-chart-9/15', dot: 'bg-chart-9' },
  'chart-10': { text: 'text-chart-10', tint: 'bg-chart-10/15', dot: 'bg-chart-10' },
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
