import os
import subprocess
import logging
import asyncio
from faster_whisper import WhisperModel
from config import AUDIO_MODEL_SIZE, AUDIO_COMPUTE_TYPE, AUDIO_DEVICE, AUDIO_TEMP_WAV, AUDIO_TRANSCRIPTION_TIMEOUT

logger = logging.getLogger(__name__)

whisper_model = None

def get_whisper_model():
    global whisper_model
    if whisper_model is None:
        whisper_model = WhisperModel(AUDIO_MODEL_SIZE, device=AUDIO_DEVICE, compute_type=AUDIO_COMPUTE_TYPE)
        logger.info("Whisper model loaded successfully")
    return whisper_model

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
        logger.error(f"ffmpeg not found: {e}")
        raise
    except subprocess.CalledProcessError as e:
        logger.error(f"Conversion error for {input_path}: {e}")
        raise

def _transcribe_sync(audio_path):
    model = get_whisper_model()
    
    file_ext = os.path.splitext(audio_path)[1].lower()
    
    if file_ext not in ['.wav']:
        logger.info(f"Converting {file_ext} to WAV format")
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
    
    logger.info(f"Detected language: {info.language}, duration: {info.duration:.2f}s")
    
    transcription = ""
    for segment in segments:
        transcription += segment.text.strip() + "\n"
    
    if audio_path_converted == AUDIO_TEMP_WAV and os.path.exists(AUDIO_TEMP_WAV):
        os.remove(AUDIO_TEMP_WAV)
        logger.info("Temporary WAV file removed")
    
    return transcription.strip()

async def transcribe_audio(audio_path):
    logger.info(f"Starting transcription of {audio_path}")
    
    try:
        transcription = await asyncio.wait_for(
            asyncio.to_thread(_transcribe_sync, audio_path),
            timeout=AUDIO_TRANSCRIPTION_TIMEOUT
        )
        
        logger.info(f"Transcription completed")
        return transcription
        
    except asyncio.TimeoutError:
        logger.error(f"Transcription timeout for {audio_path}")
        raise Exception(f"Transcription timeout after {AUDIO_TRANSCRIPTION_TIMEOUT} seconds")
    except Exception as e:
        logger.error(f"Transcription error for {audio_path}: {e}")
        raise