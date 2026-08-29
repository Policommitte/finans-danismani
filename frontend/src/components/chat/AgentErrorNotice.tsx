import type { AgentError } from "../../models/chat";

/**
 * Kismi basarisizlik uyarisi.
 *
 * `message` alani YALNIZCA gelistirme ortaminda dolu gelir (backend uretimde
 * gondermez). Gostermek onemli: "llm_error" tek basina hicbir sey soylemiyor,
 * gercek sebep ("Error code: 404 - model bulunamadi") ise tam burada.
 */
export function AgentErrorNotice({ errors }: { errors: AgentError[] }) {
  if (!errors.length) {
    return null;
  }

  return (
    <div className="mt-2 rounded-md border app-warning-box p-2 text-xs">
      {errors.map((error) => (
        <div key={`${error.agent}-${error.error_type}`}>
          <div>
            {error.agent} ajani gecici olarak tamamlanamadi ({error.error_type}).
          </div>
          {error.message ? (
            <div className="mt-1 font-mono text-[11px] opacity-80 break-words">{error.message}</div>
          ) : null}
        </div>
      ))}
    </div>
  );
}
