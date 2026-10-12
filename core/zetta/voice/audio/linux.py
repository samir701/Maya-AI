"""Linux ALSA / PipeWire / PulseAudio Real Audio Capture and Playback Providers."""

import os
import shutil
import subprocess
import time
from typing import List, Optional
from core.zetta.utils.errors import ToolError
from core.zetta.utils.logging import get_logger
from core.zetta.voice.audio.base import AudioCaptureProvider, AudioPlaybackProvider
from core.zetta.voice.audio.device import AudioDeviceManager
from core.zetta.voice.models.audio import (
    AudioChunk,
    AudioData,
    AudioDevice,
    AudioFormat,
)

logger = get_logger("linux_audio")


class LinuxALSAAudioCaptureProvider(AudioCaptureProvider):
    """Real Linux audio capture using standard ALSA `arecord` binary."""

    def __init__(self, device_manager: Optional[AudioDeviceManager] = None) -> None:
        self.device_manager = device_manager or AudioDeviceManager()
        self._arecord_path = shutil.which("arecord")
        self._process: Optional[subprocess.Popen] = None
        self._format = AudioFormat()
        self._accumulated_data = bytearray()
        self._chunk_counter = 0
        self.is_capturing = False

    def list_devices(self) -> List[AudioDevice]:
        return self.device_manager.list_input_devices()

    def start_capture(
        self,
        device_id: Optional[str] = None,
        audio_format: Optional[AudioFormat] = None,
    ) -> None:
        if not self._arecord_path:
            raise ToolError("ALSA audio capture binary 'arecord' not found on system.")

        self._format = audio_format or AudioFormat()
        self._accumulated_data = bytearray()
        self._chunk_counter = 0

        cmd = [
            self._arecord_path,
            "-f", "S16_LE",
            "-r", str(self._format.sample_rate),
            "-c", str(self._format.channels),
            "-t", "raw",
            "-q",  # Quiet mode
        ]
        if device_id and device_id != "default":
            cmd.extend(["-D", device_id])

        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0,
            )
            self.is_capturing = True
            logger.info(f"Started ALSA recording with command: {' '.join(cmd)}")
        except Exception as e:
            self.is_capturing = False
            raise ToolError(f"Failed to spawn 'arecord' process: {e}")

    def read_chunk(self, chunk_size: int = 1024) -> Optional[AudioChunk]:
        if not self.is_capturing or not self._process or not self._process.stdout:
            return None

        # Check if process terminated with error
        if self._process.poll() is not None:
            stderr = self._process.stderr.read().decode(errors="replace") if self._process.stderr else ""
            self.is_capturing = False
            if stderr:
                logger.warning(f"arecord exited unexpectedly: {stderr.strip()}")
            return None

        try:
            # Read bytes_per_chunk (chunk_size samples * 2 bytes/sample)
            byte_count = chunk_size * 2
            raw_chunk = self._process.stdout.read(byte_count)
            if not raw_chunk:
                return None

            chunk = AudioChunk(
                chunk_id=self._chunk_counter,
                data=raw_chunk,
                timestamp=time.time(),
            )
            chunk.energy = chunk.calculate_rms()
            chunk.is_speech = chunk.energy > 300.0  # nominal threshold

            self._accumulated_data.extend(raw_chunk)
            self._chunk_counter += 1
            return chunk
        except Exception as e:
            logger.warning(f"Error reading audio chunk from arecord: {e}")
            return None

    def stop_capture(self) -> AudioData:
        self.is_capturing = False
        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=1.0)
            except Exception:
                try:
                    self._process.kill()
                except Exception:
                    pass
            self._process = None

        raw_bytes = bytes(self._accumulated_data)
        logger.info(f"Stopped ALSA recording. Accumulated {len(raw_bytes)} bytes.")
        return AudioData(data=raw_bytes, format=self._format)

    def is_available(self) -> bool:
        return self._arecord_path is not None and os.path.exists(self._arecord_path)


class LinuxAudioPlaybackProvider(AudioPlaybackProvider):
    """Real Linux audio playback using standard `aplay` or `paplay`."""

    def __init__(self, device_manager: Optional[AudioDeviceManager] = None) -> None:
        self.device_manager = device_manager or AudioDeviceManager()
        self._aplay_path = shutil.which("aplay")
        self._paplay_path = shutil.which("paplay")
        self._process: Optional[subprocess.Popen] = None
        self.is_playing = False

    def list_devices(self) -> List[AudioDevice]:
        return self.device_manager.list_output_devices()

    def play(self, audio: AudioData, device_id: Optional[str] = None) -> bool:
        bin_path = self._aplay_path or self._paplay_path
        if not bin_path:
            logger.warning("Neither 'aplay' nor 'paplay' found for audio playback.")
            return False

        if not audio.data:
            return True

        cmd = [bin_path]
        # If raw PCM rather than WAV container header, pass explicit format
        if not audio.data.startswith(b"RIFF"):
            cmd.extend([
                "-f", "S16_LE",
                "-r", str(audio.format.sample_rate),
                "-c", str(audio.format.channels),
                "-t", "raw",
            ])
        if device_id and device_id != "default" and bin_path == self._aplay_path:
            cmd.extend(["-D", device_id])

        try:
            self.is_playing = True
            self._process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            self._process.communicate(input=audio.data, timeout=max(5.0, audio.duration_seconds + 2.0))
            self.is_playing = False
            return True
        except subprocess.TimeoutExpired:
            self.stop()
            return False
        except Exception as e:
            self.is_playing = False
            logger.warning(f"Error during audio playback: {e}")
            return False

    def stop(self) -> None:
        self.is_playing = False
        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=1.0)
            except Exception:
                try:
                    self._process.kill()
                except Exception:
                    pass
            self._process = None

    def is_available(self) -> bool:
        return self._aplay_path is not None or self._paplay_path is not None
