"""Prueba aislada DiffBIR v2: SCUNet y difusión sobre el par gaussiano conocido.

No importa DiffBIR ni descarga pesos al importarlo. La app reutiliza sus utilidades
de checkpoints; el ensayo con referencia se ejecuta únicamente por consola.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gc
import hashlib
import importlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from zipfile import ZipFile, ZIP_DEFLATED, is_zipfile

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM_REVISION = "5c2d6c177c3f2965e6d33a32931248d242ef7b3d"
ASSET = ROOT / "assets/ruido_gaussiano/potw1803a_sigma0.03_seed123_size256"
INPUT_HASHES = {
    "referencia_preparada.png": "71482fdf9473d832f5e2effb3873c8987e441874798df65e9f48f7ef5ad5818e",
    "entrada_ruidosa.png": "cc4ee54d8e6247933e2c9c9afd8310e27820fbcd534a9a821b4b691018b92c58",
}
WEIGHTS = {
    "scunet": {
        "url": "https://github.com/cszn/KAIR/releases/download/v1.0/scunet_color_real_psnr.pth",
        "bytes": 71982841,
        "sha256": "fa78899ba2caec9d235a900e91d96c689da71c42029230c2028b00f09f809c2e",
        "licencia_proyecto": "Apache-2.0 (SCUNet)",
        "nota": "Release oficial v1.0. SHA fijado a partir de la descarga real recibida el 16/11/2026; la release no publica digest propio.",
    },
    "sd21": {
        "repo": "ckpt/stable-diffusion-2-1-base",
        "revision": "80b44465963d65d12b35d07a2ea789545df260b9",
        "archivo": "v2-1_512-ema-pruned.ckpt",
        "bytes": 5214865159,
        "sha256": "88ecb782561455673c4b78d05093494b9c539fc6bfc08f3a9a4a0dd7b0b10f36",
        "nota": "Respaldo de terceros en HF; el enlace original de Stability AI respondió 401 al preparar esta prueba. No es otro modelo ni el checkpoint ZSNR.",
        "licencia_modelo": "CreativeML Open RAIL++-M (SD 2.1)",
    },
    "ircontrolnet": {
        "repo": "lxq007/DiffBIR-v2",
        "revision": "fd6263503564bfbfa156665a90832e1b729434f4",
        "archivo": "v2.pth",
        "bytes": 1452694018,
        "sha256": "c023992d042a4e966a335b084fae7a4e38b3ac3d0df819398c839ff371ebaba5",
        "licencia_ficha": "Apache-2.0 (DiffBIR-v2); el backbone SD conserva su licencia propia",
    },
}
PARAMETERS = {
    "version": "v2", "tarea": "denoise", "upscale_salida": 1,
    "semilla": 42, "pasos": 50, "sampler": "spaced", "cfg_scale": 4.0,
    "control_strength": 1.0, "inicio": "noise", "noise_aug": 0,
    "prompt_positivo": "", "prompt_negativo": "low quality, blurry, low-resolution, noisy, unsharp, weird textures",
    "captioner": "none", "precision": "fp16", "atencion": "sdp",
    "cleaner_tiled": False, "vae_tiled": True, "vae_tile_size": 256,
    "cldm_tiled": True, "cldm_tile_size": 512, "cldm_tile_stride": 256,
    "correccion_color": "wavelet_reconstruction oficial antes de reducir la salida",
    "advertencia_strength": "control_strength es fuerza de IRControlNet; no equivale al strength img2img de SD 1.5.",
}


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_record(folder: Path, record: dict) -> None:
    temporary = folder / "resultado.tmp"
    temporary.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(folder / "resultado.json")


def verify_inputs(folder: Path) -> None:
    from PIL import Image

    for name, expected in INPUT_HASHES.items():
        if digest(folder / name) != expected:
            raise ValueError(f"El archivo {name} no es el par conservado para esta prueba.")
        with Image.open(folder / name) as image:
            if image.mode != "RGB" or image.size != (256, 192):
                raise ValueError("Se requiere el par RGB de 256 × 192, sin conversiones adicionales.")


def prepare_trial(output: Path, asset: Path = ASSET) -> dict:
    verify_inputs(asset)
    output.mkdir(parents=True, exist_ok=False)
    for name in (*INPUT_HASHES, "reproduccion.json", "experimento.json"):
        shutil.copy2(asset / name, output / name)
    provenance = json.loads((asset / "reproduccion.json").read_text(encoding="utf-8"))["procedencia"]
    record = {
        "tipo": "prueba_acotada_diffbir_v2", "estado": "preparado_sin_inferencia",
        "creado_utc": datetime.now(timezone.utc).isoformat(),
        "revision_diffbir": UPSTREAM_REVISION, "parametros": dict(PARAMETERS),
        "pesos_declarados": WEIGHTS, "procedencia": provenance,
        "inferencia_scunet_ejecutada": False, "inferencia_difusion_ejecutada": False,
        "referencia_usada_para_generar": False,
        "codigo_prueba_sha256": digest(Path(__file__)),
        "codigo_evaluacion_sha256": digest(ROOT / "src/evaluation.py"),
        "bloqueo_entorno_sha256": digest(ROOT / "colab/diffbir/uv.lock"),
        "limites": [
            "Una imagen, una semilla y una configuración; sin validación de generalización.",
            "DiffBIR v2 amplía internamente la condición a lado mínimo 512 y devuelve 256 × 192; no se entrega superresolución.",
            "La salida final incluye difusión, corrección wavelet y reducción bicúbica; no se atribuye toda diferencia a un único componente.",
            "La referencia publicada puede tener ruido propio. Las métricas miden parecido, no autenticidad.",
            "La semilla fija no garantiza identidad bit a bit entre distintas GPU o versiones del entorno.",
            "El pipeline oficial de DiffBIR no incorpora el filtro de contenido de la app SD/Tile. No se modifica el filtro de la aplicación.",
        ],
    }
    write_record(output, record)
    return record


def evaluate_trial(output: Path, record: dict) -> dict:
    """Evalúa solo archivos producidos; una etapa ausente nunca cuenta como éxito."""
    from src.evaluation import REGIONS_POTW1803A, SSIM_OPTIONS, crop_sheet, load_rgb, reference_metrics

    verify_inputs(output)
    reference = load_rgb(output / "referencia_preparada.png")
    variants = [("Entrada ruidosa", "entrada_ruidosa.png")]
    if record["inferencia_scunet_ejecutada"]:
        variants += [("SCUNet nativo", "scunet_nativo.png"), ("Condicion ida/vuelta", "condicion_reducida.png")]
    if record["inferencia_difusion_ejecutada"]:
        variants.append(("DiffBIR final", "diffbir_final.png"))
    rows, panels = [], [("Referencia", reference)]
    for label, name in variants:
        image = load_rgb(output / name)
        metrics = reference_metrics(reference, image)
        regions = {key: reference_metrics(reference.crop(box), image.crop(box)) for key, box in REGIONS_POTW1803A.items()}
        rows.append({"etapa": label, "archivo": name, "sha256": digest(output / name), **metrics, "regiones": regions})
        panels.append((label, image))
    baseline = rows[0]
    for row in rows[1:]:
        row["delta_psnr_vs_entrada"] = None if row["psnr_infinito"] else row["psnr_db"] - baseline["psnr_db"]
        row["delta_ssim_vs_entrada"] = row["ssim_rgb"] - baseline["ssim_rgb"]
    record["evaluacion"] = {"ssim": SSIM_OPTIONS, "escala": "RGB float64 [0,1], sin alineación ni ajuste de contraste", "filas": rows}
    crop_sheet(panels, REGIONS_POTW1803A, output / "recortes.png")
    # Comparación completa a resolución común, con crédito en una banda aparte.
    from PIL import Image, ImageDraw
    sheet = Image.new("RGB", (256 * len(panels), 270), "white")
    draw = ImageDraw.Draw(sheet)
    for index, (label, image) in enumerate(panels):
        draw.text((index * 256 + 4, 4), label, fill="black")
        sheet.paste(image, (index * 256, 24))
    draw.text((4, 221), "Reconstrucción IA experimental; no verifica autenticidad.", fill="black")
    draw.text((4, 237), "NASA, ESA, and J. Comerford (University of Colorado-Boulder)", fill="black")
    draw.text((4, 253), "esahubble.org/images/potw1803a/ | CC BY 4.0 | RGB, reducción, ruido y reconstrucción", fill="black")
    sheet.save(output / "comparacion.png")
    stage1 = next((row for row in rows if row["archivo"] == "scunet_nativo.png"), None)
    final = next((row for row in rows if row["archivo"] == "diffbir_final.png"), None)
    if stage1 and final:
        record["comparacion_final_vs_scunet"] = {
            "delta_psnr": None if stage1["psnr_infinito"] or final["psnr_infinito"] else final["psnr_db"] - stage1["psnr_db"],
            "delta_ssim": final["ssim_rgb"] - stage1["ssim_rgb"],
            "interpretacion": "Diferencia del conjunto difusión + remuestreo + corrección de color; revisar también la condición ida/vuelta y los recortes.",
        }
    record["archivos_sha256"] = {p.name: digest(p) for p in output.glob("*.png")}
    write_record(output, record)
    return record


def archive_trial(output: Path) -> Path:
    archive = output / "prueba_diffbir.zip"
    with ZipFile(archive, "w", ZIP_DEFLATED) as zipped:
        for path in sorted(output.iterdir()):
            if path.is_file() and path != archive:
                zipped.write(path, path.name)
    return archive


def record_process_exit(output: Path, returncode: int) -> dict:
    """El proceso padre registra incluso una terminación que no ejecutó finally."""
    record = json.loads((output / "resultado.json").read_text(encoding="utf-8"))
    record["subproceso"] = {
        "codigo_salida": returncode,
        "compatible_con_sigkill": returncode in (-9, 137),
        "nota": "SIGKILL no identifica por sí solo falta de RAM. No se determina la causa sin evidencia del sistema.",
    }
    if not record["inferencia_difusion_ejecutada"] and not record["estado"].startswith("fallo"):
        partial = record["inferencia_scunet_ejecutada"]
        record["estado"] = "interrumpido_con_resultados_parciales" if partial else "interrumpido_sin_resultados"
        record["error"] = {"tipo": "TerminacionSubproceso", "mensaje": f"El proceso terminó con código {returncode} sin completar difusión; causa no determinada."}
    elif returncode != 0 and record["estado"].startswith("completado"):
        record["estado"] = "fallo_posterior_a_generar_difusion"
    write_record(output, record)
    return record


def memory_snapshot() -> dict:
    """Lectura informativa de RAM Linux; no se interpreta como diagnóstico OOM."""
    values = {}
    for path, fields in ((Path("/proc/meminfo"), ("MemTotal", "MemAvailable")),
                         (Path("/proc/self/status"), ("VmRSS", "VmHWM"))):
        if path.is_file():
            for line in path.read_text().splitlines():
                key, _, value = line.partition(":")
                if key in fields:
                    values[key + "_kib"] = int(value.split()[0])
    return values


def load_checkpoint_cpu(path: Path):
    """Mapea checkpoints ZIP sin copiar todos sus storages a RAM al abrirlos.

    El contenido y la validación previa de pesos se mantienen. El formato legado
    no admite mmap; en ese caso se registra que se usó la carga habitual.
    """
    import torch
    mapped = is_zipfile(path)
    # Torch 2.2 exige str (no PathLike) cuando mmap está activo.
    return torch.load(str(path), map_location="cpu", weights_only=False, mmap=mapped), mapped


def check_checkpoint_dependencies() -> dict:
    """Comprueba los imports exigidos por el checkpoint antiguo antes de crear modelos."""
    try:
        importlib.import_module("pkg_resources")
        callbacks = importlib.import_module("pytorch_lightning.callbacks")
        if not hasattr(callbacks, "ModelCheckpoint"):
            raise ImportError("Lightning no exporta ModelCheckpoint.")
    except ImportError as error:
        raise RuntimeError(
            "El entorno no puede abrir el checkpoint SD 2.1: "
            "sincronizá colab/diffbir con su uv.lock actualizado, que incluye setuptools==80.9.0. "
            f"Detalle: {error}"
        ) from error
    return {name: version(name) for name in ("setuptools", "pytorch-lightning")}


def download_weight(name: str, cache: Path) -> tuple[Path, dict]:
    """Descarga explícita desde fuentes fijadas y verifica tamaño y digest disponible."""
    spec = WEIGHTS[name]
    if "repo" in spec:
        from huggingface_hub import hf_hub_download
        path = Path(hf_hub_download(spec["repo"], spec["archivo"], revision=spec["revision"], cache_dir=cache / "hf"))
    else:
        from torch.hub import download_url_to_file
        path = cache / "scunet_color_real_psnr.pth"
        if not path.exists():
            temporary = path.with_suffix(".part")
            download_url_to_file(spec["url"], str(temporary), progress=True)
            temporary.replace(path)
    actual = digest(path)
    if path.stat().st_size != spec["bytes"] or (spec["sha256"] and actual != spec["sha256"]):
        raise ValueError(f"Checkpoint {name}: tamaño o SHA-256 inesperado; no se cargará.")
    return path, {**spec, "sha256_efectivo": actual}


def run_trial(output: Path, upstream: Path) -> dict:
    """Ejecuta una sola configuración, en CUDA; conserva resultados parciales si falla."""
    verify_inputs(output)
    record = json.loads((output / "resultado.json").read_text(encoding="utf-8"))
    if record["estado"] != "preparado_sin_inferencia":
        raise ValueError("La carpeta ya se utilizó. Prepará una carpeta nueva para otra ejecución.")
    if record["parametros"] != PARAMETERS or record["revision_diffbir"] != UPSTREAM_REVISION:
        raise ValueError("El protocolo cambió desde la preparación. Prepará otra carpeta.")
    if (record["codigo_prueba_sha256"] != digest(Path(__file__))
            or record["codigo_evaluacion_sha256"] != digest(ROOT / "src/evaluation.py")
            or record["bloqueo_entorno_sha256"] != digest(ROOT / "colab/diffbir/uv.lock")):
        raise ValueError("Código o bloqueo modificados desde la preparación; usar una carpeta nueva.")
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=upstream, text=True).strip()
    if revision != UPSTREAM_REVISION or subprocess.check_output(["git", "status", "--porcelain"], cwd=upstream, text=True).strip():
        raise ValueError("La copia de DiffBIR debe estar limpia y en la revisión fijada.")
    record["estado"] = "ejecutando"
    write_record(output, record)
    started = time.perf_counter()
    try:
        import numpy as np
        import torch
        import torch.nn.functional as functional
        from PIL import Image
        if not torch.cuda.is_available():
            raise RuntimeError("Esta prueba requiere CUDA en Colab; no se ejecutará en CPU.")
        if sys.version_info[:2] != (3, 12) or not torch.__version__.startswith("2.2.2"):
            raise RuntimeError("Usar el entorno aislado colab/diffbir con Python 3.12 y su bloqueo.")
        record["fase_actual"] = "comprobando_dependencias_checkpoint"
        write_record(output, record)
        record["dependencias_checkpoint"] = check_checkpoint_dependencies()
        write_record(output, record)
        os.environ["ATTN_MODE"] = "sdp"
        sys.path.insert(0, str(upstream.resolve()))
        from omegaconf import OmegaConf
        from diffbir.utils.common import instantiate_from_config
        from diffbir.pipeline import SCUNetPipeline
        torch.cuda.reset_peak_memory_stats()
        record["entorno"] = {
            "python": sys.version, "gpu": torch.cuda.get_device_name(0),
            "vram_bytes": torch.cuda.get_device_properties(0).total_memory,
            "cuda": torch.version.cuda,
            "versiones": {name: version(name) for name in ("torch", "torchvision", "numpy", "pillow", "scikit-image", "timm", "omegaconf")},
        }
        cache = ROOT / ".cache/diffbir"
        cache.mkdir(parents=True, exist_ok=True)
        record["pesos_cargados"] = {}

        def load(name):
            record["fase_actual"] = "descarga_y_verificacion_" + name
            record.setdefault("memoria_por_fase", {})[record["fase_actual"]] = memory_snapshot()
            write_record(output, record)
            print(f"Checkpoint {name}: descarga/verificación.", flush=True)
            path, metadata = download_weight(name, cache)
            record["pesos_cargados"][name] = metadata
            record["fase_actual"] = "carga_checkpoint_" + name
            write_record(output, record)
            # Estos checkpoints oficiales/registrados usan el formato pickle antiguo.
            # El SD de respaldo solo se carga después de verificar su SHA-256 fijado.
            print(f"Checkpoint {name}: verificado; abriendo en CPU con mmap si el formato lo admite.", flush=True)
            weights, mapped = load_checkpoint_cpu(path)
            metadata["carga_cpu_mmap"] = mapped
            record["memoria_por_fase"][record["fase_actual"]] = memory_snapshot()
            write_record(output, record)
            weights = weights.get("state_dict", weights)
            if next(iter(weights)).startswith("module."):
                weights = {key.removeprefix("module."): value for key, value in weights.items()}
            return weights

        def instantiate(filename):
            return instantiate_from_config(OmegaConf.load(upstream / "configs/inference" / filename))

        def save_tensor(tensor, name):
            if not torch.isfinite(tensor).all():
                raise ValueError(f"La etapa {name} contiene valores no finitos; no se cuantizará como imagen válida.")
            values = tensor.detach().float().mul(255).clamp(0, 255).to(torch.uint8)
            image = Image.fromarray(values[0].permute(1, 2, 0).cpu().numpy())
            image.save(output / name)
            return list(image.size)

        print("Etapa 1: descargar/cargar SCUNet y ejecutar sobre la entrada ruidosa.", flush=True)
        cleaner = instantiate("scunet.yaml")
        cleaner.load_state_dict(load("scunet"), strict=True)
        cleaner.eval().to("cuda")
        with Image.open(output / "entrada_ruidosa.png") as image:
            noisy = np.asarray(image).copy()
        lq = torch.tensor(noisy[None], dtype=torch.float32, device="cuda").div(255).permute(0, 3, 1, 2).contiguous()
        captured = {}

        def capture_native(_module, _inputs, result):
            captured["native"] = result.detach().clone()

        hook = cleaner.register_forward_hook(capture_native)
        torch.manual_seed(42)
        stage1_start = time.perf_counter()
        with torch.no_grad(), torch.autocast("cuda", dtype=torch.float16):
            condition = SCUNetPipeline(cleaner, None, None, None, "cuda").apply_cleaner(lq, False, 512, 256)
        hook.remove()
        torch.cuda.synchronize()
        save_tensor(captured.pop("native"), "scunet_nativo.png")
        dimensions = save_tensor(condition, "condicion_interna.png")
        save_tensor(functional.interpolate(condition, size=(192, 256), mode="bicubic", antialias=True), "condicion_reducida.png")
        record.update(inferencia_scunet_ejecutada=True, condicion_interna_dimensiones=dimensions,
                      segundos_scunet_y_remuestreo=time.perf_counter() - stage1_start,
                      cuantizacion="PNG RGB: multiplicar por 255, recortar y truncar a uint8 como el pipeline oficial")
        evaluate_trial(output, record)
        cleaner.to("cpu")
        del lq, cleaner
        gc.collect()
        torch.cuda.empty_cache()

        print("Etapa 2: inicializar arquitectura SD 2.1 + IRControlNet v2 en CPU.", flush=True)
        record["fase_actual"] = "inicializando_arquitectura_difusion"
        record.setdefault("memoria_por_fase", {})[record["fase_actual"]] = memory_snapshot()
        write_record(output, record)
        model = instantiate("cldm.yaml")
        print("Arquitectura construida. Se cargarán los pesos; aún no comienza el muestreo.", flush=True)
        weights = load("sd21")
        unused, missing = model.load_pretrained_sd(weights)
        record["carga_sd"] = {"claves_sin_usar": len(unused), "claves_faltantes": sorted(missing)}
        if missing:
            raise RuntimeError("Faltan pesos SD; no se ejecutará un modelo inicializado al azar.")
        del weights
        gc.collect()
        print("Pesos SD 2.1 asignados. Se cargará IRControlNet.", flush=True)
        weights = load("ircontrolnet")
        model.load_controlnet_from_ckpt(weights)
        del weights
        gc.collect()
        model.eval()
        model.cast_dtype(torch.float16)
        model.to("cuda")
        diffusion = instantiate("diffusion.yaml").to("cuda")

        class RecordedPipeline(SCUNetPipeline):
            def apply_cleaner(self, *_args, **_kwargs):
                # Reutilizar exactamente la condición float obtenida; no volver a limpiar ni cuantizar.
                return condition

            def apply_cldm(self, *args, **kwargs):
                decoded = super().apply_cldm(*args, **kwargs)
                if not torch.isfinite(decoded).all():
                    raise ValueError("La difusión devolvió valores no finitos antes de cuantizar.")
                return decoded

        pipeline = RecordedPipeline(None, model, diffusion, None, "cuda")
        torch.manual_seed(42)
        stage2_start = time.perf_counter()
        record["fase_actual"] = "muestreo_difusion"
        record["memoria_por_fase"][record["fase_actual"]] = memory_snapshot()
        write_record(output, record)
        print("Comienza el muestreo de difusión: 50 pasos.", flush=True)
        with torch.no_grad(), torch.autocast("cuda", dtype=torch.float16):
            result = pipeline.run(
                noisy[None], steps=50, strength=1.0,
                cleaner_tiled=False, cleaner_tile_size=512, cleaner_tile_stride=256,
                vae_encoder_tiled=True, vae_encoder_tile_size=256,
                vae_decoder_tiled=True, vae_decoder_tile_size=256,
                cldm_tiled=True, cldm_tile_size=512, cldm_tile_stride=256,
                pos_prompt=PARAMETERS["prompt_positivo"], neg_prompt=PARAMETERS["prompt_negativo"],
                cfg_scale=4.0, start_point_type="noise", sampler_type="spaced", noise_aug=0,
                rescale_cfg=False, s_churn=0, s_tmin=0, s_tmax=300, s_noise=1, eta=1, order=1,
            )
        torch.cuda.synchronize()
        if result.shape != (1, 192, 256, 3) or result.dtype != np.uint8:
            raise ValueError("La salida no conserva las dimensiones RGB esperadas.")
        Image.fromarray(result[0]).save(output / "diffbir_final.png")
        record.update(inferencia_difusion_ejecutada=True, estado="completado_pendiente_revision_visual",
                      segundos_difusion_y_postprocesamiento=time.perf_counter() - stage2_start,
                      pico_memoria_cuda_bytes=torch.cuda.max_memory_allocated())
        evaluate_trial(output, record)
    except Exception as error:
        record["estado"] = "fallo_con_resultados_parciales" if record["inferencia_scunet_ejecutada"] else "fallo_sin_resultados"
        record["error"] = {"tipo": type(error).__name__, "mensaje": str(error)}
        raise
    finally:
        record["segundos_totales_incluyendo_descargas"] = time.perf_counter() - started
        write_record(output, record)
        (output / "LEEME.txt").write_text(
            "Prueba experimental de reconstrucción con IA. No verifica autenticidad científica.\n"
            "Fuente: https://esahubble.org/images/potw1803a/\n"
            "Crédito: NASA, ESA, and J. Comerford (University of Colorado-Boulder). CC BY 4.0.\n"
            "Se conserva referencia RGB reducida, ruido sintético y etapas disponibles.\n"
            "El estado en resultado.json distingue una prueba completa de una fallida.\n"
            "SCUNet no es difusión; DiffBIR final incluye difusión, wavelet y reducción bicúbica.\n",
            encoding="utf-8",
        )
        archive_trial(output)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "run"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--upstream-dir", type=Path)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare_trial(args.output_dir)
        print("Par verificado y preparado; no se ejecutó inferencia.", flush=True)
    else:
        if not args.upstream_dir:
            parser.error("run requiere --upstream-dir")
        record = run_trial(args.output_dir, args.upstream_dir)
        print(json.dumps(record["evaluacion"], ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
