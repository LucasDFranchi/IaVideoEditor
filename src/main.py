"""Ponto de entrada principal do IAVideoEditor."""

from pathlib import Path
from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips, concatenate_audioclips, CompositeAudioClip, TextClip, CompositeVideoClip
import argparse


# Caminhos de arquivos de mídias
MEDIA_DIR = Path(__file__).parent.parent / "media"
LOGO_VIDEO = MEDIA_DIR / "videos" / "logo.mp4"
BACKGROUND_SONG = MEDIA_DIR / "audio" / "background_song.mp3"
OUTPUT_DIR = MEDIA_DIR / "output"
SUBTITLES_DIR = OUTPUT_DIR / "subtitles"


def break_into_small_lines(text: str, max_chars: int = 50) -> str:
    """Quebrar texto em linhas menores para melhor legibilidade.
    
    Args:
        text: Texto a ser quebrado em linhas
        max_chars: Máximo de caracteres por linha (padrão: 50)
        
    Returns:
        Texto com quebras de linha inseridas
    """
    words = text.split()
    lines = []
    current_line = []
    current_length = 0
    
    for word in words:
        # Verificar se adicionar esta palavra excederia o limite
        word_length = len(word)
        if current_length + word_length + len(current_line) > max_chars and current_line:
            # Começar uma nova linha
            lines.append(' '.join(current_line))
            current_line = [word]
            current_length = word_length
        else:
            # Adicionar palavra à linha atual
            current_line.append(word)
            current_length += word_length
    
    # Adicionar a última linha
    if current_line:
        lines.append(' '.join(current_line))
    
    return '\n'.join(lines)


def generate_subtitles(video_path: Path, subtitle_path: Path, language: str = "pt") -> list:
    """Gerar subtítulos do áudio do vídeo usando openai-whisper (LIVRE, código aberto, sem chaves de API necessárias).
    
    Args:
        video_path: Caminho para o arquivo de vídeo
        subtitle_path: Caminho para salvar subtítulos SRT (para backup, não utilizado no vídeo)
        language: Código de idioma (padrão: "pt" para Português)
        
    Returns:
        Lista de segmentos de subtítulo com chaves 'start', 'end' e 'text'
    """
    # Garantir que os caminhos sejam objetos Path
    video_path = Path(video_path) if not isinstance(video_path, Path) else video_path
    subtitle_path = Path(subtitle_path) if not isinstance(subtitle_path, Path) else subtitle_path
    
    try:
        import whisper
        import librosa
    except ImportError:
        print("Erro: Módulos necessários não encontrados. Instale com: pip install openai-whisper librosa")
        return None
    
    import tempfile
    
    print(f"\nGerando subtítulos ({language})...")
    
    # Extrair áudio do vídeo usando moviepy
    print("Extraindo áudio do vídeo...")
    video = VideoFileClip(str(video_path))
    temp_dir = Path(tempfile.gettempdir())
    temp_audio = temp_dir / "whisper_temp_audio.mp3"
    
    try:
        video.audio.write_audiofile(str(temp_audio))
        
        print(f"Carregando modelo Whisper...")
        model = whisper.load_model("base")
        
        print(f"Transcrevendo áudio...")
        # Carregar áudio usando librosa e passar como array numpy
        audio_data, sr = librosa.load(str(temp_audio), sr=16000)
        result = model.transcribe(audio_data, language=language)
        
        # Converter para formato de segmentos correspondente ao saída do faster-whisper
        segments_list = []
        for segment in result["segments"]:
            segments_list.append({
                "start": segment["start"],
                "end": segment["end"],
                "text": segment["text"].strip()
            })
        
        print(f"Transcrição de {len(segments_list)} segmentos")
        return segments_list
    finally:
        video.close()
        # Limpar arquivo de áudio temporário
        if temp_audio.exists():
            temp_audio.unlink()


def embed_subtitles(video_path: Path, segments: list, output_path: Path) -> None:
    """Embed subtitle text directly onto video frames.
    
    Args:
        video_path: Path to video file
        segments: List of subtitle segments from faster-whisper
        output_path: Path to save video with embedded subtitles
    """
    # Ensure paths are Path objects
    video_path = Path(video_path) if not isinstance(video_path, Path) else video_path
    output_path = Path(output_path) if not isinstance(output_path, Path) else output_path
    
    print(f"\nEmbedding subtitles into video...")
    video = VideoFileClip(str(video_path))
    
    # Create text clips for each subtitle
    caption_clips = []
    
    for segment in segments:
        txt = segment["text"].strip()
        
        if not txt:  # Skip empty segments
            continue
        
        # Create caption clip with automatic wrapping
        caption = (
            TextClip(
                text=txt,
                font_size=50,
                size=(int(video.w * 0.8), None),  # 80% of video width for automatic wrapping
                method="caption",  # Enables word wrapping
                color='white',
                stroke_color='black',
                stroke_width=2
            )
            .with_position(("center", "bottom"))  # Centered horizontally, positioned at bottom
            .with_start(segment["start"])
            .with_end(segment["end"])
        )
        
        caption_clips.append(caption)
    
    # Composite video with captions
    if caption_clips:
        final_video = CompositeVideoClip([video] + caption_clips)
    else:
        final_video = video
    
    # Write output
    print(f"Writing video with embedded subtitles to: {output_path}")
    final_video.write_videofile(str(output_path), fps=video.fps, codec='libx264', audio_codec='aac')
    
    video.close()
    print(f"Success: Video with embedded subtitles saved to {output_path}")


def concat_videos(video1_path: Path, video2_path: Path, output_path: Path, audio_path: Path = None, trim_start: float = 0, trim_end: float = 0) -> None:
    """Concatenar dois arquivos MP4 com áudio de fundo opcional.
    
    Args:
        video1_path: Caminho para o primeiro vídeo (overlay)
        video2_path: Caminho para o segundo vídeo (logo)
        output_path: Caminho para saída do MP4
        audio_path: Caminho para o arquivo de áudio de fundo
        trim_start: Segundos a cortar do início do overlay
        trim_end: Segundos a cortar do fim do overlay
    """
    # Garantir que todos os caminhos sejam objetos Path (podem vir como strings de CLI/GUI)
    video1_path = Path(video1_path) if not isinstance(video1_path, Path) else video1_path
    video2_path = Path(video2_path) if not isinstance(video2_path, Path) else video2_path
    output_path = Path(output_path) if not isinstance(output_path, Path) else output_path
    audio_path = Path(audio_path) if audio_path and not isinstance(audio_path, Path) else audio_path
    
    print(f"Carregando vídeo 1: {video1_path}")
    video1 = VideoFileClip(str(video1_path))
    
    # Cortar vídeo overlay se solicitado
    if trim_start > 0 or trim_end > 0:
        original_duration = video1.duration
        trim_start = max(0, trim_start)
        trim_end = max(0, trim_end)
        
        # Calcular o tempo final (duração total menos trim_end)
        trim_end_time = video1.duration - trim_end
        if trim_end_time <= trim_start:
            print(f"Erro: Os valores de corte removeriam todo o vídeo!")
            return
        
        print(f"Cortando overlay: {trim_start:.2f}s do início, {trim_end:.2f}s do fim")
        video1 = video1.subclipped(trim_start, trim_end_time)
        print(f"Duração do overlay: {original_duration:.2f}s -> {video1.duration:.2f}s")
    
    print(f"Carregando vídeo 2: {video2_path}")
    video2 = VideoFileClip(str(video2_path))
    
    print(f"\nVídeo 1 - Duração: {video1.duration:.2f}s | FPS: {video1.fps:.2f} | Tamanho: {video1.size}")
    print(f"Vídeo 2 - Duração: {video2.duration:.2f}s | FPS: {video2.fps:.2f} | Tamanho: {video2.size}")
    
    # Garantir que os vídeos tenham fps e tamanho correspondentes
    target_fps = video1.fps
    target_size = video1.size
    
    print(f"\nNota: O Vídeo 2 será redimensionado para {target_size} para correspondencer ao Vídeo 1")
    
    # Definir novo tamanho mas manter duração original
    video2_resized = video2.resized((target_size[0], target_size[1]))
    print(f"Duração do Vídeo 2 após redimensionamento: {video2_resized.duration:.2f}s (deve ainda ser {video2.duration:.2f}s)")
    
    # Concatenar
    final = concatenate_videoclips([video1, video2_resized])
    
    print(f"Duração final após concatenação: {final.duration:.2f}s (esperado: {video1.duration + video2.duration:.2f}s)")
    
    # Lidar com áudio: misturar áudio do vídeo com áudio de fundo
    audio_streams = []
    video_duration = final.duration
    
    # Adicionar áudio do vídeo original se existir
    if final.audio is not None:
        print(f"\nDuração do áudio do vídeo original: {final.audio.duration:.2f}s")
        audio_streams.append(final.audio.with_start(0))
    
    # Adicionar áudio de fundo se fornecido
    if audio_path and audio_path.exists():
        print(f"Carregando áudio de fundo: {audio_path}")
        bg_audio = AudioFileClip(str(audio_path))
        print(f"Duração do áudio de fundo: {bg_audio.duration:.2f}s")
        
        # Ajustar áudio de fundo para corresponder à duração do vídeo
        if bg_audio.duration < video_duration:
            # Fazer loop do áudio para corresponder à duração do vídeo
            print(f"Fazendo loop do áudio de fundo de {bg_audio.duration:.2f}s para {video_duration:.2f}s...")
            
            # Calcular quantas repetições precisamos
            repetitions = int(video_duration / bg_audio.duration) + 1
            
            # Criar lista de clipes de áudio para concatenar
            audio_clips = [bg_audio] * repetitions
            looped_audio = concatenate_audioclips(audio_clips)
            
            # Cortar para duração de vídeo exata
            bg_audio_adjusted = looped_audio.subclipped(0, video_duration)
        else:
            # Cortar áudio para corresponder à duração do vídeo
            print(f"Cortando áudio de fundo de {bg_audio.duration:.2f}s para {video_duration:.2f}s...")
            bg_audio_adjusted = bg_audio.subclipped(0, video_duration)
        
        print(f"Duração do áudio de fundo ajustada: {bg_audio_adjusted.duration:.2f}s")
        audio_streams.append(bg_audio_adjusted.with_start(0))
    
    # Misturar todos os fluxos de áudio
    if audio_streams:
        if len(audio_streams) > 1:
            print(f"\nMisturando {len(audio_streams)} faixas de áudio juntas...")
            final_audio = CompositeAudioClip(audio_streams)
        else:
            final_audio = audio_streams[0]
        
        final = final.with_audio(final_audio)
    
    print(f"Escrevendo para: {output_path}")
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    final.write_videofile(str(output_path), fps=target_fps, codec='libx264', audio_codec='aac')
    print(f"Sucesso: {output_path}")
    
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
