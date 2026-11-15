"""Controles de identidad, VAE y difusión con sigma cero, con referencia conocida."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

from src.diffusion import SafetyFilterBlockedError, reconstruct_vae, run_diffusion
from src.evaluation import REGIONS_POTW1803A, crop_sheet, load_rgb, reference_metrics
from src.experiment import file_hash, save_json


def run_controls(asset_dir: Path, output_dir: Path, *, device: str = "cuda") -> dict:
    """Conserva entradas, registra cada control y compara con la misma referencia.

    Sigma cero significa ausencia de ruido artificial añadido. La referencia
    publicada no se considera libre de ruido. Los errores no son aditivos.
    """
    asset_dir, output_dir = Path(asset_dir), Path(output_dir)
    if output_dir.exists():
        raise ValueError("La carpeta de controles ya existe; elegí una nueva.")
    if device not in ("cpu", "cuda"):
        raise ValueError("Elegí un dispositivo explícito: cuda o cpu.")
    manifest = json.loads((asset_dir / "experimento.json").read_text(encoding="utf-8"))
    if (manifest["tipo"] != "experimento_controlado_gaussiano" or manifest["dimensiones"] != [256, 192]
            or manifest["lado_maximo"] != 256 or manifest["ruido"]["sigma_normalizada"] != 0.03
            or manifest["ruido"]["semilla_ruido"] != 123):
        raise ValueError("Se requiere el par de 256 × 192 con sigma 0,03 y semilla 123.")
    for name in ("referencia_preparada.png", "entrada_ruidosa.png"):
        if file_hash(asset_dir / name) != manifest["archivos_sha256"][name]:
            raise ValueError(f"El archivo {name} cambió desde su preparación.")
    reference = load_rgb(asset_dir / "referencia_preparada.png")
    noisy = load_rgb(asset_dir / "entrada_ruidosa.png")
    if reference.size != noisy.size:
        raise ValueError("La referencia y la copia ruidosa deben tener igual tamaño.")
    output_dir.mkdir(parents=True, exist_ok=False)
    for name in ("referencia_preparada.png", "entrada_ruidosa.png", "experimento.json"):
        shutil.copy2(asset_dir / name, output_dir / name)
    report = {
        "tipo": "controles_sigma_cero_y_vae", "creado_utc": datetime.now(timezone.utc).isoformat(),
        "dispositivo_solicitado": device, "semilla_modelo_y_vae": 42,
        "difusion": {"intensidad": 0.1, "pasos_configurados": 30, "pasos_efectivos": 3,
                     "guidance_scale": 1.0, "scheduler": "DDIMScheduler", "controlnet_scale": 1.0},
        "fuentes_sha256": {name: file_hash(output_dir / name)
                            for name in ("referencia_preparada.png", "entrada_ruidosa.png")},
        "procedencia": manifest["procedencia_declarada"],
        "alcance": "Referencia para esta degradación sintética, no libre de ruido real. Control VAE y error de difusión no se suman ni restan para atribuir porcentajes causales.",
        "resultados": [], "ejecucion_cerrada": False, "fase": "iniciado",
    }
    panels = [("Referencia sigma 0", reference), ("Entrada sigma 0,03", noisy)]
    for label, image in panels:
        report["resultados"].append({"control": label, "estado": "identidad",
                                    "frente_referencia": reference_metrics(reference, image)})
    save_json(output_dir / "controles.json", report)
    plan = (
        ("vae_mode_sigma0", "VAE moda sigma 0", "referencia_preparada.png", "mode"),
        ("vae_sample_sigma0", "VAE muestra sigma 0", "referencia_preparada.png", "sample"),
        ("vae_sample_sigma003", "VAE muestra ruido", "entrada_ruidosa.png", "sample"),
        ("sd_sigma0", "SD sigma 0", "referencia_preparada.png", None),
        ("tile_sigma0", "Tile sigma 0", "referencia_preparada.png", None),
    )
    try:
        for identifier, label, input_name, posterior in plan:
            path = output_dir / input_name
            expected = reference if input_name == "referencia_preparada.png" else noisy
            report["fase"] = identifier
            save_json(output_dir / "controles.json", report)
            print(f"Ejecutando control: {label}", flush=True)
            try:
                if posterior:
                    prepared, processed, metadata = reconstruct_vae(path, posterior=posterior, seed=42,
                                                                   max_size=256, device=device)
                else:
                    options = {"controlnet_tile": True, "controlnet_scale": 1.0} if identifier == "tile_sigma0" else {}
                    prepared, processed, metadata = run_diffusion(path, strength=0.1, steps=30, seed=42,
                                                                  max_size=256, device=device, **options)
                    if identifier == "tile_sigma0":
                        control = metadata["controlnet_tile"]
                        control.pop("referencia_limpia_usada_como_control", None)
                        control["referencia_preparada_es_entrada_y_condicion"] = True
                        control["condicion"] = "La propia entrada sigma cero, que es la referencia preparada; sin otra imagen limpia externa."
                    metadata["ruido_artificial_agregado"] = False
            except SafetyFilterBlockedError as error:
                report["resultados"].append({"control": label, "id": identifier,
                                              "estado": "bloqueada_filtro_seguridad", "error": str(error)})
            else:
                if prepared.mode != expected.mode or prepared.size != expected.size or prepared.tobytes() != expected.tobytes():
                    raise ValueError("La preparación del control alteró la entrada conservada.")
                case = output_dir / identifier
                case.mkdir(exist_ok=False)
                processed.save(case / "salida.png")
                sigma = 0.0 if input_name == "referencia_preparada.png" else 0.03
                metadata["sigma_artificial_entrada"] = sigma
                metadata["nota_sigma_cero"] = "No se agregó ruido artificial; la foto publicada puede contener ruido propio."
                result = {
                    "control": label, "id": identifier, "estado": "correcto", "entrada": input_name,
                    "sigma_artificial_entrada": sigma, "sha256_entrada": file_hash(path),
                    "sha256_salida": file_hash(case / "salida.png"), "parametros": metadata,
                    "frente_referencia": reference_metrics(reference, processed),
                    "frente_su_entrada": reference_metrics(expected, processed),
                    "regiones_frente_referencia": {
                        name: reference_metrics(reference.crop(bounds), processed.crop(bounds))
                        for name, bounds in REGIONS_POTW1803A.items()
                    },
                }
                save_json(case / "resultado.json", result)
                report["resultados"].append(result)
                panels.append((label, processed))
            save_json(output_dir / "controles.json", report)
        crop_sheet(panels, REGIONS_POTW1803A, output_dir / "regiones_controles.png")
        report["ejecucion_cerrada"] = True
        report["fase"] = "controles_ejecutados_interpretacion_pendiente"
    except BaseException as error:
        report["fase"] = "interrumpido"
        report["error"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        report["finalizado_o_interrumpido_utc"] = datetime.now(timezone.utc).isoformat()
        save_json(output_dir / "controles.json", report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-dir", type=Path, default=Path("assets/ruido_gaussiano/potw1803a_sigma0.03_seed123_size256"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    args = parser.parse_args()
    result = run_controls(args.asset_dir, args.output_dir, device=args.device)
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
