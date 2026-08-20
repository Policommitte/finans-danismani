import type { ReactNode } from "react";

type CardProps = {
  title?: string;
  children: ReactNode;
  className?: string;
};

export default function Card({ title, children, className = "" }: CardProps) {
  return (
    <section className={`rounded-xl border app-card p-5 shadow-sm ${className}`}>
      {title && <h2 className="mb-4 text-base font-semibold app-heading">{title}</h2>}
      {children}
    </section>
  );
}
