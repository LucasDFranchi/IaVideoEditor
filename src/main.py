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
BACKGROUND_AUDIO_GAIN = 0.1  # volume relativo da música de fundo em relação ao áudio original
OUTPUT_RESOLUTION = (1080, 1920)  # 1080p vertical (9:16), exigido pelo Instagram Reels
OUTPUT_BITRATE = "8000k"
SUBTITLE_FONT = MEDIA_DIR / "fonts" / "Anton-Regular.ttf"

# Estilo de legenda (estilo VEED: palavra ativa em destaque)
SUBTITLE_FONT_SIZE = 48
SUBTITLE_COLOR = "white"
SUBTITLE_HIGHLIGHT_COLOR = "#3A96FF"  # vermelho
SUBTITLE_STROKE_COLOR = "black"
SUBTITLE_STROKE_WIDTH = 3

# Posição vertical da legenda na tela (fração da altura do vídeo)
SUBTITLE_POSITIONS = {
    "top": 0.08,
    "middle": 0.45,
    "bottom": 0.75,
}


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


class VideoTranscriber:
    """Transcreve o áudio de um vídeo usando faster-whisper (LIVRE, código aberto, sem chaves de API).

    O modelo é carregado uma única vez por instância e reutilizado entre chamadas a transcribe().
    """

    def __init__(self, model_size: str = "small", device: str = "cpu", compute_type: str = "int8"):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model = None

    def _load_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel
            print("Carregando modelo Whisper...")
            self._model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)
        return self._model

    def transcribe(self, video_path: Path, language: str = "pt") -> list:
        """Transcrever um vídeo (.mp4) e retornar os segmentos de legenda.

        Args:
            video_path: Caminho para o arquivo de vídeo
            language: Código de idioma (padrão: "pt" para Português)

        Returns:
            Lista de segmentos: [{"start", "end", "text", "words": [{"start", "end", "word"}]}]
            None se o faster-whisper não estiver instalado.
        """
        video_path = Path(video_path) if not isinstance(video_path, Path) else video_path

        try:
            model = self._load_model()
        except ImportError:
            print("Erro: Módulo necessário não encontrado. Instale com: pip install faster-whisper")
            return None

        print(f"\nGerando subtítulos ({language})...")
        print("Transcrevendo áudio...")
        # faster-whisper lê o áudio diretamente do arquivo de vídeo (via ffmpeg), sem extração manual
        segments, info = model.transcribe(str(video_path), language=language, word_timestamps=True)

        segments_list = []
        for segment in segments:
            words = [
                {"start": w.start, "end": w.end, "word": w.word.strip()}
                for w in (segment.words or [])
                if w.word.strip()
            ]
            segments_list.append({
                "start": segment.start,
                "end": segment.end,
                "text": segment.text.strip(),
                "words": words
            })

        print(f"Transcrição de {len(segments_list)} segmentos")
        return segments_list

    @staticmethod
    def to_srt(segments: list) -> str:
        """Converter segmentos de legenda em texto no formato SRT."""

        def format_timestamp(seconds: float) -> str:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            millis = int(round((seconds - int(seconds)) * 1000))
            return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

        lines = []
        for index, segment in enumerate(segments, start=1):
            lines.append(str(index))
            lines.append(f"{format_timestamp(segment['start'])} --> {format_timestamp(segment['end'])}")
            lines.append(segment["text"])
            lines.append("")

        return "\n".join(lines)


def _group_words(words: list, font, space_width: float, max_width: float, max_words: int = 6) -> list:
    """Agrupar palavras cronometradas em pequenos grupos exibidos juntos na tela.

    Agrupa por largura real renderizada (não por contagem de caracteres), para
    garantir que cada grupo caiba dentro da largura do vídeo.

    Args:
        words: Lista de palavras com chaves 'word', 'start', 'end'
        font: PIL ImageFont usado para medir a largura das palavras
        space_width: Largura em pixels de um espaço nesta fonte
        max_width: Largura máxima em pixels disponível para um grupo
        max_words: Máximo de palavras por grupo

    Returns:
        Lista de grupos (cada grupo é uma lista de palavras)
    """
    groups = []
    current = []
    current_width = 0.0

    for word in words:
        word_width = font.getlength(word["word"].strip().upper())
        added_width = word_width if not current else current_width + space_width + word_width

        if current and (len(current) >= max_words or added_width > max_width):
            groups.append(current)
            current = []
            added_width = word_width

        current.append(word)
        current_width = added_width

    if current:
        groups.append(current)

    return groups


def embed_subtitles(video_path: Path, segments: list, output_path: Path, position: str = "top",
                     font_size: int = None, color: str = None) -> None:
    """Embed karaoke-style subtitles onto video frames (VEED-style: active word highlighted in green).

    Args:
        video_path: Path to video file
        segments: List of subtitle segments from generate_subtitles(), each with word-level timestamps
        output_path: Path to save video with embedded subtitles
        position: Posição vertical da legenda: "top", "middle" ou "bottom" (padrão)
        font_size: Tamanho da fonte da legenda (padrão: SUBTITLE_FONT_SIZE)
        color: Cor da legenda em estado normal, ex: "white" ou "#FFFFFF" (padrão: SUBTITLE_COLOR)
    """
    from PIL import ImageFont

    # Ensure paths are Path objects
    video_path = Path(video_path) if not isinstance(video_path, Path) else video_path
    output_path = Path(output_path) if not isinstance(output_path, Path) else output_path

    font_size = font_size or SUBTITLE_FONT_SIZE
    color = color or SUBTITLE_COLOR

    print(f"\nEmbedding subtitles into video...")
    video = VideoFileClip(str(video_path))

    font = ImageFont.truetype(str(SUBTITLE_FONT), font_size)
    space_width = font.getlength(" ")
    position_fraction = SUBTITLE_POSITIONS.get(position, SUBTITLE_POSITIONS["bottom"])
    y_pos = int(video.h * position_fraction)
    max_group_width = video.w * 0.9

    # moviepy calcula a altura do TextClip a partir de font.getmetrics() (ascent + descent),
    # que subestima a altura real dos glifos desta fonte e corta a base do texto (ex: o rabinho
    # do "Ç"). Damos uma altura explícita com folga para evitar o corte.
    clip_height = int(font_size * 1.6)

    def make_word_clip(text, word_color, start, end, x, y):
        return (
            TextClip(
                text=text,
                font=str(SUBTITLE_FONT),
                font_size=font_size,
                color=word_color,
                stroke_color=SUBTITLE_STROKE_COLOR,
                stroke_width=SUBTITLE_STROKE_WIDTH,
                size=(None, clip_height),
                # "top" fixa a linha de base no mesmo ponto para todas as palavras.
                # Com "center" (padrão), palavras acentuadas (Ã, É...) ficam mais altas
                # que as sem acento, pois o moviepy centraliza a caixa de texto inteira
                # (incluindo o acento) em vez de alinhar pela linha de base.
                vertical_align="top",
            )
            .with_position((x, y))
            .with_start(start)
            .with_end(end)
        )

    # Create text clips for each subtitle
    caption_clips = []

    for segment in segments:
        words = segment.get("words") or []
        if not words:
            txt = segment["text"].strip()
            if txt:
                words = [{"word": txt, "start": segment["start"], "end": segment["end"]}]

        for group in _group_words(words, font, space_width, max_group_width):
            group_start = group[0]["start"]
            group_end = group[-1]["end"]

            texts = [w["word"].upper() for w in group]
            widths = [font.getlength(t) for t in texts]
            total_width = sum(widths) + space_width * (len(group) - 1)
            x = video.w / 2 - total_width / 2
            # Segurança: nunca deixar o grupo sair da área visível do vídeo
            x = max(0, min(x, max(0, video.w - total_width)))

            for word, text, width in zip(group, texts, widths):
                # Base: palavra em branco durante todo o grupo
                caption_clips.append(
                    make_word_clip(text, color, group_start, group_end, x, y_pos)
                )
                # Destaque: palavra em verde apenas enquanto está sendo falada
                caption_clips.append(
                    make_word_clip(text, SUBTITLE_HIGHLIGHT_COLOR, word["start"], word["end"], x, y_pos)
                )
                x += width + space_width

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
    target_size = OUTPUT_RESOLUTION

    print(f"\nNota: Ambos os vídeos serão redimensionados para {target_size} (1080p)")

    video1_resized = video1.resized((target_size[0], target_size[1]))
    video2_resized = video2.resized((target_size[0], target_size[1]))
    print(f"Duração do Vídeo 2 após redimensionamento: {video2_resized.duration:.2f}s (deve ainda ser {video2.duration:.2f}s)")

    # Concatenar
    final = concatenate_videoclips([video1_resized, video2_resized])
    
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
        
        bg_audio_adjusted = bg_audio_adjusted.with_volume_scaled(BACKGROUND_AUDIO_GAIN)
        print(f"Duração do áudio de fundo ajustada: {bg_audio_adjusted.duration:.2f}s (volume: {BACKGROUND_AUDIO_GAIN})")
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
    final.write_videofile(str(output_path), fps=target_fps, codec='libx264', audio_codec='aac', bitrate=OUTPUT_BITRATE)
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
    parser.add_argument("--subtitle-position", type=str, default="top", choices=["top", "middle", "bottom"], help="Vertical position of subtitles (default: top)")
    
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
            if args.start > 0 or args.end > 0:
                print("Aviso: legendas com corte (--start/--end) podem ficar dessincronizadas.")
            subtitle_segments = VideoTranscriber().transcribe(overlay_path, args.lang)
            if subtitle_segments:
                subtitle_file = SUBTITLES_DIR / f"final_output_{args.lang}.srt"
                subtitle_file.parent.mkdir(parents=True, exist_ok=True)
                subtitle_file.write_text(VideoTranscriber.to_srt(subtitle_segments), encoding="utf-8")

        if subtitle_segments:
            concat_output = OUTPUT_DIR / "_concat_temp.mp4"
            concat_videos(overlay_path, LOGO_VIDEO, concat_output, audio, args.start, args.end)
            embed_subtitles(concat_output, subtitle_segments, output_file, args.subtitle_position)
            concat_output.unlink(missing_ok=True)
        else:
            # Concatenate videos (sem legendas)
            concat_videos(overlay_path, LOGO_VIDEO, output_file, audio, args.start, args.end)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
