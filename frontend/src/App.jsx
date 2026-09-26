import { useState, useEffect, useRef } from "react";
import Onboarding from "./screens/Onboarding.jsx";
import Chat from "./screens/Chat.jsx";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export default function App() {
  const [session, setSession] = useState(null); // { sessionId, name }
  const sessionRef = useRef(null);

  useEffect(() => {
    sessionRef.current = session;
  }, [session]);

  // Fallback: if the person closes the tab/browser without pressing the
  // "Finalizar sesión de hoy" button, we still try to notify the backend
  // so it generates that session's summary. sendBeacon works even while
  // the page is being unloaded (unlike a regular fetch, which the
  // browser can cut off mid-flight).
  useEffect(() => {
    function handlePageHide() {
      const current = sessionRef.current;
      if (current?.sessionId && navigator.sendBeacon) {
        const blob = new Blob(
          [JSON.stringify({ session_id: current.sessionId })],
          { type: "application/json" }
        );
        navigator.sendBeacon(`${API_BASE}/session/close`, blob);
      }
    }
    window.addEventListener("pagehide", handlePageHide);
    return () => window.removeEventListener("pagehide", handlePageHide);
  }, []);

  if (!session) {
    return <Onboarding onAccess={setSession} />;
  }

  return (
    <Chat
      sessionId={session.sessionId}
      name={session.name}
      onEnd={() => setSession(null)}
    />
  );
}