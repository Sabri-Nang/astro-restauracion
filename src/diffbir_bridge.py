"""Comunicación con un motor DiffBIR persistente en su entorno uv aislado."""
from __future__ import annotations

import argparse
import atexit
import contextlib
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import queue
import signal
import subprocess
import sys
import threading
import tempfile
import time
import traceback
from uuid import uuid4

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PHASES = {
    "iniciando": (0.1, "Preparando la IA; la primera vez puede tardar varios minutos"),
    "preparando_limpieza": (0.15, "Preparando el modelo de limpieza; puede necesitar descargar archivos"),
    "primera_limpieza": (0.2, "Preparando una primera limpieza de tu foto"),
    "preparando_reconstruccion": (0.35, "Preparando la reconstrucción de detalles"),
    "reconstruyendo": (0.55, "Reconstruyendo la imagen; revisá los detalles al terminar"),
    "ajustando_salida": (0.75, "Terminando la imagen y comprobando el resultado"),
}


class DiffBIRSession:
    """Un proceso por aplicación, serializado; no arranca al importar módulos."""

    def __init__(self):
        self.process = None
        self.messages = queue.Queue()
        self.lock = threading.Lock()
        self.log = None
        atexit.register(self.close)

    def _source(self):
        from src.diffbir_trial import UPSTREAM_REVISION
        source = ROOT / ".cache/diffbir/source"
        if not source.exists():
            source.parent.mkdir(parents=True, exist_ok=True)
            # Publicar la caché solo después de completar la descarga; un fallo
            # de red no debe dejar una carpeta que impida el próximo intento.
            with tempfile.TemporaryDirectory(prefix="source_", dir=source.parent) as work:
                staging = Path(work) / "repo"
                for command in (["git", "init", str(staging)],
                                ["git", "-C", str(staging), "remote", "add", "origin", "https://github.com/XPixelGroup/DiffBIR.git"],
                                ["git", "-C", str(staging), "fetch", "--depth", "1", "origin", UPSTREAM_REVISION],
                                ["git", "-C", str(staging), "checkout", "--detach", "FETCH_HEAD"]):
                    subprocess.run(command, cwd=ROOT, stdout=self.log, stderr=self.log, check=True)
                staging.replace(source)
        return source

    def _start(self):
        if self.process is not None and self.process.poll() is None:
            return
        self.close()
        if sys.platform != "linux":
            raise RuntimeError("Esta reconstrucción necesita Colab con GPU. Abrí colab/ejecutar_en_colab.ipynb para procesar tu foto.")
        folder = ROOT / "logs"
        folder.mkdir(exist_ok=True)
        self.log = (folder / f"app_diffbir_{uuid4().hex}.log").open("w", encoding="utf-8")
        try:
            source = self._source()
            self.messages = queue.Queue()
            self.process = subprocess.Popen(
                ["uv", "run", "--project", "colab/diffbir", "--locked", "python", "-u", "-m", "src.diffbir_bridge", "--serve", "--upstream", str(source)],
                cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.log,
                text=True, bufsize=1, start_new_session=True,
            )
        except subprocess.SubprocessError as error:
            self.close()
            raise RuntimeError("No se pudo preparar DiffBIR. Revisá la conexión y los registros de Colab.") from error
        except Exception:
            self.close()
            raise
        process, messages = self.process, self.messages

        def read_responses():
            try:
                for line in process.stdout:
                    try:
                        messages.put(json.loads(line))
                    except json.JSONDecodeError:
                        # Los mensajes ajenos al protocolo no se interpretan como resultados.
                        continue
            finally:
                messages.put(None)

        threading.Thread(target=read_responses, daemon=True).start()

    def infer(self, prepared: Image.Image, progress=lambda *_args, **_kwargs: None):
        with self.lock:
            progress(PHASES["iniciando"][0], desc=PHASES["iniciando"][1])
            self._start()
            folder = ROOT / "outputs/interfaz_diffbir" / uuid4().hex
            folder.mkdir(parents=True)
            prepared.save(folder / "entrada.png")
            output = folder / "resultado"
            request_id = uuid4().hex
            request = {"id": request_id, "input": str(folder / "entrada.png"), "output": str(output)}
            try:
                self.process.stdin.write(json.dumps(request) + "\n")
                self.process.stdin.flush()
                started = time.monotonic()
                while True:
                    if time.monotonic() - started > 1800:
                        self.close()
                        raise RuntimeError("La reconstrucción no respondió a tiempo. Probá nuevamente; los registros quedan en logs/.")
                    try:
                        message = self.messages.get(timeout=10)
                    except queue.Empty:
                        if self.process.poll() is not None:
                            raise RuntimeError("La reconstrucción se interrumpió. Puede faltar memoria; revisá el registro de Colab antes de reintentar.")
                        continue
                    if message is None:
                        raise RuntimeError("El proceso de reconstrucción terminó sin un resultado. Revisá los registros de Colab.")
                    if message.get("id") != request_id:
                        continue
                    if message["type"] == "phase":
                        value, description = PHASES[message["phase"]]
                        progress(value, desc=description)
                    elif message["type"] == "step":
                        completed, total = message["completed"], message["total"]
                        if not (isinstance(completed, int) and isinstance(total, int) and 0 <= completed <= total and total > 0):
                            raise RuntimeError("La reconstrucción informó un avance no válido.")
                        progress((completed, total), desc="Generando reconstrucción")
                    elif message["type"] == "error":
                        raise RuntimeError("No se pudo reconstruir esta foto. Tu original se conserva. Revisá el registro de Colab; no se sustituyó la salida por otra imagen.")
                    elif message["type"] == "result":
                        return read_worker_result(prepared, output, message["metadata"])
            except (BrokenPipeError, OSError):
                self.close()
                raise RuntimeError("Se perdió la conexión con la reconstrucción. Probá nuevamente desde Colab.")

    def close(self):
        process, self.process = self.process, None
        if process is not None:
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                    process.wait(timeout=5)
                except (ProcessLookupError, subprocess.TimeoutExpired):
                    if process.poll() is None:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait()
            for stream in (process.stdin, process.stdout):
                if stream:
                    stream.close()
        if self.log:
            self.log.close()
            self.log = None


def read_worker_result(before, folder: Path, metadata: dict):
    """Verifica el resultado del proceso antes de mostrarlo o exportarlo."""
    from src.honesty import difference_map
    expected_names = ("entrada_preparada.png", "limpieza_previa.png", "salida_diffbir.png", "condicion_interna.png", "condicion_reducida.png")
    for name in expected_names:
        expected = metadata.get("artefactos", {}).get(name)
        if not expected or hashlib.sha256((folder / name).read_bytes()).hexdigest() != expected:
            raise ValueError("El resultado de reconstrucción no coincide con su registro.")
    with Image.open(folder / "entrada_preparada.png") as saved:
        if saved.mode != before.mode or saved.size != before.size or saved.tobytes() != before.tobytes():
            raise ValueError("La reconstrucción corresponde a otra entrada.")
    with Image.open(folder / "salida_diffbir.png") as image:
        after = image.copy()
    with Image.open(folder / "limpieza_previa.png") as image:
        first = image.copy()
    difference_map(before, after)
    difference_map(before, first)
    metadata = dict(metadata)
    metadata["intermedios"] = {name: str(folder / name) for name in ("limpieza_previa.png", "condicion_reducida.png")}
    return before, after, metadata


@lru_cache(maxsize=1)
def get_session():
    return DiffBIRSession()


def serve(upstream: Path):
    """Protocolo JSON por stdout; logs y bibliotecas externas van a stderr."""
    from src.diffusion import DiffBIRRuntime
    protocol = sys.stdout
    engine = None
    for line in sys.stdin:
        request = json.loads(line)
        request_id = request["id"]

        def send(message):
            protocol.write(json.dumps({"id": request_id, **message}, ensure_ascii=False) + "\n")
            protocol.flush()

        def phase(name):
            send({"type": "phase", "phase": name})

        def step(completed, total):
            send({"type": "step", "completed": completed, "total": total})

        try:
            with contextlib.redirect_stdout(sys.stderr):
                if engine is None:
                    phase("iniciando")
                    engine = DiffBIRRuntime(upstream, ROOT / ".cache/diffbir")
                with Image.open(request["input"]) as image:
                    before = image.copy()
                _, _, _, metadata = engine.process(before, Path(request["output"]), on_phase=phase, on_step=step)
            send({"type": "result", "metadata": metadata})
        except Exception:
            traceback.print_exc(file=sys.stderr)
            # No reutilizar objetos que pudieron quedar a medio cargar tras un error.
            engine = None
            import gc
            gc.collect()
            send({"type": "error"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serve", action="store_true", required=True)
    parser.add_argument("--upstream", type=Path, required=True)
    args = parser.parse_args()
    serve(args.upstream)
