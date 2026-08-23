const CLIENT_ID_KEY = "labsafe_mom_client_id";

function createClientId(): string {
  const randomId =
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  return `client-${randomId}`;
}

export function getClientId(): string {
  if (typeof window === "undefined") return "server";

  const existing = window.localStorage.getItem(CLIENT_ID_KEY);
  if (existing) return existing;

  const next = createClientId();
  window.localStorage.setItem(CLIENT_ID_KEY, next);
  return next;
}
