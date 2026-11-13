"""Comparación de píxeles y advertencias sobre la reconstrucción generativa."""

import numpy as np
from PIL import Image


DISCLAIMER = (
    "Imagen reconstruida por IA. El modelo puede borrar o inventar estructuras. "
    "Esta prueba no demuestra reducción de ruido ni autenticidad científica. "
    "La intensidad controla la transformación generativa, no el ruido eliminado."
)
DIFFERENCE_NOTICE = (
    "Mapa de diferencias absolutas entre la entrada preparada y la salida. "
    "Oscuro: pocos cambios; claro: cambios mayores. Escala fija de 0 a 255, "
    "sin amplificar el contraste. Muestra modificaciones de píxeles; no distingue "
    "ruido eliminado, detalles perdidos o estructuras inventadas."
)


def difference_map(original: Image.Image, processed: Image.Image) -> Image.Image:
    """Devuelve la media RGB de diferencias absolutas, redondeada a 8 bits.

    Exige dos imágenes RGB del mismo tamaño; no convierte ni redimensiona.
    La escala fija permite comparar mapas sin normalizarlos por imagen.
    """
    if original.mode != "RGB" or processed.mode != "RGB":
        raise ValueError("La comparación requiere dos imágenes RGB de 8 bits.")
    if original.size != processed.size:
        raise ValueError("La entrada preparada y la salida deben tener las mismas dimensiones.")
    # El entero con signo evita el desbordamiento al restar valores uint8.
    before = np.asarray(original, dtype=np.int16)
    after = np.asarray(processed, dtype=np.int16)
    differences = np.abs(after - before).mean(axis=2)
    return Image.fromarray(np.rint(differences).astype(np.uint8))
