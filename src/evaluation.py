"""Evalúa un barrido contra su referencia sintética verificada, sin inferencia."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from importlib.metadata import version
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from skimage.metrics import mean_squared_error, peak_signal_noise_ratio, structural_similarity

from src.experiment import file_hash, save_json


SSIM_OPTIONS = {
    "data_range": 1.0, "channel_axis": -1, "gaussian_weights": True,
    "sigma": 1.5, "use_sample_covariance": False, "K1": 0.01, "K2": 0.03,
}
REGIONS_POTW1803A = {
    "Fondo": (16, 16, 80, 80),
    "Galaxia superior": (116, 32, 180, 96),
    "Galaxia inferior": (96, 104, 160, 168),
    "Region puntual": (176, 112, 240, 176),
}


def load_rgb(path: Path) -> Image.Image:
    """Lee sin convertir, redimensionar ni normalizar el contraste."""
    with Image.open(path) as image:
        if image.mode != "RGB":
            raise ValueError(f"La imagen {path.name} debe ser RGB de 8 bits.")
        return image.copy()


def reference_metrics(reference: Image.Image, candidate: Image.Image) -> dict:
    """Compara con una referencia conocida, cuya procedencia debe verificar el llamador.

    RGB publicado, float64 en [0, 1], sin linealización ni registro geométrico.
    No se debe usar una toma ruidosa real como si fuera una referencia limpia.
    """
    if reference.mode != "RGB" or candidate.mode != "RGB" or reference.size != candidate.size:
        raise ValueError("Las imágenes deben ser RGB y tener las mismas dimensiones.")
    if min(reference.size) < 11:
        raise ValueError("SSIM gaussiano requiere al menos 11 píxeles por lado.")
    expected = np.asarray(reference, dtype=np.float64) / 255.0
    observed = np.asarray(candidate, dtype=np.float64) / 255.0
    mse = float(mean_squared_error(expected, observed))
    return {
        "mse_rgb_normalizado": mse,
        "psnr_db": float(peak_signal_noise_ratio(expected, observed, data_range=1.0)) if mse else None,
        "psnr_infinito": mse == 0,
        "ssim_rgb": float(structural_similarity(expected, observed, **SSIM_OPTIONS)),
    }


def crop_sheet(images: list[tuple[str, Image.Image]], regions: dict, output: Path) -> None:
    """Amplía los mismos recortes por vecino más cercano, solo para inspección."""
    try:
        font = ImageFont.truetype("arial.ttf", size=13)
    except OSError:
        font = ImageFont.load_default(size=13)
    width = len(images) * 192
    sheet = Image.new("RGB", (width, 76 + len(regions) * 230 + 82), "white")
    draw = ImageDraw.Draw(sheet)
    draw.text((8, 6), "Mismas regiones: recortes de 64 x 64 ampliados x3, vecino mas cercano", fill="black", font=font)
    draw.text((8, 26), "Valores calculados sobre pixeles originales; sin ajuste de brillo ni contraste.", fill="black", font=font)
    for index, (label, _) in enumerate(images):
        draw.text((index * 192 + 4, 52), label, fill="black", font=font)
    for row, (name, bounds) in enumerate(regions.items()):
        top = 76 + row * 230
        draw.text((8, top), f"{name}: {list(bounds)}; origen superior izquierdo; limite final excluido", fill="black", font=font)
        for column, (_, image) in enumerate(images):
            crop = image.crop(bounds)
            sheet.paste(crop.resize((192, 192), Image.Resampling.NEAREST), (column * 192, top + 24))
    bottom = 76 + len(regions) * 230
    for index, line in enumerate((
        "Fuente: esahubble.org/images/potw1803a/ | CC BY 4.0 | RGB, reduccion, ruido y difusion.",
        "Credito: NASA, ESA, and J. Comerford (University of Colorado-Boulder)",
        "Referencia sintetica; estas vistas no verifican autenticidad cientifica.",
    )):
        draw.text((8, bottom + index * 20), line, fill="black", font=font)
    sheet.save(output)


def evaluate_sweep(sweep_dir: Path, output_dir: Path, *, regions: dict | None = None) -> dict:
    """Verifica hashes y equivalencia de referencia antes de calcular las métricas.

    Guarda una evaluación nueva, sin modificar los registros de la ejecución.
    Los casos bloqueados no se sustituyen por imágenes negras ni reciben métricas.
    """
    sweep_dir, output_dir = Path(sweep_dir), Path(output_dir)
    if output_dir.exists():
        raise ValueError("La carpeta de evaluación ya existe; elegí otra para conservar el registro.")
    sweep = json.loads((sweep_dir / "barrido.json").read_text(encoding="utf-8"))
    experiment = json.loads((sweep_dir / "experimento.json").read_text(encoding="utf-8"))
    if sweep["tipo"] != "barrido_intensidades_gaussiano" or experiment["tipo"] != "experimento_controlado_gaussiano":
        raise ValueError("Se requiere el registro de un barrido con referencia sintética conocida.")
    for name in ("referencia_preparada.png", "entrada_ruidosa.png"):
        if file_hash(sweep_dir / name) != experiment["archivos_sha256"][name]:
            raise ValueError(f"El archivo {name} cambió desde su preparación.")
    reference = load_rgb(sweep_dir / "referencia_preparada.png")
    noisy = load_rgb(sweep_dir / "entrada_ruidosa.png")
    images = [("Entrada ruidosa", noisy)]
    sources = {"referencia_preparada.png": file_hash(sweep_dir / "referencia_preparada.png"),
               "entrada_ruidosa.png": file_hash(sweep_dir / "entrada_ruidosa.png")}
    omitted = []
    for item in sweep["resultados"]:
        if item["estado"] != "correcto":
            omitted.append({"intensidad": item["intensidad"], "estado": item["estado"]})
            continue
        relative = Path(item["carpeta"])
        if relative.is_absolute() or relative.drive or ".." in relative.parts:
            raise ValueError("La carpeta del ensayo debe permanecer dentro del barrido.")
        case = sweep_dir / relative
        result = json.loads((case / "resultado.json").read_text(encoding="utf-8"))
        for name, expected in (("salida.png", result["sha256_salida"]),
                               ("entrada_ruidosa.png", result["difusion"]["sha256_entrada"])):
            if file_hash(case / name) != expected:
                raise ValueError(f"El archivo {relative / name} cambió desde su ejecución.")
        if result["sha256_salida"] != item["sha256_salida"]:
            raise ValueError("El registro de salida no coincide con el barrido.")
        for name, expected in (("referencia_preparada.png", reference), ("entrada_ruidosa.png", noisy)):
            actual = load_rgb(case / name)
            if actual.size != expected.size or actual.tobytes() != expected.tobytes():
                raise ValueError("La referencia o el ruido difiere entre ensayos.")
        label = f"SD intensidad {item['intensidad']:.2f}"
        images.append((label, load_rgb(case / "salida.png")))
        sources[(relative / "salida.png").as_posix()] = result["sha256_salida"]
    if regions:
        for bounds in regions.values():
            x0, y0, x1, y1 = bounds
            if not (0 <= x0 < x1 <= reference.width and 0 <= y0 < y1 <= reference.height):
                raise ValueError("La región debe estar dentro de la referencia.")
            if (x1 - x0, y1 - y0) != (64, 64):
                raise ValueError("La lámina utiliza recortes de 64 × 64.")
    rows = []
    baseline = None
    for label, image in images:
        metrics = reference_metrics(reference, image)
        if baseline is None:
            baseline = metrics
        psnr_delta = metrics["psnr_db"] - baseline["psnr_db"] if metrics["psnr_db"] is not None and baseline["psnr_db"] is not None else None
        rows.append({"imagen": label, **metrics, "delta_psnr_vs_entrada_db": psnr_delta,
                     "delta_ssim_vs_entrada": metrics["ssim_rgb"] - baseline["ssim_rgb"],
                     "regiones": {name: reference_metrics(reference.crop(bounds), image.crop(bounds))
                                  for name, bounds in (regions or {}).items()}})
    report = {
        "tipo": "evaluacion_referencia_degradacion_sintetica",
        "creado_utc": datetime.now(timezone.utc).isoformat(),
        "sha256_barrido": file_hash(sweep_dir / "barrido.json"),
        "sha256_experimento": file_hash(sweep_dir / "experimento.json"),
        "fuentes_sha256": sources, "dimensiones": list(reference.size),
        "procedencia": experiment["procedencia_declarada"],
        "referencia": "Imagen preparada anterior al ruido artificial; puede contener ruido propio. Solo es objetivo para esta degradación sintética.",
        "metodo": {"espacio": "RGB publicado sin linealizar", "normalizacion": "float64 / 255",
                   "data_range": 1.0, "ssim": SSIM_OPTIONS,
                   "ssim_ventana": "Gaussiana 11 × 11; sigma 1,5; promedio de los tres canales y del interior válido",
                   "psnr_exacto": "Si MSE es cero: psnr_db=null y psnr_infinito=true, para mantener JSON válido",
                   "alineacion": "Sin registro, redimensionamiento ni ajuste de contraste"},
        "versiones": {name: version(name) for name in ("scikit-image", "numpy", "pillow")},
        "resultados": rows, "casos_sin_metricas": omitted,
        "regiones_xyxy": regions or {},
        "alcance": "Un caso, un nivel de ruido y una semilla. PSNR/SSIM miden cercanía al objetivo sintético; no verifican autenticidad científica ni generalización.",
    }
    output_dir.mkdir(parents=True, exist_ok=False)
    save_json(output_dir / "evaluacion.json", report)
    fields = ("imagen", "mse_rgb_normalizado", "psnr_db", "ssim_rgb", "delta_psnr_vs_entrada_db", "delta_ssim_vs_entrada")
    with (output_dir / "metricas.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    if regions:
        crop_sheet([("Referencia preparada", reference)] + images, regions, output_dir / "regiones_ampliadas.png")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sweep-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--regions-potw1803a", action="store_true", help="Añadir los cuatro recortes fijos de la referencia 256 × 192")
    args = parser.parse_args()
    if args.regions_potw1803a:
        with Image.open(args.sweep_dir / "referencia_preparada.png") as image:
            if image.size != (256, 192):
                raise ValueError("Los recortes de potw1803a requieren una referencia de 256 × 192.")
    result = evaluate_sweep(args.sweep_dir, args.output_dir,
                            regions=REGIONS_POTW1803A if args.regions_potw1803a else None)
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
