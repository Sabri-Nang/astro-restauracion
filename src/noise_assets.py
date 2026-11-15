"""Conservación y reproducción verificable de imágenes gaussianas sin IA."""

from __future__ import annotations

import argparse
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform
import shutil
import zlib

from PIL import Image

from src.experiment import file_hash, save_json
from src.noise import add_gaussian_noise


def pixel_hash(image: Image.Image) -> str:
    """SHA-256 de bytes RGB en orden de filas; registrar también modo y tamaño."""
    return hashlib.sha256(image.tobytes()).hexdigest()


def archive_noise(experiment_dir: Path, source: Path, output_dir: Path) -> dict:
    """Copia referencia y ruido ya generados, sin duplicar variantes de codificación."""
    experiment_dir, source, output_dir = Path(experiment_dir), Path(source), Path(output_dir)
    if output_dir.exists():
        raise ValueError("El directorio de conservación ya existe; no se sobrescribirá.")
    manifest = json.loads((experiment_dir / "experimento.json").read_text(encoding="utf-8"))
    if manifest["tipo"] != "experimento_controlado_gaussiano":
        raise ValueError("Se requiere un experimento gaussiano registrado.")
    if file_hash(source) != manifest["sha256_original"]:
        raise ValueError("El original no coincide con el hash registrado.")
    images = {}
    for name in ("referencia_preparada.png", "entrada_ruidosa.png"):
        if file_hash(experiment_dir / name) != manifest["archivos_sha256"][name]:
            raise ValueError(f"El archivo {name} cambió desde su preparación.")
        with Image.open(experiment_dir / name) as image:
            if image.mode != "RGB" or list(image.size) != manifest["dimensiones"]:
                raise ValueError("El modo o las dimensiones difieren del experimento.")
            images[name] = {"sha256_archivo": file_hash(experiment_dir / name),
                            "sha256_pixeles_rgb": pixel_hash(image)}
    with Image.open(experiment_dir / "referencia_preparada.png") as reference:
        reproduced, _ = add_gaussian_noise(reference, sigma=manifest["ruido"]["sigma_normalizada"],
                                           seed=manifest["ruido"]["semilla_ruido"])
    if pixel_hash(reproduced) != images["entrada_ruidosa.png"]["sha256_pixeles_rgb"]:
        raise ValueError("Los parámetros no reproducen los píxeles del ruido conservado.")
    with Image.open(source) as original:
        source_info = {"archivo": source.name, "sha256": manifest["sha256_original"],
                       "formato": original.format, "dimensiones": list(original.size), "modo": original.mode}
    metadata = {
        "tipo": "activo_ruido_gaussiano_reproducible", "original": source_info,
        "procedencia": manifest["procedencia_declarada"], "dimensiones": manifest["dimensiones"],
        "modo": "RGB", "bits_por_canal": 8, "orden_arreglo": "alto, ancho, RGB; C",
        "archivos": images, "ruido": manifest["ruido"],
        "preparacion": {
            "orientacion": "ImageOps.exif_transpose antes de RGB", "conversion": "Pillow convert('RGB')",
            "lado_maximo": manifest["lado_maximo"], "interpolacion": "Pillow Image.Resampling.LANCZOS",
            "escala": "min(1, lado_maximo / max(ancho, alto))",
            "dimensiones_finales": "int(lado_original * escala) // 8 * 8 para cada lado",
            "recorte_espacial": False, "ampliacion": False, "linealizacion_color": False,
            "ruido_antes_o_despues": "Después de redimensionar; usar la referencia conservada",
        },
        "algoritmo_ruido": {
            "arreglo": "np.asarray(referencia, dtype=np.float64) / 255.0",
            "rng": "np.random.Generator(np.random.PCG64(semilla))",
            "muestreo": "rng.normal(loc=0.0, scale=sigma, size=(alto, ancho, 3))",
            "suma": "referencia_normalizada + ruido; muestras independientes por píxel y canal",
            "recorte": "np.clip(suma, 0.0, 1.0)", "cuantizacion": "np.rint(recorte * 255.0).astype(np.uint8)",
            "redondeo": "Al entero más cercano; empate al par (np.rint)",
        },
        "codificacion_salida": {"formato": "PNG", "compress_level": 6, "optimize": False,
                                  "metadata_png_adicional": False},
        "entorno_preparacion": {"python": manifest["python"], "numpy": manifest["ruido"]["numpy"],
                                "pillow": manifest["pillow"]},
        "entorno_verificacion": {"python": platform.python_version(), "numpy": version("numpy"),
                                 "pillow": version("pillow"), "zlib": zlib.ZLIB_RUNTIME_VERSION},
        "codigo_sha256": {name: file_hash(Path(__file__).parent / name)
                           for name in ("diffusion.py", "noise.py", "experiment.py", "noise_assets.py")},
        "pixeles_reproducidos_verificados": True,
        "alcance": "Degradación RGB sintética, sin calibración de sensor. La referencia puede tener ruido propio.",
        "nota_hashes": "El hash de píxeles identifica los datos RGB; el hash PNG también depende de codificación, metadata y versiones de compresión.",
    }
    output_dir.mkdir(parents=True, exist_ok=False)
    for name in ("referencia_preparada.png", "entrada_ruidosa.png", "experimento.json"):
        shutil.copy2(experiment_dir / name, output_dir / name)
    save_json(output_dir / "reproduccion.json", metadata)
    return metadata


def reproduce_noise(metadata_path: Path, output: Path) -> dict:
    """Regenera desde la referencia conservada y exige el mismo hash de píxeles."""
    metadata_path, output = Path(metadata_path), Path(output)
    if output.exists():
        raise ValueError("La salida ya existe; no se sobrescribirá.")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata["tipo"] != "activo_ruido_gaussiano_reproducible":
        raise ValueError("El registro no corresponde a un activo gaussiano.")
    reference_path = metadata_path.parent / "referencia_preparada.png"
    if file_hash(reference_path) != metadata["archivos"][reference_path.name]["sha256_archivo"]:
        raise ValueError("La referencia conservada cambió.")
    with Image.open(reference_path) as reference:
        if reference.mode != "RGB" or list(reference.size) != metadata["dimensiones"]:
            raise ValueError("El modo o tamaño de referencia es incompatible.")
        noisy, _ = add_gaussian_noise(reference, sigma=metadata["ruido"]["sigma_normalizada"],
                                     seed=metadata["ruido"]["semilla_ruido"])
    expected = metadata["archivos"]["entrada_ruidosa.png"]
    if pixel_hash(noisy) != expected["sha256_pixeles_rgb"]:
        raise ValueError("El entorno o los parámetros no reproducen los píxeles esperados.")
    output.parent.mkdir(parents=True, exist_ok=True)
    # Abrir exclusivamente impide sobrescribir incluso si otro proceso creó la ruta.
    with output.open("xb") as stream:
        noisy.save(stream, format="PNG", compress_level=6, optimize=False)
    return {"pixeles_identicos": True, "sha256_pixeles_rgb": pixel_hash(noisy),
            "sha256_archivo": file_hash(output),
            "png_identico": file_hash(output) == expected["sha256_archivo"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    archive = commands.add_parser("archive", help="Conservar un par existente y su procedencia")
    archive.add_argument("--experiment-dir", type=Path, required=True)
    archive.add_argument("--source", type=Path, required=True)
    archive.add_argument("--output-dir", type=Path, required=True)
    reproduce = commands.add_parser("reproduce", help="Reproducir el ruido desde su registro")
    reproduce.add_argument("--metadata", type=Path, required=True)
    reproduce.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = (archive_noise(args.experiment_dir, args.source, args.output_dir) if args.command == "archive"
              else reproduce_noise(args.metadata, args.output))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
