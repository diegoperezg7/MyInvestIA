"use client";

import { usePriceFlash } from "@/hooks/usePriceFlash";

interface Props {
  value: number | undefined;
  children: React.ReactNode;
  className?: string;
}

export default function FlashCell({ value, children, className = "" }: Props) {
  const [flash, flashKey] = usePriceFlash(value);

  const flashClass = flash === "up" ? "flash-up" : flash === "down" ? "flash-down" : "";

  return (
    <span key={flashKey} className={`${flashClass} ${className}`}>
      {children}
    </span>
  );
}
