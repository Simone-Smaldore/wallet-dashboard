import type { InputHTMLAttributes } from 'react'

/** A labelled text input.
 *
 * ⚠️ `type="text"` even for amounts, with `inputMode="decimal"` to get the right
 * keyboard. Never `type="number"`: emptying the box turns the value into 0 and
 * it refills itself, so it can only be changed with the arrows — and the
 * browser's number field handles the Italian decimal comma differently
 * depending on the system language. The value is kept as a string and validated
 * separately; an empty box is reported, not corrected.
 */

interface FieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string
  hint?: string
  error?: string | null
}

export function Field({ label, hint, error, className = '', id, ...rest }: FieldProps) {
  const inputId = id ?? `field-${label.toLowerCase().replace(/\s+/g, '-')}`

  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={inputId} className="text-caption text-ink-2">
        {label}
      </label>
      <input
        id={inputId}
        type="text"
        className={[
          'min-h-11 w-full rounded-control border border-border-soft bg-surface-input px-4 py-3',
          'text-body text-ink-1 placeholder:text-ink-3',
          'transition-colors duration-200 focus:border-border-focus focus:outline-none',
          error ? 'border-danger' : '',
          className,
        ].join(' ')}
        {...rest}
      />
      {error ? <p className="text-caption text-danger">{error}</p> : null}
      {!error && hint ? <p className="text-caption text-ink-3">{hint}</p> : null}
    </div>
  )
}
