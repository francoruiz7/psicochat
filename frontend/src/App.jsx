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

  // Respaldo: si la persona cierra la pestaña/navegador sin tocar el
  // botón "Finalizar sesión de hoy", igual intentamos avisarle al backend
  // para que genere el resumen de esa sesión. sendBeacon funciona incluso
  // cuando la página se está por descargar (a diferencia de un fetch
  // normal, que el navegador puede cortar a mitad de camino).
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