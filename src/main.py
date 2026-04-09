"""Main entry point for IAVideoEditor."""

from pathlib import Path
from moviepy import VideoFileClip, concatenate_videoclips
import argparse


# Media file paths
MEDIA_DIR = Path(__file__).parent.parent / "media"
LOGO_VIDEO = MEDIA_DIR / "videos" / "logo.mp4"
OUTPUT_DIR = MEDIA_DIR / "output"


def concat_videos(video1_path: Path, video2_path: Path, output_path: Path) -> None:
    """Simple video concatenation - just join two MP4 files."""
    print(f"Loading video 1: {video1_path}")
    video1 = VideoFileClip(str(video1_path))
    
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
    print(f"Writing to: {output_path}")
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    final.write_videofile(str(output_path), fps=target_fps, codec='libx264', audio_codec='aac')
    
    print(f"Success: {output_path}")
    
    video1.close()
    video2.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Simple MP4 concatenation")
    parser.add_argument("-o", "--overlay", type=str, required=True, help="First video file")
    
    args = parser.parse_args()
    
    overlay_path = Path(args.overlay)
    if not overlay_path.exists():
        print(f"Error: File not found: {overlay_path}")
        return
    
    if not LOGO_VIDEO.exists():
        print(f"Error: File not found: {LOGO_VIDEO}")
        return
    
    print("Concatenating MP4 files...")
    print(f"Video 1: {overlay_path}")
    print(f"Video 2: {LOGO_VIDEO}\n")
    
    output_file = OUTPUT_DIR / "final_output.mp4"
    
    try:
        concat_videos(overlay_path, LOGO_VIDEO, output_file)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
