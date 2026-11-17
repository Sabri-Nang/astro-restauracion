"""Exportación local de resultados, parámetros y límites sin referencia inventada."""
import hashlib
import json
from pathlib import Path
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile
import shutil
from PIL import Image, ImageDraw, PngImagePlugin

from src.honesty import (
    DISCLAIMER, DIFFERENCE_NOTICE, HIGHLIGHT_NOTICE, HIGHLIGHT_SETTINGS,
    difference_map, highlight_changes,
)

ROOT = Path(__file__).resolve().parents[1]

def export_result(before, after, metadata, report, source_path):
    """Conserva el archivo original y las imágenes exactas mostradas."""
    folder = ROOT / "outputs" / "interfaz" / uuid4().hex
    folder.mkdir(parents=True)
    before.save(folder / "entrada_preparada.png")
    png_notice = PngImagePlugin.PngInfo()
    png_notice.add_text("Description", DISCLAIMER)
    after.save(folder / "salida_ia.png", pnginfo=png_notice)
    difference_map(before, after).save(folder / "diferencias.png")
    highlight_changes(before, after).save(folder / "zonas_para_revisar.png")
    # Copia identificada para compartir; salida_ia.png conserva dimensiones y píxeles.
    sharing = Image.new("RGB", (max(256, after.width), after.height + 44), "#111827")
    sharing.paste(after, ((sharing.width - after.width) // 2, 0))
    drawing = ImageDraw.Draw(sharing)
    drawing.text((8, after.height + 5), "Reconstruida con IA", fill="white")
    drawing.text((8, after.height + 23), "Revisar junto al original", fill="white")
    sharing.save(folder / "para_compartir_con_aviso.png", pnginfo=png_notice)
    source = Path(source_path)
    original = folder / ("original" + source.suffix.lower())
    original.write_bytes(source.read_bytes())
    intermediate_names = ("limpieza_previa.png", "condicion_reducida.png")
    for name, path in metadata.get("intermedios", {}).items():
        if name not in intermediate_names:
            raise ValueError("Etapa intermedia no reconocida.")
        stage = Path(path)
        if hashlib.sha256(stage.read_bytes()).hexdigest() != metadata.get("artefactos", {}).get(name):
            raise ValueError("La etapa intermedia cambió desde el procesamiento.")
        shutil.copyfile(stage, folder / name)
    record = dict(metadata)
    if "intermedios" in record:
        record["intermedios"] = {name: name for name in record["intermedios"]}
    record["advertencia"] = DISCLAIMER
    record["mapa_diferencias"] = DIFFERENCE_NOTICE
    record["resaltado_de_cambios"] = dict(HIGHLIGHT_SETTINGS)
    record["copia_para_compartir"] = "Se añade una banda de aviso y, si hace falta, margen lateral; no se reescala la imagen. No usar esta copia para métricas."
    record["hashes_exportados_sha256"] = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in folder.iterdir() if path.is_file()
    }
    (folder / "parametros.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    (folder / "informe.md").write_text(DISCLAIMER + "\n\n" + report, encoding="utf-8")
    (folder / "LEEME.txt").write_text(
        "RESULTADO RECONSTRUIDO POR IA. No es una observación astronómica verificada.\n"
        + HIGHLIGHT_NOTICE + "\n"
        "zonas_para_revisar.png es una copia marcada; salida_ia.png conserva la salida sin marcas.\n"
        "para_compartir_con_aviso.png incluye una banda visible de identificación de IA; no usarla para métricas.\n"
        "Si se usó DiffBIR, limpieza_previa.png conserva la primera etapa SCUNet, que no es difusión.\n"
        "La entrada preparada es la comparación válida con la salida; el original puede tener otro tamaño.\n"
        "Sin referencia confiable no se calculan PSNR ni SSIM. Los parámetros y hashes permiten rastrear "
        "esta ejecución; las diferencias de hardware pueden impedir reproducirla bit a bit.\n"
        "Las imágenes subidas conservan su procedencia y derechos; este ZIP no les otorga una licencia nueva.\n",
        encoding="utf-8",
    )
    archive = folder / "resultado_reconstruido_ia.zip"
    with ZipFile(archive, "w", compression=ZIP_DEFLATED) as zipped:
        for path in sorted(folder.iterdir()):
            if path != archive:
                zipped.write(path, path.name)
    return str(archive)
