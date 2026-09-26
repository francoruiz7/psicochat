# PromptPsyco

Web para conversar con una IA (vía API de OpenAI) como espacio de apoyo
terapéutico. Onboarding mínimo (nombre + edad, sin condicionar el sistema
con más datos), sesiones separadas por día pero con memoria de fondo entre
sesiones.

Ver también [`CASE_STUDY.md`](./CASE_STUDY.md) — resumen de decisiones de
diseño en formato portfolio.

## Estado: las 4 fases completas

**Fase 1 — núcleo funcional:**
- Backend FastAPI con gate de edad (`/onboarding`) y endpoint de chat (`/chat`)
- El system prompt vive en `backend/prompts/system_prompt.txt`
- Frontend React (Vite) con dos pantallas: onboarding y chat

**Fase 2 — memoria y continuidad:**
- Campo `username` + `password` en el onboarding: identifican tu perfil
  evolutivo entre sesiones y entre dispositivos. La contraseña se guarda
  hasheada (PBKDF2-HMAC-SHA256 con salt) — nunca en texto plano. La
  primera vez que usás un username, esa contraseña queda fijada; las
  siguientes veces tenés que repetirla o el sistema rechaza el acceso.
- Perfil evolutivo por `username`, con `profile_summary` actualizado al
  cerrar cada sesión.
- Botón "Finalizar sesión de hoy" + respaldo automático vía
  `navigator.sendBeacon` si se cierra la pestaña sin tocar el botón.
- El `profile_summary` se agrega siempre DESPUÉS del bloque estático del
  system prompt, para no romper el prompt caching de OpenAI.

**Fase 3 — riesgo, robustez y streaming:**
- **Detección de riesgo** (`backend/app/risk.py`): cada mensaje se
  clasifica con el modelo auxiliar (barato) para detectar señales de
  autolesión, ideación suicida, riesgo hacia terceros o peligro
  inmediato. Es una capa ADICIONAL a lo que ya pide el propio system
  prompt en su sección "CUANDO ESTÉ MUY ANGUSTIADO" — no la reemplaza. Si
  el clasificador falla técnicamente, no bloquea la conversación
  (fail-safe).
- **Recursos de ayuda geolocalizados** (`backend/app/resources.py`): si se
  detecta riesgo, se arma una lista de recursos según la ciudad cargada en
  el onboarding (mapeo simple por palabras clave — hoy solo distingue
  Argentina de un fallback genérico internacional). Se muestra como
  banner fijo en la interfaz, no solo como texto del modelo.
- **Streaming de respuesta** (`POST /chat/stream`): la respuesta se
  muestra token a token vía Server-Sent Events. Sigue existiendo
  `POST /chat` sin streaming como alternativa simple para debugging.
- **Manejo de errores**: timeout configurable en las llamadas a OpenAI,
  mensajes amigables si la API falla, sin romper la sesión.

**Fase 4 — SQLite y deploy:**
- Storage migrado de JSON plano a **SQLite** (`backend/promptpsyco.db`,
  un solo archivo), con la misma interfaz pública que ya usaba el resto
  del código — no hizo falta tocar `chat.py`.
- `Procfile` y `render.yaml` para desplegar el backend en Render o
  Railway.
- Preparado para desplegar el frontend en Vercel (detecta Vite
  automáticamente, sin configuración extra más que la variable de
  entorno).

## Cómo correrlo local

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # en Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# completar OPENAI_API_KEY en .env
uvicorn main:app --reload --port 8000
```

Al arrancar, se crea automáticamente `backend/promptpsyco.db` (SQLite) si
no existe — no hace falta ningún paso manual de migración.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Abrir `http://localhost:5173`.

## Cómo probar todo (paso a paso)

1. Levantar backend y frontend (pasos de arriba).
2. Completar el onboarding con nombre, un nombre de usuario, una
   contraseña, tu edad, y opcionalmente tu ciudad.
3. Mandar un par de mensajes — la respuesta debería ir apareciendo
   palabra por palabra (streaming), no de golpe.
4. Click en "Finalizar sesión de hoy".
5. Recargar la página (`F5`) y volver a entrar con el **mismo usuario y
   contraseña**. En el próximo mensaje, mencionar algo relacionado a lo
   hablado antes — el modelo debería poder retomarlo (memoria entre
   sesiones funcionando).
6. Probar entrar con el username correcto pero una contraseña distinta —
   tiene que rechazar el acceso.
7. Escribir un mensaje con una señal de riesgo explícita — debería
   aparecer el banner de recursos de ayuda arriba de los mensajes, además
   de la respuesta normal del modelo. Probar también una frase claramente
   no literal ("esto me mata de la risa") para confirmar que no dispara
   el banner sin necesidad.
8. Revisar `backend/promptpsyco.db` con cualquier visor de SQLite (por
   ejemplo, la extensión "SQLite Viewer" de VS Code, o `sqlite3
   promptpsyco.db` desde la terminal) para ver las tablas `profiles`,
   `sessions` y `messages`.

## Cómo desplegarlo (cuando quieras mostrarlo público)

### Backend (Render o Railway)

- **Render**: conectar el repo, elegir la carpeta `backend/` como raíz del
  servicio. `render.yaml` ya deja definidas las variables de entorno
  (`OPENAI_API_KEY` hay que cargarla a mano en el dashboard, nunca en el
  repo). **Importante**: el plan gratuito de Render tiene filesystem
  efímero — el archivo `promptpsyco.db` se pierde en cada redeploy o
  reinicio, salvo que agregues un disco persistente (función paga). Para
  una demo de portfolio esto puede ser aceptable; para uso real hay que
  sumar el disco o migrar a una base de datos gestionada.
- **Railway**: detecta automáticamente el `Procfile`. Los volúmenes
  persistentes de Railway sí están disponibles en su plan gratuito con
  límites — mejor opción si querés que el SQLite sobreviva a reinicios
  sin pagar de entrada.

### Frontend (Vercel)

- Conectar el repo, elegir la carpeta `frontend/` como raíz. Vercel
  detecta Vite automáticamente.
- Configurar la variable de entorno `VITE_API_BASE` en el dashboard de
  Vercel, apuntando a la URL pública del backend ya desplegado.
- En el backend, actualizar `FRONTEND_ORIGIN` a la URL de Vercel (para que
  el CORS lo permita).

## Sobre el costo (uso personal, con API key propia)

- El system prompt (~5.000 tokens) se manda en cada llamada, pero OpenAI
  cachea automáticamente el prefijo estático repetido entre llamadas
  (grandes descuentos sobre esa porción) — por eso el resumen de perfil se
  agrega siempre DESPUÉS del bloque fijo, nunca mezclado adentro.
- El resumen de sesión y la detección de riesgo usan el modelo más
  barato (`gpt-4o-mini`), no el modelo principal.
- Para uso personal esporádico, el gasto total estimado es de pocos
  dólares por mes. El límite de gasto mensual en el dashboard de OpenAI
  es buena práctica igual, por las dudas.

## Decisiones de diseño a tener presentes

- **Nombre y edad únicamente en el onboarding**: decisión deliberada para no
  condicionar al sistema con información de más.
- **Menor de edad → no arranca**: si la edad ingresada es menor a 18, no se
  crea sesión ni perfil, ni se guarda ningún dato del intento.
- **Sesión (UI) vs. memoria (contexto)**: cada ingreso es una sesión nueva
  visualmente (saludo fresco), pero de fondo el sistema acumula un perfil
  evolutivo a partir de resúmenes de sesiones anteriores.
- **API key propia, no escalable a otros usuarios**: aceptado a propósito
  para esta etapa (portfolio / uso personal). Evaluar a futuro membresía
  paga (Stripe) o que cada usuario cargue su propia key (BYOK).
- **Username + contraseña sin recuperación**: suficiente para uso
  personal; sin auth real si el proyecto se abriera a más gente.
- **Ciudad opcional en onboarding**: para poder sugerir recursos de ayuda
  geolocalizados sin pedir ubicación exacta del navegador.
