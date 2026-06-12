import http.server
import socketserver
import os
import subprocess
import json

PORT = 8000
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

class PayrollHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Serve the entire base directory
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def do_GET(self):
        # Redirect root path to result_page/index.html dashboard
        if self.path == '/' or self.path == '':
            self.send_response(301)
            self.send_header('Location', '/result_page/index.html')
            self.end_headers()
            return
        super().do_GET()

    def end_headers(self):
        # Enable CORS for convenience
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_POST(self):
        if self.path == '/api/process':
            try:
                # Trigger the processing script
                script_path = os.path.join(BASE_DIR, "pythonscript", "process_payroll.py")
                res = subprocess.run(["python", script_path], capture_output=True, text=True)
                
                if res.returncode == 0:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "status": "success", 
                        "message": "Data payroll berhasil diproses secara otomatis!"
                    }).encode('utf-8'))
                else:
                    self.send_response(500)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "status": "error", 
                        "message": f"Skrip gagal berjalan: {res.stderr}"
                    }).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))
                
        elif self.path == '/api/upload':
            try:
                # Custom multipart/form-data parser for Python 3.13 (no cgi module)
                content_type = self.headers.get('content-type', '')
                if 'boundary=' not in content_type:
                    self.send_response(400)
                    self.end_headers()
                    return
                
                boundary = content_type.split('boundary=')[1].strip().encode('utf-8')
                content_length = int(self.headers.get('content-length', 0))
                body = self.rfile.read(content_length)
                
                # Split body by boundary
                parts = body.split(b'--' + boundary)
                filename = "input_file.csv"
                file_data = b""
                
                for part in parts:
                    if b'Content-Disposition' in part:
                        headers_part, data_part = part.split(b'\r\n\r\n', 1)
                        # Remove trailing \r\n
                        if data_part.endswith(b'\r\n'):
                            data_part = data_part[:-2]
                        if data_part.endswith(b'--'):
                            data_part = data_part[:-2]
                            if data_part.endswith(b'\r\n'):
                                data_part = data_part[:-2]
                        
                        headers_str = headers_part.decode('utf-8', errors='ignore')
                        # Extract filename
                        fn_match = re.search(r'filename="([^"]+)"', headers_str)
                        name_match = re.search(r'name="([^"]+)"', headers_str)
                        
                        if name_match and name_match.group(1) == 'file':
                            file_data = data_part
                            if fn_match:
                                filename = fn_match.group(1)
                
                if file_data:
                    target_path = os.path.join(BASE_DIR, "datainput", filename)
                    with open(target_path, "wb") as f:
                        f.write(file_data)
                    
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "status": "success", 
                        "message": f"File {filename} berhasil diunggah ke folder datainput!"
                    }).encode('utf-8'))
                else:
                    self.send_response(400)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "status": "error",
                        "message": "Data file tidak ditemukan dalam request."
                    }).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

import re

def start():
    # Allow port reuse
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), PayrollHTTPRequestHandler) as httpd:
        print(f"Server berjalan di http://localhost:{PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer dihentikan.")

if __name__ == "__main__":
    start()
