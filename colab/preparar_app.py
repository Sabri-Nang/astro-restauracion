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
    files += [ROOT / "colab/diffbir" / name for name in ("pyproject.toml", "uv.lock")]
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
    cells = [cell("markdown", "inicio", """# AstroRestore AI · ejecutar en Google Colab

Aplicación de Julia: DiffBIR → comparación → CLIP → informe y descarga. DiffBIR mejoró métricas globales en un caso, pero alteró una galaxia y empeoró frente a SCUNet solo. Revisar estructuras y no atribuir autenticidad científica. No se entrena ni se entrega superresolución.

Seleccioná **GPU T4** en el entorno de ejecución e interrumpí otros servidores para liberar memoria. La primera reconstrucción descarga varios GB y carga modelos; las siguientes reutilizan el proceso. Gradio y CLIP usan el entorno principal; DiffBIR usa un proceso en su entorno aislado. El pipeline oficial de DiffBIR no incluye el filtro de contenido de SD/Tile. CLIP usa CPU.

La primera celda permite elegir `MODO = 'aplicacion'` (fotos propias) o **`MODO = 'prueba_diffbir'`** (ensayo con referencia). La app usa `MOTOR = 'diffbir'`; `sd_tile` conserva el recorrido anterior. La prueba ejecuta solo el par gaussiano conservado de potw1803a. Guarda SCUNet nativo, condición ampliada, condición reducida y salida final; compara contra la referencia sin pasarla al modelo. La app no inventa una referencia ni calcula PSNR/SSIM para fotos propias. DiffBIR amplía internamente a lado mínimo 512 y reduce de nuevo al tamaño de trabajo. El checkpoint SD 2.1 se obtiene de un respaldo de terceros fijado por revisión y SHA-256 porque el enlace original respondió 401. Los pesos ocupan aproximadamente 6,7 GB, además del entorno y cachés; no se descargan al generar este notebook.

La opción inicial clona el proyecto publicado en GitHub. Ejecutar las celdas en orden desde el navegador de Colab. Para probar cambios locales antes de publicarlos, ejecutar en el proyecto `uv run --locked python colab/preparar_app.py`, cambiar a `ORIGEN = 'paquete_local'` y subir **outputs/astrorestore_app_colab.zip** cuando se solicite. Solo incluye código y activos públicos, sin tokens ni pesos. La subida de ZIP usa el navegador de Colab, no VS Code.
"""), cell("code", "preparar", """from pathlib import Path
from datetime import datetime, timezone
from zipfile import ZipFile
import hashlib, json, subprocess, sys
from google.colab import files

ORIGEN = 'github'  # 'paquete_local' permite subir el ZIP generado desde el proyecto
MODO = 'aplicacion'  # Cambiar a 'prueba_diffbir' para el experimento acotado
MOTOR = 'diffbir'  # 'sd_tile' conserva la variante anterior de la app
if MODO not in ('aplicacion', 'prueba_diffbir'):
    raise ValueError('Elegir aplicacion o prueba_diffbir.')
if MOTOR not in ('diffbir', 'sd_tile'):
    raise ValueError('Elegir diffbir o sd_tile.')
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
def ejecutar(command, log=None):
    import contextlib, os, signal
    if log:
        log.parent.mkdir(parents=True, exist_ok=True)
    with (log.open('w', encoding='utf-8') if log else contextlib.nullcontext()) as registro:
        process = subprocess.Popen(command, cwd=proyecto, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, start_new_session=True)
        try:
            for line in process.stdout:
                print(line, end='', flush=True)
                if registro:
                    registro.write(line)
                    registro.flush()
        except KeyboardInterrupt:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
            if registro:
                registro.write('Interrupción manual desde el notebook; se detuvo el grupo de procesos.\\n')
            raise
        codigo_salida = process.wait()
        if registro:
            registro.write(f'\\nCódigo de salida del subproceso: {codigo_salida}\\n')
            registro.flush()
        if codigo_salida:
            raise subprocess.CalledProcessError(codigo_salida, command)

entorno = [] if MODO == 'aplicacion' else ['--project', 'colab/diffbir']
usa_diffbir = MODO == 'prueba_diffbir' or MOTOR == 'diffbir'
if usa_diffbir and not (proyecto / 'colab/diffbir/uv.lock').exists():
    raise RuntimeError('La copia no contiene DiffBIR. Usar paquete_local o publicar los cambios antes de clonar.')

ejecutar(['uv', 'sync', *entorno, '--locked', '--python', '3.12'])
if usa_diffbir:
    if MODO == 'aplicacion':
        ejecutar(['uv', 'sync', '--project', 'colab/diffbir', '--locked', '--python', '3.12'])
    ejecutar(['uv', 'run', '--project', 'colab/diffbir', '--locked', 'python', '-c', "from src.diffbir_trial import check_checkpoint_dependencies; print('Checkpoint: imports verificados', check_checkpoint_dependencies())"])

entorno_gpu = ['--project', 'colab/diffbir'] if usa_diffbir else []
ejecutar(['uv', 'run', *entorno_gpu, '--locked', 'python', '-c', "import torch; print('CUDA:',torch.cuda.is_available()); assert torch.cuda.is_available(), 'Seleccionar GPU T4 antes de procesar'; print(torch.cuda.get_device_name(0))"])
"""), cell("code", "abrir-app", """# Abrir el enlace gradio.live que aparezca; interrumpir esta celda para detener el servidor.
if MODO == 'aplicacion':
    ejecutar(['uv', 'run', '--locked', 'python', '-u', '-c', f"import os; os.environ['ASTRORESTORE_ENGINE'] = {MOTOR!r}; from app import launch_app; launch_app(share=True, server_name='0.0.0.0')"])
else:
    print('Se omite Gradio; continuar con la prueba DiffBIR de abajo.')
"""), cell("markdown", "explicacion-diffbir", """## Prueba acotada DiffBIR v2 (solo si se seleccionó prueba_diffbir)

Una configuración: 50 pasos, sampler spaced, CFG 4, semilla 42, control IRControlNet 1, prompt positivo vacío y captioner desactivado. El control 1 **no es** el strength img2img de nuestra app. SCUNet limpia a resolución nativa; DiffBIR usa esa condición ampliada y aplica corrección wavelet antes de reducir la salida. Guardamos también la condición de ida y vuelta para examinar el remuestreo. La referencia solo interviene en evaluación.

La celda descarga la revisión fijada del código oficial y los pesos declarados. Si falla, conserva el estado y los resultados parciales; no cambia de modelo, configuración ni dispositivo automáticamente. No se declara éxito por terminar una celda: revisar resultado.json, métricas y los mismos recortes. Descargar el ZIP incluso si SCUNet termina y difusión falla. El código y los pesos son externos; sus fuentes, revisiones y hashes quedan registrados.
"""), cell("code", "ejecutar-diffbir", """if MODO == 'prueba_diffbir':
    from zipfile import ZIP_DEFLATED
    from IPython.display import display
    from PIL import Image
    revision_diffbir = '5c2d6c177c3f2965e6d33a32931248d242ef7b3d'
    salida_diffbir = proyecto / 'outputs' / ('diffbir_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    fuente_diffbir = salida_diffbir.parent / ('fuente_diffbir_' + salida_diffbir.name)
    ejecutar(['git', 'init', str(fuente_diffbir)])
    ejecutar(['git', '-C', str(fuente_diffbir), 'remote', 'add', 'origin', 'https://github.com/XPixelGroup/DiffBIR.git'])
    ejecutar(['git', '-C', str(fuente_diffbir), 'fetch', '--depth', '1', 'origin', revision_diffbir])
    ejecutar(['git', '-C', str(fuente_diffbir), 'checkout', '--detach', 'FETCH_HEAD'])
    prefijo_diffbir = ['uv', 'run', '--project', 'colab/diffbir', '--locked', 'python', '-u', '-m', 'src.diffbir_trial']
    ejecutar([*prefijo_diffbir, 'prepare', '--output-dir', str(salida_diffbir)])
    log_diffbir = proyecto / 'logs' / (salida_diffbir.name + '.log')
    codigo_diffbir = 0
    try:
        ejecutar([*prefijo_diffbir, 'run', '--output-dir', str(salida_diffbir), '--upstream-dir', str(fuente_diffbir)], log=log_diffbir)
    except subprocess.CalledProcessError as error:
        codigo_diffbir = error.returncode
        print('PRUEBA FALLIDA. Código de salida:', codigo_diffbir)
    except KeyboardInterrupt:
        codigo_diffbir = 130
        raise
    finally:
        # El padre sigue vivo ante SIGKILL del hijo y puede cerrar su registro incompleto.
        import importlib.util
        spec = importlib.util.spec_from_file_location('registro_diffbir', proyecto / 'src/diffbir_trial.py')
        registro_modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(registro_modulo)
        registro_diffbir = registro_modulo.record_process_exit(salida_diffbir, codigo_diffbir)
        print('Estado:', registro_diffbir['estado'])
        print(json.dumps(registro_diffbir.get('evaluacion', {}), ensure_ascii=False, indent=2))
        zip_diffbir = salida_diffbir / 'prueba_diffbir.zip'
        with ZipFile(zip_diffbir, 'w', ZIP_DEFLATED) as archivo:
            for path in sorted(salida_diffbir.iterdir()):
                if path.is_file() and path != zip_diffbir:
                    archivo.write(path, path.name)
            if log_diffbir.exists():
                archivo.write(log_diffbir, 'logs/' + log_diffbir.name)
        for nombre in ('comparacion.png', 'recortes.png'):
            if (salida_diffbir / nombre).exists():
                display(Image.open(salida_diffbir / nombre))
        files.download(str(zip_diffbir))
else:
    print('Prueba DiffBIR omitida: está seleccionado el modo aplicación.')
"""), cell("markdown", "revisar", """## Recorrido para verificar

1. Subir una foto astronómica PNG o TIFF compatible. Los archivos de 16 o 32 bits requieren una copia RGB de 8 bits exportada desde el editor, conservando el original.
2. Cambiar la entrada debe limpiar resultados anteriores. La vista principal no ofrece ejemplos ni registros técnicos.
3. Con DiffBIR pulsar **Procesar y comparar**. La configuración es fija; el strength anterior no se presenta como control de limpieza de DiffBIR. Con la variante SD/Tile el control inicial sigue en 0,10.
4. Ver las tres etapas juntas. Comparar primero limpieza y reconstrucción; cambiar de par debe actualizar el deslizador, la leyenda y el amarillo sin ejecutar modelos. Las marcas no identifican invenciones: los detalles nuevos quedan no verificados hasta contar con otra observación independiente. La lectura CLIP es secundaria. Descargar el ZIP y comprobar original, salida sin marcas, primera limpieza SCUNet, copia resaltada (entrada frente a resultado final), copia con aviso visible de IA, informe, parámetros y hashes.
5. Capturar la advertencia, comparación e informe, conservando el crédito. Anotar revisión de código, GPU, duración y errores para la demo. Revisar también móvil y teclado.

Si CLIP falla después de difusión, descargar las imágenes y reintentar solo el análisis. El ensayo DiffBIR real está registrado; la app integrada nueva con proceso persistente aún debe validarse en Colab. La comprobación local de su protocolo y UI no sustituye esa prueba GPU.

Imagen de ejemplo: https://esahubble.org/images/potw1803a/ — **NASA, ESA, and J. Comerford (University of Colorado-Boulder)** — CC BY 4.0, https://creativecommons.org/licenses/by/4.0/ conforme a https://esahubble.org/copyright/. Derivadas RGB reducidas, con ruido sintético y reconstrucción IA; sin autenticidad científica garantizada.
""")]
    notebook = dict(cells=cells, metadata=dict(kernelspec=dict(display_name="Python 3", language="python", name="python3")), nbformat=4, nbformat_minor=5)
    path = ROOT / "colab/ejecutar_en_colab.ipynb"
    path.write_text(json.dumps(notebook, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for item in cells:
        if item["cell_type"] == "code":
            compile("".join(item["source"]), item["id"], "exec")
    print("Notebook:", path)
    print("Paquete:", archive, "SHA256:", hashlib.sha256(archive.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
