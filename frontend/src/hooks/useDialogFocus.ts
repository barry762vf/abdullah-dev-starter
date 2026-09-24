import { useEffect, useRef, type KeyboardEvent } from 'react'

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'

/**
 * Modal focus behaviour shared by the mobile drawer and admin dialogs: focus the first button on
 * open, keep Tab inside, close on Escape, and return focus to the opener when the dialog unmounts.
 */
export function useDialogFocus<T extends HTMLElement>(close: () => void) {
  const ref = useRef<T>(null)

  useEffect(() => {
    const opener = document.activeElement instanceof HTMLElement ? document.activeElement : null
    // Start on the first button (the Close control in both drawer and dialogs), else any control.
    const start = ref.current?.querySelector<HTMLElement>('button:not([disabled])') ?? ref.current?.querySelector<HTMLElement>(FOCUSABLE)
    start?.focus()
    return () => opener?.focus()
  }, [])

  function onKeyDown(event: KeyboardEvent<T>) {
    if (event.key === 'Escape') {
      event.preventDefault()
      close()
      return
    }
    if (event.key !== 'Tab' || !ref.current) return
    const items = Array.from(ref.current.querySelectorAll<HTMLElement>(FOCUSABLE))
    const first = items[0]
    const last = items[items.length - 1]
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault()
      last?.focus()
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault()
      first?.focus()
    }
  }

  return { ref, onKeyDown }
}
