import { useState } from "react";
import { submitOnboarding } from "../api.js";

export default function Onboarding({ onAccess }) {
  const [mode, setMode] = useState(null); // null | "login" | "signup"
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [age, setAge] = useState("");
  const [city, setCity] = useState("");
  const [blockedMessage, setBlockedMessage] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const payload =
        mode === "signup"
          ? { username, password, name, age, city }
          : { username, password };
      const res = await submitOnboarding(payload);

      if (!res.allowed) {
        if (res.retry) {
          setError(res.message);
        } else {
          setBlockedMessage(res.message);
        }
      } else {
        onAccess({ sessionId: res.session_id, name: res.name || name });
      }
    } catch (err) {
      setError("Hubo un problema al iniciar. Intentá de nuevo.");
    } finally {
      setLoading(false);
    }
  }

  if (blockedMessage) {
    return (
      <div className="onboarding">
        <div className="onboarding__card">
          <div className="blocked-message">{blockedMessage}</div>
        </div>
      </div>
    );
  }

  // Initial screen: choose between login or signup.
  if (mode === null) {
    return (
      <div className="onboarding">
        <div className="onboarding__card">
          <h1 className="onboarding__title">Bienvenido/a</h1>
          <p className="onboarding__subtitle">
            ¿Ya tenés una cuenta acá, o es tu primera vez?
          </p>
          <button className="btn-primary" onClick={() => setMode("login")}>
            Ya tengo cuenta
          </button>
          <button
            className="btn-secondary"
            onClick={() => setMode("signup")}
          >
            Soy nuevo/a
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="onboarding">
      <div className="onboarding__card">
        <h1 className="onboarding__title">
          {mode === "login" ? "Iniciar sesión" : "Crear cuenta"}
        </h1>
        {mode === "signup" && (
          <p className="onboarding__subtitle">
            Solo necesitamos tu nombre y tu edad. Nada más — para no
            condicionar la conversación.
          </p>
        )}

        <form onSubmit={handleSubmit}>
          {mode === "signup" && (
            <div className="field">
              <label htmlFor="name">Nombre</label>
              <input
                id="name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                maxLength={80}
              />
            </div>
          )}

          <div className="field">
            <label htmlFor="username">Nombre de usuario</label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              minLength={3}
              maxLength={40}
            />
          </div>

          <div className="field">
            <label htmlFor="password">Contraseña</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={4}
              maxLength={100}
            />
          </div>

          {mode === "signup" && (
            <>
              <div className="field">
                <label htmlFor="age">Edad</label>
                <input
                  id="age"
                  type="number"
                  min="0"
                  max="120"
                  value={age}
                  onChange={(e) => setAge(e.target.value)}
                  required
                />
              </div>

              <div className="field">
                <label htmlFor="city">Ciudad (opcional)</label>
                <input
                  id="city"
                  type="text"
                  value={city}
                  onChange={(e) => setCity(e.target.value)}
                  maxLength={120}
                  placeholder="Nos ayuda a orientarte mejor si hace falta"
                />
                <div className="field-hint">
                  Solo se usa para poder sugerirte recursos de ayuda cercanos
                  si fuera necesario.
                </div>
              </div>
            </>
          )}

          <button className="btn-primary" type="submit" disabled={loading}>
            {loading
              ? "Ingresando..."
              : mode === "login"
              ? "Entrar"
              : "Comenzar"}
          </button>

          {error && <div className="error-message">{error}</div>}
        </form>

        <button
          className="chat__close-link"
          style={{ marginTop: 16, display: "block" }}
          onClick={() => {
            setMode(null);
            setError(null);
          }}
        >
          Volver
        </button>
      </div>
    </div>
  );
}