# Taller: de la API de Claude al Agent SDK

Los objetivos de cada bloque están en [OBJETIVOS.md](OBJETIVOS.md).

## Requisitos

- Python 3.10 o superior
- VS Code con las extensiones **Python** y **Jupyter** (VS Code las sugiere al abrir la carpeta)
- Node.js (solo para el bloque 4)
- Una API key de Anthropic

## Instalación

1. En VS Code: **File → Open Folder…** y abre esta carpeta (`taller-claude`).
2. En la terminal integrada (`` Ctrl+` ``):

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate            # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   cp .env.example .env                 # y pon tu API key en .env
   ```

## Comprobar el entorno

1. Abre `notebooks/00-comprobar-entorno.ipynb`.
2. Pulsa **Select Kernel** (arriba a la derecha) → **Python Environments…** → `.venv`.
3. Pulsa **Run All**. Si todas las celdas terminan en ✅, el entorno está listo.

## Estructura

```
notebooks/bloque-N/     un notebook por vídeo (abre cada uno con el kernel .venv)
soluciones/bloque-N/    los mismos notebooks con los retos resueltos
config.py               el modelo que usa todo el taller
herramientas.py         funciones de negocio: incidencias, base de conocimiento, bandeja
taller_utils.py         lo ya enseñado, para importarlo desde el bloque 4 en adelante
triaje.py               el agente de triaje del bloque 5, como módulo (bloque 6)
datos/                  incidencias, política de soporte, base de conocimiento (kb/),
                        correos (bandeja/) y casos de evaluación (evals/)
sandbox/                ficheros desechables para la demo de permisos del bloque 3
logs/                   trazas de auditoría y sesiones (se generan al ejecutar)
```

Los notebooks crean y cierran incidencias de verdad en `datos/incidencias.json`. Para volver al estado inicial: `from herramientas import restaurar_datos; restaurar_datos()` (los notebooks lo hacen antes de cada demo).
