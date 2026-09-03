import type { ReactNode } from "react";

type CardProps = {
  title?: string;
  children: ReactNode;
  className?: string;
  /** Başlığın varsayılan boyutunu (text-base) geçersiz kılmak için - tek bir
   * karta özel büyütme/küçültme gerektiğinde, tüm Card'ları etkilemeden. */
  titleClassName?: string;
};

export default function Card({ title, children, className = "", titleClassName = "" }: CardProps) {
  return (
    <section className={`rounded-xl border app-card p-5 shadow-sm ${className}`}>
      {title && (
        <h2 className={`mb-4 font-semibold app-heading ${titleClassName || "text-base"}`}>
          {title}
        </h2>
      )}
      {children}
    </section>
  );
}
