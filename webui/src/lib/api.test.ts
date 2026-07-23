import { describe, expect, it, vi } from "vitest"

import { apiErrorMessage, saveMysticConfig } from "@/lib/api"

function responseError(response: Response) {
  return Object.assign(new Error("request failed"), { response })
}

describe("apiErrorMessage", () => {
  it("uses the backend JSON error field", async () => {
    const response = new Response(
      JSON.stringify({ ok: false, error: "invalid json body" }),
      {
        status: 400,
        statusText: "Bad Request",
      },
    )

    await expect(apiErrorMessage(responseError(response))).resolves.toBe(
      "invalid json body",
    )
  })

  it("uses the backend JSON detail field", async () => {
    const response = new Response(JSON.stringify({ detail: "unauthorized" }), {
      status: 401,
      statusText: "Unauthorized",
    })

    await expect(apiErrorMessage(responseError(response))).resolves.toBe(
      "unauthorized",
    )
  })

  it("falls back to the response status when the body is not JSON", async () => {
    const response = new Response("not json", {
      status: 502,
      statusText: "Bad Gateway",
    })

    await expect(apiErrorMessage(responseError(response))).resolves.toBe(
      "Request failed (502 Bad Gateway)",
    )
  })

  it("falls back to a generic Error message", async () => {
    await expect(apiErrorMessage(new Error("network down"))).resolves.toBe(
      "network down",
    )
  })
})

describe("saveMysticConfig", () => {
  it("saves mystic configuration through the focused endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true, mystic: {} }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    )
    vi.stubGlobal("fetch", fetchMock)

    await saveMysticConfig({
      enabled_types: [],
      enabled_high_risk_types: [],
      map_size_rules: [],
      min_map_size: 24,
      max_map_size: 48,
      category_weights: {},
      drop_overrides: {},
      fishing_option_rate: 0,
    })

    const request = fetchMock.mock.calls[0]?.[0]
    expect(request).toBeInstanceOf(Request)
    expect((request as Request).url).toContain("/api/mystic")
    expect((request as Request).method).toBe("PUT")
    vi.unstubAllGlobals()
  })
})
