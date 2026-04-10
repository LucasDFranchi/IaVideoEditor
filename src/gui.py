"""GUI for IAVideoEditor using PyQt6."""

import sys
from pathlib import Path

# Add src directory to path for imports
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
    """Worker thread for video processing to keep UI responsive."""
    
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, overlay_path, output_path, trim_start, trim_end, audio_path, 
                 generate_subs, language):
        super().__init__()
        self.overlay_path = overlay_path
        self.output_path = output_path
        self.trim_start = trim_start
        self.trim_end = trim_end
        self.audio_path = audio_path
        self.generate_subs = generate_subs
        self.language = language
    
    def run(self):
        try:
            self.progress.emit("Processing video...")
            
            subtitle_segments = None
            if self.generate_subs:
                self.progress.emit("Generating subtitles...")
                subtitle_file = Path(self.output_path).parent / f"final_output_{self.language}.srt"
                subtitle_segments = generate_subtitles(
                    Path(self.overlay_path), 
                    subtitle_file, 
                    self.language
                )
            
            self.progress.emit("Concatenating videos and embedding subtitles...")
            MEDIA_DIR = Path(__file__).parent.parent / "media"
            LOGO_VIDEO = MEDIA_DIR / "videos" / "logo.mp4"
            
            concat_videos(
                self.overlay_path, 
                str(LOGO_VIDEO),
                self.output_path,
                self.audio_path,
                self.trim_start,
                self.trim_end,
                subtitle_segments
            )
            
            self.finished.emit(True, f"Video completed successfully!\n\nOutput: {self.output_path}")
        except Exception as e:
            self.finished.emit(False, f"Error: {str(e)}")


class VideoEditorGUI(QMainWindow):
    """Main GUI window for video editor."""
    
    def __init__(self):
        super().__init__()
        # Initialize instance variables BEFORE init_ui()
        self.processing_thread = None
        self.media_player = None
        self.audio_output = None
        self.last_output_path = None
        # Now initialize UI (which will create the media player)
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("IA Video Editor")
        # Set window size for Instagram vertical format (fixed, smaller to fit on screen)
        # Fixed size - cannot be resized to maintain Instagram format
        self.setFixedSize(800, 950)
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Left panel - Controls
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(10)
        
        # Title
        title = QLabel("IA Video Editor")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        left_layout.addWidget(title)
        
        # Video Selection Section
        video_group = QGroupBox("1. Select Video")
        video_layout = QHBoxLayout()
        
        self.video_input = QLineEdit()
        self.video_input.setPlaceholderText("Select a video file...")
        self.video_input.setReadOnly(True)
        video_layout.addWidget(QLabel("Video:"), 0)
        video_layout.addWidget(self.video_input, 1)
        
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_video)
        video_layout.addWidget(browse_btn, 0)
        
        video_group.setLayout(video_layout)
        left_layout.addWidget(video_group)
        
        # Trimming Section
        trim_group = QGroupBox("2. Trim Video (Optional)")
        trim_layout = QVBoxLayout()
        
        # Start trim
        start_layout = QHBoxLayout()
        start_layout.addWidget(QLabel("Start (seconds):"), 0)
        self.start_spinbox = QSpinBox()
        self.start_spinbox.setMinimum(0)
        self.start_spinbox.setMaximum(3600)
        self.start_spinbox.setValue(0)
        start_layout.addWidget(self.start_spinbox, 0)
        start_layout.addStretch()
        trim_layout.addLayout(start_layout)
        
        # End trim
        end_layout = QHBoxLayout()
        end_layout.addWidget(QLabel("End (seconds):"), 0)
        self.end_spinbox = QSpinBox()
        self.end_spinbox.setMinimum(0)
        self.end_spinbox.setMaximum(3600)
        self.end_spinbox.setValue(0)
        end_layout.addWidget(self.end_spinbox, 0)
        end_layout.addStretch()
        trim_layout.addLayout(end_layout)
        
        trim_group.setLayout(trim_layout)
        left_layout.addWidget(trim_group)
        
        # Subtitles Section
        subtitle_group = QGroupBox("3. Subtitles (Optional)")
        subtitle_layout = QVBoxLayout()
        
        self.subtitle_checkbox = QCheckBox("Generate and embed subtitles")
        self.subtitle_checkbox.setChecked(False)
        self.subtitle_checkbox.stateChanged.connect(self.toggle_language)
        subtitle_layout.addWidget(self.subtitle_checkbox)
        
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel("Language:"), 0)
        self.language_combo = QComboBox()
        self.language_combo.addItems(["Portuguese (pt)", "English (en)", "Spanish (es)", 
                                       "French (fr)", "German (de)"])
        self.language_combo.setEnabled(False)
        self.language_map = {"Portuguese (pt)": "pt", "English (en)": "en", 
                            "Spanish (es)": "es", "French (fr)": "fr", "German (de)": "de"}
        lang_layout.addWidget(self.language_combo, 0)
        lang_layout.addStretch()
        subtitle_layout.addLayout(lang_layout)
        
        subtitle_group.setLayout(subtitle_layout)
        left_layout.addWidget(subtitle_group)
        
        # Processing and Output
        process_group = QGroupBox("4. Process")
        process_layout = QVBoxLayout()
        
        # Output Filename
        filename_layout = QHBoxLayout()
        filename_layout.addWidget(QLabel("Output Filename:"), 0)
        self.filename_input = QLineEdit()
        self.filename_input.setPlaceholderText("final_output.mp4")
        filename_layout.addWidget(self.filename_input, 1)
        process_layout.addLayout(filename_layout)
        
        process_btn = QPushButton("Generate Video")
        process_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;")
        process_btn.clicked.connect(self.process_video)
        process_layout.addWidget(process_btn)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        process_layout.addWidget(self.progress_bar)
        
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(120)
        self.status_text.setPlaceholderText("Status messages will appear here...")
        process_layout.addWidget(self.status_text)
        
        process_group.setLayout(process_layout)
        left_layout.addWidget(process_group)
        
        left_layout.addStretch()
        
        # Right panel - Video Player (Instagram format)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(10)
        right_layout.setContentsMargins(10, 10, 10, 10)
        
        # Video player title
        player_title = QLabel("Video Preview (Instagram Format)")
        player_font = QFont()
        player_font.setPointSize(11)
        player_font.setBold(True)
        player_title.setFont(player_font)
        right_layout.addWidget(player_title)
        
        # Video widget container - Instagram portrait format (9:16 aspect ratio)
        video_container = QWidget()
        video_container.setStyleSheet("background-color: black; border-radius: 8px;")
        video_container_layout = QVBoxLayout(video_container)
        video_container_layout.setContentsMargins(0, 0, 0, 0)
        
        # Horizontal centering wrapper
        h_center_widget = QWidget()
        h_center_layout = QHBoxLayout(h_center_widget)
        h_center_layout.addStretch()
        
        # Video widget with Instagram portrait aspect ratio (9:16)
        self.video_widget = QVideoWidget()
        self.video_widget.setStyleSheet("background-color: black;")
        # Set size for Instagram format - matches typical video dimensions (not oversized)
        self.video_widget.setFixedSize(320, 570)  # 9:16 aspect ratio, compact size
        h_center_layout.addWidget(self.video_widget)
        h_center_layout.addStretch()
        
        video_container_layout.addWidget(h_center_widget)
        right_layout.addWidget(video_container, 1)
        
        # Playback controls
        controls_layout = QVBoxLayout()
        
        # Timeline slider
        timeline_layout = QHBoxLayout()
        timeline_layout.addWidget(QLabel("00:00"), 0)
        self.timeline_slider = QSlider(Qt.Orientation.Horizontal)
        self.timeline_slider.setMinimum(0)
        self.timeline_slider.sliderMoved.connect(self.seek_video)
        timeline_layout.addWidget(self.timeline_slider, 1)
        self.time_label = QLabel("00:00")
        timeline_layout.addWidget(self.time_label, 0)
        controls_layout.addLayout(timeline_layout)
        
        # Play controls
        buttons_layout = QHBoxLayout()
        
        self.play_btn = QPushButton("▶ Play")
        self.play_btn.clicked.connect(self.play_video)
        self.play_btn.setMaximumWidth(80)
        buttons_layout.addWidget(self.play_btn)
        
        self.pause_btn = QPushButton("⏸ Pause")
        self.pause_btn.clicked.connect(self.pause_video)
        self.pause_btn.setMaximumWidth(80)
        buttons_layout.addWidget(self.pause_btn)
        
        stop_btn = QPushButton("⏹ Stop")
        stop_btn.clicked.connect(self.stop_video)
        stop_btn.setMaximumWidth(80)
        buttons_layout.addWidget(stop_btn)
        
        buttons_layout.addStretch()
        controls_layout.addLayout(buttons_layout)
        
        # Volume control
        volume_layout = QHBoxLayout()
        volume_layout.addWidget(QLabel("🔊"), 0)
        
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setMinimum(0)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setValue(100)  # Default to full volume
        self.volume_slider.setMaximumWidth(150)
        self.volume_slider.sliderMoved.connect(self.set_volume)
        volume_layout.addWidget(self.volume_slider, 0)
        
        self.mute_btn = QPushButton("Mute")
        self.mute_btn.clicked.connect(self.toggle_mute)
        self.mute_btn.setMaximumWidth(70)
        volume_layout.addWidget(self.mute_btn, 0)
        
        volume_layout.addStretch()
        controls_layout.addLayout(volume_layout)
        
        right_layout.addLayout(controls_layout)
        
        # Add left and right panels to main layout (left narrower, right wider for video preview)
        main_layout.addWidget(left_panel, 0)
        main_layout.addWidget(right_panel, 1)
        
        # Initialize media player
        self.media_player = QMediaPlayer()
        self.media_player.setVideoOutput(self.video_widget)
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        
        # Connect media player signals
        self.media_player.durationChanged.connect(self.update_duration)
        self.media_player.positionChanged.connect(self.update_position)
    
    def toggle_language(self):
        """Enable/disable language combo based on subtitle checkbox."""
        self.language_combo.setEnabled(self.subtitle_checkbox.isChecked())
    
    def browse_video(self):
        """Open file dialog to select video."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Video File",
            str(Path.home()),
            "Video Files (*.mp4 *.avi *.mov *.mkv);;All Files (*)"
        )
        if file_path:
            self.video_input.setText(file_path)
            self.load_video(file_path)
    
    def process_video(self):
        """Start video processing in a separate thread."""
        video_path = self.video_input.text()
        
        if not video_path:
            self.update_status("Error: Please select a video file")
            return
        
        if not Path(video_path).exists():
            self.update_status("Error: Selected video file does not exist")
            return
        
        # Prepare output path
        media_dir = Path(__file__).parent.parent / "media"
        output_dir = media_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Get output filename from input field
        filename = self.filename_input.text().strip()
        if not filename:
            filename = "final_output.mp4"
        elif not filename.endswith('.mp4'):
            filename += ".mp4"
        
        output_path = str(output_dir / filename)
        
        # Get parameters
        start = self.start_spinbox.value()
        end = self.end_spinbox.value()
        audio_path = str(media_dir / "audio" / "background_song.mp3")
        generate_subs = self.subtitle_checkbox.isChecked()
        language = self.language_map.get(self.language_combo.currentText(), "pt")
        
        # Disable button and show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(0)  # Indeterminate progress
        
        # Start processing thread
        self.processing_thread = VideoProcessorThread(
            video_path, output_path, start, end, audio_path, 
            generate_subs, language
        )
        self.processing_thread.progress.connect(self.update_status)
        self.processing_thread.finished.connect(self.processing_finished)
        self.processing_thread.start()
    
    def update_status(self, message):
        """Update status text."""
        self.status_text.append(message)
        # Auto scroll to bottom
        self.status_text.verticalScrollBar().setValue(
            self.status_text.verticalScrollBar().maximum()
        )
    
    def processing_finished(self, success, message):
        """Handle processing completion."""
        self.progress_bar.setVisible(False)
        self.update_status(message)
        if success:
            self.update_status("✓ Processing complete!")
            # Load the generated video in the player
            media_dir = Path(__file__).parent.parent / "media"
            output_path = str(media_dir / "output" / "final_output.mp4")
            self.load_video(output_path)
    
    def load_video(self, file_path):
        """Load a video file into the media player."""
        if Path(file_path).exists():
            self.media_player.setSource(QUrl.fromLocalFile(file_path))
            self.last_output_path = file_path
            self.update_status(f"Video loaded: {file_path}")
        else:
            self.update_status(f"Error: Video file not found: {file_path}")
    
    def play_video(self):
        """Play the current video."""
        if self.media_player.source().isValid():
            self.media_player.play()
        else:
            self.update_status("No video loaded")
    
    def pause_video(self):
        """Pause the current video."""
        self.media_player.pause()
    
    def stop_video(self):
        """Stop playback and rewind to beginning."""
        self.media_player.stop()
        self.timeline_slider.setValue(0)
    
    def seek_video(self, position):
        """Seek to a specific position in the video."""
        self.media_player.setPosition(position)
    
    def update_duration(self, duration):
        """Update the timeline slider maximum when duration changes."""
        self.timeline_slider.setMaximum(duration)
    
    def update_position(self, position):
        """Update the position label and slider as video plays."""
        if not self.timeline_slider.isSliderDown():
            self.timeline_slider.blockSignals(True)
            self.timeline_slider.setValue(position)
            self.timeline_slider.blockSignals(False)
        
        # Update time label
        total_ms = self.media_player.duration()
        current_ms = position
        
        def format_time(ms):
            seconds = ms // 1000
            minutes = seconds // 60
            seconds = seconds % 60
            return f"{minutes:02d}:{seconds:02d}"
        
        self.time_label.setText(format_time(current_ms))
    
    def set_volume(self, volume):
        """Set the volume level of the media player."""
        # Convert slider value (0-100) to QMediaPlayer volume (0-1)
        self.audio_output.setVolume(volume / 100.0)
    
    def toggle_mute(self):
        """Toggle mute on/off."""
        is_muted = self.audio_output.isMuted()
        self.audio_output.setMuted(not is_muted)
        
        # Update button text
        if not is_muted:
            self.mute_btn.setText("Unmute")
            self.volume_slider.setEnabled(False)
        else:
            self.mute_btn.setText("Mute")
            self.volume_slider.setEnabled(True)


def main():
    """Main entry point for GUI."""
    app = QApplication(sys.argv)
    window = VideoEditorGUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
