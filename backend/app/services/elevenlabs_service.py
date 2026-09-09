import os
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from backend.app.core.config import settings

class ElevenLabsService:
    @classmethod
    @retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def _post_text_to_speech_with_retry(cls, url, json_data, headers):
        with httpx.Client() as client:
            response = client.post(url, json=json_data, headers=headers, timeout=60.0)
            if response.status_code != 200:
                raise Exception(f"ElevenLabs API failed with status {response.status_code}: {response.text}")
            return response.content

    @classmethod
    def generate_speech(cls, text: str, save_path: str) -> str:
        """Generates MP3 audio for the provided script text."""
        if settings.is_elevenlabs_mock:
            return cls._generate_fallback_speech(text, save_path)
            
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{settings.ELEVENLABS_VOICE_ID}"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": settings.ELEVENLABS_API_KEY
        }
        data = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.5
            }
        }
        try:
            content = cls._post_text_to_speech_with_retry(url, data, headers)
            with open(save_path, "wb") as f:
                f.write(content)
            return save_path
        except Exception as e:
            print(f"ElevenLabs error after retries: {e}")
            raise


    @staticmethod
    def _generate_fallback_speech(text: str, save_path: str) -> str:
        """Uses gTTS if available, otherwise writes a dummy mock audio file."""
        try:
            from gtts import gTTS
            tts = gTTS(text=text, lang="en")
            tts.save(save_path)
            return save_path
        except Exception as e:
            print(f"gTTS fallback failed: {e}. Writing valid silent WAV audio.")
            import math
            import struct
            import wave

            sample_rate = 44100
            duration = 6
            with wave.open(save_path, "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(sample_rate)
                for i in range(sample_rate * duration):
                    # A very quiet tone keeps the file valid without being distracting.
                    sample = int(1200 * math.sin(2 * math.pi * 220 * (i / sample_rate)))
                    wav.writeframes(struct.pack("<h", sample))
            return save_path
class gTTS:
    pass
