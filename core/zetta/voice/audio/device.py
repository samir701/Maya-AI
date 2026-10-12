"""Audio Device Discovery and Hardware Management."""

import re
import shutil
import subprocess
from typing import List
from core.zetta.utils.logging import get_logger
from core.zetta.voice.models.audio import AudioDevice

logger = get_logger("audio_device_manager")


class AudioDeviceManager:
    """Discovers and inspects host physical and virtual audio devices."""

    def __init__(self) -> None:
        self._arecord_path = shutil.which("arecord")
        self._aplay_path = shutil.which("aplay")
        self._pactl_path = shutil.which("pactl")

    def list_input_devices(self) -> List[AudioDevice]:
        """Discover audio capture (microphone) devices."""
        devices: List[AudioDevice] = []

        if self._arecord_path:
            try:
                result = subprocess.run(
                    [self._arecord_path, "-l"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=3.0,
                )
                if result.returncode == 0:
                    devices.extend(self._parse_alsa_devices(result.stdout, is_input=True))
            except Exception as e:
                logger.debug(f"Error executing arecord -l: {e}")

        # If no ALSA hardware found or default needed, provide fallback default
        if not devices:
            devices.append(
                AudioDevice(
                    id="default",
                    name="Default System Microphone",
                    is_input=True,
                    is_output=False,
                    is_default=True,
                    backend="alsa" if self._arecord_path else "system",
                )
            )
        else:
            # Mark first device as default if none marked
            if not any(d.is_default for d in devices):
                devices[0].is_default = True

        return devices

    def list_output_devices(self) -> List[AudioDevice]:
        """Discover audio playback (speaker/headphone) devices."""
        devices: List[AudioDevice] = []

        if self._aplay_path:
            try:
                result = subprocess.run(
                    [self._aplay_path, "-l"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=3.0,
                )
                if result.returncode == 0:
                    devices.extend(self._parse_alsa_devices(result.stdout, is_input=False))
            except Exception as e:
                logger.debug(f"Error executing aplay -l: {e}")

        if not devices:
            devices.append(
                AudioDevice(
                    id="default",
                    name="Default System Speaker",
                    is_input=False,
                    is_output=True,
                    is_default=True,
                    backend="alsa" if self._aplay_path else "system",
                )
            )
        else:
            if not any(d.is_default for d in devices):
                devices[0].is_default = True

        return devices

    def _parse_alsa_devices(self, output: str, is_input: bool) -> List[AudioDevice]:
        """Parse `arecord -l` or `aplay -l` output into AudioDevice objects."""
        devices: List[AudioDevice] = []
        # Pattern e.g.: card 2: Generic_1 [HD-Audio Generic], device 0: ALC256 Analog [ALC256 Analog]
        pattern = re.compile(
            r"card\s+(\d+):\s*([^,\[]+)(?:\[([^\]]+)\])?,\s*device\s+(\d+):\s*([^\[]+)(?:\[([^\]]+)\])?",
            re.IGNORECASE,
        )

        for line in output.splitlines():
            line = line.strip()
            match = pattern.search(line)
            if match:
                card_idx = int(match.group(1))
                card_name = (match.group(3) or match.group(2)).strip()
                dev_idx = int(match.group(4))
                dev_name = (match.group(6) or match.group(5)).strip()

                device_id = f"hw:{card_idx},{dev_idx}"
                full_name = f"{card_name} - {dev_name}"

                devices.append(
                    AudioDevice(
                        id=device_id,
                        name=full_name,
                        card_index=card_idx,
                        device_index=dev_idx,
                        is_input=is_input,
                        is_output=not is_input,
                        backend="alsa",
                    )
                )

        return devices
