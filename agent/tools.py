# agent/tools.py — Herramientas del agente CHK
# Generado por AgentKit

import os
import yaml
import logging
from datetime import datetime

logger = logging.getLogger("agentkit")


def cargar_info_negocio() -> dict:
    """Carga la información del negocio desde business.yaml."""
    try:
        with open("config/business.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.error("config/business.yaml no encontrado")
        return {}


def obtener_horario() -> dict:
    """Retorna información de horario y disponibilidad."""
    return {
        "bot_disponible": True,
        "atencion_24_7": True,
        "nota": "El agente responde 24/7. El equipo humano atiende en horario comercial (por confirmar con CHK)."
    }


def es_horario_comercial() -> bool:
    """Verifica si es horario comercial aproximado (L-V 9am-6pm Venezuela, UTC-4)."""
    ahora = datetime.utcnow()
    hora_venezuela = ahora.hour - 4
    if hora_venezuela < 0:
        hora_venezuela += 24
    es_dia_laboral = ahora.weekday() < 5
    es_hora_laboral = 9 <= hora_venezuela <= 18
    return es_dia_laboral and es_hora_laboral


def obtener_tiendas() -> list[dict]:
    """Retorna información de las tiendas físicas de CHK."""
    info = cargar_info_negocio()
    tiendas = info.get("tiendas", {})
    return [
        {
            "ciudad": "Caracas",
            "direccion": tiendas.get("caracas", {}).get("direccion", ""),
            "telefono": tiendas.get("caracas", {}).get("telefono", ""),
        },
        {
            "ciudad": "Puerto Ordaz",
            "direccion": tiendas.get("puerto_ordaz", {}).get("direccion", ""),
            "telefono": tiendas.get("puerto_ordaz", {}).get("telefono", ""),
        },
        {
            "ciudad": "San Cristóbal",
            "direccion": tiendas.get("san_cristobal", {}).get("direccion", ""),
            "telefono": tiendas.get("san_cristobal", {}).get("telefono", ""),
        },
    ]


def calificar_lead(texto_conversacion: str) -> str:
    """
    Evalúa el nivel de interés del lead según señales en la conversación.

    Returns:
        "alto" | "medio" | "bajo"
    """
    texto = texto_conversacion.lower()

    # Señales de interés alto (intención de compra, productos premium)
    senales_alto = [
        "quiero comprar", "cuánto cuesta", "precio", "disponible",
        "traje", "tuxedo", "maletín", "bolso", "cita", "agendar",
        "a medida", "sastrería", "wedding", "boda", "evento"
    ]

    # Señales de interés medio (exploración)
    senales_medio = [
        "me interesa", "información", "catálogo", "tienes",
        "corbata", "zapatos", "envío", "entrega"
    ]

    puntos_alto = sum(1 for s in senales_alto if s in texto)
    puntos_medio = sum(1 for s in senales_medio if s in texto)

    if puntos_alto >= 2:
        return "alto"
    elif puntos_alto >= 1 or puntos_medio >= 2:
        return "medio"
    else:
        return "bajo"


def registrar_lead(telefono: str, nombre: str, interes: str, ciudad: str = "") -> dict:
    """
    Registra información básica de un lead calificado para seguimiento humano.
    En producción conectar con CRM o sistema de notificaciones.

    Returns:
        Diccionario con los datos del lead registrado
    """
    lead = {
        "telefono": telefono,
        "nombre": nombre,
        "interes": interes,
        "ciudad": ciudad,
        "timestamp": datetime.utcnow().isoformat(),
        "nivel": calificar_lead(interes),
    }
    logger.info(f"Lead registrado: {lead}")
    return lead


def buscar_en_knowledge(consulta: str) -> str:
    """
    Busca información relevante en los archivos de /knowledge.
    Retorna el contenido más relevante encontrado.
    """
    resultados = []
    knowledge_dir = "knowledge"

    if not os.path.exists(knowledge_dir):
        return "No hay archivos de conocimiento disponibles."

    for archivo in sorted(os.listdir(knowledge_dir)):
        ruta = os.path.join(knowledge_dir, archivo)
        if archivo.startswith(".") or not os.path.isfile(ruta):
            continue
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                contenido = f.read()
                if consulta.lower() in contenido.lower():
                    resultados.append(f"[{archivo}]: {contenido[:500]}")
        except (UnicodeDecodeError, IOError):
            continue

    if resultados:
        return "\n---\n".join(resultados[:3])
    return "No encontré información específica sobre eso en mis archivos."
