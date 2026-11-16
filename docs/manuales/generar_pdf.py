"""Genera los PDF de los manuales a partir de su fuente HTML.

Uso:
    pip install playwright
    python docs/manuales/generar_pdf.py [manual_instalacion]

Imprime con el Chrome instalado en la máquina (no descarga navegadores).
El pie de página con la numeración lo arma Chromium al imprimir.
"""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

CARPETA = Path(__file__).resolve().parent

# Fuentes HTML que se pueden regenerar. El resto de los PDF de la carpeta
# todavía no tiene fuente en el repositorio.
MANUALES = {
    "manual_instalacion": "Manual de instalación",
}

PIE = """
<div style="width:100%;font-size:7.5pt;color:#8a858d;padding:0 16mm;
            font-family:Montserrat,system-ui,'Segoe UI',sans-serif;
            display:flex;justify-content:space-between;">
  <span>Bolsa de Trabajo · {titulo}</span>
  <span><span class="pageNumber"></span> / <span class="totalPages"></span></span>
</div>
"""


def generar(nombre: str) -> Path:
    titulo = MANUALES[nombre]
    origen = CARPETA / f"{nombre}.html"
    destino = CARPETA / f"{nombre}.pdf"
    if not origen.exists():
        raise SystemExit(f"No existe la fuente {origen}")

    with sync_playwright() as p:
        navegador = p.chromium.launch(channel="chrome")
        pagina = navegador.new_page()
        pagina.goto(origen.as_uri(), wait_until="networkidle")
        pagina.pdf(
            path=str(destino),
            format="A4",
            print_background=True,
            display_header_footer=True,
            header_template="<div></div>",
            footer_template=PIE.format(titulo=titulo),
            margin={"top": "18mm", "bottom": "18mm", "left": "16mm", "right": "16mm"},
        )
        navegador.close()
    return destino


def main() -> None:
    pedidos = sys.argv[1:] or list(MANUALES)
    for nombre in pedidos:
        if nombre not in MANUALES:
            raise SystemExit(f"Manual desconocido: {nombre}. Opciones: {', '.join(MANUALES)}")
        destino = generar(nombre)
        print(f"generado: {destino.relative_to(CARPETA.parents[1])}")


if __name__ == "__main__":
    main()
