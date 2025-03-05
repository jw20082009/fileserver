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
                    <div class="video-item">
                        <a href="/videos/{f}">{f}</a>
                        <span class="video-info">
                            (Upload Time: {upload_info.get(f, {}).get('time', 'Unknown')} | 
                             Upload IP: {upload_info.get(f, {}).get('ip', 'Unknown')})
                        </span>
                        <div class="button-group">
                            <button onclick="deleteFile('{f}')" class="delete-button">Delete</button>
                            <button onclick="copyVideoUrl('{f}')" class="copy-button">Copy URL</button>
                        </div>
                    </div>
                </li>''' for f in files
            ])
            
            html = f'''
            <html>
                <head>
                    <title>Video Server</title>
                    <style>
                        body {{ 
                            font-family: Arial, sans-serif; 
                            margin: 20px; 
                            background-color: #1a1a1a;
                            color: #e0e0e0;
                        }}
                        .upload-form {{ 
                            margin: 20px 0; 
                            padding: 20px; 
                            border: 1px solid #333; 
                            border-radius: 8px; 
                            background-color: #2d2d2d;
                            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                        }}
                        .file-list {{ 
                            margin-top: 20px; 
                            padding: 20px;
                            background-color: #2d2d2d;
                            border-radius: 8px;
                            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                        }}
                        .file-list ul {{
                            list-style: none;
                            padding: 0;
                            margin: 0;
                        }}
                        .file-list li {{ 
                            margin: 20px 0;
                            padding: 20px;
                            border-bottom: 1px solid #404040;
                            transition: background-color 0.2s;
                        }}
                        .file-list li:last-child {{
                            border-bottom: none;
                        }}
                        .file-list li:hover {{
                            background-color: #383838;
                        }}
                        .video-item {{
                            display: flex;
                            align-items: center;
                            flex-wrap: wrap;
                            gap: 15px;
                        }}
                        .video-info {{
                            color: #888;
                            flex: 1;
                        }}
                        .button-group {{
                            display: flex;
                            gap: 10px;
                        }}
                        #selected-files {{ margin: 10px 0; color: #b0b0b0; }}
                        .progress {{ 
                            width: 100%; 
                            height: 20px; 
                            background: #404040; 
                            margin: 10px 0; 
                            border-radius: 10px; 
                        }}
                        .progress-bar {{ 
                            width: 0%; 
                            height: 100%; 
                            background: #4CAF50; 
                            border-radius: 10px; 
                            transition: width 0.3s; 
                        }}
                        .progress-text {{ margin-top: 5px; color: #b0b0b0; }}
                        .delete-button {{ 
                            color: white; 
                            background-color: #d32f2f; 
                            border: none;
                            padding: 8px 15px;
                            border-radius: 4px;
                            cursor: pointer;
                            transition: background-color 0.2s;
                        }}
                        .delete-button:hover {{ background-color: #b71c1c; }}
                        .copy-button {{ 
                            color: white; 
                            background-color: #0288d1; 
                            border: none;
                            padding: 8px 15px;
                            border-radius: 4px;
                            cursor: pointer;
                            transition: background-color 0.2s;
                        }}
                        .copy-button:hover {{ background-color: #01579b; }}
                        input[type="file"] {{
                            padding: 10px;
                            border: 1px solid #404040;
                            border-radius: 4px;
                            width: 100%;
                            margin-bottom: 10px;
                            background-color: #333;
                            color: #e0e0e0;
                        }}
                        h2 {{
                            color: #4CAF50;
                            margin-bottom: 20px;
                        }}
                        a {{ 
                            color: #64b5f6; 
                            text-decoration: none;
                            transition: color 0.2s;
                        }}
                        a:hover {{ 
                            color: #2196f3;
                        }}
                        .toast {{
                            position: fixed;
                            bottom: 20px;
                            left: 50%;
                            transform: translateX(-50%);
                            background-color: rgba(66, 66, 66, 0.95);
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
                            if (confirm('确定要删除视频 "' + filename + '" 吗？此操作不可恢复。')) {{
                                fetch('/delete/' + encodeURIComponent(filename), {{
                                    method: 'DELETE'
                                }}).then(response => {{
                                    if (response.ok) {{
                                        window.location.reload();
                                    }} else {{
                                        alert('删除失败！');
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
