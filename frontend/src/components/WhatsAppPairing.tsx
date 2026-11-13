import { useQuery } from "@tanstack/react-query";
import { getWhatsAppPairing } from "../api";

export function WhatsAppPairing() {
  const pairing = useQuery({
    queryKey: ["whatsapp-pairing"],
    queryFn: ({ signal }) => getWhatsAppPairing(signal),
    refetchInterval: 2000,
    gcTime: 0,
    retry: false,
  });
  const state = pairing.isError ? undefined : pairing.data;
  return (
    <div className="notice">
      <p role="status">WhatsApp: {state?.status ?? (pairing.isError ? "Settings unavailable" : "checking…")}</p>
      {state?.qr && (
        <>
          <p>On the demo phone, open WhatsApp → Linked Devices → Link a Device.</p>
          <img src={state.qr} width={320} height={320} style={{ maxWidth: "100%", height: "auto" }} alt="Scan to link the dedicated WhatsApp account" />
        </>
      )}
      {state?.status === "connected" && (
        <>
          <p>{state.dry_run ? "Dry-run is on." : "Live alerts are enabled."}</p>
          <p>Guardian consent: {state.guardian_enabled == null ? "unavailable" : state.guardian_enabled ? "active" : "waiting"}</p>
          {state.guardian_command && <p>Have the guardian send this command to the demo account: <code>{state.guardian_command}</code></p>}
        </>
      )}
    </div>
  );
}
