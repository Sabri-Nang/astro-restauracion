"""Validación básica de cinco imágenes para cerrar la etapa 2 del proyecto."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import time
from zipfile import ZipFile

from PIL import Image, ImageChops, ImageStat

from src.diffusion import MODEL_ID, MODEL_REVISION, run_diffusion


EXAMPLE_NAMES = (
    "potw1803a.tif",
    "potw1428a.tif",
    "heic0503a.tif",
    "heic1520a.tif",
    "potw1408a.tif",
)


def validate_remote_examples(input_dir: Path, output_dir: Path, server_url: str) -> dict:
    """Registra cinco inferencias de la app DiffBIR en Colab; no simula el motor.

    Sube copias preparadas con la misma función de la app para evitar transferir
    TIFF de cientos de MB. Conserva la identidad del TIFF y de la copia enviada.
    No agrega ruido, no utiliza referencia ni calcula métricas de restauración.
    """
    from gradio_client import Client, handle_file
    from PIL import ImageDraw
    from src.diffusion import prepare_image
    from src.diffbir_trial import PARAMETERS, UPSTREAM_REVISION

    input_dir, output_dir = Path(input_dir), Path(output_dir)
    missing = [name for name in EXAMPLE_NAMES if not (input_dir / name).is_file()]
    if missing:
        raise ValueError("Faltan originales: " + ", ".join(missing))
    output_dir.mkdir(parents=True, exist_ok=False)
    record = dict(tipo="validacion_app_diffbir_cinco_imagenes", iniciado_utc=datetime.now(timezone.utc).isoformat(),
                  estado="conectando", completada=False, resultados=[],
                  criterio="Cinco inferencias reales con CLIP, archivos verificados y comparación; no acredita reducción de ruido ni autenticidad",
                  entrada="Copias RGB reducidas de TIFF locales, sin ruido sintético añadido", servidor=server_url,
                  version_servidor_git="No expuesta por esta API; no se afirma igualdad de commit",
                  codigo_validacion_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())

    def save():
        temporary = output_dir / "resumen.tmp"
        temporary.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(output_dir / "resumen.json")

    save()
    client = Client(server_url, verbose=False, download_files=str(output_dir / "descargas_api"))
    api = client.view_api(print_info=False, return_format="dict")['named_endpoints']
    if len(api['/procesar_foto']['parameters']) != 1:
        raise ValueError("La API no corresponde a la app DiffBIR con configuración fija.")
    record['gradio_servidor'] = client.config.get('version')
    record['estado'] = 'ejecutando'
    save()
    for index, name in enumerate(EXAMPLE_NAMES, 1):
        case = dict(imagen=name, estado="ejecutando", iniciado_utc=datetime.now(timezone.utc).isoformat())
        record['resultados'].append(case)
        folder = output_dir / Path(name).stem
        folder.mkdir()
        started = time.monotonic()
        try:
            source = input_dir / name
            prepared = prepare_image(source, max_size=256)
            sent = folder / 'entrada_enviada.png'
            prepared.save(sent)
            case.update(sha256_original=hashlib.sha256(source.read_bytes()).hexdigest(),
                        sha256_enviada=hashlib.sha256(sent.read_bytes()).hexdigest(), dimensiones=list(prepared.size))
            save()
            print(f'[{index}/5] {name}: enviando copia {prepared.size}', flush=True)
            job = client.submit(handle_file(str(sent)), api_name='/procesar_foto')
            seen, last = 0, None
            snapshots = []
            while True:
                outputs = job.outputs()
                for item in outputs[seen:]:
                    status = str(item[0])
                    snapshots.append(dict(segundos=time.monotonic() - started, estado_html=status))
                    titles = re.findall(r'<strong>(.*?)</strong>', status)
                    title = ' | '.join(titles)
                    if title != last:
                        print(f'[{index}/5] {name}: {title}', flush=True)
                        last = title
                seen = len(outputs)
                if job.done():
                    break
                time.sleep(1)
            result = job.result()
            (folder / 'estados.json').write_text(json.dumps(snapshots, ensure_ascii=False, indent=2), encoding='utf-8')
            if not result[2]:
                raise RuntimeError('La app no entregó un ZIP: ' + re.sub('<[^>]+>', ' ', str(result[0])))
            archive = folder / 'resultado_reconstruido_ia.zip'
            shutil.copyfile(result[2], archive)
            with ZipFile(archive) as zipped:
                metadata = json.loads(zipped.read('parametros.json'))
                if metadata.get('motor') != 'diffbir_v2' or metadata.get('revision_diffbir') != UPSTREAM_REVISION:
                    raise ValueError('El resultado no acredita el motor DiffBIR fijado.')
                if metadata.get('parametros') != PARAMETERS:
                    raise ValueError('El resultado utiliza otra configuración.')
                if not metadata.get('analisis_visual', {}).get('afinidades'):
                    raise ValueError('La difusión terminó pero no hay análisis visual completo.')
                for filename, expected in metadata['hashes_exportados_sha256'].items():
                    if hashlib.sha256(zipped.read(filename)).hexdigest() != expected:
                        raise ValueError('Hash incorrecto: ' + filename)
                names = ['entrada_preparada.png', 'limpieza_previa.png', 'salida_ia.png']
                images = []
                for filename in names:
                    data = zipped.read(filename)
                    (folder / filename).write_bytes(data)
                    with zipped.open(filename) as stream, Image.open(stream) as image:
                        images.append(image.convert('RGB'))
                if images[0].tobytes() != prepared.tobytes() or any(image.size != prepared.size for image in images):
                    raise ValueError('El resultado no corresponde a la copia enviada.')
                if max(ImageStat.Stat(images[-1]).stddev) == 0:
                    raise ValueError('La salida es uniforme.')
                for filename in ('parametros.json', 'informe.md', 'LEEME.txt'):
                    (folder / filename).write_bytes(zipped.read(filename))
            view = client.predict('Foto cargada → reconstrucción', False, 'Campo completo', 'Ajustar', api_name='/mostrar_revision')
            for path, expected in zip(view[3], (images[0], images[-1])):
                with Image.open(path) as image:
                    if image.convert('RGB').tobytes() != expected.tobytes():
                        raise ValueError('La comparación de la app no coincide con el resultado descargado.')
            sheet = Image.new('RGB', (prepared.width * 3, prepared.height + 24), '#262626')
            draw = ImageDraw.Draw(sheet)
            for col, (label, image) in enumerate(zip(('Entrada preparada', 'Limpieza', 'Reconstruccion IA'), images)):
                draw.text((col * prepared.width + 4, 4), label, fill='white')
                sheet.paste(image, (col * prepared.width, 24))
            sheet.save(folder / 'comparacion.png')
            case.update(estado='correcto', inferencia_diffbir_real=True, analisis_visual_completo=True,
                        comparacion_api_verificada=True, hashes_verificados=True,
                        sha256_zip=hashlib.sha256(archive.read_bytes()).hexdigest(), hardware=metadata.get('hardware'),
                        revision_visual='Pendiente de revisar estas salidas concretas; no es evidencia de limpieza validada')
        except Exception as error:
            case.update(estado='error', error=str(error))
            print(f'[{index}/5] {name}: ERROR {error}', flush=True)
        finally:
            case.update(segundos_totales=time.monotonic() - started, finalizado_utc=datetime.now(timezone.utc).isoformat())
            save()
        print(f'[{index}/5] {name}: {case["estado"]} ({case["segundos_totales"]:.1f} s)', flush=True)
    record['completada'] = len(record['resultados']) == 5 and all(case['estado'] == 'correcto' for case in record['resultados'])
    record['estado'] = 'completado' if record['completada'] else 'incompleto'
    record['finalizado_utc'] = datetime.now(timezone.utc).isoformat()
    save()
    return record


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
    parser.add_argument("--server-url", help="App DiffBIR activa en Colab; sin esta opción se conserva la validación histórica SD.")
    args = parser.parse_args()
    report = (validate_remote_examples(args.input_dir, args.output_dir, args.server_url) if args.server_url
              else validate_examples(args.input_dir, args.output_dir, args.device))
    print(f"Validación de cinco imágenes completada: {report['completada']}", flush=True)
    if not report["completada"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
