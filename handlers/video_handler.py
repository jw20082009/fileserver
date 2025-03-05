from http.server import BaseHTTPRequestHandler
import cgi
import os
import urllib.parse
from datetime import datetime
import json
from utils.file_utils import load_upload_info, save_upload_info
from utils.template_utils import render_template

class VideoServerHandler(BaseHTTPRequestHandler):
    def get_client_ip(self):
        if 'X-Forwarded-For' in self.headers:
            return self.headers['X-Forwarded-For']
        return self.client_address[0]

    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            upload_info = load_upload_info()
            files = os.listdir('videos')
            self.wfile.write(render_template('index.html', {
                'files': files,
                'upload_info': upload_info
            }).encode())
            
        elif self.path.startswith('/videos/'):
            filename = urllib.parse.unquote(self.path[8:])
            filepath = os.path.join('videos', filename)
            
            if os.path.exists(filepath):
                self.send_response(200)
                self.send_header('Content-type', 'video/mp4')
                self.end_headers()
                with open(filepath, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, 'File not found')

    def do_POST(self):
        if self.path == '/':
            client_ip = self.get_client_ip()
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={'REQUEST_METHOD': 'POST'}
            )
            
            if 'video' in form:
                if isinstance(form['video'], list):
                    files = form['video']
                else:
                    files = [form['video']]
                
                upload_info = load_upload_info()
                
                for fileitem in files:
                    if fileitem.filename:
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                        filename = timestamp + fileitem.filename
                        filepath = os.path.join('videos', filename)
                        
                        with open(filepath, 'wb') as f:
                            f.write(fileitem.file.read())
                        
                        upload_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        upload_info[filename] = {
                            'time': upload_time,
                            'ip': client_ip
                        }
                
                save_upload_info(upload_info)
                
                self.send_response(303)
                self.send_header('Location', '/')
                self.end_headers()
                return
                
            self.send_error(400, 'Invalid request')

    def do_DELETE(self):
        if self.path.startswith('/delete/'):
            filename = urllib.parse.unquote(self.path[8:])
            filepath = os.path.join('videos', filename)
            
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                    upload_info = load_upload_info()
                    if filename in upload_info:
                        del upload_info[filename]
                        save_upload_info(upload_info)
                    
                    self.send_response(200)
                    self.end_headers()
                except Exception as e:
                    self.send_error(500, f'Failed to delete file: {str(e)}')
            else:
                self.send_error(404, 'File not found')