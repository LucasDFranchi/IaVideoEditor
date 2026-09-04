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
import logging
import threading
import http.server
import socketserver
from pathlib import Path

import webview

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

from src.main import concat_videos, VideoTranscriber, embed_subtitles

# Caminhos padrão (suporte a PyInstaller)
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).parent
LOGO_PATH = BASE_DIR / 'media' / 'videos' / 'logo.mp4'
AUDIO_PATH = BASE_DIR / 'media' / 'audio' / 'background_song.mp3'
UPLOAD_DIR = BASE_DIR / 'uploads'
OUTPUT_DIR = Path.home() / 'Desktop' / 'videos_formatados'
LOG_DIR = Path(os.getenv('LOCALAPPDATA', Path.home())) / 'IAVideoEditor' / 'logs'

# Criar pastas
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Logging para arquivo (necessário pois o executável empacotado roda sem console visível)
LOG_FILE = LOG_DIR / 'app.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger('iavideoeditor')


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

    def get_result_preview_url(self):
        """Apontar o media server para o vídeo processado, para exibir o resultado editado."""
        if self._status != 'completed' or not self._output_file:
            return {'success': False}

        output_path = str(OUTPUT_DIR / self._output_file)
        if not os.path.exists(output_path):
            return {'success': False}

        MediaHandler.video_file = output_path
        preview_url = f'http://127.0.0.1:{self._media_port}/video'
        return {'success': True, 'preview_url': preview_url}

    def process_video(self, video_path, trim_start, trim_end, output_name, no_background_song=False, add_subtitles=True, subtitle_position='top'):
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

                logger.info(
                    "Processando vídeo | video=%s logo=%s audio=%s saida=%s trim=%s-%s legendas=%s",
                    video_path, LOGO_PATH, audio_path, output_path, trim_start, trim_end, add_subtitles
                )

                subtitle_segments = None
                if add_subtitles:
                    self._message = 'Gerando legendas (isso pode demorar)...'
                    self._progress = 20
                    subtitle_segments = VideoTranscriber().transcribe(video_path, 'pt')
                    if subtitle_segments:
                        subtitle_file = OUTPUT_DIR / 'subtitles' / f'{Path(output_name).stem}.srt'
                        subtitle_file.parent.mkdir(parents=True, exist_ok=True)
                        subtitle_file.write_text(VideoTranscriber.to_srt(subtitle_segments), encoding='utf-8')
                    else:
                        logger.warning("Legendas solicitadas mas não foi possível gerá-las (verifique se faster-whisper está instalado)")

                if subtitle_segments:
                    self._message = 'Concatenando vídeos...'
                    self._progress = 40
                    concat_temp = OUTPUT_DIR / f'_concat_temp_{os.getpid()}.mp4'
                    concat_videos(
                        video1_path=video_path,
                        video2_path=str(LOGO_PATH),
                        output_path=str(concat_temp),
                        audio_path=audio_path,
                        trim_start=int(trim_start),
                        trim_end=int(trim_end)
                    )

                    self._message = 'Adicionando legendas...'
                    self._progress = 80
                    embed_subtitles(concat_temp, subtitle_segments, output_path, subtitle_position)
                    concat_temp.unlink(missing_ok=True)
                else:
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
                    logger.info("Sucesso: %s (%.1f MB)", output_path, file_size)
                else:
                    self._status = 'error'
                    self._message = 'Erro: arquivo não foi criado'
                    self._progress = 0
                    logger.error("Arquivo não criado em %s", output_path)

            except Exception as e:
                self._status = 'error'
                self._message = f'Erro: {str(e)}'
                self._progress = 0
                logger.exception("Falha ao processar vídeo")

        thread = threading.Thread(target=do_process)
        thread.start()

        return {'success': True}


if __name__ == '__main__':
    try:
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

        logger.info("=" * 60)
        logger.info("Editor de Vídeo IA - Desktop")
        logger.info("Logo: %s (exists: %s)", LOGO_PATH, LOGO_PATH.exists())
        logger.info("Audio: %s (exists: %s)", AUDIO_PATH, AUDIO_PATH.exists())
        logger.info("Output: %s", OUTPUT_DIR)
        logger.info("Log file: %s", LOG_FILE)
        logger.info("Media server: http://127.0.0.1:%s", media_port)
        logger.info("=" * 60)

        webview.start(debug=False)
    except Exception:
        logger.exception("Falha fatal ao iniciar a aplicação")
        raise
