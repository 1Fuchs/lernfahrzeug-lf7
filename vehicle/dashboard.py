"""Bedient die Weboberfläche.

Rechnet selbst nichts. Es zeigt nur, was die Steuerung zuletzt im Cache
abgelegt hat. Deshalb können beliebig viele Browser
gleichzeitig zusehen.
"""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from time import sleep

from vehicle.cache import SharedCache

STREAM_PAUSE_S = 0.04

SEITE = b"""<!DOCTYPE html>
<html lang="de"><head><meta charset="utf-8"><title>Lernfahrzeug</title>
<style>
 body { font-family: sans-serif; background: #222; color: #eee; text-align: center; }
 img { width: 640px; max-width: 96vw; image-rendering: pixelated; border: 2px solid #444; }
 button { font-size: 20px; padding: 12px 32px; margin: 12px 8px; border: 0;
          border-radius: 6px; color: #fff; cursor: pointer; }
 .start { background: #2f8073; } .stop { background: #b03a48; }
 .dreh { background: #40506b; }
 table { margin: 16px auto; border-collapse: collapse; }
 td { padding: 4px 16px; border-bottom: 1px solid #444; text-align: left; }
 #fehler { color: #ff8a80; font-weight: bold; }
</style></head><body>
<h1>Lernfahrzeug</h1>
<img src="/stream">
<div>
  <button class="start" onclick="fetch('/start')">Starten</button>
  <button class="stop"  onclick="fetch('/stop')">Stoppen</button>
</div>
<div>
  <button class="dreh" id="links">Links drehen</button>
  <button class="dreh" id="rechts">Rechts drehen</button>
</div>
<div id="fehler"></div>
<div id="entscheidung_feld" style="display:none">
 <h2>Entscheidung</h2>
 <table>
  <tr><td>Aktion</td><td id="aktion">-</td></tr>
  <tr><td>Eingaben</td><td id="eingaben">-</td></tr>
  <tr><td>Hinweis</td><td id="hinweis">-</td></tr>
 </table>
</div>
<table>
 <tr><td>Zustand</td><td id="zustand">-</td></tr>
 <tr><td>Linienmitte</td><td id="mitte">-</td></tr>
 <tr><td>Linienbreite</td><td id="breite">-</td></tr>
 <tr><td>Abstand</td><td id="abstand">-</td></tr>
 <tr><td>Erkannt</td><td id="objekte">-</td></tr>
</table>
<script>
 let nachschub = null;
 function drehenAn(richtung) {
   fetch('/drehen?' + richtung);
   clearInterval(nachschub);
   nachschub = setInterval(() => fetch('/drehen?' + richtung), 200);
 }
 function drehenAus() {
   clearInterval(nachschub);
   fetch('/drehen?aus');
 }
 for (const richtung of ['links', 'rechts']) {
   const knopf = document.getElementById(richtung);
   knopf.addEventListener('mousedown', () => drehenAn(richtung));
   knopf.addEventListener('touchstart', (e) => { e.preventDefault(); drehenAn(richtung); });
   for (const ereignis of ['mouseup', 'mouseleave', 'touchend', 'touchcancel']) {
     knopf.addEventListener(ereignis, drehenAus);
   }
 }

 setInterval(async () => {
   const z = await (await fetch('/zustand.json')).json();
   zustand.textContent = z.fahrt_frei ? 'FAHRT' : 'STOPP';
   mitte.textContent   = z.linienmitte === null ? 'keine Linie' : z.linienmitte + ' px';
   breite.textContent  = z.linienbreite === null ? '-' : z.linienbreite + ' px';
   abstand.textContent = z.abstand_cm + ' cm';
   objekte.textContent = z.objekte.length
     ? z.objekte.map(f => f.name + ' ' + f.konfidenz).join(', ') : 'nichts';
   fehler.textContent  = z.fehler ? 'Steuerung abgebrochen: ' + z.fehler : '';
   const e = z.entscheidung;
   entscheidung_feld.style.display = e ? '' : 'none';
   if (e) {
     aktion.textContent   = e.aktion;
     eingaben.textContent = e.eingaben.length
       ? e.eingaben.map(f => f.klasse + ' ' + f.konfidenz + ' ' + f.seite).join(', ') : 'keine';
     hinweis.textContent  = e.hinweis || '-';
   }
 }, 250);
</script>
</body></html>"""


class Dashboard(BaseHTTPRequestHandler):
    """Beantwortet die Anfragen des Browsers."""

    cache: SharedCache = None

    def do_GET(self):
        if self.path == "/":
            self._send(SEITE, "text/html; charset=utf-8")
        elif self.path == "/stream":
            self._stream()
        elif self.path == "/zustand.json":
            self._send(self.cache.get_status_json(), "application/json")
        elif self.path in ("/start", "/stop"):
            self.cache.set_drive_control(self.path == "/start")
            self._send(b"ok", "text/plain")
        elif self.path.startswith("/drehen"):
            richtung = self.path.partition("?")[2]
            self.cache.set_turn_request(richtung if richtung in ("links", "rechts") else None)
            self._send(b"ok", "text/plain")
        else:
            self.send_error(404)

    def _send(self, daten: bytes, typ: str) -> None:
        """Schreibt eine vollständige Antwort und schließt sie ab."""
        self.send_response(200)
        self.send_header("Content-Type", typ)
        self.send_header("Content-Length", str(len(daten)))
        self.end_headers()
        self.wfile.write(daten)

    def _stream(self) -> None:
        """Sendet die Bilder als MJPEG, bis der Browser abbricht.

        Jedes Bild wird mit eigenen Kopfzeilen direkt in den Datenstrom
        geschrieben. Der Browser zeigt die Folge als Video.
        """
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=RAHMEN")
        self.end_headers()

        try:
            while self.cache.is_running:
                jpeg = self.cache.get_image()
                if jpeg is None:
                    sleep(0.05)
                    continue

                self.wfile.write(b"--RAHMEN\r\n")
                self.wfile.write(b"Content-Type: image/jpeg\r\n")
                self.wfile.write(f"Content-Length: {len(jpeg)}\r\n\r\n".encode())
                self.wfile.write(jpeg)
                self.wfile.write(b"\r\n")
                sleep(STREAM_PAUSE_S)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, format, *args):
        return


def start_server(speicher: SharedCache, port: int) -> None:
    """Startet den Webserver und bedient Anfragen, bis er unterbrochen wird.

    ThreadingHTTPServer gibt jeder Anfrage einen eigenen Thread. Ohne ihn
    würde der endlose Stream jede weitere Anfrage blockieren und ein zweiter
    Browser wartete vergeblich.
    """
    Dashboard.cache = speicher
    server = ThreadingHTTPServer(("", port), Dashboard)
    try:
        server.serve_forever()
    finally:
        server.server_close()
