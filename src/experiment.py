"""Ensayo gaussiano en dos fases: inspección sin IA y difusión explícita."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform

from PIL import Image, ImageDraw

from src.diffusion import prepare_image, run_diffusion
from src.honesty import DISCLAIMER, difference_map
from src.noise import add_gaussian_noise


def file_hash(path: Path) -> str:
    """Identifica el archivo exacto que se utilizó o generó."""
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def save_json(path: Path, data: dict) -> None:
    """Escribe el registro UTF-8 con un reemplazo atómico del archivo."""
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def comparison_strip(images: list[Image.Image], labels: list[str]) -> Image.Image:
    """Compone vistas con etiquetas sin modificar las imágenes de cálculo."""
    width, height = images[0].size
    strip = Image.new("RGB", (width * len(images), height + 28), "white")
    drawing = ImageDraw.Draw(strip)
    for index, (image, label) in enumerate(zip(images, labels, strict=True)):
        strip.paste(image, (index * width, 28))
        drawing.text((index * width + 4, 6), label, fill="black")
    return strip


def prepare_experiment(
    source: str | Path, output_dir: str | Path, *, sigma: float = 0.03,
    noise_seed: int = 123, max_size: int = 256, provenance: dict | None = None,
) -> dict:
    """Conserva la referencia común y genera ruido sin cargar difusión.

    Exige una carpeta nueva para no sobrescribir ensayos anteriores. La fuente
    original no se modifica. La procedencia declarada queda registrada, no validada.
    """
    source, output_dir = Path(source), Path(output_dir)
    reference = prepare_image(source, max_size)
    noisy, noise_metadata = add_gaussian_noise(reference, sigma=sigma, seed=noise_seed)
    source_hash = file_hash(source)
    output_dir.mkdir(parents=True, exist_ok=False)
    reference.save(output_dir / "referencia_preparada.png")
    noisy.save(output_dir / "entrada_ruidosa.png")
    difference_map(reference, noisy).save(output_dir / "diferencias_referencia_ruido.png")
    comparison_strip([reference, noisy], ["Referencia preparada", "Con ruido gaussiano"]).save(
        output_dir / "comparacion_referencia_ruido.png"
    )
    metadata = {
        "tipo": "experimento_controlado_gaussiano",
        "fase": "ruido_preparado_sin_inferencia",
        "creado_utc": datetime.now(timezone.utc).isoformat(),
        "entrada_original": source.name,
        "sha256_original": source_hash,
        "procedencia_declarada": provenance or {
            "registro": "assets/ejemplos/README.md",
            "nota": "Consultar el registro si corresponde a un ejemplo; completar fuente, crédito y licencia antes de compartir otra imagen.",
        },
        "dimensiones": list(reference.size),
        "modo": "RGB",
        "python": platform.python_version(),
        "pillow": version("pillow"),
        "lado_maximo": max_size,
        "preparacion": "RGB 8 bits, LANCZOS, sin recorte ni ampliación, lados múltiplos de ocho",
        "ruido": noise_metadata,
        "archivos_sha256": {
            name: file_hash(output_dir / name)
            for name in ("referencia_preparada.png", "entrada_ruidosa.png")
        },
        "alcance_referencia": "Referencia para esta degradación sintética; no se supone libre de ruido ni científicamente perfecta.",
        "evaluacion_visual": "Pendiente: revisar fondo, estrellas tenues y estructuras difusas antes de ejecutar difusión.",
        "inferencia_ejecutada": False,
    }
    save_json(output_dir / "experimento.json", metadata)
    return metadata


def restore_experiment(
    experiment_dir: str | Path, output_dir: str | Path, *, strength: float = 0.2,
    steps: int = 30, model_seed: int = 42, device: str = "cuda",
) -> dict:
    """Procesa exactamente la entrada ruidosa guardada, con semilla IA separada."""
    experiment_dir, output_dir = Path(experiment_dir), Path(output_dir)
    if output_dir.exists():
        raise ValueError("La carpeta de salida ya existe; elegí otra para conservar cada ejecución.")
    manifest_path = experiment_dir / "experimento.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["tipo"] != "experimento_controlado_gaussiano":
        raise ValueError("El registro no corresponde a un experimento gaussiano.")
    for name in ("referencia_preparada.png", "entrada_ruidosa.png"):
        if file_hash(experiment_dir / name) != manifest["archivos_sha256"][name]:
            raise ValueError(f"El archivo {name} cambió desde la preparación; no se ejecutará difusión.")
    with Image.open(experiment_dir / "referencia_preparada.png") as image:
        reference = image.copy()
    with Image.open(experiment_dir / "entrada_ruidosa.png") as image:
        noisy = image.copy()
    if reference.mode != "RGB" or noisy.mode != "RGB" or reference.size != noisy.size:
        raise ValueError("La referencia y la entrada ruidosa deben ser RGB del mismo tamaño.")
    prepared, processed, diffusion_metadata = run_diffusion(
        experiment_dir / "entrada_ruidosa.png", strength=strength, steps=steps,
        seed=model_seed, max_size=manifest["lado_maximo"], device=device,
    )
    if prepared.mode != noisy.mode or prepared.size != noisy.size or prepared.tobytes() != noisy.tobytes():
        raise ValueError("La difusión modificó la preparación de entrada; la comparación no sería equivalente.")
    changes = difference_map(noisy, processed)
    residual = difference_map(reference, processed)
    output_dir.mkdir(parents=True, exist_ok=False)
    processed.save(output_dir / "salida.png")
    changes.save(output_dir / "diferencias_ruido_salida.png")
    residual.save(output_dir / "diferencias_referencia_salida.png")
    comparison_strip(
        [reference, noisy, processed], ["Referencia preparada", "Entrada con ruido", "Salida de difusion"],
    ).save(output_dir / "comparacion_triple.png")
    # El pipeline no agrega ruido de evaluación: ya estaba en su archivo de entrada.
    diffusion_metadata = dict(diffusion_metadata)
    diffusion_metadata["ruido_artificial_agregado"] = True
    diffusion_metadata["origen_ruido_evaluacion"] = "Aplicado antes de difusión y registrado en el experimento"
    metadata = {
        "tipo": "ensayo_difusion_sobre_ruido_gaussiano",
        "inferencia_ejecutada": True,
        "fase": "difusion_ejecutada_evaluacion_visual_pendiente",
        "creado_utc": datetime.now(timezone.utc).isoformat(),
        "experimento": manifest,
        "sha256_registro_experimento": file_hash(manifest_path),
        "difusion": diffusion_metadata,
        "sha256_salida": file_hash(output_dir / "salida.png"),
        "evaluacion_visual": "Pendiente: comparar las tres vistas; registrar reducción aparente, pérdidas y posibles artefactos.",
        "interpretacion_mapas": "Ruido-salida muestra cambios del modelo; referencia-salida muestra diferencias respecto del objetivo sintético. Ninguno prueba autenticidad.",
        "advertencia": DISCLAIMER,
        "metricas_calculadas": False,
    }
    save_json(output_dir / "resultado.json", metadata)
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="phase", required=True)
    prepare = commands.add_parser("prepare", help="Generar e inspeccionar ruido sin cargar modelos")
    prepare.add_argument("--input", type=Path, required=True)
    prepare.add_argument("--output-dir", type=Path, required=True)
    prepare.add_argument("--sigma", type=float, default=0.03)
    prepare.add_argument("--noise-seed", type=int, default=123)
    prepare.add_argument("--size", type=int, choices=(256, 512), default=256)
    prepare.add_argument("--provenance", type=Path, help="JSON con fuente, crédito y licencia declarados")
    restore = commands.add_parser("restore", help="Ejecutar difusión explícitamente sobre el ruido guardado")
    restore.add_argument("--experiment-dir", type=Path, required=True)
    restore.add_argument("--output-dir", type=Path, required=True)
    restore.add_argument("--strength", type=float, default=0.2)
    restore.add_argument("--steps", type=int, default=30)
    restore.add_argument("--model-seed", type=int, default=42)
    restore.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    args = parser.parse_args()
    if args.phase == "prepare":
        provenance = json.loads(args.provenance.read_text(encoding="utf-8")) if args.provenance else None
        metadata = prepare_experiment(
            args.input, args.output_dir, sigma=args.sigma, noise_seed=args.noise_seed,
            max_size=args.size, provenance=provenance,
        )
    else:
        metadata = restore_experiment(
            args.experiment_dir, args.output_dir, strength=args.strength,
            steps=args.steps, model_seed=args.model_seed, device=args.device,
        )
    print(json.dumps(metadata, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
