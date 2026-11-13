"""Comparación de píxeles y advertencias sobre la reconstrucción generativa."""

import math

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


def amplified_difference(raw: Image.Image, gain: float = 16) -> tuple[Image.Image, dict]:
    """Amplifica solo la visualización; conserva el mapa absoluto de entrada.

    Se usa una ganancia explícita, sin normalizar cada imagen por su máximo.
    Las estadísticas describen diferencias de píxeles, no calidad de restauración.
    """
    if raw.mode != "L":
        raise ValueError("La vista amplificada requiere un mapa en escala de grises.")
    if not math.isfinite(gain) or not 1 <= gain <= 64:
        raise ValueError("La ganancia visual debe estar entre 1 y 64.")
    values = np.asarray(raw, dtype=np.float64)
    amplified = values * gain
    stats = {
        "minimo_mapa_absoluto": int(values.min()),
        "maximo_mapa_absoluto": int(values.max()),
        "media_mapa_absoluto": float(values.mean()),
        "fraccion_pixeles_mapa_no_cero": float(np.mean(values > 0)),
        "ganancia_solo_visual": float(gain),
        "fraccion_pixeles_recortados_en_vista": float(np.mean(amplified > 255)),
        "interpretacion": "Estadísticas del mapa RGB medio redondeado a 8 bits; no son métricas de calidad ni autenticidad.",
    }
    return Image.fromarray(np.rint(np.clip(amplified, 0, 255)).astype(np.uint8)), stats
