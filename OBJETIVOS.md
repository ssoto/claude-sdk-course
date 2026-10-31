# Objetivos del taller

## Bloque 1 · Bases de la API de Claude

Este bloque va enfocado a ver el comportamiento de la API. Aprenderemos cómo es su funcionamiento básico, con cuestiones como que la API no tiene memoria, que cada llamada es independiente o que el historial de la conversación se gestiona (y se paga) desde nuestro código.

### 1.1 · Primera llamada

Empezamos por lo imprescindible: dejar el entorno preparado y hacer la primera llamada a la API. A partir de ahí aprenderemos a leer la respuesta completa y no solo el texto, viendo qué bloques trae, por qué se detiene el modelo y cuántos tokens consume.

- Preparar el entorno en VS Code (`.venv`, dependencias, `.env`) y comprobarlo con `00-comprobar-entorno`, incluido el error más habitual: el kernel equivocado.
- Hacer la primera llamada con `client.messages.create` e inspeccionar el objeto completo: `content` es una lista de bloques (`thinking`, `text`), `stop_reason` dice por qué paró y `usage` cuenta los tokens.
- Extraer el texto filtrando los bloques por tipo, no tratando `content` como un string.
- Añadir un `system` prompt y comparar las dos respuestas: el `system` define **quién es** el modelo; `messages` es **la conversación**.

### 1.2 · El chat que se olvida de ti

Aquí convertimos las llamadas sueltas en una conversación. Un chat que falla a propósito nos mostrará que la API no recuerda los turnos anteriores; después le daremos memoria guardando y reenviando el historial, y mostraremos la respuesta en streaming.

- Escribir un chat ingenuo que solo envía la última pregunta y ver cómo falla: no recuerda el nombre ni la factura del turno anterior.
- Entender por qué: cada llamada es una petición HTTP aislada y solo cuenta lo que se envía.
- Arreglarlo con una lista `messages` que guarda todos los turnos (incluido `response.content` completo) y se reenvía en cada llamada.
- Inspeccionar `messages` (y el panel **Variables**) y ver cómo `input_tokens` crece en cada turno: cada turno paga de nuevo todo lo anterior.
- Añadir streaming para ver la respuesta mientras se genera, sin cambiar el modelo mental: al final se guarda el mensaje completo igual que antes.

### 1.3 · Tokens, contexto e imágenes

Con el historial ya funcionando, toca controlar cuánto crece. Mediremos los tokens, detectaremos respuestas cortadas y recortaremos la conversación cuando haga falta. También comprobaremos que una imagen es solo otro tipo de bloque, con su propio coste.

- Contar tokens **antes** de enviar con `count_tokens` (frente a `usage`, que llega **después**).
- Provocar una respuesta cortada con un `max_tokens` bajo, reconocerla por `stop_reason == "max_tokens"` y avisar de ello en `chat()`.
- Limitar el historial con una ventana deslizante (`recortar()`) y vaciarlo con `reset()`, y comparar esta estrategia con resumir lo antiguo.
- Enviar una imagen como bloque `image` en base64 y medir cuántos tokens añade, que se siguen pagando en cada turno siguiente.
- Convertir todo lo construido en un CLI conversacional con un bucle de `input()` en una sola celda.

## Bloque 2 · Tool use: el paso a agente

Es el momento en que el modelo deja de limitarse a responder y empieza a **actuar**. Descubriremos qué son las herramientas, que el modelo únicamente *pide* acciones y que tanto el bucle como la ejecución de esas acciones son cosa de nuestro código.

### 2.1 · Anatomía de una herramienta

¿Qué es una herramienta desde el punto de vista del modelo? Responderemos a esta pregunta viendo cómo se define, comprobando que el modelo nunca la ejecuta por sí mismo y completando a mano, paso a paso, una vuelta de petición y resultado.

- Comprobar que, sin herramientas, el modelo se inventa los datos o dice que no los tiene.
- Definir `buscar_incidencias` con sus tres partes: **nombre**, **descripción** (lo que el modelo lee para decidir, y que funciona como un prompt) y **esquema** JSON de los parámetros.
- Ver que la respuesta llega con `stop_reason: tool_use` y un bloque `tool_use`: el modelo **pide** la búsqueda, no la hace.
- Cerrar la vuelta a mano, paso a paso: ejecutar la función, guardar el turno `assistant`, devolver un `tool_result` enlazado por `tool_use_id` y volver a llamar hasta obtener la respuesta final.

### 2.2 · El bucle desde cero

Lo que en el apartado anterior hicimos a mano, ahora lo automatizamos. Programaremos desde cero el bucle de un agente, veremos al modelo encadenar herramientas según lo que va encontrando y lo romperemos a propósito para entender sus puntos frágiles.

- Añadir una segunda herramienta (`crear_incidencia`) y un mapa de despacho de nombre a función.
- Escribir `ejecutar_agente()`: un bucle que llama, ejecuta las herramientas pedidas y devuelve los resultados hasta que el modelo termina.
- Las cuatro decisiones de diseño del bucle: guardar todo `response.content`, devolver varios `tool_result` en un único mensaje, devolver los errores al modelo con `is_error` para que se corrija, y limitar las iteraciones.
- Ver al modelo encadenar `buscar_incidencias` → `crear_incidencia` y, al repetir la pregunta, encontrar la incidencia sin crear un duplicado: la ruta la decide el modelo, no el código.
- Romper el bucle a propósito (quitar el turno `assistant`, cambiar un `tool_use_id`) para entender los errores 400 más comunes.

### 2.3 · Caching y salida estructurada

Dos técnicas para acercar el agente a producción. Por un lado, la caché, que abarata lo que se repite en cada llamada; por otro, la salida estructurada, que nos da un resultado validado que otro programa puede consumir.

- Activar el prompt caching con `cache_control` sobre un system prompt largo y comparar `cache_creation_input_tokens` y `cache_read_input_tokens` entre ejecuciones.
- Entender que la caché es un **prefijo** (`tools` → `system` → `messages`): cambiar un solo byte, como meter la fecha en el system, la invalida.
- Pedir el resultado final en un formato fijo con un modelo Pydantic y `messages.parse`, y recibir un objeto Python validado en lugar de texto libre.

## Bloque 3 · Del loop manual al Agent SDK

Damos el salto al Agent SDK, pero sin tratarlo como una caja negra. La idea es comprobar que supone un ahorro real de trabajo, porque todo lo que hace por dentro ya lo hemos programado a mano en el bloque 2.

### 3.1 · El mismo agente, en una fracción del código

Reescribimos con el SDK el agente del bloque anterior y ponemos las dos versiones lado a lado. Así se ve claramente cómo desaparece el código frágil del bucle manual y qué control cedemos a cambio.

- Portar las herramientas con `@tool` y `create_sdk_mcp_server` sin cambiar las funciones de negocio.
- Configurar el agente con `ClaudeAgentOptions` y ejecutarlo con `query()` usando `async for` directamente en la celda (sin `asyncio.run`).
- Inspeccionar los mensajes que emite el SDK (`SystemMessage`, `AssistantMessage`, `UserMessage`, `ResultMessage`): es la misma secuencia que el historial del bloque 2.
- Entender el nombre de las herramientas: `mcp__<servidor>__<herramienta>`.
- Comparar los dos agentes lado a lado: el bucle, los `append`, los `tool_use_id`, el manejo de errores y el límite de iteraciones los resuelve ahora el SDK.
- Saber qué se cede (control fino del bucle) y cuándo sigue teniendo sentido la API directa.

### 3.2 · Qué hace el SDK por ti

¿Qué hace el SDK por nosotros? Mantener conversaciones con contexto entre turnos, para empezar. Además repasaremos sus opciones de configuración y trataremos los permisos como una pieza de diseño del agente, no como algo que se añade al final.

- Mantener una conversación con `ClaudeSDKClient`, un turno por celda, y repetir la prueba de «¿cómo me llamo?» del bloque 1: ahora recuerda.
- Distinguir `query()` (una tarea y fin) de `ClaudeSDKClient` (conversación con estado).
- Ver que el historial sigue existiendo y costando, pero lo gestiona el SDK, que además lo compacta cuando se acerca al límite.
- Limitar las iteraciones con `max_turns` y reconocer el error `error_max_turns`.
- Repasar las opciones principales: `system_prompt`, `model`, `cwd`, `allowed_tools`, `disallowed_tools`, `permission_mode` y `setting_sources=[]`.
- Aplicar permisos en tres capas (`disallowed_tools`, `allowed_tools`, `permission_mode` / `can_use_tool`) y ver cómo un callback deniega borrar un fichero.

## Bloque 4 · Capacidades avanzadas del SDK

En este bloque el agente de soporte crece. Cada problema real que le surja nos servirá para presentar una capacidad avanzada del SDK: herramientas propias, servidores MCP externos, subagentes, hooks y sesiones.

### 4.1 · Herramientas con `@tool` y MCP in-process

Una herramienta mal definida es la causa más común de que un agente haga cosas raras. Por eso aprenderemos a convertir funciones de Python en herramientas con esquemas claros, errores que ayudan al modelo a corregirse y metadatos, y a agruparlas en un servidor MCP in-process.

- Definir herramientas con `@tool` y elegir la forma del esquema: mapa de tipos, JSON Schema completo (enums, campos opcionales, descripciones por campo) o `TypedDict`.
- Escribir errores que digan al modelo **qué hacer a continuación** y verlo corregirse solo al pedir cerrar una incidencia que no existe.
- Añadir anotaciones (`readOnlyHint`, `destructiveHint`) como metadatos para el agente y para las políticas de permisos.
- Agrupar las herramientas en un servidor MCP in-process: corre dentro del propio programa Python, sin procesos aparte ni red.

### 4.2 · Servidores MCP externos

No hace falta reescribir integraciones que ya existen. Conectaremos un servidor MCP externo junto a nuestras herramientas y veremos con qué criterio elegir cuáles de sus herramientas habilitar.

- Entender la diferencia entre un servidor in-process y uno externo (otro proceso, por stdio o HTTP): para el agente no cambia nada.
- Conectar un servidor de sistema de ficheros por stdio apuntando a la base de conocimiento, con una ruta absoluta.
- Listar las herramientas que expone el servidor y habilitar solo las necesarias.
- Ver al agente buscar en la base de conocimiento y citar el artículo adecuado.

### 4.3 · Subagentes

Cuando el agente principal hace de todo, su contexto se llena de ruido y decide peor. La solución que veremos son los subagentes: especialistas en los que delegar tareas concretas. También hablaremos de cuándo compensa usarlos y cuándo no.

- Definir un subagente `clasificador` con sus cuatro piezas: `description` (cuándo usarlo), `prompt`, `tools` (solo las que necesita) y `model` (puede ser más barato).
- Ver en las trazas cómo el agente principal delega, el subagente trabaja y devuelve solo la conclusión, y el principal crea la incidencia con esa prioridad.
- Entender por qué funciona: contexto aislado, mínimo privilegio y menor coste.
- Saber cuándo **no** usar subagentes: tareas cortas en las que delegar cuesta más que hacerlo directamente.

### 4.4 · Hooks y persistencia

Un agente que no se puede observar tampoco se puede depurar. Con los hooks registraremos y bloquearemos acciones para saber qué ha hecho el agente y por qué; con las sesiones, podremos retomar una conversación más tarde.

- Escribir un hook de auditoría (`PreToolUse` / `PostToolUse`) que registra cada llamada a herramienta en un fichero `.jsonl` y leerlo como tabla con pandas.
- Escribir un hook que bloquea una acción (cerrar incidencias de prioridad alta) y ver cómo el modelo explica el motivo.
- Distinguir hooks de `can_use_tool`: el hook se ejecuta **siempre**, por eso es la herramienta para aplicar políticas.
- Guardar el `session_id`, reiniciar el kernel y retomar la conversación con `resume` (o abrir una rama nueva con `fork_session`).

## Bloque 5 · Proyecto guiado end-to-end

Llega la hora de practicar. Construiremos de principio a fin un agente de triaje de correos de soporte que propone respuestas pero nunca envía nada, juntando todo lo aprendido en los bloques anteriores.

### 5.1 · Pizarra: diseñar y acotar

Antes de escribir una línea de código, toca diseñar. El primer paso de un agente es decidir qué **no** hace; con eso claro, dejaremos definidos su alcance, su arquitectura y los criterios para saber si funciona.

- Acotar el alcance en dos columnas, «Hace» y «NO hace», y traducir cada «NO hace» en una herramienta que no se le da o un permiso que se le niega.
- Diseñar el agente: herramientas, subagente clasificador, hook de auditoría y el JSON de salida por correo.
- Fijar tres criterios de éxito concretos (correo duplicado, correo urgente y correo que no es una incidencia), que se reutilizan como evals en el bloque 6.

### 5.2 · Implementación I: esqueleto y herramientas

Ponemos en pie el esqueleto del agente: sus herramientas, su system prompt y sus opciones. El objetivo es llegar a procesar un correo y obtener una respuesta en texto.

- Escribir las herramientas razonando cada frase de su descripción: ¿qué necesita saber el modelo para decidir cuándo usarla?
- Probar cada herramienta por separado antes de dársela al agente.
- Escribir el system prompt con los pasos del triaje y las opciones del agente.
- Crear una función `triar(correo)` (una `query()` por correo, sin historial compartido) y probarla con un correo sencillo.
- 🔸 Reto: añadir la búsqueda en la base de conocimiento y comprobar que el agente cita un artículo.

### 5.3 · Implementación II: subagente, trazas y primera ejecución

Completamos el agente con el subagente, la auditoría y la salida estructurada. Con todo montado, procesaremos la bandeja entera y contrastaremos los resultados con los criterios de éxito… y alguno fallará.

- Añadir el subagente clasificador y el hook de auditoría, marcando cada línea del log con el nombre del correo.
- Obtener la salida estructurada con `output_format` y un esquema Pydantic.
- Procesar los cinco correos, ver la bandeja triada como tabla junto con el coste total y revisar los criterios de éxito: uno falla.
- 🔸 Reto: añadir un campo `confianza` a la salida.

### 5.4 · El fallo provocado: depurar con lenguaje

Partimos de ese fallo para aprender a depurar un agente. Descubriremos que muchos errores no están en el código sino en el lenguaje (descripciones y system prompt), y seguiremos un método para diagnosticarlos leyendo trazas.

- Reproducir el síntoma: con un correo duplicado, el agente crea una incidencia nueva.
- Resistir la tentación de parchearlo con código (un `if` que compare asuntos).
- Leer las trazas y preguntarse si la decisión era razonable con la información que tenía el modelo.
- Arreglar las descripciones de las herramientas y el system prompt, y comparar las trazas de antes y después.
- Aplicar el método: reproducir, leer trazas, evaluar la decisión, arreglar el lenguaje (o el código) y volver a comparar, cambiando una sola cosa cada vez.
- 🔸 Reto: encontrar y arreglar, sin tocar Python, un segundo fallo que convierte una felicitación en incidencia.

## Bloque 6 · Llevarlo a producción

Antes de poner un agente delante de clientes hay que tener en cuenta tres riesgos: **coste**, **seguridad** y **calidad**. Sin teoría extensa, veremos criterios rápidos y concretos para cada uno.

### 6.1 · Costes, seguridad y evaluación

Tres preguntas guían este apartado: ¿cuánto cuesta el agente de triaje?, ¿qué pasa si alguien intenta engañarlo? y ¿cómo sabemos que sigue funcionando cuando cambiemos el prompt? Les daremos respuesta con una demo para cada una.

- **Coste:** medir el coste por correo, encontrar el más caro y entender por qué en las trazas. Aplicar las palancas en orden: caché, límites duros (`max_turns`, `max_budget_usd` y tratar su error), modelo adecuado para cada tarea y herramientas que devuelven solo lo necesario. Medir el coste por tarea completada, no por llamada.
- **Seguridad:** ver un intento de prompt injection escondido en un correo y entender que todo lo que entra por una herramienta es dato, no instrucción. Defenderse por capas: mínimo privilegio, hooks de política, una persona que revisa, separar datos de instrucciones en el prompt y nunca `bypassPermissions` ni herramientas genéricas con entrada externa.
- **Calidad:** convertir los criterios de éxito del bloque 5 en casos de prueba y escribir una función `evaluar()` que compruebe qué devolvió el agente y qué herramientas usó. Ejecutar cada caso varias veces y volver a ejecutar los evals con cada cambio de prompt.
- Repasar la checklist de producción y la idea final: el notebook sirve para explorar y depurar; lo que va a producción es un módulo con sus evals.

## Cierre

Para terminar, consolidamos lo aprendido. Repasaremos los errores más frecuentes que han aparecido durante el taller y nos quedaremos con una lista de buenas prácticas para consultar después.

- Ocho errores frecuentes, cada uno con el momento del taller en que apareció: olvidar el historial, descripciones vagas, bucles sin límite, errores que no ayudan, permisos amplios, confiar en la entrada, parchear con código lo que es lenguaje y no medir.
- Buenas prácticas: empezar por lo más simple, diseñar el alcance antes del código, tratar prompts y descripciones como código, explorar en notebook y desplegar en módulo, observar desde el primer día, cambiar una cosa cada vez y medir el coste por tarea completada.
