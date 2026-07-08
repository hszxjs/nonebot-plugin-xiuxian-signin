import { useEffect } from "react";

export type SaveState = "idle" | "saving" | "saved" | "error";
export type DirtyChangeHandler = (dirty: boolean) => void;

export function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

export function cloneJson<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

export function finiteNumber(value: unknown) {
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

export function hasUnsavedChanges<T>(draft: T | null, original: T | null) {
  if (!draft || !original) {
    return false;
  }
  return JSON.stringify(draft) !== JSON.stringify(original);
}

export function statusLabel(dirty: boolean, saveState: SaveState) {
  if (saveState === "saving") {
    return "保存中";
  }
  if (saveState === "saved") {
    return "已保存";
  }
  return dirty ? "未保存" : "同步";
}

export function confirmDiscard(message = "当前页面有未保存修改，确认切换吗？") {
  if (typeof window === "undefined") {
    return true;
  }
  return window.confirm(message);
}

export function useDirtyFlag(dirty: boolean, onDirtyChange?: DirtyChangeHandler) {
  useEffect(() => {
    onDirtyChange?.(dirty);
    return () => onDirtyChange?.(false);
  }, [dirty, onDirtyChange]);
}
