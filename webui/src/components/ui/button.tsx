import type { ButtonHTMLAttributes } from "react";
import { twMerge } from "tailwind-merge";

export function Button({ className, type = "button", ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={twMerge(
        "inline-flex h-9 max-w-full items-center justify-center gap-2 overflow-hidden rounded-md border border-border bg-card px-3 text-sm font-medium text-card-foreground shadow-sm transition hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      type={type}
      {...props}
    />
  );
}

export function PrimaryButton({ className, ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <Button
      className={twMerge("border-primary bg-primary text-primary-foreground hover:bg-primary/90", className)}
      {...props}
    />
  );
}
