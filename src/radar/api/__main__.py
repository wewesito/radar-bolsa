"""Arranque del motor: `python -m radar.api --token XXX [--port 0] [--watch-parent]`.

Con --port 0 el sistema elige un puerto libre. Al estar listo escribe en la salida estándar
una línea `RADAR_ENGINE_READY port=NNNN`, que la app de escritorio lee para conectarse.
Con --watch-parent el motor se cierra solo si la app que lo lanzó desaparece.
"""

import argparse
import os
import socket
import sys
import threading
import time

import uvicorn

from radar import config
from radar.api.app import create_app
from radar.api.state import Engine
from radar.data.service import default_service
from radar.db.database import Database

READY_PREFIX = "RADAR_ENGINE_READY"


def _watch_parent() -> None:
    parent = os.getppid()

    def loop() -> None:
        while True:
            time.sleep(2)
            if os.getppid() != parent:  # el padre murió: nos adoptó otro proceso
                os._exit(0)

    threading.Thread(target=loop, daemon=True).start()


def main(argv: list[str] | None = None) -> None:
    if "--check-alerts" in (argv if argv is not None else sys.argv[1:]):
        from radar.alerts.checker import run  # lo lanza launchd con la app cerrada

        run(notify=True)
        return
    ap = argparse.ArgumentParser(prog="radar-engine")
    ap.add_argument("--port", type=int, default=0)
    ap.add_argument("--token", default=os.getenv("RADAR_TOKEN"))
    ap.add_argument("--watch-parent", action="store_true")
    args = ap.parse_args(argv)
    if not args.token:
        sys.exit("Falta --token (o la variable RADAR_TOKEN).")

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", args.port))  # solo local: nunca accesible desde la red
    port = sock.getsockname()[1]

    engine = Engine(default_service(), Database(config.DB_PATH))
    app = create_app(engine, args.token)
    engine.start_alert_loop()
    threading.Thread(target=engine.log_signals, daemon=True).start()
    if args.watch_parent:
        _watch_parent()
    print(f"{READY_PREFIX} port={port}", flush=True)
    server = uvicorn.Server(
        uvicorn.Config(app, log_level="warning", loop="asyncio", http="h11", lifespan="off")
    )
    server.run(sockets=[sock])


if __name__ == "__main__":
    main()
