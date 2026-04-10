# IA Video Editor

A Python-based video editing tool with automatic subtitle generation and embedding.

## Features

- ✅ **Video Concatenation**: Combine videos with automatic resizing
- ✅ **Video Trimming**: Trim start and end frames with `--start` and `--end` arguments
- ✅ **Background Music**: Add looping background audio with volume control
- ✅ **Audio Mixing**: Mix multiple audio tracks (video audio + background music)
- ✅ **Auto Subtitles**: Generate subtitles from video audio using Whisper AI (FREE, no API keys)
- ✅ **Subtitle Embedding**: Embed subtitles directly into video with customizable font, size, and border
- ✅ **GUI Interface**: User-friendly PyQt6-based graphical interface with built-in video player
- ✅ **Video Preview**: View generated videos with minimal player (play, pause, seek)
- ✅ **Special Character Support**: Full Unicode support including Portuguese accents, tildes, etc.

## Installation

### 1. Create and activate virtual environment
```bash
python -m venv venv
venv\Scripts\activate  # On Windows
# or
source venv/bin/activate  # On macOS/Linux
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

## Usage

### GUI Mode (Recommended)
```bash
python gui_launcher.py
```

This opens an intuitive interface where you can:
1. **Select a video file** using the file browser
2. **Set trim values** (start/end in seconds)
3. **Enable subtitles** and choose language
4. **Click "Generate Video"** to process
5. **Preview the result** in the built-in video player with play/pause/seek controls

### GUI Features
- **Left Panel**: Video controls (file selection, trimming, subtitles, processing)
- **Right Panel**: Video preview player with:
  - Play/Pause/Stop buttons
  - Timeline slider with time display
  - Automatic video loading after processing

### CLI Mode
```bash
python -m src.main -o <path_to_video> [OPTIONS]
```

**Arguments:**
- `-o, --overlay` (required): Path to video file to process
- `--start` (default: 0): Trim seconds from the beginning
- `--end` (default: 0): Trim seconds from the end
- `--no-audio` (default: false): Skip background music
- `--subtitles` (default: false): Generate and embed subtitles
- `--lang` (default: "pt"): Language code for subtitles (pt, en, es, fr, de)

**Examples:**

```bash
# Basic: Concatenate video with logo and background music
python -m src.main -o video_to_be_edit.mp4

# With trimming: Remove 5 seconds from start, 3 from end
python -m src.main -o video_to_be_edit.mp4 --start 5 --end 3

# With Portuguese subtitles
python -m src.main -o video_to_be_edit.mp4 --start 5 --end 3 --subtitles --lang pt

# With English subtitles, no background music
python -m src.main -o video_to_be_edit.mp4 --subtitles --lang en --no-audio
```

## Supported Languages for Subtitles

- `pt` - Portuguese
- `en` - English
- `es` - Spanish
- `fr` - French
- `de` - German
- (Any language supported by Whisper)

## Project Structure

```
IAVideoEditor/
├── src/
│   ├── main.py           # Core video processing logic
│   ├── gui.py            # PyQt6 GUI application with video player
│   └── __init__.py
├── media/
│   ├── videos/
│   │   └── logo.mp4      # Logo video (concatenated at end)
│   ├── audio/
│   │   └── background_song.mp3  # Background music
│   └── output/           # Generated videos stored here
├── requirements.txt      # Python dependencies
├── gui_launcher.py       # Easy GUI launcher
└── README.md            # This file
```

## Subtitle Customization

Subtitles are automatically:
- Broken into smaller readable lines (max 50 chars per line)
- Rendered with **40pt Arial font** for visibility
- Added **2pt black border** for contrast against video
- Positioned **220px from bottom** for optimal placement
- Support **all Unicode characters** (accents, tildes, etc.)

## Video Player Controls

The GUI includes a built-in video player with:
- **Play Button** (▶): Play the video
- **Pause Button** (⏸): Pause playback
- **Stop Button** (⏹): Stop and rewind to beginning
- **Timeline Slider**: Click or drag to seek to any position
- **Time Display**: Shows current playback time

## Dependencies

- **moviepy**: Video processing and editing
- **openai-whisper**: Free, open-source audio transcription (no API keys needed)
- **librosa**: Audio processing
- **PyQt6**: GUI framework with multimedia support

## Notes

- First run of subtitle generation downloads the Whisper model (~140MB)
- Processing time depends on video length and your system specs
- Output videos are saved in `media/output/` directory
- The video player automatically loads generated videos for preview

## Keyboard Shortcuts

In the GUI:
- Use the file browser button to select videos
- SpinBoxes accept keyboard input for trim values
- All playback controls are accessible via buttons

## License

MIT

