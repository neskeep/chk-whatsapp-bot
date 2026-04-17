# agent/providers/whapi.py — Adaptador para Whapi.cloud
# Generado por AgentKit

import os
import logging
import httpx
from fastapi import Request
from agent.providers.base import ProveedorWhatsApp, MensajeEntrante

logger = logging.getLogger("agentkit")


class ProveedorWhapi(ProveedorWhatsApp):
    """Proveedor de WhatsApp usando Whapi.cloud (REST API simple)."""

    def __init__(self):
        self.token = os.getenv("WHAPI_TOKEN")
        self.url_envio = "https://gate.whapi.cloud/messages/text"

    # Tipos de Whapi que se mapean a categorías simples
    _TIPOS = {
        "text": "text",
        "image": "image",
        "audio": "audio",
        "ptt": "audio",       # push-to-talk (nota de voz)
        "voice": "audio",
        "video": "video",
        "gif": "sticker",
        "sticker": "sticker",
        "document": "document",
        "location": "location",
        "contact": "contact",
        "contacts_array": "contact",
        "reaction": "reaction",
    }

    async def parsear_webhook(self, request: Request) -> list[MensajeEntrante]:
        """Parsea el payload de Whapi.cloud detectando el tipo de cada mensaje."""
        body = await request.json()
        mensajes = []
        for msg in body.get("messages", []):
            tipo_whapi = msg.get("type", "text")
            tipo = self._TIPOS.get(tipo_whapi, "unknown")

            # Extraer texto: del cuerpo en mensajes de texto,
            # o del caption en mensajes multimedia con leyenda adjunta
            if tipo == "text":
                texto = msg.get("text", {}).get("body", "")
            else:
                # Algunos tipos permiten caption (imagen, video, documento)
                datos = msg.get(tipo_whapi, {})
                texto = datos.get("caption", "") if isinstance(datos, dict) else ""

            mensajes.append(MensajeEntrante(
                telefono=msg.get("chat_id", ""),
                texto=texto,
                mensaje_id=msg.get("id", ""),
                es_propio=msg.get("from_me", False),
                tipo=tipo,
            ))
        return mensajes

    async def enviar_mensaje(self, telefono: str, mensaje: str) -> bool:
        """Envía mensaje via Whapi.cloud."""
        if not self.token:
            logger.warning("WHAPI_TOKEN no configurado — mensaje no enviado")
            return False
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient() as client:
            r = await client.post(
                self.url_envio,
                json={"to": telefono, "body": mensaje},
                headers=headers,
            )
            if r.status_code != 200:
                logger.error(f"Error Whapi: {r.status_code} — {r.text}")
            return r.status_code == 200
