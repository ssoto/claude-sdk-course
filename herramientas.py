# Funciones de negocio del agente de soporte.
# No son el foco del taller: los notebooks las importan y las convierten en herramientas.
import json
import re
import shutil
from datetime import date
from pathlib import Path

DATOS = Path(__file__).parent / "datos"
INCIDENCIAS = DATOS / "incidencias.json"
INCIDENCIAS_INICIAL = DATOS / "incidencias_inicial.json"
KB = DATOS / "kb"
BANDEJA = DATOS / "bandeja"


def _cargar():
    if not INCIDENCIAS.exists():
        restaurar_datos()
    return json.loads(INCIDENCIAS.read_text(encoding="utf-8"))


def _guardar(incidencias):
    INCIDENCIAS.write_text(json.dumps(incidencias, ensure_ascii=False, indent=2), encoding="utf-8")


def restaurar_datos():
    """Devuelve incidencias.json a su estado inicial."""
    shutil.copy(INCIDENCIAS_INICIAL, INCIDENCIAS)


# --- Incidencias ---

def buscar_incidencias(texto=None, estado=None, cliente=None) -> list[dict]:
    """Filtra por texto (en asunto y descripción), estado y cliente. Los filtros vacíos se ignoran."""
    resultado = []
    for inc in _cargar():
        if estado and inc["estado"] != estado:
            continue
        if cliente and inc["cliente"].lower() != cliente.lower():
            continue
        if texto:
            contenido = (inc["asunto"] + " " + inc["descripcion"]).lower()
            if not all(palabra in contenido for palabra in texto.lower().split()):
                continue
        resultado.append({k: inc[k] for k in ("id", "cliente", "asunto", "estado", "prioridad", "fecha")})
    return resultado


def obtener(id) -> dict | None:
    """Devuelve la incidencia completa o None si no existe."""
    return next((inc for inc in _cargar() if inc["id"] == id), None)


def crear_incidencia(cliente, asunto, descripcion, prioridad) -> dict:
    if prioridad not in ("alta", "media", "baja"):
        raise ValueError(f"Prioridad no válida: {prioridad!r}. Usa alta, media o baja.")
    incidencias = _cargar()
    siguiente = max(int(inc["id"].split("-")[1]) for inc in incidencias) + 1
    nueva = {
        "id": f"INC-{siguiente:03d}",
        "cliente": cliente,
        "asunto": asunto,
        "descripcion": descripcion,
        "estado": "abierta",
        "prioridad": prioridad,
        "fecha": date.today().isoformat(),
    }
    incidencias.append(nueva)
    _guardar(incidencias)
    return nueva


def cerrar_incidencia(id) -> dict:
    incidencias = _cargar()
    inc = next((i for i in incidencias if i["id"] == id), None)
    if inc is None:
        raise ValueError(f"No existe la incidencia {id}")
    inc["estado"] = "cerrada"
    _guardar(incidencias)
    return inc


# --- Base de conocimiento ---

def buscar_kb(consulta) -> list[dict]:
    """Devuelve los artículos de la KB que más palabras de la consulta contienen, con su fragmento más relevante."""
    palabras = [p for p in re.findall(r"\w+", consulta.lower()) if len(p) > 3]
    resultados = []
    for articulo in sorted(KB.glob("*.md")):
        texto = articulo.read_text(encoding="utf-8")
        titulo = texto.splitlines()[0].lstrip("# ").strip()
        parrafos = [p.strip() for p in texto.split("\n\n") if p.strip() and not p.startswith("#")]
        puntuar = lambda t: sum(t.lower().count(p) for p in palabras)
        puntos = puntuar(texto)
        if puntos:
            resultados.append({
                "articulo": articulo.name,
                "titulo": titulo,
                "fragmento": max(parrafos, key=puntuar),
                "puntos": puntos,
            })
    return sorted(resultados, key=lambda r: r["puntos"], reverse=True)[:3]


# --- Bandeja de correos ---

def listar_bandeja() -> list[str]:
    return sorted(p.name for p in BANDEJA.glob("*.txt"))


def leer_correo(nombre) -> str:
    ruta = BANDEJA / nombre
    if not ruta.exists():
        raise FileNotFoundError(f"No existe el correo {nombre}. Correos disponibles: {', '.join(listar_bandeja())}")
    return ruta.read_text(encoding="utf-8")
