"""Main entry point for IAVideoEditor."""

from pathlib import Path
from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips, concatenate_audioclips, CompositeAudioClip
import argparse


# Media file paths
MEDIA_DIR = Path(__file__).parent.parent / "media"
LOGO_VIDEO = MEDIA_DIR / "videos" / "logo.mp4"
BACKGROUND_SONG = MEDIA_DIR / "audio" / "background_song.mp3"
OUTPUT_DIR = MEDIA_DIR / "output"


def concat_videos(video1_path: Path, video2_path: Path, output_path: Path, audio_path: Path = None, trim_start: float = 0, trim_end: float = 0) -> None:
    """Simple video concatenation - just join two MP4 files with optional background audio.
    
    Args:
        video1_path: Path to first video (overlay)
        video2_path: Path to second video (logo)
        output_path: Path for output MP4
        audio_path: Path to background audio file
        trim_start: Seconds to cut from beginning of overlay
        trim_end: Seconds to cut from ending of overlay
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
    final.write_videofile(str(output_path), fps=target_fps, codec='libx264', audio_codec='aac')
    
    print(f"Success: {output_path}")
    
    video1.close()
    video2.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Video concatenation with background audio")
    parser.add_argument("-o", "--overlay", type=str, required=True, help="First video file (overlay)")
    parser.add_argument("--start", type=float, default=0, help="Seconds to cut from beginning of overlay (default: 0)")
    parser.add_argument("--end", type=float, default=0, help="Seconds to cut from ending of overlay (default: 0)")
    parser.add_argument("--no-audio", action="store_true", help="Disable background audio")
    
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
    print()
    
    output_file = OUTPUT_DIR / "final_output.mp4"
    
    try:
        audio = None if args.no_audio else BACKGROUND_SONG
        concat_videos(overlay_path, LOGO_VIDEO, output_file, audio, args.start, args.end)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
