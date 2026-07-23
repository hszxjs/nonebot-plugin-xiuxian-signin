import "@testing-library/jest-dom/vitest"
import React from "react"
import { vi } from "vitest"

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

Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

vi.mock("@ant-design/charts", () => ({
  Bar: ({ data }: { data?: Array<{ realm?: string; count?: number }> }) =>
    React.createElement(
      "div",
      { "data-testid": "realm-distribution-chart" },
      data?.map((item) => `${item.realm}:${item.count}`).join(", "),
    ),
}))
