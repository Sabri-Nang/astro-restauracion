"""Ensayo gaussiano en dos fases: inspección sin IA y difusión explícita."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform
import shutil

from PIL import Image, ImageDraw

from src.diffusion import (
    CONTROLNET_TILE_ID, CONTROLNET_TILE_REVISION, DEFAULT_PROMPT, MODEL_ID,
    MODEL_REVISION, SafetyFilterBlockedError, prepare_image, run_diffusion,
)
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
    controlnet_tile: bool = False, controlnet_scale: float = 1.0,
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
    control_arguments = {"controlnet_tile": True, "controlnet_scale": controlnet_scale} if controlnet_tile else {}
    prepared, processed, diffusion_metadata = run_diffusion(
        experiment_dir / "entrada_ruidosa.png", strength=strength, steps=steps,
        seed=model_seed, max_size=manifest["lado_maximo"], device=device,
        **control_arguments,
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


def sweep_experiment(
    experiment_dir: str | Path, output_dir: str | Path, *, controlnet_tile: bool = True,
    controlnet_scale: float = 1.0, device: str = "cuda",
) -> dict:
    """Prueba cuatro intensidades sobre el mismo par gaussiano conservado.

    Fija 30 pasos y semilla IA 42. Exige sigma 0,03, semilla de ruido 123 y
    lado máximo 256. Un bloqueo de contenido se registra y no recibe métricas;
    otros errores interrumpen el barrido conservando los resultados anteriores.
    """
    experiment_dir, output_dir = Path(experiment_dir), Path(output_dir)
    if output_dir.exists():
        raise ValueError("La carpeta del barrido ya existe; elegí una nueva.")
    if device not in ("cuda", "cpu"):
        raise ValueError("Elegí un dispositivo explícito: cuda o cpu.")
    manifest = json.loads((experiment_dir / "experimento.json").read_text(encoding="utf-8"))
    if (manifest["tipo"] != "experimento_controlado_gaussiano"
            or manifest["ruido"]["sigma_normalizada"] != 0.03
            or manifest["ruido"]["semilla_ruido"] != 123 or manifest["lado_maximo"] != 256):
        raise ValueError("El barrido exige sigma 0,03, semilla de ruido 123 y lado máximo 256.")
    for name in ("referencia_preparada.png", "entrada_ruidosa.png"):
        if file_hash(experiment_dir / name) != manifest["archivos_sha256"][name]:
            raise ValueError(f"El archivo {name} cambió desde su preparación.")
    output_dir.mkdir(parents=True, exist_ok=False)
    for name in ("referencia_preparada.png", "entrada_ruidosa.png", "experimento.json"):
        shutil.copy2(experiment_dir / name, output_dir / name)
    strengths = (0.10, 0.15, 0.20, 0.25)
    report = {
        "tipo": "barrido_intensidades_gaussiano", "creado_utc": datetime.now(timezone.utc).isoformat(),
        "variante": "sd15_controlnet_tile" if controlnet_tile else "sd15_img2img",
        "condiciones_fijas": {
            "sigma": 0.03, "semilla_ruido": 123, "lado_maximo": 256,
            "sha256_original": manifest["sha256_original"], "dimensiones": manifest["dimensiones"],
            "sha256_entrada": file_hash(output_dir / "entrada_ruidosa.png"),
            "modelo": MODEL_ID, "revision_modelo": MODEL_REVISION,
            "prompt": DEFAULT_PROMPT, "scheduler": "DDIMScheduler", "guidance_scale": 1.0,
            "pasos_configurados": 30, "semilla_modelo": 42, "dispositivo": device,
            "controlnet": CONTROLNET_TILE_ID if controlnet_tile else None,
            "revision_controlnet": CONTROLNET_TILE_REVISION if controlnet_tile else None,
            "controlnet_scale": controlnet_scale if controlnet_tile else None,
            "condicion": "Misma entrada ruidosa; nunca la referencia" if controlnet_tile else None,
        },
        "intensidades": list(strengths), "resultados": [], "completada": False,
        "ejecucion_cerrada": False, "metricas_calculadas": False, "fase": "iniciado",
        "evaluacion": "Pendiente; el barrido no implica mejora de restauración.",
    }
    save_json(output_dir / "barrido.json", report)
    try:
        for strength in strengths:
            case = output_dir / f"intensidad_{strength:.2f}"
            print(f"Intensidad {strength:.2f}: 30 pasos, semilla IA 42, Tile={controlnet_tile}", flush=True)
            report["fase"] = f"ejecutando_{strength:.2f}"
            save_json(output_dir / "barrido.json", report)
            try:
                result = restore_experiment(
                    output_dir, case, strength=strength, steps=30, model_seed=42, device=device,
                    controlnet_tile=controlnet_tile, controlnet_scale=controlnet_scale,
                )
            except SafetyFilterBlockedError as error:
                report["resultados"].append({"intensidad": strength, "estado": "bloqueada_filtro_seguridad",
                                              "salida_guardada": False, "error": str(error)})
            else:
                for name in ("referencia_preparada.png", "entrada_ruidosa.png", "experimento.json"):
                    shutil.copy2(output_dir / name, case / name)
                report["resultados"].append({
                    "intensidad": strength, "estado": "correcto", "carpeta": case.name,
                    "sha256_salida": result["sha256_salida"],
                    "sha256_entrada_modelo": result["difusion"]["sha256_entrada"],
                    "pasos_efectivos": result["difusion"]["pasos_efectivos"],
                    "segundos_inferencia": result["difusion"]["segundos_inferencia"],
                })
            save_json(output_dir / "barrido.json", report)
        report["salidas_validas"] = sum(item["estado"] == "correcto" for item in report["resultados"])
        report["completada"] = report["salidas_validas"] == len(strengths)
        report["ejecucion_cerrada"] = True
        report["fase"] = "barrido_ejecutado_evaluacion_pendiente"
    except BaseException as error:
        report["fase"] = "interrumpido"
        report["error"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        report["finalizado_o_interrumpido_utc"] = datetime.now(timezone.utc).isoformat()
        save_json(output_dir / "barrido.json", report)
    return report


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
    restore.add_argument("--controlnet-tile", action="store_true")
    restore.add_argument("--controlnet-scale", type=float, default=1.0)
    sweep = commands.add_parser("sweep", help="Probar 0,10/0,15/0,20/0,25 sin cambiar la entrada gaussiana")
    sweep.add_argument("--experiment-dir", type=Path, required=True)
    sweep.add_argument("--output-dir", type=Path, required=True)
    sweep.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    sweep.add_argument("--controlnet-tile", action="store_true")
    sweep.add_argument("--controlnet-scale", type=float, default=1.0)
    args = parser.parse_args()
    if args.phase == "prepare":
        provenance = json.loads(args.provenance.read_text(encoding="utf-8")) if args.provenance else None
        metadata = prepare_experiment(
            args.input, args.output_dir, sigma=args.sigma, noise_seed=args.noise_seed,
            max_size=args.size, provenance=provenance,
        )
    elif args.phase == "restore":
        metadata = restore_experiment(
            args.experiment_dir, args.output_dir, strength=args.strength,
            steps=args.steps, model_seed=args.model_seed, device=args.device,
            controlnet_tile=args.controlnet_tile, controlnet_scale=args.controlnet_scale,
        )
    else:
        metadata = sweep_experiment(
            args.experiment_dir, args.output_dir, device=args.device,
            controlnet_tile=args.controlnet_tile, controlnet_scale=args.controlnet_scale,
        )
    print(json.dumps(metadata, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
