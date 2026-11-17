#!/usr/bin/env python3
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import json
ROOT=Path("/opt/securityprepper/trading-dashboard/web")
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        route=self.path.split("?")[0]
        routes={"/trading/":("index.html","text/html; charset=utf-8"),"/trading/app.js":("app.js","text/javascript; charset=utf-8"),
            "/trading/style.css":("style.css","text/css; charset=utf-8"),"/trading/sw.js":("sw.js","text/javascript; charset=utf-8"),
            "/trading/manifest.webmanifest":("manifest.webmanifest","application/manifest+json"),"/trading/icon.svg":("icon.svg","image/svg+xml"),
            "/trading/icon-192.png":("icon-192.png","image/png"),"/trading/icon-512.png":("icon-512.png","image/png")}
        try:
            if route=="/trading/api/dashboard":
                body=Path("/var/lib/securityprepper-dashboard/dashboard.json").read_bytes(); mime="application/json"
            elif route in routes:
                name,mime=routes[route]; body=(ROOT/name).read_bytes()
            else: self.send_error(404); return
            self.send_response(200); self.send_header("Content-Type",mime)
            self.send_header("Cache-Control","no-store"); self.send_header("X-Content-Type-Options","nosniff")
            self.send_header("Content-Security-Policy","default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self'; connect-src 'self'; worker-src 'self'; manifest-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'")
            self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body)
        except FileNotFoundError: self.send_error(503,"Waiting for first verified snapshot")
    def do_POST(self): self.send_error(405)
    def log_message(self,*args): pass
if __name__=="__main__": ThreadingHTTPServer(("127.0.0.1",8824),Handler).serve_forever()