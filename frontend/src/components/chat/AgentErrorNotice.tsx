import type { AgentError } from "../../models/chat";

export function AgentErrorNotice({ errors }: { errors: AgentError[] }) {
  if (!errors.length) {
    return null;
  }

  return (
    <div className="mt-2 rounded-md border app-warning-box p-2 text-xs">
      {errors.map((error) => (
        <div key={`${error.agent}-${error.error_type}`}>
          {error.agent} ajani gecici olarak tamamlanamadi ({error.error_type}).
        </div>
      ))}
    </div>
  );
}
