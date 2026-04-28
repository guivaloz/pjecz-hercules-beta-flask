"""
Clean HTML
"""

import re

from lxml.html.clean import Cleaner

# HTML tags y classes permitidos en el contenido de los oficios
ALLOWED_TAGS = [
    "b",
    "i",
    "u",
    "em",
    "strong",
    "p",
    "br",
    "ul",
    "ol",
    "li",
    "div",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
    "a",
    "img",
]

# Atributos permitidos en las etiquetas HTML
SAFE_ATTRS = [
    "style",  # for p, div, th, td, img
    "class",  # for table
    "role",  # for table
    "border",  # for table
    "colspan",  # for th, td
    "rowspan",  # for th, td
    "width",  # for th, td
    "href",  # for a
    "src",  # for img
    "alt",  # for img
    "title",  # for img
    "height",  # for img
]

# Atributos de estilo permitidos, con valores específicos o patrones de valores (ej. números seguidos de "px" o "%")
SAFE_STYLES_REGEXP = [
    r"margin-bottom:[\d]+px;",
    r"margin:0 auto;",
    r"text-align:center;",
    r"text-align:left;",
    r"text-align:justify;",
    r"text-align:right;",
    r"vertical-align:bottom;",
    r"vertical-align:center;",
    r"vertical-align:top;",
    r"width:[\d]+%;",
]


# Función para limpiar el HTML usando lxml.html.clean
def clean_html(html: str) -> str:
    """Limpiar el HTML usando lxml.html.clean con las reglas definidas"""
    if html.strip() == "":
        return ""
    cleaner = Cleaner(
        style=False,
        allow_tags=ALLOWED_TAGS,
        safe_attrs_only=True,
        safe_attrs=SAFE_ATTRS,
    )

    # Primero limpiar el HTML con lxml, lo que eliminará las etiquetas y atributos no permitidos,
    # pero mantendrá los estilos en el atributo style
    cleaned_html = cleaner.clean_html(html)

    # Luego procesar cada atributo en styles
    for style in re.findall(r'style="([^"]*)"', cleaned_html):
        # Separar las propiedades CSS individuales y filtrar solo las permitidas
        estilos_permitidos = []
        for propiedad in style.split(";"):
            propiedad = propiedad.strip()
            if propiedad == "":
                continue
            propiedad_con_punto_y_coma = propiedad + ";"
            for style_regexp in SAFE_STYLES_REGEXP:
                if re.fullmatch(style_regexp, propiedad_con_punto_y_coma):
                    estilos_permitidos.append(propiedad_con_punto_y_coma)
                    break
        # Reemplazar el atributo style por solo los estilos permitidos
        if estilos_permitidos:
            cleaned_html = cleaned_html.replace(f'style="{style}"', f'style="{" ".join(estilos_permitidos)}"')
        else:
            cleaned_html = cleaned_html.replace(f'style="{style}"', "")

    # Entregar el HTML limpio, con solo las etiquetas, atributos y estilos permitidos
    return cleaned_html
