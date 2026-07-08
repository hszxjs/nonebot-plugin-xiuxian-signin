import type { HTMLAttributes, TdHTMLAttributes, ThHTMLAttributes } from "react";
import { twMerge } from "tailwind-merge";

export function Table({ className, ...props }: HTMLAttributes<HTMLTableElement>) {
  return <table className={twMerge("w-full caption-bottom text-sm", className)} {...props} />;
}

export function TableHeader({ className, ...props }: HTMLAttributes<HTMLTableSectionElement>) {
  return <thead className={twMerge("border-b border-border", className)} {...props} />;
}

export function TableBody({ className, ...props }: HTMLAttributes<HTMLTableSectionElement>) {
  return <tbody className={twMerge("[&_tr:last-child]:border-0", className)} {...props} />;
}

export function TableRow({ className, ...props }: HTMLAttributes<HTMLTableRowElement>) {
  return <tr className={twMerge("border-b border-border transition hover:bg-muted/60", className)} {...props} />;
}

export function TableHead({ className, ...props }: ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th
      className={twMerge("h-10 px-3 text-left align-middle text-xs font-medium text-muted-foreground", className)}
      {...props}
    />
  );
}

export function TableCell({ className, ...props }: TdHTMLAttributes<HTMLTableCellElement>) {
  return <td className={twMerge("px-3 py-2 align-middle text-sm", className)} {...props} />;
}
