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

  it("appends field issues from config validation failures", async () => {
    const response = new Response(
      JSON.stringify({
        ok: false,
        error: "配置校验未通过",
        issues: [
          { path: "mystic.fishing_option_rate", message: "不能大于 1" },
          { path: "signin.extra_fishing_chance_rate", message: "必须是数字" },
        ],
      }),
      { status: 400, statusText: "Bad Request" },
    )

    await expect(apiErrorMessage(responseError(response))).resolves.toBe(
      "配置校验未通过：mystic.fishing_option_rate: 不能大于 1；signin.extra_fishing_chance_rate: 必须是数字",
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

  it("prefers ky's parsed error.data because ky already consumed the body", async () => {
    // ky v2 在抛出 HTTPError 前已读取响应体（bodyUsed=true），真实报错路径
    // 只能从 error.data 拿文案；这里复刻该形状，防止回归成 "Request failed (401)"。
    const response = new Response(
      JSON.stringify({ ok: false, error: "账号或密码不正确" }),
      {
        status: 401,
        headers: { "content-type": "application/json" },
      },
    )
    await response.text()
    const error = Object.assign(
      new Error("Request failed with status code 401"),
      {
        name: "HTTPError",
        response,
        data: { ok: false, error: "账号或密码不正确" },
      },
    )

    await expect(apiErrorMessage(error)).resolves.toBe("账号或密码不正确")
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
