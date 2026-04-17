# agent/main.py — Servidor FastAPI + Webhook de WhatsApp
# Generado por AgentKit

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv

from agent.brain import generar_respuesta
from agent.memory import inicializar_db, guardar_mensaje, obtener_historial
from agent.providers import obtener_proveedor

# Respuestas fijas por tipo — no consumen tokens de Claude
_RESPUESTAS_NO_TEXTO = {
    "audio":    "Disculpe, por el momento solo puedo procesar mensajes escritos. ¿Me podría escribir su consulta? Con gusto le atiendo.",
    "image":    "Gracias por compartir la imagen. Por el momento solo proceso texto. ¿Me podría describir brevemente lo que le interesa del producto? O si prefiere, le conecto con un asesor que pueda revisar la foto.",
    "video":    "Disculpe, no puedo procesar videos por ahora. ¿Me podría escribir su consulta? Con gusto le atiendo.",
    "document": "Gracias por compartir el documento. Por el momento solo proceso texto. ¿Me podría resumir en unas líneas qué necesita? O si prefiere, le conecto con un asesor.",
    "sticker":  "😊 ¿En qué le puedo ayudar hoy?",
    "location": "Gracias por compartir su ubicación. ¿Me podría escribir su consulta? Con gusto le atiendo.",
    "contact":  "Gracias por la información. ¿En qué puedo ayudarle?",
    "reaction": None,   # Las reacciones se ignoran silenciosamente
}
_RESPUESTA_DESCONOCIDA = "Disculpe, solo puedo procesar mensajes escritos. ¿Me podría escribir su consulta?"

# Mensaje especial para primer contacto por audio (req. 5)
_BIENVENIDA_AUDIO = (
    "¡Bienvenido a CHK! Disculpe, por el momento solo puedo procesar mensajes escritos. "
    "¿Me podría escribir su consulta? Y si es tan amable, su nombre para atenderle mejor."
)


def _respuesta_no_texto(tipo: str, es_primer_contacto: bool) -> str | None:
    """
    Retorna la respuesta fija para mensajes no-texto.
    Retorna None si el mensaje debe ignorarse silenciosamente (ej: reactions).
    """
    if es_primer_contacto and tipo == "audio":
        return _BIENVENIDA_AUDIO

    respuesta = _RESPUESTAS_NO_TEXTO.get(tipo, _RESPUESTA_DESCONOCIDA)

    if respuesta is None:
        return None  # ignorar silenciosamente

    if es_primer_contacto and tipo != "sticker":
        # Para cualquier otro primer contacto no-texto, agregar bienvenida
        respuesta = f"¡Bienvenido a CHK! {respuesta}"

    return respuesta

load_dotenv()

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
log_level = logging.DEBUG if ENVIRONMENT == "development" else logging.INFO
logging.basicConfig(level=log_level)
logger = logging.getLogger("agentkit")

proveedor = obtener_proveedor()
PORT = int(os.getenv("PORT", 8000))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa la base de datos al arrancar el servidor."""
    await inicializar_db()
    logger.info("Base de datos inicializada")
    logger.info(f"Servidor AgentKit corriendo en puerto {PORT}")
    logger.info(f"Proveedor de WhatsApp: {proveedor.__class__.__name__}")
    yield


app = FastAPI(
    title="CHK Asistente — WhatsApp AI Agent",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/")
async def health_check():
    """Endpoint de salud para Railway/monitoreo."""
    return {"status": "ok", "service": "chk-agentkit", "version": "1.0.0"}


@app.get("/webhook")
async def webhook_verificacion(request: Request):
    """Verificación GET del webhook (requerido por Meta Cloud API, no-op para otros)."""
    resultado = await proveedor.validar_webhook(request)
    if resultado is not None:
        return PlainTextResponse(str(resultado))
    return {"status": "ok"}


@app.post("/webhook")
async def webhook_handler(request: Request):
    """
    Recibe mensajes de WhatsApp via Whapi.cloud.
    Procesa el mensaje, genera respuesta con Claude y la envía de vuelta.
    """
    try:
        mensajes = await proveedor.parsear_webhook(request)

        for msg in mensajes:
            if msg.es_propio:
                continue

            # --- Mensajes sin texto (audio, imagen, video, etc.) ---
            if not msg.texto:
                historial = await obtener_historial(msg.telefono)
                es_primer_contacto = len(historial) == 0
                respuesta_fija = _respuesta_no_texto(msg.tipo, es_primer_contacto)

                if respuesta_fija:
                    logger.info(f"Mensaje no-texto ({msg.tipo}) de {msg.telefono} — respuesta fija")
                    await proveedor.enviar_mensaje(msg.telefono, respuesta_fija)
                    # No guardar en historial (req. 4)
                else:
                    logger.debug(f"Mensaje tipo '{msg.tipo}' de {msg.telefono} ignorado silenciosamente")
                continue

            # --- Mensajes de texto: flujo normal con Claude ---
            logger.info(f"Mensaje de {msg.telefono}: {msg.texto}")

            historial = await obtener_historial(msg.telefono)
            respuesta = await generar_respuesta(msg.texto, historial)

            await guardar_mensaje(msg.telefono, "user", msg.texto)
            await guardar_mensaje(msg.telefono, "assistant", respuesta)

            await proveedor.enviar_mensaje(msg.telefono, respuesta)
            logger.info(f"Respuesta a {msg.telefono}: {respuesta[:80]}...")

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Error en webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))
