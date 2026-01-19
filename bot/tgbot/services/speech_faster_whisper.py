from faster_whisper import WhisperModel


# Загружаем модель один раз (лучше вынести глобально, чтобы не пересоздавалась на каждый файл)
model = WhisperModel("small", device="cpu", compute_type="int8")

async def process_voice_with_faster_whisper(file_path: str) -> str:
    """
    Распознаёт речь в аудио через faster-whisper.
    """

    def generate_segments(file_path: str, beam_size: int = 1, vad_filter: bool = True):
        """
        Генератор сегментов из Faster-Whisper.
        """
        segments, info = model.transcribe(file_path, log_progress=True, beam_size=beam_size, vad_filter=vad_filter)

        for segment in segments:
            yield segment

    text_parts = []
    for seg in generate_segments(file_path):
        text_parts.append(seg.text.strip())
        
    return " ".join(text_parts)
