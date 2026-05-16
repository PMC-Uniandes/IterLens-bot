"""Application-wide constants for the IterLens bot."""

import os

SUPERVISOR_WHATSAPP = os.getenv("SUPERVISOR_WHATSAPP", "")

QUESTIONS = {
    "id_maquina": "¿En qué máquina ocurrió la falla?",
    "id_tipo_parada": "¿Qué tipo de falla fue? \n\nPuedes describirla o poner su código.",
    "turno": "¿En qué turno (dia, tarde, noche) ocurrió?",
    "tiempo_parada_horas": "¿Cuánto tiempo estuvo parada la máquina?",
    "prioridad": "¿Que prioridad le asignas a este problema?",
    "observaciones": "¿Alguna observación adicional?",
}

REQUIRED_FIELDS = ["id_maquina", "id_tipo_parada", "turno", "tiempo_parada_horas", "prioridad"]

STOP_WORDS = [
    "la", "el", "se", "un", "una", "de", "maquina", "máquina",
    "equipo", "por", "falla", "fallo", "avería", "averia",
    "problema", "parada", "tipo", "causa",
]

VALID_INTENTS = {
    "saludo",
    "reportar_falla",
    "completar_reporte",
    "cancelar",
    "listar_maquinas",
    "listar_tipos_parada",
    "seleccionar_opcion",
}

PRIORITY_EMOJI = {
    "alta": "\U0001F534",
    "media": "\U0001F7E1",
    "baja": "\U0001F7E2",
}

CATEGORY_EMOJI = {
    "DISPONIBILIDAD": "\U0001F534",
    "RENDIMIENTO": "\U0001F7E1",
    "CALIDAD": "\U0001F535",
    "MERCADO": "\u26AA",
    "PLANIFICADO": "\U0001F7E2",
}

RESET_FIELDS = {
    "id_maquina": None,
    "id_tipo_parada": None,
    "tipo_parada_texto": None,
    "maquina_texto": None,
    "turno": None,
    "tiempo_parada_horas": None,
    "prioridad": None,
    "observaciones": None,
    "missing_fields": [],
    "is_complete": False,
    "pending_supervisor_msg": None,
    "status": None,
    "last_list_items": None,
    "last_list_type": None,
    "pending_selection_item": None,
    "pending_observation": None,
}

OLD_MESSAGE_THRESHOLD_SECONDS = 60
