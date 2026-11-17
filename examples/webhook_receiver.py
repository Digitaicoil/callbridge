"""A minimal receiver for CallBridge's webhook sink: checks the secret, saves each call. No dependencies.

  CALLBRIDGE_WEBHOOK_SECRET=change-me python examples/webhook_receiver.py     # listens on :8787
  # .env:  CALLBRIDGE_SINKS=webhook  CALLBRIDGE_WEBHOOK_URL=http://localhost:8787/calls  CALLBRIDGE_WEBHOOK_SECRET=change-me
"""
import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

SECRET = os.environ.get("CALLBRIDGE_WEBHOOK_SECRET", "")


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if SECRET and not hmac.compare_digest(self.headers.get("X-CallBridge-Secret", ""), SECRET):
            self.send_response(401), self.end_headers()
            return
        call = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        print(f"{call['started_at']}  {call['direction']:8}  {call['number']:16}  "
              f"{call['data'].get('outcome', '-'):20}  {call['summary'][:80]}")
        # → create the lead / contact / ticket in your system here
        self.send_response(204), self.end_headers()


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", 8787), Handler).serve_forever()
