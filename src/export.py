"""Exportación local de resultados, parámetros y límites sin referencia inventada."""
import hashlib
import json
from pathlib import Path
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile

from src.honesty import DISCLAIMER, DIFFERENCE_NOTICE, difference_map

ROOT = Path(__file__).resolve().parents[1]

def export_result(before, after, metadata, report, source_path):
    """Conserva el archivo original y las imágenes exactas mostradas."""
    folder = ROOT / "outputs" / "interfaz" / uuid4().hex
    folder.mkdir(parents=True)
    before.save(folder / "entrada_preparada.png")
    after.save(folder / "salida_ia.png")
    difference_map(before, after).save(folder / "diferencias.png")
    source = Path(source_path)
    original = folder / ("original" + source.suffix.lower())
    original.write_bytes(source.read_bytes())
    record = dict(metadata)
    record["advertencia"] = DISCLAIMER
    record["mapa_diferencias"] = DIFFERENCE_NOTICE
    record["hashes_exportados_sha256"] = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in folder.iterdir() if path.is_file()
    }
    (folder / "parametros.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    (folder / "informe.md").write_text(DISCLAIMER + "\n\n" + report, encoding="utf-8")
    (folder / "LEEME.txt").write_text(
        "La entrada preparada es la comparación válida con la salida; el original puede tener otro tamaño.\n"
        "Sin referencia confiable no se calculan PSNR ni SSIM. Los parámetros y hashes permiten rastrear "
        "esta ejecución; las diferencias de hardware pueden impedir reproducirla bit a bit.\n"
        "Las imágenes subidas conservan su procedencia y derechos; este ZIP no les otorga una licencia nueva.\n",
        encoding="utf-8",
    )
    archive = folder / "resultado.zip"
    with ZipFile(archive, "w", compression=ZIP_DEFLATED) as zipped:
        for path in sorted(folder.iterdir()):
            if path != archive:
                zipped.write(path, path.name)
    return str(archive)
