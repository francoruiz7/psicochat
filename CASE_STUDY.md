# PromptPsyco — Caso de estudio

Web conversacional para usar un LLM (vía API de OpenAI) como espacio de
apoyo terapéutico, con memoria persistente entre sesiones, detección de
riesgo y streaming de respuesta.

## El problema de diseño central

La tensión que organizó la mayoría de las decisiones técnicas fue esta:
**la interfaz debía sentirse como sesiones discretas** (la persona entra,
charla, se va, y la próxima vez arranca fresco — no quiere reabrir un chat
interminable pegado en la última frase de hace tres semanas), **pero el
sistema necesitaba memoria real** de todo lo hablado antes, para poder dar
continuidad genuina en vez de "amnesia" entre visitas.

La solución fue separar dos capas que suelen tratarse como una sola cosa:

- **Sesión** = la unidad de interfaz (un saludo fresco, un cierre explícito)
- **Perfil evolutivo** = un resumen acumulativo que persiste de fondo,
  regenerado por un modelo auxiliar al cerrar cada sesión, e inyectado en
  el system prompt de la sesión siguiente

Esto evita dos problemas a la vez: no hay que arrastrar el historial
completo (caro, y con el tiempo excede el contexto del modelo), y la
persona no tiene que "recontarle todo" al sistema cada vez que vuelve.

## Identidad sin cuenta completa

El proyecto es de uso personal, así que un sistema de autenticación
completo (email, recuperación de contraseña, verificación) hubiera sido
sobre-ingeniería. Se resolvió con un username + contraseña simple
(hasheada con PBKDF2-HMAC-SHA256 y salt, nunca en texto plano), suficiente
para que la memoria funcione entre dispositivos sin depender de
`localStorage` de un navegador puntual. Documentado explícitamente como
insuficiente si el proyecto se abriera a más de una persona.

## Seguridad como capas independientes, no como un único prompt

En vez de confiarle toda la responsabilidad de seguridad al modelo
conversacional principal (que tiene un system prompt largo y con mucho
matiz, optimizado para profundidad psicológica, no para seguridad), la
detección de riesgo corre como una **clasificación separada y
determinística** sobre cada mensaje, con un modelo más simple. Si se
detecta riesgo, la interfaz muestra un banner fijo con recursos de ayuda
— no depende de que el modelo principal "se acuerde" de mencionarlo bien
en su respuesta de texto libre. Las dos capas son independientes: si una
falla (ej. el clasificador tiene un error técnico), la otra sigue de pie.

## Costo bajo control sin sacrificar calidad

Con un system prompt de ~700 líneas, el costo de mandarlo en cada llamada
podía haber sido un problema. Dos decisiones lo resuelven:

1. El bloque estático del prompt va siempre idéntico y primero en cada
   llamada, para aprovechar el prompt caching de OpenAI (descuento fuerte
   sobre esa porción repetida). El resumen de perfil se agrega siempre
   después, nunca mezclado adentro, para no invalidar ese caching.
2. Las tareas auxiliares (resumen de sesión, clasificación de riesgo) usan
   un modelo más barato que el conversacional principal — no necesitan la
   misma profundidad.

## Streaming como decisión de producto, no solo técnica

En un espacio pensado para sostener una conversación emocionalmente
sensible, esperar en silencio a que aparezca un bloque de texto completo
se siente distinto a ver la respuesta construirse en tiempo real. Se
implementó streaming vía Server-Sent Events, con un endpoint alternativo
sin streaming (`/chat`) para debugging simple.

## Limitaciones conocidas (a propósito, no por descuido)

- Sin recuperación de contraseña — si se olvida, se pierde el acceso al
  perfil (aceptable para un único usuario).
- Los recursos de ayuda geolocalizados son un mapeo simple por palabras
  clave sobre texto libre, no geolocalización real.
- SQLite en un único archivo — adecuado para uso personal, no pensado
  para escalar a múltiples usuarios concurrentes.
- El modelo de costos asume que el dueño del proyecto paga su propia API
  key; no es un diseño pensado para abrir a otros usuarios sin agregar
  billing o un esquema BYOK.
