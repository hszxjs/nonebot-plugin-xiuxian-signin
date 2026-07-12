const numberFormatter = new Intl.NumberFormat("zh-CN")
const compactNumberFormatter = new Intl.NumberFormat("zh-CN", {
  notation: "compact",
  maximumFractionDigits: 1,
})
const percentFormatter = new Intl.NumberFormat("zh-CN", {
  style: "percent",
  maximumFractionDigits: 1,
})

export function formatNumber(value: unknown) {
  const number = Number(value)
  return Number.isFinite(number) ? numberFormatter.format(number) : "0"
}

export function formatCompactNumber(value: unknown) {
  const number = Number(value)
  return Number.isFinite(number) ? compactNumberFormatter.format(number) : "0"
}

export function formatPercent(value: unknown) {
  const number = Number(value)
  return Number.isFinite(number) ? percentFormatter.format(number) : "0%"
}

export function formatJson(value: unknown) {
  return JSON.stringify(value, null, 2)
}

export function clampRate(value: unknown) {
  const number = Number(value)
  if (!Number.isFinite(number)) {
    return 0
  }
  return Math.min(1, Math.max(0, number))
}

export function rateToSliderValue(value: unknown) {
  return [Math.round(clampRate(value) * 100)]
}

export function sliderValueToRate(value: number[]) {
  return Math.min(1, Math.max(0, Number(value[0] ?? 0) / 100))
}
