"""Main entry point for IAVideoEditor."""

from pathlib import Path
from moviepy import AudioFileClip, VideoFileClip, CompositeAudioClip, concatenate_videoclips
import argparse


# Media file paths
MEDIA_DIR = Path(__file__).parent.parent / "media"
BACKGROUND_SONG = MEDIA_DIR / "audio" / "background_song.mp3"
LOGO_VIDEO = MEDIA_DIR / "videos" / "logo.mp4"
OUTPUT_DIR = MEDIA_DIR / "output"


def concat_audio_and_video(audio_path: Path, video_path: Path, output_path: Path, volume_boost: float = 0) -> None:
    """
    Concatenate an audio file with a video file and output as MP4.
    
    The background song plays first, followed by the logo video at the end.
    
    Args:
        audio_path: Path to the MP3 audio file (background_song.mp3)
        video_path: Path to the MP4 video file (logo.mp4)
        output_path: Path where the output MP4 will be saved
        volume_boost: Percentage to increase volume (default: 0, range: 0-100)
    """
    print(f"Loading audio: {audio_path}")
    audio_clip = AudioFileClip(str(audio_path))
    
    print(f"Loading video: {video_path}")
    video_clip = VideoFileClip(str(video_path))
    
    # Get durations
    audio_duration = audio_clip.duration
    video_duration = video_clip.duration
    
    print(f"Audio duration: {audio_duration:.2f}s")
    print(f"Video duration: {video_duration:.2f}s")
    
    # Create a black frame/placeholder for the audio duration
    from moviepy import ColorClip
    
    # Get video size from the logo video
    video_width, video_height = video_clip.size
    
    # Create a black placeholder video for the first part (audio duration)
    placeholder = ColorClip(size=(video_width, video_height), color=(0, 0, 0), duration=audio_duration)
    
    # Concatenate: placeholder video + logo video
    final_video = concatenate_videoclips([placeholder, video_clip])
    
    # Adjust audio volume based on boost percentage
    volume_multiplier = 1 + (volume_boost / 100)
    audio_clip_adjusted = audio_clip.with_volume_scaled(volume_multiplier)
    
    print(f"Volume boost: +{volume_boost}% (multiplier: {volume_multiplier:.2f}x)")
    
    # Set the audio to just the audio clip (it will play during the placeholder part)
    final_video = final_video.with_audio(audio_clip_adjusted)
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"\nWriting output to: {output_path}")
    final_video.write_videofile(str(output_path))
    
    print(f"✓ Output file created successfully: {output_path}")
    
    # Clean up
    audio_clip.close()
    video_clip.close()


def main() -> None:
    """Run the IAVideoEditor application."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="IAVideoEditor - Concatenate audio and video files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.main                    # Default (no volume boost)
  python -m src.main -s 10              # Increase volume by 10%
  python -m src.main --sound 25         # Increase volume by 25%
        """
    )
    parser.add_argument(
        "-s", "--sound",
        type=float,
        default=0,
        help="Sound volume increase percentage (0-100, default: 0)"
    )
    
    args = parser.parse_args()
    
    # Validate volume boost
    if not 0 <= args.sound <= 200:
        print(f"✗ Invalid sound boost value: {args.sound}. Must be between 0 and 200.")
        return
    
    print("IAVideoEditor - Welcome!")
    print("This is the main entry point for the video editing application.")
    
    # Display media file paths
    print(f"\nMedia files location: {MEDIA_DIR}")
    print(f"Background song: {BACKGROUND_SONG}")
    print(f"Logo video: {LOGO_VIDEO}")
    
    # Check if media files exist
    if BACKGROUND_SONG.exists():
        print(f"✓ Background song found: {BACKGROUND_SONG}")
    else:
        print(f"✗ Background song not found: {BACKGROUND_SONG}")
        return
    
    if LOGO_VIDEO.exists():
        print(f"✓ Logo video found: {LOGO_VIDEO}")
    else:
        print(f"✗ Logo video not found: {LOGO_VIDEO}")
        return
    
    # Create output
    output_file = OUTPUT_DIR / "final_output.mp4"
    print(f"\n{'='*50}")
    print("Starting concatenation process...")
    print(f"{'='*50}")
    
    try:
        concat_audio_and_video(BACKGROUND_SONG, LOGO_VIDEO, output_file, args.sound)
    except Exception as e:
        print(f"✗ Error during concatenation: {e}")


if __name__ == "__main__":
    main()
