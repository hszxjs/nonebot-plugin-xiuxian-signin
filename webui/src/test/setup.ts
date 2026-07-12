import "@testing-library/jest-dom/vitest"

class ResizeObserverStub {
  observe() {
    return undefined
  }

  unobserve() {
    return undefined
  }

  disconnect() {
    return undefined
  }
}

globalThis.ResizeObserver = ResizeObserverStub
