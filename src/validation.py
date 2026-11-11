"""Validación básica de cinco imágenes para cerrar la etapa 2 del proyecto."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

from src.diffusion import MODEL_ID, MODEL_REVISION, run_diffusion


EXAMPLE_NAMES = (
    "potw1803a.tif",
    "potw1428a.tif",
    "heic0503a.tif",
    "heic1520a.tif",
    "potw1408a.tif",
)


def validate_examples(input_dir: Path, output_dir: Path, device: str = "auto") -> dict:
    """Procesa las cinco entradas y registra éxitos y errores individualmente."""
    missing = [name for name in EXAMPLE_NAMES if not (input_dir / name).is_file()]
    if missing:
        raise ValueError("Faltan imágenes de ejemplo: " + ", ".join(missing))
    output_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "etapa": "2 — Prototipo básico",
        "iniciado_utc": datetime.now(timezone.utc).isoformat(),
        "modelo": MODEL_ID,
        "revision_modelo": MODEL_REVISION,
        "criterio": "Cinco entradas diferentes procesadas; no evalúa denoising ni autenticidad",
        "resultados": [],
        "completada": False,
    }

    def save_report():
        temporary = output_dir / "resumen.tmp"
        temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(output_dir / "resumen.json")

    save_report()
    for index, name in enumerate(EXAMPLE_NAMES, start=1):
        print(f"[{index}/5] Procesando {name}", flush=True)
        result = {"imagen": name, "estado": "error"}
        try:
            prepared, processed, metadata = run_diffusion(
                input_dir / name, strength=0.5, steps=4, seed=42,
                max_size=256, device=device,
            )
            if prepared.size != processed.size:
                raise ValueError("La salida tiene dimensiones diferentes a la entrada preparada.")
            if max(ImageStat.Stat(processed).stddev) == 0:
                raise ValueError("La salida es uniforme; requiere revisión antes de aceptar la prueba.")
            folder = output_dir / Path(name).stem
            folder.mkdir(exist_ok=True)
            prepared.save(folder / "entrada_preparada.png")
            processed.save(folder / "salida.png")
            metadata["diferencia_con_entrada"] = ImageChops.difference(prepared, processed).getbbox() is not None
            metadata["sha256_salida_png"] = hashlib.sha256((folder / "salida.png").read_bytes()).hexdigest()
            metadata["evaluacion_visual"] = "Pendiente de revisión humana; ejecución técnica verificada"
            (folder / "parametros.json").write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            # Ambas imágenes se presentan juntas para revisar cada caso.
            comparison = Image.new("RGB", (prepared.width * 2, prepared.height))
            comparison.paste(prepared, (0, 0))
            comparison.paste(processed, (prepared.width, 0))
            comparison.save(folder / "comparacion.png")
            result.update(
                estado="correcto", carpeta=folder.name,
                parametros=metadata,
                comparacion="Izquierda: entrada preparada; derecha: salida generativa",
            )
            print(f"[{index}/5] Correcto: {metadata['segundos_inferencia']:.3f} s de inferencia", flush=True)
        except (ValueError, OSError, RuntimeError) as error:
            result["error"] = str(error)
            print(f"[{index}/5] Error: {error}", flush=True)
        report["resultados"].append(result)
        save_report()
    successful = [item for item in report["resultados"] if item["estado"] == "correcto"]
    unique_inputs = {item["parametros"]["sha256_entrada"] for item in successful}
    report["completada"] = len(successful) == 5 and len(unique_inputs) == 5
    report["finalizado_utc"] = datetime.now(timezone.utc).isoformat()
    save_report()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=Path("assets/ejemplos/originales"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/etapa2"))
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    args = parser.parse_args()
    report = validate_examples(args.input_dir, args.output_dir, args.device)
    print(f"Validación de cinco imágenes completada: {report['completada']}", flush=True)
    if not report["completada"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
