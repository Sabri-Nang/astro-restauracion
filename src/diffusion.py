"""Prueba reproducible de difusión imagen a imagen, sin cargas al importar."""

from __future__ import annotations

import argparse
from functools import lru_cache
import hashlib
from importlib.metadata import version
import json
import math
from pathlib import Path
import platform
from time import perf_counter

from PIL import Image, ImageOps

from src.honesty import DISCLAIMER


MODEL_ID = "stable-diffusion-v1-5/stable-diffusion-v1-5"
MODEL_REVISION = "451f4fe16113bff5a5d2269ed5ad43b0592e9a14"
MODEL_LICENSE = "CreativeML OpenRAIL-M"
CONTROLNET_TILE_ID = "lllyasviel/control_v11f1e_sd15_tile"
CONTROLNET_TILE_REVISION = "3f877705c37010b7221c3d10743307d6b5b6efac"
CONTROLNET_TILE_LICENSE = "CreativeML OpenRAIL-M"
MODEL_CACHE = Path(__file__).resolve().parents[1] / ".cache" / "huggingface"
DEFAULT_PROMPT = "astronomical photograph, stars and galaxies"


class SafetyFilterBlockedError(RuntimeError):
    """La salida fue rechazada por el filtro de contenido del pipeline."""


class DiffBIRRuntime:
    """Motor CUDA reutilizable para fotos propias, sin referencia de evaluación.

    Vive en el proceso aislado de colab/diffbir. El ensayo controlado conserva su
    recorrido en diffbir_trial.py; aquí nunca se busca ni se recibe una referencia.
    """

    def __init__(self, upstream: Path, cache: Path):
        import subprocess
        import sys
        import os
        import torch
        from src.diffbir_trial import UPSTREAM_REVISION, check_checkpoint_dependencies

        if not torch.cuda.is_available():
            raise RuntimeError("DiffBIR necesita CUDA; ejecutá la aplicación en Colab con GPU.")
        if sys.version_info[:2] != (3, 12) or not torch.__version__.startswith("2.2.2"):
            raise RuntimeError("DiffBIR requiere el entorno aislado de colab/diffbir.")
        check_checkpoint_dependencies()
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=upstream, text=True).strip()
        dirty = subprocess.check_output(["git", "status", "--porcelain"], cwd=upstream, text=True).strip()
        if revision != UPSTREAM_REVISION or dirty:
            raise RuntimeError("La fuente de DiffBIR no coincide con la revisión fijada.")
        os.environ["ATTN_MODE"] = "sdp"
        sys.path.insert(0, str(upstream.resolve()))
        self.upstream, self.cache = upstream, cache
        self.cache.mkdir(parents=True, exist_ok=True)
        self.cleaner = self.model = self.diffusion = None
        self.weight_records = {}

    def _instantiate(self, filename):
        from omegaconf import OmegaConf
        from diffbir.utils.common import instantiate_from_config
        return instantiate_from_config(OmegaConf.load(self.upstream / "configs/inference" / filename))

    def _weights(self, name):
        from src.diffbir_trial import download_weight, load_checkpoint_cpu
        path, record = download_weight(name, self.cache)
        weights, mapped = load_checkpoint_cpu(path)
        record["carga_cpu_mmap"] = mapped
        self.weight_records[name] = record
        weights = weights.get("state_dict", weights)
        if next(iter(weights)).startswith("module."):
            weights = {key.removeprefix("module."): value for key, value in weights.items()}
        return weights

    def process(self, before: Image.Image, destination: Path, on_phase=lambda _: None):
        """Devuelve reconstrucción, primera limpieza y registro sin métricas inventadas."""
        import gc
        import numpy as np
        import torch
        import torch.nn.functional as functional
        from diffbir.pipeline import SCUNetPipeline
        from src.diffbir_trial import PARAMETERS, UPSTREAM_REVISION

        if before.mode != "RGB" or min(before.size) < 64 or max(before.size) > 256:
            raise ValueError("Se requiere la copia RGB preparada de 64 a 256 píxeles por lado.")
        destination.mkdir(parents=True, exist_ok=False)
        started = perf_counter()
        reused = self.model is not None
        torch.cuda.reset_peak_memory_stats()
        on_phase("primera_limpieza")
        if self.cleaner is None:
            cleaner = self._instantiate("scunet.yaml")
            cleaner.load_state_dict(self._weights("scunet"), strict=True)
            self.cleaner = cleaner.eval()
        self.cleaner.to("cuda")
        noisy = np.asarray(before).copy()
        lq = torch.tensor(noisy[None], dtype=torch.float32, device="cuda").div(255).permute(0, 3, 1, 2).contiguous()
        captured = {}
        handle = self.cleaner.register_forward_hook(lambda _m, _i, result: captured.update(native=result.detach().clone()))
        torch.manual_seed(42)
        try:
            with torch.no_grad(), torch.autocast("cuda", dtype=torch.float16):
                condition = SCUNetPipeline(self.cleaner, None, None, None, "cuda").apply_cleaner(lq, False, 512, 256)
        finally:
            handle.remove()
            self.cleaner.to("cpu")

        def save_tensor(tensor, filename):
            if not torch.isfinite(tensor).all():
                raise ValueError("La reconstrucción contiene valores no finitos.")
            pixels = tensor.detach().float().mul(255).clamp(0, 255).to(torch.uint8)
            image = Image.fromarray(pixels[0].permute(1, 2, 0).cpu().numpy())
            image.save(destination / filename)
            return image

        first = save_tensor(captured.pop("native"), "limpieza_previa.png")
        save_tensor(condition, "condicion_interna.png")
        save_tensor(functional.interpolate(condition, size=(before.height, before.width), mode="bicubic", antialias=True), "condicion_reducida.png")
        del lq
        gc.collect()
        torch.cuda.empty_cache()
        on_phase("preparando_reconstruccion")
        if self.model is None:
            # Cargar y liberar cada checkpoint por separado reduce el pico de RAM.
            model = self._instantiate("cldm.yaml")
            weights = self._weights("sd21")
            _, missing = model.load_pretrained_sd(weights)
            if missing:
                raise RuntimeError("Faltan pesos de SD 2.1; se interrumpe la reconstrucción.")
            del weights
            gc.collect()
            weights = self._weights("ircontrolnet")
            model.load_controlnet_from_ckpt(weights)
            del weights
            gc.collect()
            model.eval()
            model.cast_dtype(torch.float16)
            model.to("cuda")
            diffusion = self._instantiate("diffusion.yaml").to("cuda")
            self.model, self.diffusion = model, diffusion

        class ConditionedPipeline(SCUNetPipeline):
            def apply_cleaner(self, *_args, **_kwargs):
                return condition

            def apply_cldm(self, *args, **kwargs):
                decoded = super().apply_cldm(*args, **kwargs)
                if not torch.isfinite(decoded).all():
                    raise ValueError("La difusión devolvió valores no finitos.")
                return decoded

        on_phase("reconstruyendo")
        sampling = perf_counter()
        torch.manual_seed(42)
        with torch.no_grad(), torch.autocast("cuda", dtype=torch.float16):
            result = ConditionedPipeline(None, self.model, self.diffusion, None, "cuda").run(
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
        if result.dtype != np.uint8 or result.shape != (1, before.height, before.width, 3):
            raise ValueError("La reconstrucción no conserva las dimensiones esperadas.")
        after = Image.fromarray(result[0])
        after.save(destination / "salida_diffbir.png")
        before.save(destination / "entrada_preparada.png")
        metadata = {
            "motor": "diffbir_v2", "revision_diffbir": UPSTREAM_REVISION,
            "parametros": dict(PARAMETERS), "modelo_reutilizado": reused,
            "pesos": dict(self.weight_records), "referencia_usada_para_generar": False,
            "dimensiones": list(before.size), "condicion_interna_dimensiones": [condition.shape[3], condition.shape[2]],
            "semilla": 42, "pasos_configurados": 50,
            "segundos_reconstruccion": perf_counter() - sampling,
            "segundos_procesamiento_total": perf_counter() - started,
            "gpu": torch.cuda.get_device_name(0), "pico_memoria_cuda_bytes": torch.cuda.max_memory_allocated(),
            "versiones": {name: version(name) for name in ("torch", "torchvision", "numpy", "pillow")},
            "limites": "Difusión, remuestreo y wavelet pueden alterar estructuras. Una prueba global favorable no valida autenticidad ni generalización. No se calculan métricas sin referencia.",
            "filtro_contenido": "No incluido por el pipeline oficial DiffBIR; no se desactiva ni se utiliza el filtro de SD/Tile.",
            "artefactos": {name: hashlib.sha256((destination / name).read_bytes()).hexdigest() for name in
                           ("entrada_preparada.png", "limpieza_previa.png", "condicion_interna.png", "condicion_reducida.png", "salida_diffbir.png")},
        }
        return before.copy(), after, first, metadata


def prepare_image(path: str | Path, max_size: int = 256) -> Image.Image:
    """Lee PNG/TIFF de 8 bits y ajusta a múltiplos de ocho, sin recortar."""
    if max_size not in (256, 512):
        raise ValueError("El tamaño máximo debe ser 256 o 512 píxeles.")
    with Image.open(path) as source:
        if source.format not in ("PNG", "TIFF"):
            raise ValueError(
                f"El contenido del archivo es {source.format}, aunque su nombre pueda indicar otra extensión. "
                "Esta versión admite PNG o TIFF. Exportá una copia PNG RGB de 8 bits desde tu editor; "
                "cambiar solo el nombre no convierte la imagen. Conservá el original."
            )
        bits = getattr(source, "tag_v2", {}).get(258, (8,))
        if source.format == "PNG":
            # Pillow puede decodificar PNG RGB de 16 bits como RGB de 8 bits.
            # Consultar IHDR permite rechazar esa conversión silenciosa.
            with Path(path).open("rb") as png:
                header = png.read(25)
            bits = (header[24],)
        if isinstance(bits, int):
            bits = (bits,)
        if any(bit > 8 for bit in bits) or source.mode in ("I", "F") or source.mode.startswith("I;16"):
            raise ValueError(
                "Tu archivo guarda más niveles de color de los que admite esta versión. "
                "Desde tu editor, exportá una copia PNG o TIFF RGB de 8 bits por canal. "
                "Conservá el original. Esto no se refiere a sus dimensiones ni a su peso."
            )
        if source.width < 64 or source.height < 64:
            raise ValueError("La imagen debe medir al menos 64 píxeles por lado.")
        image = ImageOps.exif_transpose(source).convert("RGB")
    scale = min(1.0, max_size / max(image.size))
    width = int(image.width * scale) // 8 * 8
    height = int(image.height * scale) // 8 * 8
    if min(width, height) < 64:
        raise ValueError("La relación de aspecto deja un lado menor a 64 píxeles.")
    return image.resize((width, height), Image.Resampling.LANCZOS)


@lru_cache(maxsize=1)
def load_pipeline(device: str = "auto", controlnet_tile: bool = False):
    """Carga la revisión fijada solo cuando se solicita procesar una imagen."""
    import torch
    from diffusers import DDIMScheduler, StableDiffusionImg2ImgPipeline

    if device not in ("auto", "cpu", "cuda"):
        raise ValueError("El dispositivo debe ser auto, cpu o cuda.")
    selected = "cuda" if device == "auto" and torch.cuda.is_available() else device
    if selected == "auto":
        selected = "cpu"
    if selected == "cuda" and not torch.cuda.is_available():
        raise ValueError("CUDA no está disponible; utilizá CPU o un entorno GPU de Colab.")
    # La precisión reducida evita duplicar los pesos en float32 en equipos de 16 GB.
    dtype = torch.float16 if selected == "cuda" else torch.bfloat16
    pipeline_class = StableDiffusionImg2ImgPipeline
    extra = {}
    if controlnet_tile:
        from diffusers import ControlNetModel, StableDiffusionControlNetImg2ImgPipeline

        # La revisión oficial de Tile ofrece pesos .bin, sin variante Safetensors.
        controlnet = ControlNetModel.from_pretrained(
            CONTROLNET_TILE_ID, revision=CONTROLNET_TILE_REVISION,
            dtype=dtype, use_safetensors=False, cache_dir=str(MODEL_CACHE),
        )
        pipeline_class = StableDiffusionControlNetImg2ImgPipeline
        extra["controlnet"] = controlnet
    pipeline = pipeline_class.from_pretrained(
        MODEL_ID,
        revision=MODEL_REVISION,
        variant="fp16",
        dtype=dtype,
        use_safetensors=True,
        cache_dir=str(MODEL_CACHE),
        **extra,
    )
    pipeline.scheduler = DDIMScheduler.from_config(pipeline.scheduler.config)
    pipeline.vae.enable_slicing()
    pipeline.to(selected)
    return pipeline


def run_diffusion(
    path: str | Path,
    *,
    strength: float = 0.2,
    steps: int = 10,
    seed: int = 42,
    max_size: int = 256,
    device: str = "auto",
    controlnet_tile: bool = False,
    controlnet_scale: float = 1.0,
) -> tuple[Image.Image, Image.Image, dict]:
    """Ejecuta una prueba generativa y devuelve ambas imágenes y su registro."""
    if not 0 < strength <= 0.5:
        raise ValueError("La intensidad debe ser mayor a cero y como máximo 0,5.")
    if not isinstance(steps, int) or not 2 <= steps <= 50:
        raise ValueError("Los pasos deben ser un entero entre 2 y 50.")
    if int(steps * strength) < 1:
        raise ValueError("Aumentá los pasos o la intensidad para ejecutar al menos un paso efectivo.")
    if not isinstance(seed, int) or not 0 <= seed <= 2**32 - 1:
        raise ValueError("La semilla debe ser un entero entre 0 y 4294967295.")
    if not math.isfinite(controlnet_scale) or not 0 <= controlnet_scale <= 2:
        raise ValueError("La fuerza de ControlNet debe ser finita y estar entre 0 y 2.")
    image = prepare_image(path, max_size)
    with Path(path).open("rb") as source:
        source_hash = hashlib.file_digest(source, "sha256").hexdigest()
    started = perf_counter()
    pipeline = load_pipeline(device, controlnet_tile=True) if controlnet_tile else load_pipeline(device)
    load_seconds = perf_counter() - started

    import torch

    generator = torch.Generator(device=pipeline.device).manual_seed(seed)
    control_arguments = {}
    if controlnet_tile:
        control_arguments = {
            "control_image": image, "controlnet_conditioning_scale": controlnet_scale,
            "control_guidance_start": 0.0, "control_guidance_end": 1.0, "guess_mode": False,
        }
    started = perf_counter()
    with torch.inference_mode():
        result = pipeline(
            prompt=DEFAULT_PROMPT,
            image=image,
            strength=strength,
            num_inference_steps=steps,
            guidance_scale=1.0,
            generator=generator,
            **control_arguments,
        )
    inference_seconds = perf_counter() - started
    if result.nsfw_content_detected and any(result.nsfw_content_detected):
        raise SafetyFilterBlockedError("El filtro de seguridad bloqueó la salida; no se guardó como prueba válida.")
    restored = result.images[0]
    metadata = {
        "tipo": "prueba_tecnica_img2img_no_evaluacion_de_denoising",
        "modelo": MODEL_ID,
        "revision": MODEL_REVISION,
        "licencia": MODEL_LICENSE,
        "entrada": Path(path).name,
        "sha256_entrada": source_hash,
        "dimensiones_preparadas": list(image.size),
        "preprocesamiento": "RGB 8 bits, LANCZOS, sin recorte, lados ajustados a múltiplos de 8",
        "ruido_artificial_agregado": False,
        "prompt": DEFAULT_PROMPT,
        "intensidad": strength,
        "pasos_configurados": steps,
        "pasos_efectivos": int(steps * strength),
        "guidance_scale": 1.0,
        "semilla": seed,
        "scheduler": type(pipeline.scheduler).__name__,
        "dispositivo": str(pipeline.device),
        "precision": str(pipeline.unet.dtype),
        "segundos_carga_o_acceso_cache_memoria": round(load_seconds, 3),
        "segundos_inferencia": round(inference_seconds, 3),
        "python": platform.python_version(),
        "sistema": platform.platform(),
        "versiones": {name: version(name) for name in ("torch", "diffusers", "transformers", "pillow")},
        "advertencia": DISCLAIMER,
    }
    if controlnet_tile:
        metadata["controlnet_tile"] = {
            "modelo": CONTROLNET_TILE_ID, "revision": CONTROLNET_TILE_REVISION,
            "licencia": CONTROLNET_TILE_LICENSE, "formato_pesos": "PyTorch .bin oficial",
            "pipeline": type(pipeline).__name__, "fuerza_condicionamiento": controlnet_scale,
            "inicio_control": 0.0, "fin_control": 1.0, "guess_mode": False,
            "condicion": "La misma entrada ruidosa preparada, sin filtro ni redimensionamiento adicional",
            "sha256_archivo_condicion": source_hash, "referencia_limpia_usada_como_control": False,
            "superresolucion": False,
        }
    return image, restored, metadata


def reconstruct_vae(
    path: str | Path, *, posterior: str = "sample", seed: int = 42,
    max_size: int = 256, device: str = "cuda",
) -> tuple[Image.Image, Image.Image, dict]:
    """Control de codificación/decodificación VAE, sin ejecutar UNet ni scheduler.

    `sample` utiliza el muestreo posterior que usa img2img; `mode` toma su moda
    determinista. Se conserva el escalado latente y el filtro del pipeline.
    Este control no descompone de forma aditiva el error de difusión.
    """
    if posterior not in ("sample", "mode"):
        raise ValueError("El posterior VAE debe ser sample o mode.")
    if not isinstance(seed, int) or isinstance(seed, bool) or not 0 <= seed <= 2**32 - 1:
        raise ValueError("La semilla debe ser un entero entre 0 y 4294967295.")
    image = prepare_image(path, max_size)
    with Path(path).open("rb") as source:
        source_hash = hashlib.file_digest(source, "sha256").hexdigest()
    started = perf_counter()
    pipeline = load_pipeline(device)
    load_seconds = perf_counter() - started

    import torch

    generator = torch.Generator(device=pipeline.device).manual_seed(seed) if posterior == "sample" else None
    started = perf_counter()
    with torch.inference_mode():
        tensor = pipeline.image_processor.preprocess(image).to(device=pipeline.device, dtype=pipeline.vae.dtype)
        distribution = pipeline.vae.encode(tensor).latent_dist
        latent = distribution.sample(generator=generator) if posterior == "sample" else distribution.mode()
        scale = pipeline.vae.config.scaling_factor
        latent = latent * scale
        decoded = pipeline.vae.decode(latent / scale, return_dict=False, generator=generator)[0]
        decoded, flags = pipeline.run_safety_checker(decoded, pipeline.device, pipeline.vae.dtype)
        if flags is not None and any(flags):
            raise SafetyFilterBlockedError("El filtro de seguridad bloqueó el control VAE; no se guardó la salida.")
        restored = pipeline.image_processor.postprocess(decoded, output_type="pil", do_denormalize=[True])[0]
    if restored.mode != "RGB" or restored.size != image.size:
        raise ValueError("El control VAE debe conservar el tamaño y modo RGB de entrada.")
    metadata = {
        "tipo": "control_reconstruccion_vae_sin_difusion", "modelo": MODEL_ID,
        "revision": MODEL_REVISION, "licencia": MODEL_LICENSE,
        "entrada": Path(path).name, "sha256_entrada": source_hash,
        "dimensiones_preparadas": list(image.size), "posterior_vae": posterior,
        "semilla_vae": seed if posterior == "sample" else None,
        "scaling_factor": float(scale), "normalizacion": "Preprocesador del pipeline: RGB a [-1, 1]",
        "dispositivo": str(pipeline.device), "precision_vae": str(pipeline.vae.dtype),
        "unet_ejecutada": False, "scheduler_ejecutado": False, "pasos_efectivos": 0,
        "controlnet_ejecutado": False, "filtro_seguridad": "Mismo filtro del pipeline, activo",
        "segundos_carga_o_acceso_cache_memoria": round(load_seconds, 3),
        "segundos_reconstruccion_y_filtro": round(perf_counter() - started, 3),
        "python": platform.python_version(), "sistema": platform.platform(),
        "versiones": {name: version(name) for name in ("torch", "diffusers", "transformers", "pillow")},
        "advertencia": "Control de pérdida de representación; no es entrenamiento ni prueba de eliminación de ruido. La referencia publicada puede tener ruido propio.",
    }
    return image, restored, metadata


def main() -> None:
    """Guarda una prueba y sus parámetros sin modificar la imagen de origen."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Imagen PNG o TIFF de 8 bits")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/prueba_diffusion"))
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--strength", type=float, default=0.2)
    parser.add_argument("--steps", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--size", type=int, choices=(256, 512), default=256)
    parser.add_argument("--controlnet-tile", action="store_true")
    parser.add_argument("--controlnet-scale", type=float, default=1.0)
    args = parser.parse_args()
    print(f"Modelo: {MODEL_ID}\nRevisión: {MODEL_REVISION}", flush=True)
    prepared, processed, metadata = run_diffusion(
        args.input, strength=args.strength, steps=args.steps, seed=args.seed,
        max_size=args.size, device=args.device,
        controlnet_tile=args.controlnet_tile, controlnet_scale=args.controlnet_scale,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    prepared.save(args.output_dir / "entrada_preparada.png")
    processed.save(args.output_dir / "salida.png")
    (args.output_dir / "parametros.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(metadata, ensure_ascii=False, indent=2), flush=True)
    print(f"Prueba guardada en: {args.output_dir.resolve()}", flush=True)


if __name__ == "__main__":
    main()
