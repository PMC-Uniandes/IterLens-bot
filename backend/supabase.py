from functools import lru_cache
from supabase import create_client, Client
from datetime import datetime

import os
import pytz

tz = pytz.timezone("America/Bogota")

@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    return create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_ANON_KEY")
    )

def get_tipos_parada():
    client = get_supabase_client()
    return (
        client.table("tipo_parada")
        .select("id_tipo_parada, codigo, descripcion, categoria_oee")
        .order("categoria_oee, codigo")
        .execute()
        .data
    )

def get_maquinas():
    client = get_supabase_client()
    data = (
        client.table("maquina")
        .select("id_maquina, nombre_maquina, celula(nombre_celula)")
        .eq("activa", True)
        .execute()
        .data
    )
    # Aplanar el dict anidado antes de retornar
    for m in data:
        if isinstance(m.get("celula"), dict):
            m["celula"] = m["celula"].get("nombre_celula", "Sin célula")
    return data

def crear_registro_parada(
    id_maquina: str,
    id_tipo_parada: str,
    turno: str,
    tiempo_parada_horas: float,
    observaciones: str = None,
    registrado_por: str = None,
):
    client = get_supabase_client()
    
    row = {
        "id_maquina":          id_maquina,
        "id_tipo_parada":      id_tipo_parada,
        "turno":               turno,
        "tiempo_parada_horas": float(tiempo_parada_horas),
        "fecha":               datetime.now(tz).date().isoformat(),
        "observaciones":       observaciones,
        "registrado_por":      registrado_por,
    }

    row = {k: v for k, v in row.items() if v is not None}

    result = client.table("registro_parada").insert(row).execute()
    return result.data[0] if result.data else {}