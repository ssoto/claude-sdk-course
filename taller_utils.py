# Lo que ya se ha enseñado en el taller, sacado de los notebooks para no arrastrar copias.
# Cada sección indica el vídeo en el que se explicó.
import datetime
import json
from pathlib import Path

from claude_agent_sdk import (
    AgentDefinition, AssistantMessage, ResultMessage, TextBlock, ToolAnnotations, ToolUseBlock, tool,
)

import herramientas
from herramientas import restaurar_datos  # noqa: F401  (se importa desde aquí en los bloques 5 y 6)

RAIZ = Path(__file__).parent
LOGS = RAIZ / "logs"
LOG_AUDITORIA = LOGS / "auditoria.jsonl"
ULTIMA_SESION = LOGS / "ultima_sesion.txt"
KB = RAIZ / "datos" / "kb"


# --- 3.1 · Imprimir los mensajes del SDK ---

def imprimir(msg):
    # 4.3: los mensajes con parent_tool_use_id son de un subagente
    sangria = "      [subagente] " if getattr(msg, "parent_tool_use_id", None) else ""
    if isinstance(msg, AssistantMessage):
        for b in msg.content:
            if isinstance(b, ToolUseBlock):
                print(f"{sangria}  → {b.name}({b.input})")
            elif isinstance(b, TextBlock):
                print(f"{sangria}{b.text}")
    elif isinstance(msg, ResultMessage):
        print(f"[{msg.subtype}] turnos={msg.num_turns} coste=${msg.total_cost_usd:.4f}")


# --- 4.1 · Herramientas del servidor "soporte" ---

def _texto(dato):
    return {"content": [{"type": "text", "text": json.dumps(dato, ensure_ascii=False)}]}


def _error(mensaje):
    return {"content": [{"type": "text", "text": mensaje}], "is_error": True}


@tool("buscar_incidencias",
      "Busca incidencias de soporte existentes. Úsala siempre antes de crear una incidencia y cuando "
      "pregunten por incidencias de un cliente o por su estado. Todos los filtros son opcionales y se "
      "combinan. Devuelve una lista JSON con id, cliente, asunto, estado, prioridad y fecha; [] si no "
      "hay coincidencias.",
      {
          "type": "object",
          "properties": {
              "texto": {"type": "string", "description": "Palabras clave a buscar en asunto y descripción"},
              "estado": {"type": "string", "enum": ["abierta", "cerrada"]},
              "cliente": {"type": "string", "description": "Nombre comercial corto del cliente, p. ej. 'ACME'"},
          },
      },
      annotations=ToolAnnotations(readOnlyHint=True))
async def buscar_incidencias(args):
    return _texto(herramientas.buscar_incidencias(**args))


@tool("crear_incidencia",
      "Crea una incidencia nueva. Úsala SOLO después de comprobar con buscar_incidencias que no existe "
      "ya una abierta sobre el mismo problema para el mismo cliente. Devuelve la incidencia creada con su id.",
      {
          "type": "object",
          "properties": {
              "cliente": {"type": "string", "description": "Nombre comercial corto del cliente"},
              "asunto": {"type": "string", "description": "Resumen en menos de 10 palabras"},
              "descripcion": {"type": "string"},
              "prioridad": {"type": "string", "enum": ["alta", "media", "baja"]},
          },
          "required": ["cliente", "asunto", "descripcion", "prioridad"],
      })
async def crear_incidencia(args):
    return _texto(herramientas.crear_incidencia(**args))


@tool("cerrar_incidencia", "Cierra una incidencia abierta por su id (formato INC-123).",
      {"id": str},
      annotations=ToolAnnotations(destructiveHint=True))
async def cerrar_incidencia(args):
    inc = herramientas.obtener(args["id"])
    if inc is None:
        return _error(f"No existe la incidencia {args['id']}. "
                      "Usa buscar_incidencias para obtener ids válidos.")
    if inc["estado"] == "cerrada":
        return _error(f"La incidencia {args['id']} ya estaba cerrada. No hay que hacer nada más.")
    return _texto(herramientas.cerrar_incidencia(args["id"]))


# Reto del 4.1
@tool("buscar_kb",
      "Busca en la base de conocimiento artículos que ayuden a resolver un problema. Úsala para "
      "proponer soluciones al cliente: nunca propongas una solución que no esté en un artículo. "
      "Devuelve hasta 3 artículos con su nombre de fichero, título y el fragmento más relevante.",
      {"consulta": str},
      annotations=ToolAnnotations(readOnlyHint=True))
async def buscar_kb(args):
    resultados = herramientas.buscar_kb(args["consulta"])
    if not resultados:
        return _error("No hay artículos sobre eso. Prueba con otras palabras clave más generales "
                      "(p. ej. 'PDF', 'contraseña', 'factura').")
    return _texto(resultados)


# --- 4.2 · Servidor MCP externo con la base de conocimiento ---

def servidor_kb():
    return {
        "type": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", str(KB.resolve())],
    }


# --- 4.3 · Subagente clasificador ---

HERRAMIENTAS_KB = ["mcp__kb__read_text_file", "mcp__kb__search_files", "mcp__kb__list_directory"]

CLASIFICADOR = AgentDefinition(
    description=("Especialista en clasificar incidencias de soporte. Úsalo cuando haya que "
                 "decidir la prioridad o la categoría de una incidencia nueva o existente."),
    prompt=("Eres un clasificador de incidencias. Dada una incidencia, consulta los criterios de "
            "prioridad (prioridades.md en la base de conocimiento) y devuelve SOLO: prioridad "
            "(alta/media/baja), categoría (facturación/técnico/cuenta/otro) y una justificación "
            "de una línea."),
    tools=HERRAMIENTAS_KB,
    mcpServers=[{"kb": servidor_kb()}],   # la KB es solo del subagente: el principal no la ve
    model="claude-haiku-5-5",
)


# --- 4.4 · Hooks y sesiones ---

# Campos que se añaden a cada línea del log (en el 5.3: el nombre del correo)
CONTEXTO_LOG = {}


async def auditar(input_data, tool_use_id, context):
    registro = {
        "ts": datetime.datetime.now().isoformat(),
        **CONTEXTO_LOG,
        "evento": input_data["hook_event_name"],
        "herramienta": input_data.get("tool_name"),
        "entrada": input_data.get("tool_input"),
        "tool_use_id": tool_use_id,
    }
    if input_data["hook_event_name"] == "PostToolUse":
        registro["salida"] = str(input_data.get("tool_response"))[:500]
    LOGS.mkdir(exist_ok=True)
    with open(LOG_AUDITORIA, "a") as f:
        f.write(json.dumps(registro, ensure_ascii=False) + "\n")
    return {}


async def proteger_cierres(input_data, tool_use_id, context):
    inc = herramientas.obtener(input_data["tool_input"]["id"])
    if inc and inc["prioridad"] == "alta":
        return {"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": "Las incidencias de prioridad alta solo las cierra un humano.",
        }}
    return {}


def guardar_sesion(session_id):
    LOGS.mkdir(exist_ok=True)
    ULTIMA_SESION.write_text(session_id)


def cargar_sesion():
    return ULTIMA_SESION.read_text().strip()


def leer_log():
    import pandas as pd
    if not LOG_AUDITORIA.exists():
        return pd.DataFrame(columns=["ts", "evento", "herramienta", "entrada"])
    return pd.read_json(LOG_AUDITORIA, lines=True)


def borrar_log():
    LOG_AUDITORIA.unlink(missing_ok=True)
