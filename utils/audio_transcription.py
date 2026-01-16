import os
import subprocess
import logging
from faster_whisper import WhisperModel
from config import AUDIO_MODEL_SIZE, AUDIO_COMPUTE_TYPE, AUDIO_DEVICE, AUDIO_TEMP_WAV

logger = logging.getLogger(__name__)

def convert_to_wav(input_path, output_path=AUDIO_TEMP_WAV):
    try:
        subprocess.run([
            "/usr/bin/ffmpeg", "-i", input_path,
            "-ar", "16000", "-ac", "1",
            "-vn",
            "-y", output_path
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return output_path
    except FileNotFoundError as e:
        logger.error(f"ffmpeg не найден: {e}")
        raise
    except subprocess.CalledProcessError as e:
        logger.error(f"Ошибка конвертации {input_path}: {e}")
        raise

async def transcribe_audio(audio_path):
    logger.info(f"Начинаю транскрибацию {audio_path}")
    
    try:
        model = WhisperModel(AUDIO_MODEL_SIZE, device=AUDIO_DEVICE, compute_type=AUDIO_COMPUTE_TYPE)
        
        file_ext = os.path.splitext(audio_path)[1].lower()
        
        if file_ext not in ['.wav']:
            logger.info(f"Конвертирую {file_ext} в WAV формат")
            audio_path_converted = convert_to_wav(audio_path)
        else:
            audio_path_converted = audio_path
        
        segments, info = model.transcribe(
            audio_path_converted,
            beam_size=20,
            best_of=10,
            temperature=0.2,
            word_timestamps=False,
            vad_filter=False,
            condition_on_previous_text=True,
            language=None
        )
        
        logger.info(f"Определён язык: {info.language}, длительность: {info.duration:.2f}с")
        
        transcription = ""
        for segment in segments:
            transcription += segment.text.strip() + "\n"
        
        if audio_path_converted == AUDIO_TEMP_WAV and os.path.exists(AUDIO_TEMP_WAV):
            os.remove(AUDIO_TEMP_WAV)
            logger.info("Временный WAV файл удалён")
        
        logger.info(f"Транскрибация завершена")
        return transcription.strip()
        
    except Exception as e:
        logger.error(f"Ошибка транскрибации {audio_path}: {e}")
        raise