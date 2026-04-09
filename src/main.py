"""Main entry point for IAVideoEditor."""

from pathlib import Path
from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips, concatenate_audioclips, CompositeAudioClip, TextClip, CompositeVideoClip
import argparse


# Media file paths
MEDIA_DIR = Path(__file__).parent.parent / "media"
LOGO_VIDEO = MEDIA_DIR / "videos" / "logo.mp4"
BACKGROUND_SONG = MEDIA_DIR / "audio" / "background_song.mp3"
OUTPUT_DIR = MEDIA_DIR / "output"
SUBTITLES_DIR = OUTPUT_DIR / "subtitles"


def break_into_small_lines(text: str, max_chars: int = 50) -> str:
    """Break text into smaller lines for better readability.
    
    Args:
        text: Text to break into lines
        max_chars: Maximum characters per line (default: 50)
        
    Returns:
        Text with line breaks inserted
    """
    words = text.split()
    lines = []
    current_line = []
    current_length = 0
    
    for word in words:
        # Check if adding this word would exceed the limit
        word_length = len(word)
        if current_length + word_length + len(current_line) > max_chars and current_line:
            # Start a new line
            lines.append(' '.join(current_line))
            current_line = [word]
            current_length = word_length
        else:
            # Add word to current line
            current_line.append(word)
            current_length += word_length
    
    # Add the last line
    if current_line:
        lines.append(' '.join(current_line))
    
    return '\n'.join(lines)


def generate_subtitles(video_path: Path, subtitle_path: Path, language: str = "pt") -> list:
    """Generate SRT subtitles from video audio using Whisper AI (FREE, open-source, no API keys needed).
    
    Args:
        video_path: Path to video file
        subtitle_path: Path to save SRT subtitles
        language: Language code (default: "pt" for Portuguese)
        
    Returns:
        List of subtitle segments
    """
    try:
        import whisper
        import librosa
    except ImportError:
        print("Error: Required modules not found. Install with: pip install openai-whisper librosa")
        return None
    
    import tempfile
    
    print(f"\nGenerating subtitles ({language})...")
    
    # Extract audio from video using moviepy
    print("Extracting audio from video...")
    video = VideoFileClip(str(video_path))
    temp_dir = Path(tempfile.gettempdir())
    temp_audio = temp_dir / "whisper_temp_audio.mp3"
    
    try:
        video.audio.write_audiofile(str(temp_audio))
        
        print(f"Loading Whisper model (this may take a moment on first run)...")
        model = whisper.load_model("base")
        
        print(f"Transcribing audio...")
        # Load audio using librosa and pass as numpy array
        audio_data, sr = librosa.load(str(temp_audio), sr=16000)
        result = model.transcribe(audio_data, language=language)
        
        def format_time(t: float) -> str:
            """Format time in SRT format (HH:MM:SS,mmm)."""
            hours = int(t // 3600)
            minutes = int((t % 3600) // 60)
            seconds = int(t % 60)
            milliseconds = int((t % 1) * 1000)
            return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"
        
        print(f"Writing subtitles to: {subtitle_path}")
        subtitle_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(subtitle_path, "w", encoding="utf-8") as f:
            for i, segment in enumerate(result["segments"], start=1):
                start = segment["start"]
                end = segment["end"]
                text = segment["text"].strip()
                
                # Ensure text is properly encoded (handle bytes if needed)
                if isinstance(text, bytes):
                    text = text.decode('utf-8')
                
                # Break text into smaller lines for better readability
                text = break_into_small_lines(text, max_chars=50)
                
                f.write(f"{i}\n")
                f.write(f"{format_time(start)} --> {format_time(end)}\n")
                f.write(f"{text}\n\n")
        
        print(f"Subtitles saved: {subtitle_path}")
        return result["segments"]  # Return segments for embedding
    finally:
        video.close()
        # Clean up temp audio file
        if temp_audio.exists():
            temp_audio.unlink()


def embed_subtitles(video_path: Path, segments: list, output_path: Path) -> None:
    """Embed subtitle text directly onto video frames.
    
    Args:
        video_path: Path to video file
        segments: List of subtitle segments from Whisper
        output_path: Path to save video with embedded subtitles
    """
    print(f"\nEmbedding subtitles into video...")
    video = VideoFileClip(str(video_path))
    
    # Create text clips for each subtitle
    text_clips = []
    
    for segment in segments:
        start_time = segment["start"]
        end_time = segment["end"]
        text = segment["text"].strip()
        
        # Ensure text is properly encoded (handle bytes if needed)
        if isinstance(text, bytes):
            text = text.decode('utf-8')
        
        # Break text into smaller lines for better readability
        text = break_into_small_lines(text, max_chars=50)
        
        # Create text clip using correct moviepy 2.2.1 parameters
        # Note: font_size (with underscore), not fontsize
        # Use Arial font with full path for special character support
        # Add larger font size and border (stroke) for better visibility
        txt_clip = TextClip(
            text=text,
            font_size=40,  # Increased from 20 for larger text
            color='white',
            size=(video.w - 80, None),  # Reduced width from w-40 to w-80 for better wrapping
            method='label',
            font='C:/Windows/Fonts/arial.ttf',
            stroke_color='black',  # Border color
            stroke_width=2  # Border thickness
        )
        
        # Position at bottom center with more space for wrapped text
        txt_clip = txt_clip.with_position(('center', video.h - 220))
        txt_clip = txt_clip.with_start(start_time).with_end(end_time)
        
        text_clips.append(txt_clip)
    
    # Composite video with text
    if text_clips:
        final_video = CompositeVideoClip([video.without_audio()] + text_clips).with_audio(video.audio)
    else:
        final_video = video
    
    # Write output
    print(f"Writing video with embedded subtitles to: {output_path}")
    final_video.write_videofile(str(output_path), fps=video.fps, codec='libx264', audio_codec='aac')
    
    video.close()
    print(f"Success: Video with embedded subtitles saved to {output_path}")


def concat_videos(video1_path: Path, video2_path: Path, output_path: Path, audio_path: Path = None, trim_start: float = 0, trim_end: float = 0, subtitle_segments: list = None) -> None:
    """Simple video concatenation - just join two MP4 files with optional background audio and subtitles.
    
    Args:
        video1_path: Path to first video (overlay)
        video2_path: Path to second video (logo)
        output_path: Path for output MP4
        audio_path: Path to background audio file
        trim_start: Seconds to cut from beginning of overlay
        trim_end: Seconds to cut from ending of overlay
        subtitle_segments: List of subtitle segments to embed
    """
    print(f"Loading video 1: {video1_path}")
    video1 = VideoFileClip(str(video1_path))
    
    # Trim overlay video if requested
    if trim_start > 0 or trim_end > 0:
        original_duration = video1.duration
        trim_start = max(0, trim_start)
        trim_end = max(0, trim_end)
        
        # Calculate the end time (total duration minus trim_end)
        trim_end_time = video1.duration - trim_end
        if trim_end_time <= trim_start:
            print(f"Error: Trim values would remove entire video!")
            return
        
        print(f"Trimming overlay: {trim_start:.2f}s from start, {trim_end:.2f}s from end")
        video1 = video1.subclipped(trim_start, trim_end_time)
        print(f"Overlay duration: {original_duration:.2f}s -> {video1.duration:.2f}s")
    
    print(f"Loading video 2: {video2_path}")
    video2 = VideoFileClip(str(video2_path))
    
    print(f"\nVideo 1 - Duration: {video1.duration:.2f}s | FPS: {video1.fps:.2f} | Size: {video1.size}")
    print(f"Video 2 - Duration: {video2.duration:.2f}s | FPS: {video2.fps:.2f} | Size: {video2.size}")
    
    # Make sure videos have matching fps and size
    target_fps = video1.fps
    target_size = video1.size
    
    print(f"\nNote: Video 2 will be resized to {target_size} to match Video 1")
    
    # Set new size but keep original duration
    video2_resized = video2.resized((target_size[0], target_size[1]))
    print(f"Video 2 duration after resize: {video2_resized.duration:.2f}s (should still be {video2.duration:.2f}s)")
    
    # Concatenate
    final = concatenate_videoclips([video1, video2_resized])
    
    print(f"Final duration after concat: {final.duration:.2f}s (expected: {video1.duration + video2.duration:.2f}s)")
    
    # Handle audio: mix video audio with background audio
    audio_streams = []
    video_duration = final.duration
    
    # Add original video audio if it exists
    if final.audio is not None:
        print(f"\nOriginal video audio duration: {final.audio.duration:.2f}s")
        audio_streams.append(final.audio.with_start(0))
    
    # Add background audio if provided
    if audio_path and audio_path.exists():
        print(f"Loading background audio: {audio_path}")
        bg_audio = AudioFileClip(str(audio_path))
        print(f"Background audio duration: {bg_audio.duration:.2f}s")
        
        # Adjust background audio to match video duration
        if bg_audio.duration < video_duration:
            # Loop the audio to match video duration
            print(f"Looping background audio from {bg_audio.duration:.2f}s to {video_duration:.2f}s...")
            
            # Calculate how many repetitions we need
            repetitions = int(video_duration / bg_audio.duration) + 1
            
            # Create list of audio clips to concatenate
            audio_clips = [bg_audio] * repetitions
            looped_audio = concatenate_audioclips(audio_clips)
            
            # Trim to exact video duration
            bg_audio_adjusted = looped_audio.subclipped(0, video_duration)
        else:
            # Cut audio to match video duration
            print(f"Trimming background audio from {bg_audio.duration:.2f}s to {video_duration:.2f}s...")
            bg_audio_adjusted = bg_audio.subclipped(0, video_duration)
        
        print(f"Adjusted background audio duration: {bg_audio_adjusted.duration:.2f}s")
        audio_streams.append(bg_audio_adjusted.with_start(0))
    
    # Mix all audio streams
    if audio_streams:
        if len(audio_streams) > 1:
            print(f"\nMixing {len(audio_streams)} audio tracks together...")
            final_audio = CompositeAudioClip(audio_streams)
        else:
            final_audio = audio_streams[0]
        
        final = final.with_audio(final_audio)
    
    print(f"Writing to: {output_path}")
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Embed subtitles if provided
    if subtitle_segments:
        # Write temp video without subtitles first
        temp_output = output_path.parent / "temp_no_subtitles.mp4"
        final.write_videofile(str(temp_output), fps=target_fps, codec='libx264', audio_codec='aac')
        
        # Embed subtitles
        embed_subtitles(temp_output, subtitle_segments, output_path)
        
        # Clean up temp file - use try-except in case file is still in use
        try:
            temp_output.unlink()
        except Exception as e:
            print(f"Warning: Could not delete temp file {temp_output}: {e}")
    else:
        final.write_videofile(str(output_path), fps=target_fps, codec='libx264', audio_codec='aac')
        print(f"Success: {output_path}")
    
    video1.close()
    video2.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Video concatenation with background audio and subtitles")
    parser.add_argument("-o", "--overlay", type=str, required=True, help="First video file (overlay)")
    parser.add_argument("--start", type=float, default=0, help="Seconds to cut from beginning of overlay (default: 0)")
    parser.add_argument("--end", type=float, default=0, help="Seconds to cut from ending of overlay (default: 0)")
    parser.add_argument("--no-audio", action="store_true", help="Disable background audio")
    parser.add_argument("--subtitles", action="store_true", help="Generate subtitles from audio")
    parser.add_argument("--lang", type=str, default="pt", help="Language for subtitles (default: pt for Portuguese)")
    
    args = parser.parse_args()
    
    overlay_path = Path(args.overlay)
    if not overlay_path.exists():
        print(f"Error: File not found: {overlay_path}")
        return
    
    if not LOGO_VIDEO.exists():
        print(f"Error: File not found: {LOGO_VIDEO}")
        return
    
    if not args.no_audio and not BACKGROUND_SONG.exists():
        print(f"Error: Background song not found: {BACKGROUND_SONG}")
        return
    
    print("Concatenating MP4 files...")
    print(f"Video 1: {overlay_path}")
    if args.start > 0 or args.end > 0:
        print(f"  Trim: {args.start}s from start, {args.end}s from end")
    print(f"Video 2: {LOGO_VIDEO}")
    if not args.no_audio:
        print(f"Background audio: {BACKGROUND_SONG}")
    if args.subtitles:
        print(f"Subtitles: {args.lang.upper()}")
    print()
    
    output_file = OUTPUT_DIR / "final_output.mp4"
    
    try:
        audio = None if args.no_audio else BACKGROUND_SONG
        
        # Generate subtitles first if requested (from the overlay video)
        subtitle_segments = None
        if args.subtitles:
            subtitle_file = SUBTITLES_DIR / f"final_output_{args.lang}.srt"
            subtitle_segments = generate_subtitles(overlay_path, subtitle_file, args.lang)
        
        # Concatenate videos with optional embedded subtitles
        concat_videos(overlay_path, LOGO_VIDEO, output_file, audio, args.start, args.end, subtitle_segments)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
