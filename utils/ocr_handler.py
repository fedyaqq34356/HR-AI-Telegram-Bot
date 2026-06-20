import re
import logging

logger = logging.getLogger(__name__)

def extract_id(image_bytes):
    logger.info("OCR disabled, returning None")
    return None