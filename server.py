import threading
import os
import time
import urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"PepeRush Bot is running!")
    
    def log_message(self, format, *args):
        pass

def keep_alive():
    url = os.environ.get("RENDER_EXTERNAL_URL", "")
    if not url:
        return
    while True:
        try:
            urllib.request.urlopen(url)
        except:
            pass
        time.sleep(600)  # ping every 10 minutes

def run_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()

def start():
    t1 = threading.Thread(target=run_server, daemon=True)
    t1.start()
    t2 = threading.Thread(target=keep_alive, daemon=True)
    t2.start()
