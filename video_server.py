from http.server import HTTPServer
from handlers.video_handler import VideoServerHandler

UPLOAD_DIR = "videos"
PORT = 8000

def run_server(port=PORT):
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)
        
    server = HTTPServer(('', port), VideoServerHandler)
    print(f'Server started at http://localhost:{port}')
    server.serve_forever()

if __name__ == '__main__':
    run_server()