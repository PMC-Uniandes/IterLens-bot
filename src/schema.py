from pydantic import BaseModel, Field
from typing import Optional


class ExtractionSchema(BaseModel):
    maquina_texto: Optional[str] = Field(
        None,
        description=(
            "Nombre o identificador de la máquina afectada, tal como lo menciona el operario. "
            "Ejemplos: 'máquina 3', 'torno 2', 'M-04', 'la prensa', 'equipo 1'. "
            "No normalizar ni inventar — capturar exactamente lo que dijo."
        )
    )

    tipo_parada_texto: Optional[str] = Field(
        None,
        description=(
            "Descripción LITERAL de la falla tal como la menciona el operario. "
            "NO inferir, NO categorizar, NO completar con información que el usuario no dijo. "
            "Solo llenar si el usuario menciona explícitamente una causa o tipo de problema. "
            "Ejemplos válidos: 'corto circuito', 'se trabó la banda', 'falla eléctrica', '0008'. "
            "Ejemplos INVÁLIDOS — dejar null: 'se dañó', 'falló', 'tiene un problema', 'no funciona'. "
            "Estas frases son demasiado vagas y no describen una causa real."
        )
    )

    turno: Optional[str] = Field(
        None,
        description=(
            "Turno en que ocurrió la parada. Normalizar siempre a DIA, TARDE o NOCHE. "
            "DIA:   menciona mañana, madrugada, o una hora entre 00:00 y 11:59. "
            "TARDE: menciona tarde, o una hora entre 12:00 y 17:59. "
            "NOCHE: menciona noche, o una hora entre 18:00 y 23:59. "
            "Ejemplos: 'de mañana' → DIA, 'en la tarde' → TARDE, 'anoche' → NOCHE, "
            "'a las 3pm' → TARDE, 'a las 8am' → DIA, 'a las 11pm' → NOCHE."
        )
    )

    tiempo_parada_horas: Optional[float] = Field(
        None,
        description=(
            "Duración total de la parada expresada en horas como número decimal. "
            "Convertir cualquier unidad de tiempo mencionada. "
            "Ejemplos: 'dos horas' → 2.0, 'media hora' → 0.5, "
            "'90 minutos' → 1.5, 'un cuarto de hora' → 0.25, '3 horas y media' → 3.5. "
            "Si menciona solo minutos, dividir entre 60."
        )
    )

    prioridad: Optional[str] = Field(
        None,
        description=(
            "Urgencia o criticidad del incidente. Normalizar a: alta, media o baja. "
            "alta:  palabras como urgente, crítico, inmediato, paró la línea, ya, ahora. "
            "media: palabras como importante, pronto, afecta producción. "
            "baja:  palabras como cuando puedan, no es urgente, leve, menor. "
            "Ejemplos: 'es urgente' → alta, 'cuando puedan' → baja, 'hay que revisarlo pronto' → media."
        )
    )

    observaciones: Optional[str] = Field(
        None,
        description=(
            "Información adicional relevante que el operario menciona explícitamente "
            "y que no está contenida en los otros campos. "
            "No duplicar lo que ya está en tipo_parada_texto. "
            "Ejemplos: 'ya pasó antes esta semana', 'avisé al supervisor', "
            "'tiene mal olor', 'el técnico Juan ya lo revisó'. "
            "Si todo lo mencionado ya cabe en otros campos, dejar null."
        )
    )


class ConfirmationSchema(BaseModel):
    confirm: Optional[bool] = Field(None, description="True si confirma, False si cancela")