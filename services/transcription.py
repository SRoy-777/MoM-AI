import os
import tempfile
import logging
from typing import Dict, Any, List

logger = logging.getLogger("mom_ai.transcription")

class AudioTranscriptionService:
    def __init__(self):
        self.whisper_model = None
        self._init_model()

    def _init_model(self):
        """Attempts to lazy load faster-whisper if available in the environment."""
        try:
            from faster_whisper import WhisperModel
            # Using tiny / base for fast CPU inference in free HF Space environment
            logger.info("Initializing faster-whisper model...")
            self.whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
            logger.info("faster-whisper initialized successfully.")
        except Exception as e:
            logger.warning(f"faster-whisper not available or failed to load ({e}). Web Speech API and text transcripts will be used.")

    def transcribe_audio_bytes(self, audio_bytes: bytes, filename: str = "audio.wav") -> Dict[str, Any]:
        """Transcribes raw audio bytes using faster-whisper if available."""
        if not self.whisper_model:
            return {
                "success": False,
                "error": "faster-whisper is not enabled on server. Please use browser speech-to-text or provide direct transcript."
            }

        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1] or ".wav") as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            segments, info = self.whisper_model.transcribe(tmp_path, beam_size=5)
            transcript_lines = []
            segment_list = []
            
            for segment in segments:
                transcript_lines.append(f"[{segment.start:.1f}s - {segment.end:.1f}s] {segment.text.strip()}")
                segment_list.append({
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip()
                })

            full_transcript = "\n".join(transcript_lines)
            return {
                "success": True,
                "transcript": full_transcript,
                "segments": segment_list,
                "language": info.language
            }
        except Exception as e:
            logger.error(f"Error during audio transcription: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
