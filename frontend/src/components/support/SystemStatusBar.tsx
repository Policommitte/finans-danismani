"use client";

export type SystemService = {
  name: string;
  operational: boolean;
};

/**
 * Mock veri. Ileride gercek bir health-check endpoint'ine baglanacaksa, bu
 * dizi bir useAsyncData/useEffect ile doldurulup ayni sekilde render edilebilir -
 * bilesenin geri kalani zaten operational bayragina gore calisir.
 */
const services: SystemService[] = [
  { name: "BIST Veri Akışı", operational: true },
  { name: "Bülten Bildirim Servisi", operational: true },
  { name: "Yapay Zeka Asistanı", operational: true },
];

function StatusDot({ operational, pulse = false }: { operational: boolean; pulse?: boolean }) {
  const color = operational ? "var(--color-success)" : "var(--color-danger)";

  return (
    <span className="relative flex h-2.5 w-2.5 shrink-0">
      {pulse && (
        <span
          className="absolute inline-flex h-full w-full animate-ping rounded-full opacity-75"
          style={{ background: color }}
        />
      )}
      <span className="relative inline-flex h-2.5 w-2.5 rounded-full" style={{ background: color }} />
    </span>
  );
}

export function SystemStatusBar() {
  const allOperational = services.every((service) => service.operational);

  return (
    <div className="flex flex-wrap items-center gap-x-6 gap-y-2 rounded-xl border app-card px-4 py-2.5 text-sm shadow-sm">
      <div className="flex items-center gap-2">
        <StatusDot operational={allOperational} pulse />
        <span className="font-medium app-heading">
          {allOperational ? "Tüm sistemler çalışır durumda" : "Sorun yaşanıyor"}
        </span>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {services.map((service) => (
          <span
            key={service.name}
            className="inline-flex items-center gap-1.5 rounded-full app-card-muted px-2.5 py-1 text-xs app-muted"
          >
            <StatusDot operational={service.operational} />
            {service.name}
          </span>
        ))}
      </div>
    </div>
  );
}
