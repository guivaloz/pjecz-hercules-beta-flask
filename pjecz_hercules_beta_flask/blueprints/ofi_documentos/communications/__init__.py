"""
Communications init
"""

import logging

bitacora = logging.getLogger(__name__)
bitacora.setLevel(logging.INFO)
formato = logging.Formatter("%(asctime)s:%(levelname)s:%(message)s")
empunadura = logging.FileHandler("logs/ofi_documentos_communications.log")
empunadura.setFormatter(formato)
bitacora.addHandler(empunadura)
