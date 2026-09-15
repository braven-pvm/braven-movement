"""Serve a packaged athlete studio locally, including GLB access from local Tactics."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import argparse


class Handler(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map, '.glb': 'model/gltf-binary'}

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache')
        super().end_headers()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path(__file__).parent / 'studio')
    parser.add_argument('--port', type=int, default=5393)
    args = parser.parse_args()
    root = args.root.resolve()
    if not (root / 'athlete-assets/netball-athlete.glb').is_file():
        parser.error('Root must contain the packaged studio and athlete-assets/netball-athlete.glb')
    print(f'Athlete studio: http://127.0.0.1:{args.port}/', flush=True)
    ThreadingHTTPServer(('127.0.0.1', args.port), partial(Handler, directory=str(root))).serve_forever()
