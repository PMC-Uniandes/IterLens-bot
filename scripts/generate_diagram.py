#!/usr/bin/env python3
"""Script to generate a PNG diagram of the LangGraph workflow."""

import logging
import sys

from dotenv import load_dotenv

from src.graph import build_graph

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    """Generate a visual diagram of the LangGraph state machine."""
    load_dotenv()

    graph = build_graph()

    try:
        png_data = graph.get_graph().draw_mermaid_png()
        output_path = "langgraph_diagram.png"
        with open(output_path, "wb") as f:
            f.write(png_data)
        logger.info("PNG diagram generated: %s", output_path)

    except Exception as e:
        logger.warning("PNG generation failed: %s", e)
        logger.info("Generating fallback formats...")

        try:
            ascii_diagram = graph.get_graph().draw_ascii()
            print("\nASCII Diagram:")
            print(ascii_diagram)

            mermaid_code = graph.get_graph().to_mermaid()
            with open("langgraph_diagram.md", "w") as f:
                f.write("# Diagrama de LangGraph\n\n")
                f.write("```mermaid\n")
                f.write(mermaid_code)
                f.write("\n```\n")

            logger.info("Mermaid diagram saved to langgraph_diagram.md")
            logger.info("Visualize at: https://mermaid.live/")

        except Exception as e2:
            logger.error("Fallback also failed: %s", e2)
            sys.exit(1)


if __name__ == "__main__":
    main()
