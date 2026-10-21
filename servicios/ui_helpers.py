"""Pequeñas utilidades visuales y de paginación de CurriculAi."""
from html import escape
import math
import re


def seguro(valor, limite=200):
    return escape(str(valor or "")[:limite], quote=True)


def pagina(registros, numero, por_pagina=4):
    total = max(1, math.ceil(len(registros) / por_pagina))
    numero = max(1, min(int(numero or 1), total))
    inicio = (numero - 1) * por_pagina
    return registros[inicio:inicio + por_pagina], numero, total


def es_finalista(entrevista):
    estado = str(entrevista.get('estado') or '').lower().strip()
    return 'finalista' in estado or 'aceptado' in estado


def telefono_mx(valor):
    digitos = re.sub(r'\D', '', str(valor or ''))
    if len(digitos) == 10:
        return '52' + digitos
    if len(digitos) == 12 and digitos.startswith('52'):
        return digitos
    return ''
