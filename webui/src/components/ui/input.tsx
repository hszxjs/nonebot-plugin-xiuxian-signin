import type { InputHTMLAttributes } from "react";
import { twMerge } from "tailwind-merge";

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={twMerge(
        "h-9 w-full min-w-0 rounded-md border border-border bg-card px-3 text-sm text-card-foreground shadow-sm outline-none transition placeholder:text-muted-foreground focus:border-primary disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      {...props}
    />
  );
}
