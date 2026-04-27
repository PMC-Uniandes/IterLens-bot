from langchain_core.messages import AIMessage
from .state import ReportState
from .config import llm, structured_llm, confirm_llm
from backend.supabase import get_tipos_parada, get_maquinas, crear_registro_parada


QUESTIONS = {
    "id_maquina":           "¿En qué máquina ocurrió la falla?",
    "id_tipo_parada":       "¿Qué tipo de falla fue? \n\nPuedes describirla o poner su código.",
    "turno":                "¿En qué turno (dia, tarde, noche) ocurrió?",
    "tiempo_parada_horas":  "¿Cuánto tiempo estuvo parada la máquina?",
    "prioridad":            "¿Que prioridad le asignas a este problema?",
    "observaciones":        "¿Alguna observación adicional?",
}

REQUIRED_FIELDS = ["id_maquina", "id_tipo_parada", "turno", "tiempo_parada_horas", "prioridad"]

STOP_WORDS = ["la", "el", "se", "un", "una", "de", "maquina", "máquina", "equipo", "por", 
              "falla", "fallo", "avería", "averia", "problema", "parada", "tipo", "causa"]


def parse_intent(state: ReportState):
    print("[INTENT] Detecting intent...")

    messages = state.get("messages", [])
    if not messages:
        return {"intent": "otro"}

    last_message = messages[-1].content

    has_active_report = state.get("missing_fields", None)
    awaiting_confirmation = state.get("awaiting_confirmation", False)

    context = ""
    if awaiting_confirmation:
        context = "CONTEXTO: El bot acaba de mostrar un resumen del reporte y está esperando confirmación del usuario."
    elif has_active_report:
        context = "CONTEXTO: Hay un reporte en curso. El bot está recopilando campos faltantes. 'alta', 'baja', 'sí', 'no', 'tarde' NO son cancelaciones."

    prompt = f"""
    Eres un clasificador de intenciones para un bot de mantenimiento industrial.
    Tu tarea es identificar qué quiere hacer el operario con su mensaje.

    {context}

    CATEGORÍAS:
    - saludo: el usuario saluda o hace un comentario de cortesía sin pedir nada concreto.
    Ejemplos: "hola", "buenos días", "gracias", "ok"

    - reportar_falla: el usuario quiere reportar que una máquina falló o tuvo una parada.
    Ejemplos: "se dañó la máquina 3", "la prensa paró", "avería en torno 2", "falla eléctrica en M-04", "nuevo reporte"

    - completar_reporte: el usuario está respondiendo una pregunta del bot para completar un reporte en curso.
    Solo aplica si hay un reporte activo. Incluye turnos, tiempos, tipos de falla, observaciones, prioridad.
    Ejemplos: "maquina x", "turno tarde", "2 horas", "falla mecánica", "ninguna observación", "0008"

    - confirmar: el usuario responde afirmativa o negativamente al resumen del reporte.
    SOLO usar cuando el bot está esperando confirmación del usuario.
    Ejemplos afirmativos: "sí", "correcto", "confirmo", "dale", "está bien", "ok", "sí registra"
    Ejemplos negativos: "no", "cancela", "incorrecto", "está mal", "no registres"

    - cancelar: el usuario quiere abandonar o cancelar el reporte que está en curso, sin importar en qué paso esté.
    Aplica en cualquier momento del flujo, no solo en la confirmación final.
    Ejemplos directos: "cancela", "cancelar", "no registres", "olvídalo", "déjalo así",
    "no importa", "para", "detente", "salir", "exit", "abort"
    Ejemplos indirectos: "mejor no", "no quiero reportar", "me equivoqué de chat",
    "no era esto", "déjame", "no sigas", "no continúes"
    IMPORTANTE: distinguir de 'confirmar' negativo — "no" solo es cancelar si hay un reporte
    activo a mitad del flujo. Si el bot mostró el resumen final y el usuario dice "no",
    eso es 'confirmar' (negativo), no 'cancelar'.

    - listar_maquinas: el usuario quiere ver el catálogo de máquinas disponibles.
    Ejemplos: "qué máquinas hay", "lista de máquinas", "muéstrame las máquinas",
    "cuáles son los equipos", "no sé el nombre de la máquina", "qué opciones de máquina tengo"

    - listar_tipos_parada: el usuario quiere ver los tipos de parada o falla disponibles.
    Ejemplos: "qué tipos de falla hay", "muéstrame los códigos", "cuáles son las opciones de parada",
    "no sé qué tipo poner", "qué categorías de falla existen", "lista los códigos"

    - otro: el mensaje no encaja en ninguna categoría anterior.

    Mensaje del usuario: "{last_message}"

    Responde ÚNICAMENTE con una de estas palabras exactas, sin puntuación ni explicación:
    saludo | reportar_falla | completar_reporte | confirmar | cancelar | listar_maquinas | listar_tipos_parada | otro
    """

    response = llm.invoke(prompt)
    intent = response.content.strip().lower().rstrip(".,;:")


    valid_intents = {"saludo", "reportar_falla", "completar_reporte", "confirmar", "cancelar", "listar_maquinas", "listar_tipos_parada"}
    if intent not in valid_intents:
        intent = "otro"

    return {"intent": intent}


def greeting_handler(state: ReportState):
    print("[GREETING] Greet user...")

    response = "¡Hola! Soy Lens, tu asistente de mantenimiento. \n¿Quieres reportar un incidente con alguna maquina?"

    return {
        "messages": [AIMessage(response)],
        "intent": None
    }


def report_handler(state: ReportState):
    print("[REPORT] Reporting or updating a issue...")

    last_message = state["messages"][-1].content

    campos_actuales = {
        "id_maquina":           state.get("id_maquina"),
        "tipo_parada_texto":    state.get("tipo_parada_texto"),
        "turno":                state.get("turno"),
        "tiempo_parada_horas":  state.get("tiempo_parada_horas"),
        "observaciones":        state.get("observaciones"),
    }

    prompt = f"""
    Eres un asistente de registro de mantenimiento industrial.

    CAMPOS YA RECOPILADOS (no los repitas, solo actualiza si el usuario corrige):
    {campos_actuales}

    NUEVO MENSAJE DEL OPERARIO:
    "{last_message}"

    Extrae SOLO los campos que el operario menciona en este mensaje.
    Si el usuario está corrigiendo un campo ya recopilado, actualízalo.
    Si no menciona un campo, devuélvelo como null (aunque ya estuviera lleno).
    No inventes datos.
    """

    response = structured_llm.invoke(prompt)

    updated = {}
    for field in ["maquina_texto", "tipo_parada_texto", "turno", "tiempo_parada_horas", "observaciones", "prioridad"]:
        nuevo = getattr(response, field, None)
        updated[field] = nuevo if nuevo is not None else state.get(field)

    return updated


def validator(state: ReportState):
    print("[VALIDATOR] Validating fields of report...")

    missing = [f for f in REQUIRED_FIELDS if not state.get(f)]

    if missing:
        next_field = missing[0]
        return {
            "missing_fields": missing,
            "is_complete": False,
            "awaiting_confirmation": False,
            "messages": [AIMessage(content=QUESTIONS[next_field])]
        }

    return {
        "missing_fields": [],
        "is_complete": True,
        "awaiting_confirmation": False,
    }


def mapper(state: ReportState):
    print("[MAPPER] Mapping fields of report...")

    result = {}

    # --- Mapear máquina ---
    texto_maquina = state.get("maquina_texto")
    
    if texto_maquina:
        maquinas = get_maquinas()

        tokens = [t for t in texto_maquina.lower().split() if t not in STOP_WORDS and len(t) >= 3]

        for m in maquinas:
            nombre = m["nombre_maquina"].lower()
            id_maq = m["id_maquina"].lower()
            
            if any(token in nombre or token in id_maq for token in tokens):
                result["id_maquina"] = m["id_maquina"]
                break


    # --- Mapear tipo de parada ---
    tipo_parada_texto = state.get("tipo_parada_texto")

    if tipo_parada_texto:
        tipos = get_tipos_parada()

        match = next((t for t in tipos if t["codigo"] == tipo_parada_texto.strip()), None)

        if not match:
            tokens = [t for t in tipo_parada_texto.lower().split() if t not in STOP_WORDS and len(t) >= 3]

            if tokens:
                for t in tipos:
                    descripcion = t["descripcion"].lower()
                    if any(token in descripcion for token in tokens):
                        match = t
                        break

        if not match:
            tipos_str = "\n".join(f"{t['codigo']} | {t['descripcion']}" for t in tipos)
            prompt = f"""
            Del siguiente catálogo de tipos de parada, ¿cuál corresponde mejor a: "{tipo_parada_texto}"?

            {tipos_str}

            Responde SOLO con el código de 4 dígitos (ej: 0008). Si no hay ninguno adecuado responde: null
            """
            response = llm.invoke(prompt)
            codigo = response.content.strip()
            match = next((t for t in tipos if t["codigo"] == codigo), None)

        if match:
            result["id_tipo_parada"] = match["id_tipo_parada"]
            result["tipo_parada_texto"] = match["descripcion"]

    return result


def confirm(state: ReportState) -> dict:

    print("[CONFIRM] User is confirming report...")

    if state.get("awaiting_confirmation"):
        last_message = state["messages"][-1].content
        response = confirm_llm.invoke(last_message)

        if response.confirm is None:
            return {
                "awaiting_confirmation": True,
                "messages": [AIMessage(content="No entendí tu respuesta. ¿Confirmas el registro? Responde sí o no.")]
            }

        return {
            "awaiting_confirmation": False,
            "confirmed": response.confirm
        }

    prioridad_emoji = {"alta": "🔴", "media": "🟡", "baja": "🟢"}
    emoji = prioridad_emoji.get((state.get("prioridad") or "").lower(), "⚪")

    resumen = (
        f"📋 Resumen del incidente:\n\n"
        f"🔧 ID Máquina: {state.get('id_maquina')}\n"
        f"⚡ Tipo de parada: {state.get('id_tipo_parada')} - {state.get('tipo_parada_texto')}\n"
        f"🕐 Turno: {state.get('turno')}\n"
        f"⏱️ Duración: {state.get('tiempo_parada_horas')} horas\n"
        f"📝 Observaciones: {state.get('observaciones') or 'Ninguna'}\n"
        f"{emoji} Prioridad: {state.get('prioridad') or 'No especificada'}\n\n"
        f"¿Confirmas el registro?"
    )

    return {
        "awaiting_confirmation": True,
        "confirmed": False,
        "messages": [AIMessage(content=resumen)]
    }

def cancel_report(state: ReportState):
    print("[CANCEL] Canceled report...")

    return {
        "messages": [AIMessage(content="❌ Reporte cancelado. Puedes empezar uno nuevo cuando quieras.")]
    }

def save_report(state: ReportState):
    print("[SAVE] Saving report...")

    registro = crear_registro_parada(
        id_maquina          = state.get("id_maquina"),
        id_tipo_parada      = state.get("id_tipo_parada"),
        turno               = state.get("turno"),
        tiempo_parada_horas = state.get("tiempo_parada_horas"),
        observaciones       = state.get("observaciones"),
        registrado_por      = state.get("user_id"),
    )
    
    ticket_id = str(registro.get("id_registro_parada", "???"))

    mensaje = (
        f"✅ Listo, reporte guardado\n\n"
        f"Ticket: #{ticket_id}\n"
        f"Máquina: {state.get('id_maquina')}\n"
        f"Falla: {state.get('tipo_parada_texto')}\n"
        f"Turno: {state.get('turno')}\n"
        f"Tiempo parado: {state.get('tiempo_parada_horas')} horas\n\n"
        f"Si hay otra novedad, escríbeme cuando quieras 👋"
    )

    return {
        "messages": [AIMessage(content=mensaje)],
    }


def restart(state: ReportState):
    print("[RESTART] Restarting state for new report...")

    return {
        "confirmed": False,
        "awaiting_confirmation": False,
        "id_maquina": None,
        "tipo_parada_texto": None,
        "id_tipo_parada": None,
        "turno": None,
        "tiempo_parada_horas": None,
        "observaciones": None,
        "missing_fields": [],
        "is_complete": False,
    }


def list_machines(state: ReportState):
    maquinas = get_maquinas()

    if not maquinas:
        return {"messages": [AIMessage(content="⚠️ No hay máquinas registradas.")]}

    # Agrupar por célula
    from collections import defaultdict
    por_celula = defaultdict(list)
    for m in maquinas:
        celula = m.get("celula") or "Sin célula"
        por_celula[celula].append(m)

    lineas = ["🏭 Máquinas disponibles:\n"]
    for celula, maquinas_celula in por_celula.items():
        lineas.append(f"📦 {celula}")
        for m in maquinas_celula:
            lineas.append(f"  • {m['id_maquina']} — {m['nombre_maquina']}")
        lineas.append("")

    return {"messages": [AIMessage(content="\n".join(lineas))]}


def list_failures(state: ReportState):
    tipos = get_tipos_parada()

    if not tipos:
        return {"messages": [AIMessage(content="⚠️ No hay tipos de parada registrados.")]}

    # Agrupar por categoría OEE
    from collections import defaultdict
    por_categoria = defaultdict(list)
    for t in tipos:
        categoria = t.get("categoria_oee") or "Otra"
        por_categoria[categoria].append(t)

    categoria_emoji = {
        "DISPONIBILIDAD": "🔴",
        "RENDIMIENTO":    "🟡",
        "CALIDAD":        "🔵",
        "MERCADO":        "⚪",
        "PLANIFICADO":    "🟢",
    }

    lineas = ["⚡ Tipos de parada disponibles:\n"]
    for categoria, tipos_cat in por_categoria.items():
        emoji = categoria_emoji.get(categoria, "⚪")
        lineas.append(f"{emoji} {categoria}")
        for t in tipos_cat:
            lineas.append(f"  • {t['codigo']} — {t['descripcion']}")
        lineas.append("")

    return {"messages": [AIMessage(content="\n".join(lineas))]}


def fallback(state: ReportState):
    messages = state.get("messages", [])

    greeting = True if len(messages) <= 1 else False

    last_message = messages[-1].content if messages else ""
    
    prompt = f"""Eres Lens, un asistente de mantenimiento industrial para plantas manufactureras.
    
    ¿Debes saludar al usuario?:"{greeting}"

    El usuario escribió: "{last_message}"

    Responde de forma breve y amable en español. Puedes:
    - Explicar qué puedes hacer si te lo preguntan 
    - Responder preguntas generales sobre mantenimiento industrial
    - Si el mensaje es completamente incomprensible o irrelevante, di explícitamente que no entendiste y explica qué puedes hacer

    Lo que SÍ puedes hacer:
    - Registrar fallas de máquinas (pídele que te diga la máquina, tipo de falla, turno y tiempo parado)
    - Mostrar las máquinas disponibles
    - Mostrar los tipos de parada disponibles

    Sé conciso. Máximo 3 líneas."""

    response = llm.invoke(prompt)
    return {"messages": [AIMessage(content=response.content)]}