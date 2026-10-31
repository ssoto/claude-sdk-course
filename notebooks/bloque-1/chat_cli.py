from dotenv import load_dotenv
load_dotenv()

import sys
from pathlib import Path
# raíz del taller, relativa a este archivo (no al directorio desde el que se ejecuta)
sys.path.append(str(Path(__file__).resolve().parents[2]))
from config import MODEL

import anthropic
client = anthropic.Anthropic()   # lee ANTHROPIC_API_KEY del entorno


SYSTEM = (
    "Eres un agente de soporte de nivel 1 de una empresa de software. "
    "Respondes en español, en tono cercano y como máximo en dos frases."
)
messages = []  # historial de mensajes del chat

def tokens():
    if not messages:   # la API exige al menos un mensaje
        return 0
    count = client.messages.count_tokens(
        model=MODEL, system=SYSTEM, messages=messages
    )
    return count.input_tokens


def chat(pregunta):
    messages.append({"role": "user", "content": pregunta})
    print("agente> ", end="", flush=True)
    with client.messages.stream(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM,
        messages=messages
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
        respuesta = stream.get_final_message()
    print()
    # max tokens stop reason
    if respuesta.stop_reason == "max_tokens":
        print("¡He alcanzado el límite de tokens!")
    messages.append({"role": "assistant", "content": respuesta.content})

def reset():
    messages.clear()

# escribe "salir" para terminar
while (pregunta := input("tú> ")) != "salir":
    if pregunta == "/tokens": print(tokens()); continue
    if pregunta == "/reset":  reset(); continue
    chat(pregunta)
    print()