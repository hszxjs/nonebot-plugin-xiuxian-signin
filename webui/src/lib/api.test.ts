import { describe, expect, it } from "vitest"

import { apiErrorMessage } from "@/lib/api"

function responseError(response: Response) {
  return Object.assign(new Error("request failed"), { response })
}

describe("apiErrorMessage", () => {
  it("uses the backend JSON error field", async () => {
    const response = new Response(JSON.stringify({ ok: false, error: "invalid json body" }), {
      status: 400,
      statusText: "Bad Request",
    })

    await expect(apiErrorMessage(responseError(response))).resolves.toBe("invalid json body")
  })

  it("uses the backend JSON detail field", async () => {
    const response = new Response(JSON.stringify({ detail: "unauthorized" }), {
      status: 401,
      statusText: "Unauthorized",
    })

    await expect(apiErrorMessage(responseError(response))).resolves.toBe("unauthorized")
  })

  it("falls back to the response status when the body is not JSON", async () => {
    const response = new Response("not json", {
      status: 502,
      statusText: "Bad Gateway",
    })

    await expect(apiErrorMessage(responseError(response))).resolves.toBe("Request failed (502 Bad Gateway)")
  })

  it("falls back to a generic Error message", async () => {
    await expect(apiErrorMessage(new Error("network down"))).resolves.toBe("network down")
  })
})
