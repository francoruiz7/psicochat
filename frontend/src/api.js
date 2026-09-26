const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export async function submitOnboarding({ username, password, name, age, city }) {
  const res = await fetch(`${API_BASE}/onboarding`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      username,
      password,
      name: name || null,
      age: age !== undefined && age !== "" ? Number(age) : null,
      city: city || null,
    }),
  });
  if (!res.ok) throw new Error("No se pudo iniciar la sesión");
  return res.json();
}

export async function closeSession({ sessionId }) {
  const res = await fetch(`${API_BASE}/session/close`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId }),
  });
  if (!res.ok) throw new Error("No se pudo cerrar la sesión");
  return res.json();
}

/**
 * Consumes the /chat/stream endpoint (Server-Sent Events over POST).
 * callbacks: { onToken(text), onRisk(resources), onDone(riskFlag), onError(message) }
 */
export async function streamChat({ sessionId, message }, callbacks) {
  const res = await fetch(`${API_BASE}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message }),
  });

  if (!res.ok || !res.body) {
    callbacks.onError?.("No se pudo conectar con el servidor.");
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let boundary;
    while ((boundary = buffer.indexOf("\n\n")) !== -1) {
      const rawEvent = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      handleRawEvent(rawEvent, callbacks);
    }
  }
}

function handleRawEvent(rawEvent, callbacks) {
  const lines = rawEvent.split("\n");
  let eventType = "message";
  let dataStr = "";
  for (const line of lines) {
    if (line.startsWith("event:")) eventType = line.slice(6).trim();
    if (line.startsWith("data:")) dataStr += line.slice(5).trim();
  }
  if (!dataStr) return;

  let data;
  try {
    data = JSON.parse(dataStr);
  } catch {
    return;
  }

  if (eventType === "token") callbacks.onToken?.(data.text);
  if (eventType === "risk") callbacks.onRisk?.(data.resources);
  if (eventType === "done") callbacks.onDone?.(data.risk_flag);
  if (eventType === "error") callbacks.onError?.(data.message);
}