import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

// Node 26 exposes an unavailable experimental global localStorage. Supply the
// browser Storage contract explicitly for the jsdom test environment.
class MemoryStorage implements Storage {
  private values = new Map<string, string>()
  get length() { return this.values.size }
  clear() { this.values.clear() }
  getItem(key: string) { return this.values.get(key) ?? null }
  key(index: number) { return Array.from(this.values.keys())[index] ?? null }
  removeItem(key: string) { this.values.delete(key) }
  setItem(key: string, value: string) { this.values.set(key, value) }
}

// Edge-function tests run in the node environment, which has no window.
if (typeof window !== 'undefined') {
  Object.defineProperty(window, 'localStorage', { configurable: true, value: new MemoryStorage() })
}

afterEach(() => cleanup())
