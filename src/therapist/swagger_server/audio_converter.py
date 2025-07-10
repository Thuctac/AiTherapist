import uuid
import os
from pathlib import Path
from pydub import AudioSegment


def save_and_convert_audio(storage, directory: Path, target_ext: str = ".wav") -> str | None:
    """Save the uploaded file, convert it to target_ext (wav/mp3), and return the new path."""
    if storage is None:
        return None

    # Ensure the output directory exists
    directory.mkdir(parents=True, exist_ok=True)

    # 1) Save original upload as a temporary file
    suffix = Path(storage.filename).suffix or ""
    temp_name = f"{uuid.uuid4().hex}_temp{suffix}"
    temp_path = directory / temp_name
    storage.save(temp_path)

    # 2) Convert to desired format (let FFmpeg auto-detect the input!)
    final_name = f"{uuid.uuid4().hex}{target_ext}"
    final_path = directory / final_name

    # By not passing `format`, pydub/ffmpeg will probe the file for its true format
    audio = AudioSegment.from_file(temp_path)
    audio.export(final_path, format=target_ext.lstrip('.'))

    # 3) Clean up the temporary file
    try:
        os.remove(temp_path)
    except OSError:
        pass

    return str(final_path)
