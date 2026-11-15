"""Prepara un paquete de código y datos públicos para Colab sin publicar Git."""

import hashlib
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED


ROOT = Path(__file__).resolve().parents[1]
ASSET = "assets/ruido_gaussiano/potw1803a_sigma0.03_seed123_size256"
BASELINE = ROOT / "outputs/etapa3/barrido_potw1803a_20261115T023534122516Z/evaluacion/evaluacion.json"
PACKAGE = ROOT / "outputs/controlnet_tile_colab.zip"


def cell(kind, identifier, source):
    result = {"cell_type": kind, "id": identifier, "metadata": {}, "source": source.splitlines(keepends=True)}
    if kind == "code":
        result.update(execution_count=None, outputs=[])
    return result


def main():
    names = ["pyproject.toml", "uv.lock", ".python-version", "src/diffusion.py", "src/noise.py",
             "src/noise_assets.py", "src/honesty.py", "src/experiment.py", "src/evaluation.py"]
    names += [path.relative_to(ROOT).as_posix() for path in sorted((ROOT / "assets/ruido_gaussiano").rglob("*")) if path.is_file()]
    snapshots = {name: (ROOT / name).read_bytes() for name in names}
    if BASELINE.is_file():
        snapshots["comparacion_previa/sd15_evaluacion.json"] = BASELINE.read_bytes()
    index = {name: hashlib.sha256(data).hexdigest() for name, data in snapshots.items()}
    PACKAGE.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(PACKAGE, "w", compression=ZIP_DEFLATED) as archive:
        for name, data in snapshots.items():
            archive.writestr(name, data)
        archive.writestr("paquete_sha256.json", json.dumps(index, ensure_ascii=False, indent=2))
    digest = hashlib.sha256(PACKAGE.read_bytes()).hexdigest()
    helper = json.loads((ROOT / "colab/laboratorio_ruido.ipynb").read_text(encoding="utf-8"))["cells"][1]["source"]
    helper = "".join(helper) if isinstance(helper, list) else helper
    cells = [
        cell("markdown", "introduccion-tile", """# SD 1.5 + ControlNet Tile · Ensayo gaussiano

Notebook de ejecución experimental, separado de la interfaz principal. Usa la
misma referencia y copia ruidosa conservadas en `assets/ruido_gaussiano`.
**Estado al preparar este notebook: implementación comprobada con pruebas
simuladas; todavía no hay resultados reales de ControlNet Tile.**

Seleccioná **Entorno de ejecución → Cambiar tipo de entorno → GPU T4** si está
disponible. Interrumpí otros servidores Gradio antes de ejecutar para liberar
la GPU. La primera inferencia descarga los pesos oficiales fijados por revisión.
No se entrena ningún modelo ni se amplían las imágenes.

Por defecto se clona el proyecto publicado en GitHub, incluidos los PNG
gaussianos y sus registros. No hace falta subir imágenes ni un ZIP.
Como alternativa, `ORIGEN = 'paquete_local'` permite subir
`controlnet_tile_colab.zip` para probar cambios aún no publicados.

Fuente de la imagen: https://esahubble.org/images/potw1803a/
Crédito: **NASA, ESA, and J. Comerford (University of Colorado-Boulder)**.
Licencia: CC BY 4.0 — https://creativecommons.org/licenses/by/4.0/ — según
https://esahubble.org/copyright/. Las derivadas incluyen RGB, reducción LANCZOS,
ruido gaussiano y, cuando se ejecute, difusión. No garantizan autenticidad científica.
"""),
        cell("code", "salida-subprocesos", helper),
        cell("code", "subir-paquete", f'''from pathlib import Path
from datetime import datetime, timezone
from io import BytesIO
import hashlib
import json
import subprocess
import sys
from zipfile import ZipFile
from google.colab import files

if not Path('/content').is_dir():
    raise RuntimeError('Este notebook se ejecuta en Google Colab.')
ORIGEN = 'github'  # Alternativa: 'paquete_local'
HASH_PAQUETE_ESPERADO = '{digest}'
proyecto = Path('/content') / ('astrorestore_tile_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
if ORIGEN == 'github':
    subprocess.run(['git', 'clone', '--branch', 'main', '--single-branch',
                    'https://github.com/Sabri-Nang/astro-restauracion.git', str(proyecto)], check=True)
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=proyecto, text=True).strip()
    origen_codigo = {{'tipo': 'github', 'revision': revision}}
    necesarios = {names!r}
    indice = {{}}
    for nombre in necesarios:
        archivo = proyecto / nombre
        if not archivo.is_file():
            raise ValueError('Falta publicar el archivo necesario: ' + nombre)
        indice[nombre] = hashlib.sha256(archivo.read_bytes()).hexdigest()
    (proyecto / 'paquete_sha256.json').write_text(json.dumps(indice, indent=2), encoding='utf-8')
elif ORIGEN == 'paquete_local':
    subidos = files.upload()
    if len(subidos) != 1:
        raise ValueError('Subí únicamente controlnet_tile_colab.zip.')
    contenido = next(iter(subidos.values()))
    if hashlib.sha256(contenido).hexdigest() != HASH_PAQUETE_ESPERADO:
        raise ValueError('El ZIP no corresponde a la revisión preparada para este notebook.')
    proyecto.mkdir(exist_ok=False)
    with ZipFile(BytesIO(contenido)) as paquete:
        for nombre in paquete.namelist():
            ruta = Path(nombre)
            if ruta.is_absolute() or '..' in ruta.parts or '\\\\' in nombre:
                raise ValueError('Ruta insegura en el paquete.')
        paquete.extractall(proyecto)
    indice = json.loads((proyecto / 'paquete_sha256.json').read_text(encoding='utf-8'))
    for nombre, esperado in indice.items():
        if hashlib.sha256((proyecto / nombre).read_bytes()).hexdigest() != esperado:
            raise ValueError('El contenido no coincide: ' + nombre)
    origen_codigo = {{'tipo': 'paquete_local', 'sha256': HASH_PAQUETE_ESPERADO}}
else:
    raise ValueError('ORIGEN debe ser github o paquete_local.')
print('Origen verificado:', origen_codigo)
print('Proyecto:', proyecto)
'''),
        cell("code", "preparar-entorno", '''subprocess.run([sys.executable, '-m', 'pip', 'install', 'uv==0.12.3'], check=True)
ejecutar_con_salida(['uv', 'sync', '--locked', '--python', '3.12'], cwd=proyecto)
ejecutar_con_salida(['uv', 'run', '--locked', 'python', '-c',
    "import sys,torch; assert sys.version_info[:2]==(3,12); assert torch.cuda.is_available(), 'Activá una GPU en Colab'; print('GPU:',torch.cuda.get_device_name(0))"], cwd=proyecto)
'''),
        cell("markdown", "condiciones-fijas", """## Condiciones fijadas

- Referencia de 256 × 192 RGB; sigma 0,03, semilla de ruido 123, PCG64.
- Imagen inicial y condición de ControlNet: **la misma entrada ruidosa**.
  La referencia se reserva para evaluar y nunca se usa como condición.
- SD 1.5 y `lllyasviel/control_v11f1e_sd15_tile`, con revisiones fijadas en código.
- Intensidades 0,10 / 0,15 / 0,20 / 0,25; 30 pasos configurados, semilla IA 42.
- DDIM, guidance 1; fuerza de ControlNet 1,0; control activo entre 0 y 1;
  `guess_mode=False`. Sin prefiltrado de la condición ni superresolución.
- El filtro de seguridad permanece activo. Los bloqueos se registran sin métricas.

La fuerza 1,0 es un punto inicial experimental, sin eficacia demostrada.
"""),
        cell("code", "verificar-ruido", f'''from IPython.display import display, Image, Markdown

experimento = proyecto / '{ASSET}'
ejecutar_con_salida(['uv', 'run', '--locked', 'python', '-m', 'src.noise_assets', 'reproduce',
    '--metadata', str(experimento / 'reproduccion.json'),
    '--output', str(proyecto / 'outputs/verificacion/ruido_reproducido.png')], cwd=proyecto)
display(Markdown('### Referencia preparada'))
display(Image(filename=str(experimento / 'referencia_preparada.png')))
display(Markdown('### Misma entrada gaussiana conservada'))
display(Image(filename=str(experimento / 'entrada_ruidosa.png')))
'''),
        cell("code", "ejecutar-barrido-tile", '''salida = proyecto / 'outputs/etapa3/controlnet_tile'
ejecutar_con_salida(['uv', 'run', '--locked', 'python', '-u', '-m', 'src.experiment', 'sweep',
    '--experiment-dir', str(experimento), '--output-dir', str(salida),
    '--device', 'cuda', '--controlnet-tile', '--controlnet-scale', '1.0'], cwd=proyecto)
registro = json.loads((salida / 'barrido.json').read_text(encoding='utf-8'))
registro['origen_codigo'] = origen_codigo
(salida / 'barrido.json').write_text(json.dumps(registro, ensure_ascii=False, indent=2) + '\\n', encoding='utf-8')
print(json.dumps(registro, ensure_ascii=False, indent=2))
'''),
        cell("code", "evaluar-tile", '''evaluacion = salida / 'evaluacion'
ejecutar_con_salida(['uv', 'run', '--locked', 'python', '-m', 'src.evaluation',
    '--sweep-dir', str(salida), '--output-dir', str(evaluacion), '--regions-potw1803a'], cwd=proyecto)
actual = json.loads((evaluacion / 'evaluacion.json').read_text(encoding='utf-8'))
archivo_anterior = proyecto / 'comparacion_previa/sd15_evaluacion.json'
if archivo_anterior.is_file():
    anterior = json.loads(archivo_anterior.read_text(encoding='utf-8'))
    for nombre in ('referencia_preparada.png', 'entrada_ruidosa.png'):
        if anterior['fuentes_sha256'][nombre] != actual['fuentes_sha256'][nombre]:
            raise ValueError('La referencia o el ruido difiere de la evaluación previa.')
    print('Evaluación previa de SD 1.5 sin Tile:')
    for fila in anterior['resultados']:
        print(fila['imagen'], 'PSNR dB:', fila['psnr_db'], 'SSIM:', fila['ssim_rgb'])
print('Evaluación actual de SD 1.5 + Tile:')
for fila in actual['resultados']:
    print(fila['imagen'], 'PSNR dB:', fila['psnr_db'], 'SSIM:', fila['ssim_rgb'])
print('Casos sin métricas:', actual['casos_sin_metricas'])
display(Image(filename=str(evaluacion / 'regiones_ampliadas.png')))
'''),
        cell("code", "comparaciones-tile", '''for caso in registro['resultados']:
    display(Markdown('### Intensidad ' + str(caso['intensidad'])))
    if caso['estado'] == 'correcto':
        display(Image(filename=str(salida / caso['carpeta'] / 'comparacion_triple.png')))
    else:
        print(caso)
print('Revisar fondo, estrellas tenues, contornos, color y estructuras difusas. Las métricas no prueban autenticidad.')
'''),
        cell("code", "descargar-tile", '''import shutil
shutil.copy2(proyecto / 'paquete_sha256.json', salida / 'paquete_sha256.json')
archivo = shutil.make_archive(str(salida.parent / 'ensayo_controlnet_tile'), 'zip', salida)
files.download(archivo)
print('Conservar el ZIP antes de finalizar la sesión de Colab.')
'''),
    ]
    notebook = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                 "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}
    path = ROOT / "colab/experimento_controlnet_tile.ipynb"
    path.write_text(json.dumps(notebook, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for item in cells:
        if item["cell_type"] == "code":
            compile("".join(item["source"]), f"{path.name}:{item['id']}", "exec")
    print(json.dumps({"notebook": str(path), "paquete": str(PACKAGE), "sha256_paquete": digest,
                      "archivos": len(snapshots), "bytes": PACKAGE.stat().st_size,
                      "estado": "Preparado y sintaxis comprobada; este script no ejecuta inferencias ControlNet"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
