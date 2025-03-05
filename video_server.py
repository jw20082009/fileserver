from http.server import HTTPServer, BaseHTTPRequestHandler
import cgi
import os
import urllib.parse
from datetime import datetime
import json

UPLOAD_DIR = "videos"
LOG_FILE = "upload.log"
UPLOAD_INFO_FILE = "upload_info.json"

class VideoServerHandler(BaseHTTPRequestHandler):
    def get_client_ip(self):
        if 'X-Forwarded-For' in self.headers:
            return self.headers['X-Forwarded-For']
        return self.client_address[0]

    def load_upload_info(self):
        if os.path.exists(UPLOAD_INFO_FILE):
            try:
                with open(UPLOAD_INFO_FILE, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_upload_info(self, info):
        with open(UPLOAD_INFO_FILE, 'w') as f:
            json.dump(info, f, indent=2)

    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            upload_info = self.load_upload_info()
            files = os.listdir(UPLOAD_DIR)
            files_html = '\n'.join([
                f'''<li>
                    <a href="/videos/{f}">{f}</a>
                    <span style="color: #666; margin: 0 10px;">
                        (Upload Time: {upload_info.get(f, {}).get('time', 'Unknown')} | 
                         Upload IP: {upload_info.get(f, {}).get('ip', 'Unknown')})
                    </span>
                    <button onclick="deleteFile('{f}')" class="delete-button">Delete</button>
                    <button onclick="copyVideoUrl('{f}')" class="copy-button">Copy URL</button>
                </li>''' for f in files
            ])
            
            html = f'''
            <html>
                <head>
                    <title>Video Server</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 20px; }}
                        .upload-form {{ margin: 20px 0; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }}
                        .file-list {{ margin-top: 10px; }}
                        #selected-files {{ margin: 10px 0; color: #666; }}
                        .progress {{ width: 100%; height: 20px; background: #f0f0f0; margin: 10px 0; border-radius: 10px; }}
                        .progress-bar {{ width: 0%; height: 100%; background: #4CAF50; border-radius: 10px; transition: width 0.3s; }}
                        .progress-text {{ margin-top: 5px; color: #666; }}
                        .delete-button {{ 
                            color: white; 
                            background-color: #ff4444; 
                            margin-left: 10px; 
                            border: none;
                            padding: 5px 10px;
                            border-radius: 3px;
                            cursor: pointer;
                        }}
                        .delete-button:hover {{ background-color: #cc0000; }}
                        .copy-button {{ 
                            color: white; 
                            background-color: #2196F3; 
                            margin-left: 10px; 
                            border: none;
                            padding: 5px 10px;
                            border-radius: 3px;
                            cursor: pointer;
                        }}
                        .copy-button:hover {{ background-color: #1976D2; }}
                        .toast {{
                            position: fixed;
                            bottom: 20px;
                            left: 50%;
                            transform: translateX(-50%);
                            background-color: #333;
                            color: white;
                            padding: 12px 24px;
                            border-radius: 4px;
                            display: none;
                            z-index: 1000;
                            animation: fadeInOut 2s ease;
                        }}
                        @keyframes fadeInOut {{
                            0% {{ opacity: 0; }}
                            10% {{ opacity: 1; }}
                            90% {{ opacity: 1; }}
                            100% {{ opacity: 0; }}
                        }}
                        input[type="submit"] {{
                            background-color: #4CAF50;
                            color: white;
                            padding: 10px 20px;
                            border: none;
                            border-radius: 5px;
                            cursor: pointer;
                        }}
                        input[type="submit"]:hover {{ background-color: #45a049; }}
                        li {{ margin: 10px 0; }}
                        a {{ color: #2196F3; text-decoration: none; }}
                        a:hover {{ text-decoration: underline; }}
                    </style>
                    <script>
                        let uploadQueue = [];
                        let isUploading = false;

                        function showToast(message) {{
                            const toast = document.getElementById('toast');
                            toast.textContent = message;
                            toast.style.display = 'block';
                            
                            setTimeout(() => {{
                                toast.style.display = 'none';
                            }}, 2000);
                        }}

                        function updateFileList() {{
                            const input = document.getElementById('video-input');
                            const fileList = document.getElementById('selected-files');
                            uploadQueue.push(...Array.from(input.files));
                            
                            fileList.innerHTML = 'Files to upload:<br>';
                            uploadQueue.forEach((file, index) => {{
                                fileList.innerHTML += `
                                    <div>
                                        - ${{file.name}}
                                        <button onclick="removeFromQueue(${{index}})" style="margin-left: 10px;">Remove</button>
                                    </div>`;
                            }});
                            
                            input.value = '';
                            
                            if (!isUploading && uploadQueue.length > 0) {{
                                uploadFiles();
                            }}
                        }}

                        function removeFromQueue(index) {{
                            if (!isUploading || index !== 0) {{
                                uploadQueue.splice(index, 1);
                                updateQueueDisplay();
                            }}
                        }}

                        function updateQueueDisplay() {{
                            const fileList = document.getElementById('selected-files');
                            fileList.innerHTML = 'Files to upload:<br>';
                            uploadQueue.forEach((file, index) => {{
                                fileList.innerHTML += `
                                    <div>
                                        - ${{file.name}}
                                        <button onclick="removeFromQueue(${{index}})" style="margin-left: 10px;">Remove</button>
                                    </div>`;
                            }});
                        }}

                        function uploadFiles() {{
                            if (!isUploading && uploadQueue.length > 0) {{
                                isUploading = true;
                                const progressBar = document.getElementById('progress-bar');
                                progressBar.style.width = '0%';
                                progressBar.style.backgroundColor = '#4CAF50';
                                uploadNextFile();
                            }}
                            return false;
                        }}

                        function uploadNextFile() {{
                            if (uploadQueue.length > 0) {{
                                const file = uploadQueue[0];
                                const formData = new FormData();
                                formData.append('video', file);
                                
                                const xhr = new XMLHttpRequest();
                                xhr.open('POST', '/');
                                
                                xhr.upload.onprogress = function(e) {{
                                    if (e.lengthComputable) {{
                                        const percent = (e.loaded / e.total) * 100;
                                        const progressBar = document.getElementById('progress-bar');
                                        const progressText = document.getElementById('progress-text');
                                        progressBar.style.width = percent + '%';
                                        progressText.textContent = `Uploading ${{file.name}}: ${{Math.round(percent)}}%`;
                                    }}
                                }};
                                
                                xhr.onreadystatechange = function() {{
                                    if (xhr.readyState === 4) {{
                                        if (xhr.status === 303 || xhr.status === 200) {{
                                            uploadQueue.shift();
                                            updateQueueDisplay();
                                            const progressText = document.getElementById('progress-text');
                                            
                                            if (uploadQueue.length > 0) {{
                                                progressText.textContent = `${{file.name}} uploaded. Starting next file...`;
                                                setTimeout(uploadNextFile, 1000);
                                            }} else {{
                                                progressText.textContent = 'All files uploaded!';
                                                isUploading = false;
                                            }}
                                            refreshVideoList();
                                        }} else {{
                                            const progressText = document.getElementById('progress-text');
                                            progressText.textContent = `Failed to upload ${{file.name}}`;
                                            const progressBar = document.getElementById('progress-bar');
                                            progressBar.style.backgroundColor = '#ff0000';
                                            isUploading = false;
                                        }}
                                    }}
                                }};
                                
                                xhr.send(formData);
                            }}
                        }}

                        function refreshVideoList() {{
                            fetch('/')
                                .then(response => response.text())
                                .then(html => {{
                                    const parser = new DOMParser();
                                    const doc = parser.parseFromString(html, 'text/html');
                                    const newList = doc.querySelector('.file-list');
                                    const currentList = document.querySelector('.file-list');
                                    currentList.innerHTML = newList.innerHTML;
                                }});
                        }}

                        function deleteFile(filename) {{
                            if (confirm('Are you sure you want to delete ' + filename + '?')) {{
                                fetch('/delete/' + encodeURIComponent(filename), {{
                                    method: 'DELETE'
                                }}).then(response => {{
                                    if (response.ok) {{
                                        window.location.reload();
                                    }} else {{
                                        alert('Delete failed!');
                                    }}
                                }});
                            }}
                        }}

                        function copyVideoUrl(filename) {{
                            const url = window.location.origin + '/videos/' + filename;
                            const tempInput = document.createElement('input');
                            tempInput.style.position = 'absolute';
                            tempInput.style.left = '-9999px';
                            tempInput.value = url;
                            document.body.appendChild(tempInput);
                            
                            tempInput.select();
                            try {{
                                document.execCommand('copy');
                                showToast('URL copied successfully!');
                            }} catch (err) {{
                                console.error('Failed to copy URL:', err);
                                showToast('Failed to copy URL');
                            }}
                            
                            document.body.removeChild(tempInput);
                        }}
                    </script>
                </head>
                <body>
                    <div class="upload-form">
                        <h2>Upload Videos</h2>
                        <form id="upload-form" enctype="multipart/form-data" onsubmit="return uploadFiles()">
                            <input type="file" name="video" id="video-input" accept="video/*" multiple 
                                   onchange="updateFileList()">
                            <div id="selected-files"></div>
                            <div class="progress">
                                <div id="progress-bar" class="progress-bar"></div>
                            </div>
                            <div id="progress-text" class="progress-text"></div>
                        </form>
                    </div>
                    <div class="file-list">
                        <h2>Video List</h2>
                        <ul>{files_html}</ul>
                    </div>
                    <div id="toast" class="toast"></div>
                </body>
            </html>
            '''
            self.wfile.write(html.encode())
            
        elif self.path.startswith('/videos/'):
            filename = urllib.parse.unquote(self.path[8:])
            filepath = os.path.join(UPLOAD_DIR, filename)
            
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
                
                upload_info = self.load_upload_info()
                
                for fileitem in files:
                    if fileitem.filename:
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                        filename = timestamp + fileitem.filename
                        filepath = os.path.join(UPLOAD_DIR, filename)
                        
                        with open(filepath, 'wb') as f:
                            f.write(fileitem.file.read())
                        
                        upload_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        upload_info[filename] = {
                            'time': upload_time,
                            'ip': client_ip
                        }
                
                self.save_upload_info(upload_info)
                
                self.send_response(303)
                self.send_header('Location', '/')
                self.end_headers()
                return
                
            self.send_error(400, 'Invalid request')

    def do_DELETE(self):
        if self.path.startswith('/delete/'):
            filename = urllib.parse.unquote(self.path[8:])
            filepath = os.path.join(UPLOAD_DIR, filename)
            
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                    upload_info = self.load_upload_info()
                    if filename in upload_info:
                        del upload_info[filename]
                        self.save_upload_info(upload_info)
                    
                    self.send_response(200)
                    self.end_headers()
                except Exception as e:
                    self.send_error(500, f'Failed to delete file: {str(e)}')
            else:
                self.send_error(404, 'File not found')

def run_server(port=8000):
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)
        
    server = HTTPServer(('', port), VideoServerHandler)
    print(f'Server started at http://localhost:{port}')
    server.serve_forever()

if __name__ == '__main__':
    run_server()
