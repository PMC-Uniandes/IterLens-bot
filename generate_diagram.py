#!/usr/bin/env python3
"""
Script para generar un diagrama PNG del flujo de langgraph
"""

from dotenv import load_dotenv
from src.graph import build_graph

# Cargar variables de entorno
load_dotenv()

# Construir el gráfico
graph = build_graph()

try:
    # Generar la imagen PNG
    png_data = graph.get_graph().draw_mermaid_png()
    
    # Guardar la imagen
    output_path = "langgraph_diagram.png"
    with open(output_path, "wb") as f:
        f.write(png_data)
    
    print(f"✓ Diagrama PNG generado exitosamente: {output_path}")
    
except Exception as e:
    print(f"Error generando PNG: {e}")
    print("\nIntentando generar diagrama alternativo...")
    
    try:
        # Generar diagrama ASCII
        ascii_diagram = graph.get_graph().draw_ascii()
        print("\nDiagrama ASCII:")
        print(ascii_diagram)
        
        # Generar código Mermaid
        mermaid_code = graph.get_graph().to_mermaid()
        
        # Guardar el código Mermaid
        with open("langgraph_diagram.md", "w") as f:
            f.write("# Diagrama de LangGraph\n\n")
            f.write("```mermaid\n")
            f.write(mermaid_code)
            f.write("\n```\n")
        
        print("\n✓ Diagrama Mermaid guardado en: langgraph_diagram.md")
        print("Puedes visualizarlo en: https://mermaid.live/")
        
    except Exception as e2:
        print(f"Error: {e2}")
