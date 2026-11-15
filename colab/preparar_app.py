"""Genera el notebook de entrega y un ZIP local de código y activos públicos."""
import hashlib
import json
from pathlib import Path
import subprocess
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]


def cell(kind, name, text):
    result = dict(cell_type=kind, id=name, metadata={}, source=text.splitlines(keepends=True))
    if kind == "code":
        result.update(execution_count=None, outputs=[])
    return result


def main():
    files = [ROOT / name for name in ("app.py", "pyproject.toml", "uv.lock", ".python-version", "README.md")]
    for directory in ("src", "assets/interfaz", "assets/ruido_gaussiano", "assets/ejemplos/etapa3_tile"):
        files += [p for p in (ROOT / directory).rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    files.append(ROOT / "assets/ejemplos/README.md")
    payload = {p.relative_to(ROOT).as_posix(): p.read_bytes() for p in files}
    manifest = dict(
        git_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        cambios_locales=subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).splitlines(),
        sha256={name: hashlib.sha256(data).hexdigest() for name, data in payload.items()},
    )
    archive = ROOT / "outputs/astrorestore_app_colab.zip"
    archive.parent.mkdir(exist_ok=True)
    with ZipFile(archive, "w", ZIP_DEFLATED) as zipped:
        for name, data in payload.items():
            zipped.writestr(name, data)
        zipped.writestr("paquete_sha256.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    cells = [cell("markdown", "inicio", """# AstroRestore AI · aplicación integrada

Etapa 4: prueba de uso y preparación de la demo. SD 1.5 + ControlNet Tile → comparación → CLIP → informe y descarga. No se entrena ni se amplían imágenes. Los ensayos actuales no demostraron mejorar la entrada ruidosa.

Seleccioná **GPU T4** en el entorno de ejecución e interrumpí otros servidores para liberar memoria. El primer procesamiento descarga varios GB. El filtro de seguridad permanece activo. CLIP usa CPU.

Este notebook permite probar commits locales antes de publicarlos. Desde el proyecto ejecutar `uv run --locked python colab/preparar_app.py` y subir **outputs/astrorestore_app_colab.zip** cuando se solicite. Solo incluye código y activos públicos, sin tokens ni pesos. Como alternativa, después de publicar los cambios, seleccionar `ORIGEN = 'github'`.
"""), cell("code", "preparar", """from pathlib import Path
from datetime import datetime, timezone
from zipfile import ZipFile
import hashlib, json, subprocess, sys
from google.colab import files

ORIGEN = 'paquete_local'  # 'github' requiere que los commits ya estén publicados
proyecto = Path('/content') / ('astrorestore_app_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
if ORIGEN == 'github':
    subprocess.run(['git', 'clone', '--depth', '1', 'https://github.com/Sabri-Nang/astro-restauracion.git', str(proyecto)], check=True)
elif ORIGEN == 'paquete_local':
    uploaded = files.upload()
    if len(uploaded) != 1:
        raise ValueError('Subir únicamente astrorestore_app_colab.zip.')
    from io import BytesIO
    with ZipFile(BytesIO(next(iter(uploaded.values())))) as zipped:
        index = json.loads(zipped.read('paquete_sha256.json'))
        proyecto.mkdir()
        for name, digest in index['sha256'].items():
            target = (proyecto / name).resolve()
            if not target.is_relative_to(proyecto.resolve()):
                raise ValueError('Ruta inválida en paquete.')
            data = zipped.read(name)
            if hashlib.sha256(data).hexdigest() != digest:
                raise ValueError('Hash incorrecto: ' + name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        (proyecto / 'paquete_sha256.json').write_text(json.dumps(index, indent=2))
    print('Commit base:', index['git_commit'], 'Cambios locales al empaquetar:', index['cambios_locales'])
else:
    raise ValueError('ORIGEN debe ser paquete_local o github.')
if 'def launch_app(' not in (proyecto / 'app.py').read_text(encoding='utf-8'):
    raise RuntimeError('Esta copia no contiene la aplicación integrada. Publicar los commits o usar el paquete local.')
print('Proyecto:', proyecto)
"""), cell("code", "instalar", """subprocess.run([sys.executable, '-m', 'pip', 'install', 'uv==0.12.3'], check=True)
def ejecutar(command):
    process = subprocess.Popen(command, cwd=proyecto, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    for line in process.stdout:
        print(line, end='', flush=True)
    if process.wait():
        raise RuntimeError('Falló el comando: ' + str(command))

ejecutar(['uv', 'sync', '--locked', '--python', '3.12'])
ejecutar(['uv', 'run', '--locked', 'python', '-c', "import torch; print('CUDA:',torch.cuda.is_available()); assert torch.cuda.is_available(), 'Seleccionar GPU T4 antes de procesar'; print(torch.cuda.get_device_name(0))"])
"""), cell("code", "abrir-app", """# Abrir el enlace gradio.live que aparezca; interrumpir esta celda para detener el servidor.
ejecutar(['uv', 'run', '--locked', 'python', '-u', '-c', "from app import launch_app; launch_app(share=True, server_name='0.0.0.0')"])
"""), cell("markdown", "revisar", """## Recorrido para verificar

1. Abrir **Ver ensayo guardado**: debe indicar que no se ejecutaron modelos. Sirve para revisar la interfaz y estudiar un resultado real anterior.
2. Elegir el ejemplo gaussiano o subir un PNG/TIFF de 8 bits. Cambiar la entrada debe limpiar resultados anteriores.
3. Mantener intensidad 0,10, 30 pasos, semilla 42 y lado máximo 256. Pulsar **Procesar y comparar** para una ejecución nueva. Registrar cualquier bloqueo sin desactivar el filtro.
4. Revisar imágenes, deslizador, mapa y reporte CLIP; no interpretarlo como porcentaje de limpieza. Descargar el ZIP y comprobar imágenes, informe, parámetros y hashes.
5. Capturar la advertencia, comparación e informe, conservando el crédito. Anotar revisión de código, GPU, duración y errores para la demo. Revisar también móvil y teclado.

Si CLIP falla después de difusión, descargar las imágenes y reintentar solo el análisis. La instalación y sintaxis del notebook se comprueban localmente; la ejecución completa de esta versión en Colab debe registrarse, no se da por realizada.

Imagen de ejemplo: https://esahubble.org/images/potw1803a/ — **NASA, ESA, and J. Comerford (University of Colorado-Boulder)** — CC BY 4.0, https://creativecommons.org/licenses/by/4.0/ conforme a https://esahubble.org/copyright/. Derivadas RGB reducidas, con ruido sintético y reconstrucción IA; sin autenticidad científica garantizada.
""")]
    notebook = dict(cells=cells, metadata=dict(kernelspec=dict(display_name="Python 3", language="python", name="python3")), nbformat=4, nbformat_minor=5)
    path = ROOT / "colab/app_integrada.ipynb"
    path.write_text(json.dumps(notebook, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for item in cells:
        if item["cell_type"] == "code":
            compile("".join(item["source"]), item["id"], "exec")
    print("Notebook:", path)
    print("Paquete:", archive, "SHA256:", hashlib.sha256(archive.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
