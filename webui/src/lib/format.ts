export function formatNumber(value: number | string | null | undefined) {
  const number = Number(value ?? 0);
  return Number.isFinite(number) ? number.toLocaleString("zh-CN") : "0";
}

export function percent(value: number) {
  return `${Math.round(value * 100)}%`;
}

export function compactDate(value: string | null | undefined) {
  if (!value) {
    return "未记录";
  }
  return value.slice(0, 10);
}
