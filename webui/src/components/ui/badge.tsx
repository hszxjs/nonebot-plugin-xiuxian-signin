import type { HTMLAttributes } from "react";
import { twMerge } from "tailwind-merge";

export function Badge({ className, ...props }: HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={twMerge(
        "inline-flex max-w-full items-center rounded-sm border border-border bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground",
        className,
      )}
      {...props}
    />
  );
}
