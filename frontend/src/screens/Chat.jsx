import { useState, useRef, useEffect } from "react";
import { streamChat, closeSession } from "../api.js";

export default function Chat({ sessionId, name, onEnd }) {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content: `Hola ${name || ""}. ¿Cómo estás hoy? ¿Qué te gustaría trabajar?`.trim(),
    },
  ]);
  const [input, setInput] = useState("");
  const [streamingText, setStreamingText] = useState(null); // null = no está respondiendo
  const [riskResources, setRiskResources] = useState(null);
  const [closing, setClosing] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [messages, streamingText]);

  async function handleSend() {
    const text = input.trim();
    if (!text || streamingText !== null || closing) return;

    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setInput("");
    setStreamingText("");

    let accumulated = "";

    await streamChat(
      { sessionId, message: text },
      {
        onRisk: (resources) => setRiskResources(resources),
        onToken: (chunk) => {
          accumulated += chunk;
          setStreamingText(accumulated);
        },
        onDone: () => {
          setMessages((prev) => [
            ...prev,
            { role: "assistant", content: accumulated },
          ]);
          setStreamingText(null);
        },
        onError: (message) => {
          setMessages((prev) => [
            ...prev,
            {
              role: "assistant",
              content:
                message || "No pude generar una respuesta. ¿Lo intentamos de nuevo?",
            },
          ]);
          setStreamingText(null);
        },
      }
    );
  }

  async function handleCloseSession() {
    if (closing) return;
    setClosing(true);
    try {
      await closeSession({ sessionId });
    } catch (err) {
      // No es bloqueante: igual volvemos al inicio.
    } finally {
      onEnd?.();
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  const canType = !closing && streamingText === null;

  return (
    <div className="chat">
      <div className="chat__header">
        <p className="chat__header-title">PsicoChat</p>
        <button
          className="chat__close-link"
          onClick={handleCloseSession}
          disabled={closing}
        >
          {closing ? "Guardando..." : "Finalizar sesión de hoy"}
        </button>
      </div>

      {riskResources && (
        <div className="chat__risk-banner">
          <strong>Si esto es urgente, no estás solo/a.</strong>
          <ul>
            {riskResources.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="chat__messages" ref={scrollRef}>
        {messages.map((m, i) => (
          <div key={i} className={`message message--${m.role}`}>
            {m.content}
          </div>
        ))}
        {streamingText !== null && (
          <div className="message message--assistant">
            {streamingText || "…"}
          </div>
        )}
      </div>

      <div className="chat__input-bar">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={canType ? "Escribí lo que estés pensando..." : ""}
          rows={1}
          disabled={!canType}
        />
        <button
          className="chat__send-btn"
          onClick={handleSend}
          disabled={!canType || !input.trim()}
        >
          Enviar
        </button>
      </div>
    </div>
  );
}