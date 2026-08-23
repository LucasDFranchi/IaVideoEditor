"""GUI do IAVideoEditor usando PyQt6."""

import sys
from pathlib import Path

# Adicionar diretório src ao caminho para importações
sys.path.insert(0, str(Path(__file__).parent))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSpinBox, QCheckBox, QComboBox,
    QFileDialog, QProgressBar, QTextEdit, QGroupBox, QSlider,
    QSplitter
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl, QTime
from PyQt6.QtGui import QFont
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from main import concat_videos, generate_subtitles


class VideoProcessorThread(QThread):
    """Thread de trabalho para processamento de vídeo para manter a interface responsiva."""
    
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, overlay_path, output_path, trim_start, trim_end, audio_path):
        super().__init__()
        self.overlay_path = overlay_path
        self.output_path = output_path
        self.trim_start = trim_start
        self.trim_end = trim_end
        self.audio_path = audio_path
    
    def run(self):
        try:
            self.progress.emit("Processando vídeo...")
            self.progress.emit("Concatenando vídeos...")
            MEDIA_DIR = Path(__file__).parent.parent / "media"
            LOGO_VIDEO = MEDIA_DIR / "videos" / "logo.mp4"
            
            concat_videos(
                self.overlay_path, 
                str(LOGO_VIDEO),
                self.output_path,
                self.audio_path,
                self.trim_start,
                self.trim_end
            )
            
            self.finished.emit(True, f"Vídeo processado com sucesso!\n\nSaída: {self.output_path}")
        except Exception as e:
            self.finished.emit(False, f"Erro: {str(e)}")


class VideoEditorGUI(QMainWindow):
    """Janela principal do editor de vídeo."""
    
    def __init__(self):
        super().__init__()
        # Inicializar variáveis de instância ANTES de init_ui()
        self.processing_thread = None
        self.media_player = None
        self.audio_output = None
        self.last_output_path = None
        # Agora inicializar a interface (que criará o reprodutor de mídia)
        self.init_ui()
        
    def init_ui(self):
        """Inicializar a interface do usuário."""
        self.setWindowTitle("Editor de Vídeo IA")
        # Definir tamanho da janela para formato vertical Instagram (fixo, menor para caber na tela)
        # Tamanho fixo - não pode ser redimensionado para manter o formato Instagram
        self.setFixedSize(800, 950)
        
        # Criar widget central e layout principal
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Painel esquerdo - Controles
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(10)
        
        # Título
        title = QLabel("Editor de Vídeo IA")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        left_layout.addWidget(title)
        
        # Seção de Seleção de Vídeo
        video_group = QGroupBox("1. Selecionar Vídeo")
        video_layout = QHBoxLayout()
        
        self.video_input = QLineEdit()
        self.video_input.setPlaceholderText("Selecione um arquivo de vídeo...")
        self.video_input.setReadOnly(True)
        video_layout.addWidget(QLabel("Vídeo:"), 0)
        video_layout.addWidget(self.video_input, 1)
        
        browse_btn = QPushButton("Procurar")
        browse_btn.clicked.connect(self.browse_video)
        video_layout.addWidget(browse_btn, 0)
        
        video_group.setLayout(video_layout)
        left_layout.addWidget(video_group)
        
        # Seção de Corte de Vídeo
        trim_group = QGroupBox("2. Cortar Vídeo (Opcional)")
        trim_layout = QVBoxLayout()
        
        # Início do corte
        start_layout = QHBoxLayout()
        start_layout.addWidget(QLabel("Início (segundos):"), 0)
        self.start_spinbox = QSpinBox()
        self.start_spinbox.setMinimum(0)
        self.start_spinbox.setMaximum(3600)
        self.start_spinbox.setValue(0)
        start_layout.addWidget(self.start_spinbox, 0)
        start_layout.addStretch()
        trim_layout.addLayout(start_layout)
        
        # Fim do corte
        end_layout = QHBoxLayout()
        end_layout.addWidget(QLabel("Fim (segundos):"), 0)
        self.end_spinbox = QSpinBox()
        self.end_spinbox.setMinimum(0)
        self.end_spinbox.setMaximum(3600)
        self.end_spinbox.setValue(0)
        end_layout.addWidget(self.end_spinbox, 0)
        end_layout.addStretch()
        trim_layout.addLayout(end_layout)
        
        trim_group.setLayout(trim_layout)
        left_layout.addWidget(trim_group)
        
        # Processamento e Saída
        process_group = QGroupBox("4. Processar")
        process_layout = QVBoxLayout()
        
        # Nome do Arquivo de Saída
        filename_layout = QHBoxLayout()
        filename_layout.addWidget(QLabel("Nome do Arquivo de Saída:"), 0)
        self.filename_input = QLineEdit()
        self.filename_input.setPlaceholderText("saida_final.mp4")
        filename_layout.addWidget(self.filename_input, 1)
        process_layout.addLayout(filename_layout)
        
        self.no_background_song_checkbox = QCheckBox("Remover música de fundo (para plataformas que não aceitam)")
        process_layout.addWidget(self.no_background_song_checkbox)

        process_btn = QPushButton("Gerar Vídeo")
        process_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;")
        process_btn.clicked.connect(self.process_video)
        process_layout.addWidget(process_btn)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        process_layout.addWidget(self.progress_bar)
        
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(120)
        self.status_text.setPlaceholderText("Mensagens de status aparecerão aqui...")
        process_layout.addWidget(self.status_text)
        
        process_group.setLayout(process_layout)
        left_layout.addWidget(process_group)
        
        left_layout.addStretch()
        
        # Painel direito - Reprodutor de Vídeo (formato Instagram)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(10)
        right_layout.setContentsMargins(10, 10, 10, 10)
        
        # Título do reprodutor de vídeo
        player_title = QLabel("Visualização de Vídeo (Formato Instagram)")
        player_font = QFont()
        player_font.setPointSize(11)
        player_font.setBold(True)
        player_title.setFont(player_font)
        right_layout.addWidget(player_title)
        
        # Contêiner do widget de vídeo - formato retrato Instagram (proporção 9:16)
        video_container = QWidget()
        video_container.setStyleSheet("background-color: black; border-radius: 8px;")
        video_container_layout = QVBoxLayout(video_container)
        video_container_layout.setContentsMargins(0, 0, 0, 0)
        
        # Envoltório de centralização horizontal
        h_center_widget = QWidget()
        h_center_layout = QHBoxLayout(h_center_widget)
        h_center_layout.addStretch()
        
        # Widget de vídeo com proporção retrato Instagram (9:16)
        self.video_widget = QVideoWidget()
        self.video_widget.setStyleSheet("background-color: black;")
        # Definir tamanho para formato Instagram - corresponde às dimensões de vídeo típicas (não superdimensionado)
        self.video_widget.setFixedSize(320, 570)  # proporção 9:16, tamanho compacto
        h_center_layout.addWidget(self.video_widget)
        h_center_layout.addStretch()
        
        video_container_layout.addWidget(h_center_widget)
        right_layout.addWidget(video_container, 1)
        
        # Controles de reprodução
        controls_layout = QVBoxLayout()
        
        # Controle deslizante da linha do tempo
        timeline_layout = QHBoxLayout()
        timeline_layout.addWidget(QLabel("00:00"), 0)
        self.timeline_slider = QSlider(Qt.Orientation.Horizontal)
        self.timeline_slider.setMinimum(0)
        self.timeline_slider.sliderMoved.connect(self.seek_video)
        timeline_layout.addWidget(self.timeline_slider, 1)
        self.time_label = QLabel("00:00")
        timeline_layout.addWidget(self.time_label, 0)
        controls_layout.addLayout(timeline_layout)
        
        # Controles de reprodução
        buttons_layout = QHBoxLayout()
        
        self.play_btn = QPushButton("▶ Reproduzir")
        self.play_btn.clicked.connect(self.play_video)
        self.play_btn.setMaximumWidth(80)
        buttons_layout.addWidget(self.play_btn)
        
        self.pause_btn = QPushButton("⏸ Pausar")
        self.pause_btn.clicked.connect(self.pause_video)
        self.pause_btn.setMaximumWidth(80)
        buttons_layout.addWidget(self.pause_btn)
        
        stop_btn = QPushButton("⏹ Parar")
        stop_btn.clicked.connect(self.stop_video)
        stop_btn.setMaximumWidth(80)
        buttons_layout.addWidget(stop_btn)
        
        buttons_layout.addStretch()
        controls_layout.addLayout(buttons_layout)
        
        # Controle de volume
        volume_layout = QHBoxLayout()
        volume_layout.addWidget(QLabel("🔊"), 0)
        
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setMinimum(0)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setValue(100)  # Default to full volume
        self.volume_slider.setMaximumWidth(150)
        self.volume_slider.sliderMoved.connect(self.set_volume)
        volume_layout.addWidget(self.volume_slider, 0)
        
        self.mute_btn = QPushButton("Mutar")
        self.mute_btn.clicked.connect(self.toggle_mute)
        self.mute_btn.setMaximumWidth(70)
        volume_layout.addWidget(self.mute_btn, 0)
        
        volume_layout.addStretch()
        controls_layout.addLayout(volume_layout)
        
        right_layout.addLayout(controls_layout)
        
        # Adicionar painéis esquerdo e direito ao layout principal (esquerdo mais estreito, direito mais largo para visualização de vídeo)
        main_layout.addWidget(left_panel, 0)
        main_layout.addWidget(right_panel, 1)
        
        # Inicializar reprodutor de mídia
        self.media_player = QMediaPlayer()
        self.media_player.setVideoOutput(self.video_widget)
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        
        # Conectar sinais do reprodutor de mídia
        self.media_player.durationChanged.connect(self.update_duration)
        self.media_player.positionChanged.connect(self.update_position)
    
    def browse_video(self):
        """Abrir diálogo de arquivo para selecionar vídeo."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar Arquivo de Vídeo",
            str(Path.home()),
            "Arquivos de Vídeo (*.mp4 *.avi *.mov *.mkv);;Todos os Arquivos (*)"
        )
        if file_path:
            self.video_input.setText(file_path)
            self.load_video(file_path)
    
    def process_video(self):
        """Iniciar processamento de vídeo em uma thread separada."""
        video_path = self.video_input.text()
        
        if not video_path:
            self.update_status("Erro: Selecione um arquivo de vídeo")
            return
        
        if not Path(video_path).exists():
            self.update_status("Erro: O arquivo de vídeo selecionado não existe")
            return
        
        # Preparar caminho de saída
        media_dir = Path(__file__).parent.parent / "media"
        output_dir = media_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Obter nome do arquivo de saída do campo de entrada
        filename = self.filename_input.text().strip()
        if not filename:
            filename = "saida_final.mp4"
        elif not filename.endswith('.mp4'):
            filename += ".mp4"
        
        output_path = str(output_dir / filename)
        
        # Obter parâmetros
        start = self.start_spinbox.value()
        end = self.end_spinbox.value()
        audio_path = None if self.no_background_song_checkbox.isChecked() else str(media_dir / "audio" / "background_song.mp3")
        
        # Desativar botão e mostrar barra de progresso
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(0)  # Progresso indeterminado
        
        # Iniciar thread de processamento
        self.processing_thread = VideoProcessorThread(
            video_path, output_path, start, end, audio_path
        )
        self.processing_thread.progress.connect(self.update_status)
        self.processing_thread.finished.connect(self.processing_finished)
        self.processing_thread.start()
    
    def update_status(self, message):
        """Atualizar texto de status."""
        self.status_text.append(message)
        # Auto rolar para a parte inferior
        self.status_text.verticalScrollBar().setValue(
            self.status_text.verticalScrollBar().maximum()
        )
    
    def processing_finished(self, success, message):
        """Processar conclusão do processamento."""
        self.progress_bar.setVisible(False)
        self.update_status(message)
        if success:
            self.update_status("✓ Processamento concluído!")
            # Carregar o vídeo gerado no reprodutor
            media_dir = Path(__file__).parent.parent / "media"
            output_path = str(media_dir / "output" / "saida_final.mp4")
            self.load_video(output_path)
    
    def load_video(self, file_path):
        """Carregar um arquivo de vídeo no reprodutor de mídia."""
        if Path(file_path).exists():
            self.media_player.setSource(QUrl.fromLocalFile(file_path))
            self.last_output_path = file_path
            self.update_status(f"Vídeo carregado: {file_path}")
        else:
            self.update_status(f"Erro: Arquivo de vídeo não encontrado: {file_path}")
    
    def play_video(self):
        """Reproduzir o vídeo atual."""
        if self.media_player.source().isValid():
            self.media_player.play()
        else:
            self.update_status("Nenhum vídeo carregado")
    
    def pause_video(self):
        """Pausar o vídeo atual."""
        self.media_player.pause()
    
    def stop_video(self):
        """Parar a reprodução e rebobinar para o início."""
        self.media_player.stop()
        self.timeline_slider.setValue(0)
    
    def seek_video(self, position):
        """Procurar uma posição específica no vídeo."""
        self.media_player.setPosition(position)
    
    def update_duration(self, duration):
        """Atualizar o máximo do controle deslizante da linha do tempo quando a duração muda."""
        self.timeline_slider.setMaximum(duration)
    
    def update_position(self, position):
        """Atualizar o rótulo de posição e o controle deslizante enquanto o vídeo é reproduzido."""
        if not self.timeline_slider.isSliderDown():
            self.timeline_slider.blockSignals(True)
            self.timeline_slider.setValue(position)
            self.timeline_slider.blockSignals(False)
        
        # Atualizar rótulo de hora
        total_ms = self.media_player.duration()
        current_ms = position
        
        def format_time(ms):
            seconds = ms // 1000
            minutes = seconds // 60
            seconds = seconds % 60
            return f"{minutes:02d}:{seconds:02d}"
        
        self.time_label.setText(format_time(current_ms))
    
    def set_volume(self, volume):
        """Definir o nível de volume do reprodutor de mídia."""
        # Converter valor do controle deslizante (0-100) para volume do QMediaPlayer (0-1)
        self.audio_output.setVolume(volume / 100.0)
    
    def toggle_mute(self):
        """Alternar mutar ativado/desativado."""
        is_muted = self.audio_output.isMuted()
        self.audio_output.setMuted(not is_muted)
        
        # Atualizar texto do botão
        if not is_muted:
            self.mute_btn.setText("Desmutar")
            self.volume_slider.setEnabled(False)
        else:
            self.mute_btn.setText("Mutar")
            self.volume_slider.setEnabled(True)


def main():
    """Ponto de entrada principal da GUI."""
    app = QApplication(sys.argv)
    window = VideoEditorGUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
