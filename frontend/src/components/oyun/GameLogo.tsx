"use client";

type Props = {
  size?: number;
};

export function GameLogo({ size = 40 }: Props) {
  return (
    <svg
      viewBox="0 0 48 48"
      width={size}
      height={size}
      aria-label="Şans Yatırımda logosu"
      role="img"
    >
      <circle cx="24" cy="24" r="23" fill="var(--color-panel-dark)" />

      {/* yükselen trend çizgisi */}
      <path
        d="M9 30 L18 21 L24 27 L39 12"
        fill="none"
        stroke="var(--color-cta)"
        strokeWidth="3.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path d="M31 12 L39 12 L39 20" fill="none" stroke="var(--color-cta)" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round" />

      {/* zar noktaları — şans unsuru */}
      <rect x="9" y="30" width="9" height="9" rx="2.2" fill="var(--color-on-primary)" />
      <circle cx="12" cy="33" r="1" fill="var(--color-panel-dark)" />
      <circle cx="15" cy="36" r="1" fill="var(--color-panel-dark)" />
      <circle cx="15" cy="33" r="1" fill="var(--color-panel-dark)" />
      <circle cx="12" cy="36" r="1" fill="var(--color-panel-dark)" />
    </svg>
  );
}