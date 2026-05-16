"""LangGraph node functions for the maintenance report workflow."""

import json
import logging
from collections import defaultdict

from langchain_core.messages import AIMessage

from constants import (
    CATEGORY_EMOJI,
    PRIORITY_EMOJI,
    QUESTIONS,
    REQUIRED_FIELDS,
    RESET_FIELDS,
    STOP_WORDS,
    VALID_INTENTS,
    SUPERVISOR_WHATSAPP,
)
from integrations.whatsapp.client import send_whatsapp_message_sync
from services.supabase import crear_registro_parada, get_maquinas, get_tipos_parada
from src.config import llm, structured_llm
from src.state import ReportState

logger = logging.getLogger(__name__)


def parse_intent(state: ReportState) -> dict:
    """Classify the user's message into an intent category."""
    logger.info("Detecting intent...")

    messages = state.get("messages", [])
    if not messages:
        return {"intent": "otro"}

    last_message = messages[-1].content
    has_active_report = state.get("missing_fields")
    has_list_shown = bool(state.get("last_list_type"))
    has_pending_selection = bool(state.get("pending_selection_item"))

    context = ""
    if has_active_report:
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

    - cancelar: el usuario quiere abandonar o cancelar el reporte que está en curso, sin importar en qué paso esté.
    Ejemplos directos: "cancela", "cancelar", "no registres", "olvídalo", "déjalo así",
    "no importa", "para", "detente", "salir", "exit", "abort"
    Ejemplos indirectos: "mejor no", "no quiero reportar", "me equivoqué de chat",
    "no era esto", "déjame", "no sigas", "no continúes"

    - listar_maquinas: el usuario quiere ver el catálogo de máquinas disponibles.
    Ejemplos: "qué máquinas hay", "lista de máquinas", "muéstrame las máquinas",
    "cuáles son los equipos", "no sé el nombre de la máquina", "qué opciones de máquina tengo"

    - listar_tipos_parada: el usuario quiere ver los tipos de parada o falla disponibles.
    Ejemplos: "qué tipos de falla hay", "muéstrame los códigos", "cuáles son las opciones de parada",
    "no sé qué tipo poner", "qué categorías de falla existen", "lista los códigos"

    - seleccionar_opcion: el usuario está eligiendo un elemento de una lista que el bot le mostró,
      o está respondiendo a una confirmación de selección (sí/no).
    Ejemplos: "la primera", "primera", "la 1", "1", "opcion 1", "segunda",
    "la segunda", "2", "tercera", "última", "la de arriba", "esa", "esa de alli",
    "la última", "esa misma", "esa máquina", "esa falla", "esa opción",
    "la que dije", "la primera opción", "número 1",
    "sí", "si", "confirmo", "no", "cancelar selección"
    SOLO aplicar si el bot mostró una lista recientemente o hay una selección pendiente de confirmación.

    - otro: el mensaje no encaja en ninguna categoría anterior.

    Mensaje del usuario: "{last_message}"

    ¿El bot mostró una lista recientemente?: {'sí' if has_list_shown else 'no'}
    ¿Hay una selección pendiente de confirmación?: {'sí' if has_pending_selection else 'no'}

    Responde ÚNICAMENTE con una de estas palabras exactas, sin puntuación ni explicación:
    saludo | reportar_falla | completar_reporte | cancelar | listar_maquinas | listar_tipos_parada | seleccionar_opcion | otro
    """

    response = llm.invoke(prompt)
    intent = response.content.strip().lower().rstrip(".,;:")

    if intent not in VALID_INTENTS:
        intent = "otro"

    return {"intent": intent}


def greeting_handler(state: ReportState) -> dict:
    """Respond to user greetings and prompt for action."""
    logger.info("Greeting user...")

    response = (
        "¡Hola! Soy Lens, tu asistente de mantenimiento. "
        "\n¿Quieres reportar un incidente con alguna maquina?"
    )

    return {
        "messages": [AIMessage(response)],
        "intent": None,
    }


def report_handler(state: ReportState) -> dict:
    """Extract field updates from the user's message for an active report."""
    logger.info("Reporting or updating an issue...")

    last_message = state["messages"][-1].content

    current_fields = {
        "id_maquina": state.get("id_maquina"),
        "tipo_parada_texto": state.get("tipo_parada_texto"),
        "turno": state.get("turno"),
        "tiempo_parada_horas": state.get("tiempo_parada_horas"),
        "observaciones": state.get("observaciones"),
    }

    prompt = f"""
    Eres un asistente de registro de mantenimiento industrial.

    CAMPOS YA RECOPILADOS (no los repitas, solo actualiza si el usuario corrige):
    {current_fields}

    NUEVO MENSAJE DEL OPERARIO:
    "{last_message}"

    Extrae SOLO los campos que el operario menciona en este mensaje.
    Si el usuario está corrigiendo un campo ya recopilado, actualízalo.
    Si no menciona un campo, devuélvelo como null (aunque ya estuviera lleno).
    No inventes datos.
    """

    response = structured_llm.invoke(prompt)

    updated = {}
    for field in [
        "maquina_texto",
        "tipo_parada_texto",
        "turno",
        "tiempo_parada_horas",
        "observaciones",
        "prioridad",
    ]:
        nuevo = getattr(response, field, None)
        updated[field] = nuevo if nuevo is not None else state.get(field)

    return updated


def validator(state: ReportState) -> dict:
    """Validate that all required report fields are present."""
    logger.info("Validating report fields...")

    missing = [f for f in REQUIRED_FIELDS if not state.get(f)]

    if missing:
        next_field = missing[0]
        return {
            "missing_fields": missing,
            "is_complete": False,
            "messages": [AIMessage(content=QUESTIONS[next_field])],
        }

    return {
        "missing_fields": [],
        "is_complete": True,
    }


def mapper(state: ReportState) -> dict:
    """Map user-provided text to database IDs for machines and failure types."""
    logger.info("Mapping fields to database IDs...")

    result = {}

    texto_maquina = state.get("maquina_texto")
    if texto_maquina:
        maquinas = get_maquinas()
        tokens = [
            t
            for t in texto_maquina.lower().split()
            if t not in STOP_WORDS and len(t) >= 3
        ]

        for m in maquinas:
            nombre = m["nombre_maquina"].lower()
            id_maq = m["id_maquina"].lower()
            if any(token in nombre or token in id_maq for token in tokens):
                result["id_maquina"] = m["id_maquina"]
                break

    tipo_parada_texto = state.get("tipo_parada_texto")
    if tipo_parada_texto:
        tipos = get_tipos_parada()
        match = next(
            (t for t in tipos if t["codigo"] == tipo_parada_texto.strip()), None
        )

        if not match:
            tokens = [
                t
                for t in tipo_parada_texto.lower().split()
                if t not in STOP_WORDS and len(t) >= 3
            ]
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


def ask_observations(state: ReportState) -> dict:
    """Ask user if they want to add observations before submitting."""
    logger.info("Asking about observations...")

    pending = state.get("pending_observation")

    # No obsevaciones and no pending flag → ask
    if pending is None:
        if state.get("observaciones"):
            return {"pending_observation": "done"}
        return {
            "pending_observation": "ask",
            "messages": [AIMessage(content="\u00bfDeseas agregar alguna observaci\u00f3n adicional? (s\u00ed o no)")],
        }

    # User responded to the first question (yes/no)
    if pending == "ask":
        last_message = state["messages"][-1].content
        prompt = f"""
        El usuario dijo: "{last_message}"
        El bot preguntó si quiere agregar una observación al reporte.
        ¿El usuario está diciendo que sí (quiere agregar) o que no (no quiere)?

        Responde SOLO con: si o no
        Si no se entiende: ?
        """
        try:
            response = llm.invoke(prompt)
            decision = response.content.strip().lower().rstrip(".,;!")
        except Exception:
            decision = "?"

        if decision == "si":
            return {
                "pending_observation": "text",
                "messages": [AIMessage(content="\u00bfQu\u00e9 observaci\u00f3n deseas agregar?")],
            }
        elif decision == "no":
            return {"pending_observation": "done"}
        else:
            return {
                "messages": [AIMessage(content="No entend\u00ed. \u00bfDeseas agregar una observaci\u00f3n? Responde s\u00ed o no.")],
            }

    # User provided the observation text
    if pending == "text":
        last_message = state["messages"][-1].content
        return {
            "observaciones": last_message,
            "pending_observation": "done",
        }

    # Shouldn't reach here
    return {"pending_observation": None}


def submit_for_approval(state: ReportState) -> dict:
    """Save report with pending status and notify supervisor."""
    logger.info("Submitting report for supervisor approval...")

    registro = crear_registro_parada(
        id_maquina=state.get("id_maquina"),
        id_tipo_parada=state.get("id_tipo_parada"),
        turno=state.get("turno"),
        tiempo_parada_horas=state.get("tiempo_parada_horas"),
        observaciones=state.get("observaciones"),
        registrado_por=state.get("user_id"),
        prioridad=state.get("prioridad"),
        status="pending",
    )

    ticket_id = str(registro.get("id_registro_parada", "???"))

    prioridad_texto = (state.get("prioridad") or "").lower()
    emoji_prioridad = PRIORITY_EMOJI.get(prioridad_texto, "\u26AA")

    operator_msg = (
        f"\U0001F4CB Resumen del incidente:\n\n"
        f"\U0001F527 M\u00e1quina: {state.get('id_maquina')}\n"
        f"\u26A1 Falla: {state.get('tipo_parada_texto')}\n"
        f"\U0001F550 Turno: {state.get('turno')} | \u23F1 Duraci\u00f3n: {state.get('tiempo_parada_horas')}h\n"
        f"{emoji_prioridad} Prioridad: {state.get('prioridad', 'No especificada')}\n"
        f"\U0001F4DD Obs: {state.get('observaciones') or 'Ninguna'}\n\n"
        f"\U0001F4DD Reporte #{ticket_id} enviado para aprobaci\u00f3n.\n\n"
        f"Tu reporte est\u00e1 en espera de que un supervisor lo revise.\n"
        f"Puedes hacer otro reporte mientras tanto si lo necesitas."
    )

    supervisor_msg = (
        f"\U0001F477 Nuevo reporte de avería para aprobación\n\n"
        f"Ticket: #{ticket_id}\n"
        f"Operario: {state.get('user_id')}\n"
        f"Máquina: {state.get('id_maquina')}\n"
        f"Falla: {state.get('tipo_parada_texto')}\n"
        f"Turno: {state.get('turno')}\n"
        f"Duración: {state.get('tiempo_parada_horas')} horas\n"
        f"Prioridad: {state.get('prioridad')}\n\n"
        f"Responde: APROBAR {ticket_id}, RECHAZAR {ticket_id}, o LISTA para ver pendientes."
    )

    # Send supervisor notification directly (before restart clears state)
    if SUPERVISOR_WHATSAPP:
        try:
            send_whatsapp_message_sync(SUPERVISOR_WHATSAPP, supervisor_msg)
        except Exception:
            logger.exception("Failed to send supervisor notification")

    reset = dict(RESET_FIELDS)
    reset["messages"] = [AIMessage(content=operator_msg)]

    return reset


def handle_selection(state: ReportState) -> dict:
    """Handle user selection from a displayed list, with confirmation step."""
    logger.info("Handling selection from list...")

    pending = state.get("pending_selection_item")

    # ── 2do llamado: usuario respondió a la confirmación ──
    if pending:
        logger.info("Processing confirmation for pending selection")
        try:
            pending_data = json.loads(pending)
        except Exception:
            pending_data = None

        last_message = state["messages"][-1].content

        prompt = f"""
        El usuario dijo: "{last_message}"

        El bot preguntó si confirma la selección de un elemento.
        ¿El usuario está confirmando (sí, dale, confirmo, ok, correcto, adelante)
        o rechazando (no, cancelar, otra, mejor no, equivoqué)?

        Responde SOLO con: si o no
        Si no se entiende: ?
        """

        try:
            response = llm.invoke(prompt)
            decision = response.content.strip().lower().rstrip(".,;!")
        except Exception:
            decision = "?"

        if decision == "si":
            result = {}
            if pending_data and pending_data.get("field_type") == "maquinas":
                result["id_maquina"] = pending_data["id"]
                result["maquina_texto"] = pending_data["name"]
            elif pending_data and pending_data.get("field_type") == "tipos_parada":
                result["id_tipo_parada"] = pending_data["id"]
                result["tipo_parada_texto"] = pending_data["description"]

            result["pending_selection_item"] = None
            result["last_list_items"] = None
            result["last_list_type"] = None

            # Continuar con el flujo de validator: preguntar siguiente campo faltante
            merged = dict(state)
            merged.update(result)
            missing = [f for f in REQUIRED_FIELDS if not merged.get(f)]
            if missing:
                result["missing_fields"] = missing
                result["is_complete"] = False
                result["messages"] = [AIMessage(content=QUESTIONS[missing[0]])]
            else:
                result["missing_fields"] = []
                result["is_complete"] = True

            return result

        elif decision == "no":
            result = {"pending_selection_item": None}
            if pending_data and pending_data.get("field_type") == "maquinas":
                result["messages"] = [AIMessage(content="\u00bfEn qu\u00e9 m\u00e1quina ocurri\u00f3 la falla?")]
            elif pending_data and pending_data.get("field_type") == "tipos_parada":
                result["messages"] = [AIMessage(content="\u00bfQu\u00e9 tipo de falla fue?\n\nPuedes describirla o poner su c\u00f3digo.")]
            else:
                result["messages"] = [AIMessage(content="Selecci\u00f3n cancelada.")]
            return result

        else:
            return {
                "messages": [AIMessage(content="No entend\u00ed tu respuesta. \u00bfConfirmas la selecci\u00f3n? Responde s\u00ed o no.")],
            }

    # ── 1er llamado: usuario dio un ordinal ──
    last_list_type = state.get("last_list_type")
    last_list_items = state.get("last_list_items")

    if not last_list_type or not last_list_items:
        return {
            "messages": [
                AIMessage(
                    content="Primero necesito mostrarte una lista. \u00bfQuieres ver m\u00e1quinas disponibles o tipos de parada?"
                )
            ]
        }

    try:
        items = json.loads(last_list_items)
    except Exception:
        items = []

    if not items:
        return {"messages": [AIMessage(content="No hay elementos en la lista.")]}

    last_message = state["messages"][-1].content

    items_str = "\n".join(
        f"{i}. {item.get('name') or item.get('description') or item.get('code', '?')}"
        for i, item in enumerate(items, 1)
    )

    prompt = f"""
    El usuario dijo: "{last_message}"

    Lista numerada mostrada al usuario:
    {items_str}

    \u00bfQu\u00e9 opci\u00f3n est\u00e1 seleccionando el usuario?
    Responde SOLO con el n\u00famero de opci\u00f3n (1-based). Si no se entiende o no corresponde: 0
    """

    try:
        response = llm.invoke(prompt)
        index_str = response.content.strip().rstrip(".,;!")
        index = int(index_str) - 1
    except Exception:
        index = -1

    if index < 0 or index >= len(items):
        return {
            "messages": [
                AIMessage(
                    content=f"No entend\u00ed cu\u00e1l elegiste. Responde con un n\u00famero del 1 al {len(items)}."
                )
            ]
        }

    selected = items[index]

    if last_list_type == "maquinas":
        name = f"{selected['id']} \u2014 {selected['name']}"
        field_type = "maquinas"
    elif last_list_type == "tipos_parada":
        name = f"{selected['code']} \u2014 {selected['description']}"
        field_type = "tipos_parada"
    else:
        name = selected.get("name") or selected.get("description", "?")
        field_type = last_list_type

    return {
        "messages": [AIMessage(content=f"Seleccionaste {name}. \u00bfConfirmas?")],
        "pending_selection_item": json.dumps({
            "field_type": field_type,
            "id": selected.get("id"),
            "name": selected.get("name"),
            "code": selected.get("code"),
            "description": selected.get("description"),
        }, ensure_ascii=False),
    }


def cancel_report(state: ReportState) -> dict:
    """Cancel the current report and notify the user."""
    logger.info("Report canceled.")

    return {
        "messages": [
            AIMessage(
                content="\u274C Reporte cancelado. Puedes empezar uno nuevo cuando quieras."
            )
        ]
    }


def restart(state: ReportState) -> dict:
    """Reset report-related state fields for a fresh session."""
    logger.info("Restarting state for new report...")

    return dict(RESET_FIELDS)


def list_machines(state: ReportState) -> dict:
    """List all available machines grouped by cell."""
    maquinas = get_maquinas()
    if not maquinas:
        return {"messages": [AIMessage(content="\u26A0️ No hay máquinas registradas.")]}

    por_celula: dict[str, list] = defaultdict(list)
    for m in maquinas:
        celula = m.get("celula") or "Sin célula"
        por_celula[celula].append(m)

    items_data = []
    lineas = ["\U0001F3ED Máquinas disponibles:\n"]
    for celula, maquinas_celula in por_celula.items():
        lineas.append(f"\U0001F4E6 {celula}")
        for m in maquinas_celula:
            lineas.append(f"  • {m['id_maquina']} — {m['nombre_maquina']}")
            items_data.append({
                "id": m["id_maquina"],
                "name": m["nombre_maquina"],
                "celula": celula,
            })
        lineas.append("")

    return {
        "messages": [AIMessage(content="\n".join(lineas))],
        "last_list_type": "maquinas",
        "last_list_items": json.dumps(items_data, ensure_ascii=False),
    }


def list_failures(state: ReportState) -> dict:
    """List all available failure types grouped by OEE category."""
    tipos = get_tipos_parada()
    if not tipos:
        return {
            "messages": [
                AIMessage(content="\u26A0️ No hay tipos de parada registrados.")
            ]
        }

    items_data = []
    por_categoria: dict[str, list] = defaultdict(list)
    for t in tipos:
        categoria = t.get("categoria_oee") or "Otra"
        por_categoria[categoria].append(t)

    lineas = ["\u26A1 Tipos de parada disponibles:\n"]
    for categoria, tipos_cat in por_categoria.items():
        emoji = CATEGORY_EMOJI.get(categoria, "\u26AA")
        lineas.append(f"{emoji} {categoria}")
        for t in tipos_cat:
            lineas.append(f"  • {t['codigo']} — {t['descripcion']}")
            items_data.append({
                "id": t["id_tipo_parada"],
                "code": t["codigo"],
                "description": t["descripcion"],
                "category": categoria,
            })
        lineas.append("")

    return {
        "messages": [AIMessage(content="\n".join(lineas))],
        "last_list_type": "tipos_parada",
        "last_list_items": json.dumps(items_data, ensure_ascii=False),
    }


def fallback(state: ReportState) -> dict:
    """Handle unrecognized intents with a contextual and charismatic response."""
    messages = state.get("messages", [])
    last_message = messages[-1].content if messages else ""

    prompt = f"""Eres Lens, un asistente de mantenimiento industrial con personalidad.
Eres experto en inteligencia operacional y plantas manufactureras,
pero siempre respondes con carisma y buen humor.

El usuario escribió: "{last_message}"

PERSONALIDAD:
- Sé natural, como un compañero de trabajo experto y buena onda
- Si el contexto lo permite, agrega un comentario ingenioso o una
  expresión creativa relacionada al mundo industrial
- Usa un tono conversacional, sin ser robótico
- Mantén siempre el foco en ayudar

LO QUE PUEDES HACER:
- Registrar fallas de máquinas (pídele que te diga la máquina, tipo de falla, turno y tiempo parado)
- Mostrar máquinas disponibles
- Mostrar tipos de parada

Sé conciso: máximo 3 líneas."""

    response = llm.invoke(prompt)
    return {"messages": [AIMessage(content=response.content)]}
