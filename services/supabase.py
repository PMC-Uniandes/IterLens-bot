"""Supabase database client and query functions."""

import logging
import os
from datetime import datetime
from functools import lru_cache
from typing import Any

import pytz
from supabase import Client, create_client

logger = logging.getLogger(__name__)

TZ = pytz.timezone(os.getenv("TIMEZONE", "America/Bogota"))


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """Return a cached Supabase client instance."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")

    if not supabase_url or not supabase_key:
        logger.error("SUPABASE_URL or SUPABASE_ANON_KEY not configured")
        raise ValueError("Supabase credentials not configured")

    return create_client(supabase_url, supabase_key)


def get_tipos_parada() -> list[dict[str, Any]]:
    """Retrieve all stop/failure types from the database."""
    client = get_supabase_client()
    return (
        client.table("tipo_parada")
        .select("id_tipo_parada, codigo, descripcion, categoria_oee")
        .order("categoria_oee, codigo")
        .execute()
        .data
    )


def get_maquinas() -> list[dict[str, Any]]:
    """Retrieve all active machines with their cell information."""
    client = get_supabase_client()
    data = (
        client.table("maquina")
        .select("id_maquina, nombre_maquina, celula(nombre_celula)")
        .eq("activa", True)
        .execute()
        .data
    )
    for m in data:
        if isinstance(m.get("celula"), dict):
            m["celula"] = m["celula"].get("nombre_celula", "Sin célula")
    return data


def crear_registro_parada(
    id_maquina: str,
    id_tipo_parada: str,
    turno: str,
    tiempo_parada_horas: float,
    observaciones: str | None = None,
    registrado_por: str | None = None,
) -> dict[str, Any]:
    """Create a new stop/failure report record in the database."""
    client = get_supabase_client()

    row = {
        "id_maquina": id_maquina,
        "id_tipo_parada": id_tipo_parada,
        "turno": turno,
        "tiempo_parada_horas": float(tiempo_parada_horas) if tiempo_parada_horas is not None else 0.0,
        "fecha": datetime.now(TZ).date().isoformat(),
        "observaciones": observaciones,
        "registrado_por": registrado_por,
    }

    row = {k: v for k, v in row.items() if v is not None}

    result = client.table("registro_parada").insert(row).execute()
    return result.data[0] if result.data else {}
