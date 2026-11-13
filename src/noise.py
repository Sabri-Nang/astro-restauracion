"""Degradación gaussiana reproducible sobre copias RGB, sin modelos de IA."""

import math

import numpy as np
from PIL import Image


def add_gaussian_noise(
    reference: Image.Image, *, sigma: float = 0.03, seed: int = 123,
) -> tuple[Image.Image, dict]:
    """Suma muestras independientes N(0, sigma²) en RGB normalizado a [0, 1].

    El recorte y la cuantización modifican la distribución final, especialmente
    cerca de negro y blanco. No se simulan electrones, ADC ni ruido de un sensor.
    """
    if reference.mode != "RGB":
        raise ValueError("El ruido requiere una referencia RGB de 8 bits.")
    if not math.isfinite(sigma) or not 0 <= sigma <= 1:
        raise ValueError("Sigma debe ser finito y estar entre 0 y 1, en escala normalizada.")
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= 2**32 - 1:
        raise ValueError("La semilla del ruido debe ser un entero entre 0 y 4294967295.")
    rng = np.random.Generator(np.random.PCG64(seed))
    values = np.asarray(reference, dtype=np.float64) / 255.0
    noise = rng.normal(loc=0.0, scale=sigma, size=values.shape)
    unbounded = values + noise
    noisy = np.rint(np.clip(unbounded, 0.0, 1.0) * 255.0).astype(np.uint8)
    metadata = {
        "tipo": "gaussiano_aditivo",
        "media_teorica": 0.0,
        "sigma_normalizada": float(sigma),
        "sigma_equivalente_8bits": float(sigma * 255),
        "semilla_ruido": seed,
        "generador": "PCG64",
        "numpy": np.__version__,
        "escala_calculo": [0.0, 1.0],
        "canales": "RGB; muestra independiente por píxel y canal",
        "aplicacion": "Después del redimensionamiento; sobre valores RGB publicados, sin linealización",
        "recorte": "clip [0, 1] antes de redondear al entero más cercano y convertir a uint8",
        "fraccion_muestras_recortadas_inferior": float(np.mean(unbounded < 0)),
        "fraccion_muestras_recortadas_superior": float(np.mean(unbounded > 1)),
        "advertencia": "Degradación sintética; no representa una calibración física del sensor.",
    }
    return Image.fromarray(noisy), metadata
