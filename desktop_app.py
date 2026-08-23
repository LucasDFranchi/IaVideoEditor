#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Editor de Vídeo IA - Aplicação Desktop
Usa PyWebView com API Python exposta diretamente ao JavaScript.
Sem Flask, sem HTTP - comunicação direta Python <-> JS.
"""

import os
import re
import sys
import shutil
import threading
import http.server
import socketserver
from pathlib import Path

import webview

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

from src.main import concat_videos

# Caminhos padrão (suporte a PyInstaller)
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).parent
LOGO_PATH = BASE_DIR / 'media' / 'videos' / 'logo.mp4'
AUDIO_PATH = BASE_DIR / 'media' / 'audio' / 'background_song.mp3'
UPLOAD_DIR = BASE_DIR / 'uploads'
OUTPUT_DIR = Path.home() / 'Desktop' / 'videos_formatados'

# Criar pastas
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================
# Servidor HTTP simples para servir vídeos locais
# ============================================

class MediaHandler(http.server.BaseHTTPRequestHandler):
    """Serve um único arquivo de vídeo com suporte a Range requests."""
    video_file = None

    def do_GET(self):
        if not self.video_file or not os.path.exists(self.video_file):
            self.send_error(404)
            return

        file_size = os.path.getsize(self.video_file)
        range_header = self.headers.get('Range')

        if range_header:
            match = re.match(r'bytes=(\d+)-(\d*)', range_header)
            if match:
                start = int(match.group(1))
                end = int(match.group(2)) if match.group(2) else file_size - 1
                end = min(end, file_size - 1)
                length = end - start + 1

                self.send_response(206)
                self.send_header('Content-Range', f'bytes {start}-{end}/{file_size}')
                self.send_header('Content-Length', str(length))
                self.send_header('Content-Type', 'video/mp4')
                self.send_header('Accept-Ranges', 'bytes')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()

                with open(self.video_file, 'rb') as f:
                    f.seek(start)
                    self.wfile.write(f.read(length))
                return

        self.send_response(200)
        self.send_header('Content-Type', 'video/mp4')
        self.send_header('Content-Length', str(file_size))
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        with open(self.video_file, 'rb') as f:
            shutil.copyfileobj(f, self.wfile)

    def log_message(self, format, *args):
        pass  # Suprimir logs do servidor


def start_media_server():
    """Inicia servidor HTTP para servir arquivos de vídeo."""
    server = socketserver.TCPServer(('127.0.0.1', 0), MediaHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return port


class Api:
    """API Python exposta ao JavaScript via pywebview."""

    def __init__(self, media_port):
        self._status = 'idle'
        self._message = ''
        self._progress = 0
        self._output_file = ''
        self._media_port = media_port

    def upload_video(self, file_name, file_data):
        """Receber vídeo via file dialog nativo do pywebview."""
        # Não usado diretamente - usamos select_video com dialog nativo
        pass

    def select_video(self):
        """Abrir diálogo nativo para selecionar vídeo."""
        result = window.create_file_dialog(
            webview.OPEN_DIALOG,
            allow_multiple=False,
            file_types=('Arquivos de Vídeo (*.mp4;*.avi;*.mov;*.mkv;*.wmv)',)
        )
        if result and len(result) > 0:
            path = result[0]
            # Servir o vídeo pelo media server para preview
            MediaHandler.video_file = path
            preview_url = f'http://127.0.0.1:{self._media_port}/video'
            return {'success': True, 'path': path, 'name': os.path.basename(path), 'preview_url': preview_url}
        return {'success': False}

    def get_status(self):
        """Retornar status atual do processamento."""
        return {
            'status': self._status,
            'message': self._message,
            'progress': self._progress,
            'output_file': self._output_file
        }

    def process_video(self, video_path, trim_start, trim_end, output_name, no_background_song=False):
        """Iniciar processamento de vídeo em thread separada."""
        if self._status == 'processing':
            return {'success': False, 'error': 'Já existe um processamento em andamento'}

        # Validações
        if not video_path or not os.path.exists(video_path):
            return {'success': False, 'error': f'Vídeo não encontrado: {video_path}'}

        if not LOGO_PATH.exists():
            return {'success': False, 'error': f'Logo não encontrado: {LOGO_PATH}'}

        # Garantir extensão .mp4
        if not output_name.endswith('.mp4'):
            output_name += '.mp4'

        output_path = str(OUTPUT_DIR / output_name)
        audio_path = str(AUDIO_PATH) if (not no_background_song and AUDIO_PATH.exists()) else None

        self._status = 'processing'
        self._message = 'Iniciando...'
        self._progress = 5

        def do_process():
            try:
                self._message = 'Carregando vídeos...'
                self._progress = 10

                print(f"\n{'='*60}")
                print(f"PROCESSANDO VÍDEO")
                print(f"Vídeo: {video_path}")
                print(f"Logo: {LOGO_PATH}")
                print(f"Áudio: {audio_path}")
                print(f"Saída: {output_path}")
                print(f"Trim: {trim_start}s - {trim_end}s")
                print(f"{'='*60}\n")

                concat_videos(
                    video1_path=video_path,
                    video2_path=str(LOGO_PATH),
                    output_path=output_path,
                    audio_path=audio_path,
                    trim_start=int(trim_start),
                    trim_end=int(trim_end)
                )

                if os.path.exists(output_path):
                    file_size = os.path.getsize(output_path) / (1024 * 1024)
                    self._status = 'completed'
                    self._message = f'Vídeo salvo em {output_path} ({file_size:.1f} MB)'
                    self._progress = 100
                    self._output_file = output_name
                    print(f"\n✅ SUCESSO: {output_path} ({file_size:.1f} MB)\n")
                else:
                    self._status = 'error'
                    self._message = 'Erro: arquivo não foi criado'
                    self._progress = 0
                    print(f"\n❌ ERRO: arquivo não criado em {output_path}\n")

            except Exception as e:
                self._status = 'error'
                self._message = f'Erro: {str(e)}'
                self._progress = 0
                print(f"\n❌ ERRO: {e}\n")
                import traceback
                traceback.print_exc()

        thread = threading.Thread(target=do_process)
        thread.start()

        return {'success': True}


if __name__ == '__main__':
    media_port = start_media_server()
    api = Api(media_port)

    window = webview.create_window(
        title='Editor de Vídeo IA',
        url=str(BASE_DIR / 'ui' / 'index.html'),
        js_api=api,
        width=1400,
        height=900,
        resizable=True,
        maximized=True,
        background_color='#f5f5f5'
    )

    print("="*60)
    print("  Editor de Vídeo IA - Desktop")
    print("="*60)
    print(f"Logo: {LOGO_PATH} (exists: {LOGO_PATH.exists()})")
    print(f"Audio: {AUDIO_PATH} (exists: {AUDIO_PATH.exists()})")
    print(f"Output: {OUTPUT_DIR}")
    print(f"Media server: http://127.0.0.1:{media_port}")
    print("="*60)

    webview.start(debug=False)
