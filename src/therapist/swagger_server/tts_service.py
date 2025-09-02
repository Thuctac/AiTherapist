import os
import re
import math
import time
import uuid
import traceback
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional, Tuple, Callable, List, Union, Dict
import hashlib
import json

try:
    from openai import OpenAI  # type: ignore
    _openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None
except Exception:
    _openai_client = None

import torch
import torchaudio
import soundfile as sf
from transformers import SpeechT5Processor, SpeechT5ForTextToSpeech, SpeechT5HifiGan


ENABLE_TTS = True
TTS_VOICE: List[str] = [f"swagger_server/voice_samples/arctic_a{str(i).zfill(4)}.wav" for i in range(1, 101)]
TTS_OUT_FORMAT = "mp3"  


DEFAULT_VOICE_REFS_ROOT = Path(__file__).parent / "voice_refs"


VOICE_EMB_CACHE_DIR = Path(__file__).parent / ".voice_emb_cache"
VOICE_EMB_CACHE_DIR.mkdir(exist_ok=True)
_SPK_EMB_CACHE: Dict[str, torch.Tensor] = {}




def is_tts_enabled() -> bool:
    """Check if TTS is enabled."""
    return ENABLE_TTS



def check_openai_quota() -> bool:
    """
    Legacy endpoint support: returns True if we can list models on OpenAI.
    This is NOT used by local SpeechT5 synthesis, but some routes call it.
    """
    try:
        if _openai_client is None:
            # If no client configured, just return True to avoid blocking local TTS.
            return True
        _openai_client.models.list()
        return True
    except Exception as e:
        msg = str(e).lower()
        if "quota" in msg or "rate_limit" in msg or "insufficient" in msg:
            print(f"[TTS] OpenAI quota check failed: {e}")
            return False
        # Other network/auth errors should not block local TTS
        print(f"[TTS] OpenAI check warning (ignoring): {e}")
        return True



@dataclass
class _EmbedBackend:
    name: str
    sample_rate: int
    embed_fn: Callable[[torch.Tensor], torch.Tensor]


@lru_cache(maxsize=1)
def _get_processor():
    return SpeechT5Processor.from_pretrained("microsoft/speecht5_tts")


@lru_cache(maxsize=1)
def _get_acoustic():
    return SpeechT5ForTextToSpeech.from_pretrained("microsoft/speecht5_tts")


@lru_cache(maxsize=1)
def _get_vocoder():
    return SpeechT5HifiGan.from_pretrained("microsoft/speecht5_hifigan")


@lru_cache(maxsize=1)
def _get_speaker_embedder_backend(require_real: bool, allow_random: bool) -> _EmbedBackend:
    superb = getattr(getattr(torchaudio, "pipelines", object()), "SUPERB_XVECTOR", None)
    if superb is not None:
        bundle = superb
        model = bundle.get_model().eval()

        def _embed_fn_superb(wav_mono: torch.Tensor) -> torch.Tensor:
            with torch.no_grad():
                seq, _ = model(wav_mono)
                emb = seq.mean(dim=1)
            return emb

        return _EmbedBackend("torchaudio:SUPERB_XVECTOR", bundle.sample_rate, _embed_fn_superb)

    try:
        from speechbrain.inference import EncoderClassifier
        ecapa = EncoderClassifier.from_hparams(source="speechbrain/spkrec-ecapa-voxceleb", run_opts={"device": "cpu"})

        def _embed_fn_ecapa(wav_mono: torch.Tensor) -> torch.Tensor:
            with torch.no_grad():
                emb = ecapa.encode_batch(wav_mono)
            emb = emb.squeeze(0)
            if emb.shape[1] < 512:
                pad = torch.zeros((1, 512 - emb.shape[1]), dtype=emb.dtype)
                emb = torch.cat([emb, pad], dim=1)
            else:
                emb = emb[:, :512]
            return emb

        return _EmbedBackend("speechbrain:ECAPA", 16000, _embed_fn_ecapa)
    except Exception as e:
        if allow_random and not require_real:
            def _embed_fn_rand(_: torch.Tensor) -> torch.Tensor:
                return torch.randn(1, 512)
            return _EmbedBackend("random:seeded", 16000, _embed_fn_rand)
        raise RuntimeError("No speaker embedding backend available.") from e



def _rms_norm(wav: torch.Tensor, target_rms: float = 0.05, eps: float = 1e-8) -> torch.Tensor:
    rms = torch.sqrt(torch.mean(wav**2) + eps)
    gain = target_rms / max(rms, eps)
    return torch.clamp(wav * gain, -1.0, 1.0)


def _trim_silence(wav: torch.Tensor, sr: int, top_db: float = 32.0) -> torch.Tensor:
    amp = wav.abs()
    dbfs = 20 * torch.log10(torch.clamp(amp + 1e-8, 1e-8))
    mask = dbfs > (-top_db)
    if not mask.any():
        return wav
    idx = torch.where(mask[0])[0]
    start, end = idx.min().item(), idx.max().item()
    return wav[:, start:end + 1]


def _apply_vad(wav: torch.Tensor, sr: int, frame_ms: int = 30) -> torch.Tensor:
    frame_len = int(sr * frame_ms / 1000)
    if frame_len < 1:
        return wav
    frames = wav.unfold(dimension=1, size=frame_len, step=frame_len)
    rms = torch.sqrt((frames ** 2).mean(dim=2) + 1e-8)
    thr = rms.median() * 0.8
    keep = (rms > thr)[0]
    kept = frames[0, keep]
    if kept.numel() == 0:
        return wav
    return kept.flatten().unsqueeze(0)


def _crop_duration(wav: torch.Tensor, sr: int, min_sec: float, max_sec: float) -> torch.Tensor:
    T = wav.shape[1]
    min_len = int(min_sec * sr)
    max_len = int(max_sec * sr)
    if T < min_len:
        reps = math.ceil(min_len / max(T, 1))
        wav = wav.repeat(1, reps)
    if wav.shape[1] > max_len:
        wav = wav[:, :max_len]
    return wav


def _preprocess_reference(wav: torch.Tensor, sr: int, target_sr: int, min_ref_sec: float, max_ref_sec: float, log_debug: bool) -> torch.Tensor:
    if sr != target_sr:
        wav = torchaudio.functional.resample(wav, sr, target_sr)
        sr = target_sr
    wav = _trim_silence(wav, sr)
    wav = _apply_vad(wav, sr)
    wav = _rms_norm(wav)
    wav = _crop_duration(wav, sr, min_ref_sec, max_ref_sec)
    if log_debug:
        dur = wav.shape[1] / sr
        print(f"[REF] duration after preprocess: {dur:.2f}s @ {sr} Hz")
    return wav


def _segment_for_embedding(wav: torch.Tensor, sr: int, seg_sec: float = 2.0, hop_sec: float = 1.0, max_chunks: int = 6) -> List[torch.Tensor]:
    seg = int(seg_sec * sr)
    hop = int(hop_sec * sr)
    T = wav.shape[1]
    starts = list(range(0, max(T - seg, 1), hop))
    chunks: List[torch.Tensor] = []
    for s in starts[: 3 * max_chunks]:
        e = s + seg
        if e > T:
            break
        ch = wav[:, s:e]
        if ch.abs().mean() < 1e-3:
            continue
        chunks.append(ch)
        if len(chunks) >= max_chunks:
            break
    if not chunks:
        chunks = [wav[:, :min(seg, T)]]
    return chunks


def _male_tone(wav: torch.Tensor, sr: int, treble_cut_db: float, presence_cut_db: float, body_boost_db: float) -> torch.Tensor:
    mono = wav.unsqueeze(0) if wav.dim() == 1 else wav
    y = mono
    y = torchaudio.functional.equalizer_biquad(y, sr, center_freq=4000.0, gain=-abs(treble_cut_db), Q=0.8)
    y = torchaudio.functional.equalizer_biquad(y, sr, center_freq=2500.0, gain=-abs(presence_cut_db), Q=0.9)
    y = torchaudio.functional.equalizer_biquad(y, sr, center_freq=180.0, gain=abs(body_boost_db), Q=0.7)
    y = torch.tanh(1.1 * y)
    return y.squeeze(0) if wav.dim() == 1 else y


def _log_embed_stats(emb: torch.Tensor, backend_name: str, sr: int, wav: Optional[torch.Tensor]) -> None:
    mean = emb.mean().item()
    std = emb.std().item()
    norm = torch.linalg.vector_norm(emb).item()
    print(f"[EMBED] backend={backend_name} | mean={mean:.4f} std={std:.4f} ||emb||={norm:.3f}")



def _voice_files_signature(paths: List[str]) -> str:
    """Hash of (absolute path, size, mtime) to detect changes."""
    uniq_paths = sorted({str(Path(x).expanduser().resolve()) for x in paths if x})

    sig_items = []
    for p in uniq_paths:
        try:
            st = os.stat(p)
            sig_items.append([p, int(st.st_size), int(st.st_mtime)])
        except FileNotFoundError:
            sig_items.append([p, 0, 0])
        except Exception:
            sig_items.append([p, 0, 0])

    blob = json.dumps(sig_items, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()


def _cache_key_for_embedding(paths: List[str], backend_name: str,
                             min_ref_sec: float, max_ref_sec: float) -> str:
    files_sig = _voice_files_signature(paths)
    meta = f"{backend_name}|{min_ref_sec:.2f}|{max_ref_sec:.2f}|{files_sig}"
    return hashlib.sha1(meta.encode("utf-8")).hexdigest()


def _disk_cache_path(key: str) -> Path:
    return VOICE_EMB_CACHE_DIR / f"{key}.pt"


def _load_emb_from_disk(key: str) -> Optional[torch.Tensor]:
    fp = _disk_cache_path(key)
    if fp.exists():
        try:
            return torch.load(fp, map_location="cpu")
        except Exception as e:
            print(f"[TTS] Failed loading cached embedding {fp}: {e}")
    return None


def _save_emb_to_disk(key: str, emb: torch.Tensor) -> None:
    fp = _disk_cache_path(key)
    try:
        torch.save(emb.detach().cpu(), fp)
    except Exception as e:
        print(f"[TTS] Failed saving cached embedding {fp}: {e}")


def _get_cached_speaker_embedding(
    ref_wavs: List[str],
    emb_backend: _EmbedBackend,
    *,
    min_ref_sec: float,
    max_ref_sec: float,
    require_real: bool,
    allow_random: bool,
    random_seed: int,
    log_debug: bool,
) -> torch.Tensor:
    
    if not ref_wavs:
        if not require_real and allow_random:
            torch.manual_seed(random_seed)
            if log_debug:
                print("[TTS] Using random speaker embedding (no refs).")
            return torch.randn(1, 512)
        raise RuntimeError("No reference wavs provided and random fallback disabled.")

    key = _cache_key_for_embedding(ref_wavs, emb_backend.name, min_ref_sec, max_ref_sec)


    if key in _SPK_EMB_CACHE:
        if log_debug:
            print("[TTS] Speaker embedding hit (memory cache).")
        return _SPK_EMB_CACHE[key].clone()


    emb_disk = _load_emb_from_disk(key)
    if emb_disk is not None:
        if log_debug:
            print(f"[TTS] Speaker embedding hit (disk cache: {_disk_cache_path(key).name}).")
        _SPK_EMB_CACHE[key] = emb_disk
        return emb_disk.clone()


    all_embs: List[torch.Tensor] = []
    for wav_path in ref_wavs:
        if not wav_path:
            continue
        try:
            wav, sr = torchaudio.load(wav_path)
        except Exception as e:
            print(f"[TTS] Skipping ref '{wav_path}': {e}")
            continue
        if wav.numel() == 0:
            continue
        if wav.shape[0] > 1:
            wav = wav.mean(dim=0, keepdim=True)
        if sr != emb_backend.sample_rate:
            wav = torchaudio.functional.resample(wav, sr, emb_backend.sample_rate)
            sr = emb_backend.sample_rate

        wav = _preprocess_reference(
            wav, sr, target_sr=emb_backend.sample_rate,
            min_ref_sec=min_ref_sec, max_ref_sec=max_ref_sec,
            log_debug=log_debug,
        )

        chunks = _segment_for_embedding(wav, emb_backend.sample_rate)
        for ch in chunks:
            try:
                e = emb_backend.embed_fn(ch)
                all_embs.append(e)
            except Exception as ee:
                print(f"[TTS] Embed chunk failed for '{wav_path}': {ee}")

    if not all_embs:
        if not require_real and allow_random:
            torch.manual_seed(random_seed)
            if log_debug:
                print("[TTS] Using random speaker embedding (no valid chunks).")
            spk_emb = torch.randn(1, 512)
        else:
            raise RuntimeError("No valid embeddings extracted from reference wavs.")
    else:
        spk_emb = torch.stack(all_embs, dim=0).mean(dim=0)  # [1, 512]

    spk_emb = torch.nn.functional.normalize(spk_emb, dim=1)

    _SPK_EMB_CACHE[key] = spk_emb.detach().cpu()
    _save_emb_to_disk(key, spk_emb)

    if log_debug:
        _log_embed_stats(spk_emb, backend_name=emb_backend.name, sr=emb_backend.sample_rate, wav=None)
        print(f"[TTS] Speaker embedding cached under key {key[:8]}…")

    return spk_emb



def _normalize_text_quick(s: str) -> str:
    s = re.sub(r'\s+', ' ', s.strip())
    s = s.replace(" - ", " — ")
    if not re.search(r'[\.!\?]\s*$', s):
        s += "."
    return s


def _chunk_text_by_tokens(text: str, processor: SpeechT5Processor, max_tokens: int = 280) -> List[str]:
    """
    Split text into chunks whose tokenized length stays ~<=280.
    This keeps prosody stable while remaining well below the ~600 cap.
    """
    if not text or not text.strip():
        return []
    # Prefer splitting at sentence boundaries or paragraph gaps; keep punctuation
    raw = re.split(r'(?<=[\.\!\?\:])\s+|\n{2,}', text.strip())
    pieces = [p.strip() for p in raw if p and p.strip()]

    chunks: List[str] = []
    cur_parts: List[str] = []
    cur_tokens = 0
    tok = processor.tokenizer

    for p in pieces:
        tlen = len(tok(p, add_special_tokens=False).input_ids)
        if cur_parts and cur_tokens + tlen + 1 > max_tokens:
            chunks.append(" ".join(cur_parts))
            cur_parts = [p]
            cur_tokens = tlen
        else:
            cur_parts.append(p)
            cur_tokens += tlen + (1 if cur_tokens > 0 else 0)
    if cur_parts:
        chunks.append(" ".join(cur_parts))

    # Fallback: hard-wrap by tokens if text had no punctuation at all
    if not chunks:
        ids = tok(text, add_special_tokens=False).input_ids
        start = 0
        while start < len(ids):
            end = min(start + max_tokens, len(ids))
            sub = tok.decode(ids[start:end], skip_special_tokens=True)
            chunks.append(sub)
            start = end
    return chunks


def _concat_with_pauses(waves: List[torch.Tensor], sr: int, pause_ms: int = 120, edge_fade_ms: int = 6) -> torch.Tensor:
    """
    Concatenate chunks with a short silence gap and tiny edge tapers to avoid clicks.
    This preserves intelligibility much better than long crossfades.
    """
    if not waves:
        return torch.zeros(1)
    pause = torch.zeros(max(1, int(sr * pause_ms / 1000)))
    out = []

    for i, w in enumerate(waves):
        w = w.detach().cpu().view(-1)
        if edge_fade_ms > 0 and w.numel() > 8:
            L = min(int(sr * edge_fade_ms / 1000), w.numel() // 8)
            if L > 0:
                ramp = torch.linspace(0.0, 1.0, steps=L)
                w[:L] *= ramp
                w[-L:] *= torch.flip(ramp, dims=[0])
        out.append(w)
        if i != len(waves) - 1:
            out.append(pause)

    return torch.cat(out) if out else torch.zeros(1)


def _match_rms(w: torch.Tensor, target_rms: float = 0.045, eps: float = 1e-8) -> torch.Tensor:
    rms = torch.sqrt((w**2).mean() + eps)
    if rms < eps:
        return w
    return torch.clamp(w * (target_rms / rms), -1.0, 1.0)


# (legacy) kept for reference; not used in the main path anymore
def _concat_with_crossfade(waves: List[torch.Tensor], sr: int, fade_ms: int = 15) -> torch.Tensor:
    """Linearly crossfade-concatenate 1D CPU tensors to avoid clicks (legacy)."""
    if not waves:
        return torch.zeros(1)
    out = waves[0].detach().cpu().view(-1).clone()
    fade = max(1, int(sr * fade_ms / 1000))
    for w in waves[1:]:
        b = w.detach().cpu().view(-1)
        a = out.view(-1)
        L = min(fade, a.numel(), b.numel())
        if L > 0:
            fade_out = torch.linspace(1.0, 0.0, steps=L)
            fade_in  = torch.linspace(0.0, 1.0, steps=L)
            cross = a[-L:] * fade_out + b[:L] * fade_in
            out = torch.cat([a[:-L], cross, b[L:]], dim=0)
        else:
            out = torch.cat([a, b], dim=0)
    return out



def tts_speecht5_hifigan(
    text: str,
    voice_ref_wavs: Union[str, List[str]],  # accept one or many
    out_path: str,
    device: Optional[str] = None,
    normalize_spk: bool = True,
    require_real_embed: bool = True,
    allow_random_fallback: bool = True,
    random_seed: int = 0,
    pitch_shift_steps: float = 0.0,
    min_ref_sec: float = 5.0,
    max_ref_sec: float = 20.0,
    log_debug: bool = True,
    male_timbre_tweak: bool = True,
    treble_cut_db: float = 6.0,
    presence_cut_db: float = 3.0,
    body_boost_db: float = 2.5,
) -> Tuple[str, int]:
    """
    Text-to-Speech (SpeechT5 + HiFi-GAN) with multiple reference support.
    - Accepts one or many reference files (list of paths).
    - Averages embeddings across all files and speech chunks.
    - Optional pitch shift + EQ tweaks for darker/more male timbre.
    - Splits long text into ~280-token chunks to avoid crash/drift.
    """
    if device is None:
        device = (
            "cuda" if torch.cuda.is_available() else
            ("mps" if torch.backends.mps.is_available() else "cpu")
        )

    processor = _get_processor()
    acoustic = _get_acoustic().to(device).eval()
    vocoder = _get_vocoder().to(device).eval()

    # Use vocoder's configured sample rate (avoid hardcoding 16k)
    sr_out = int(getattr(getattr(vocoder, "config", None), "sampling_rate", 16000))

    emb_backend = _get_speaker_embedder_backend(require_real=require_real_embed,
                                                allow_random=allow_random_fallback)

    # resolve refs via cache-aware path
    if isinstance(voice_ref_wavs, str):
        voice_ref_wavs = [voice_ref_wavs]

    spk_emb = _get_cached_speaker_embedding(
        ref_wavs=voice_ref_wavs,
        emb_backend=emb_backend,
        min_ref_sec=min_ref_sec,
        max_ref_sec=max_ref_sec,
        require_real=require_real_embed,
        allow_random=allow_random_fallback,
        random_seed=random_seed,
        log_debug=log_debug,
    ).to(device)

    if normalize_spk:
        spk_emb = torch.nn.functional.normalize(spk_emb, dim=1)

    if log_debug:
        _log_embed_stats(spk_emb, backend_name=emb_backend.name, sr=emb_backend.sample_rate, wav=None)

    # --- Normalize & chunk text ---
    text = _normalize_text_quick(text)
    chunks = _chunk_text_by_tokens(text, processor, max_tokens=280)
    if log_debug and len(chunks) > 1:
        print(f"[TTS] Long text split into {len(chunks)} chunks (<=280 tokens each).")

    # Optional: tone down FX automatically for very long inputs
    joined_len = sum(len(c) for c in chunks)
    if joined_len > 800:
        # Disable by default for long-form; you can override by passing flags from routes
        pitch_shift_steps = 0.0
        male_timbre_tweak = False
        if log_debug:
            print("[TTS] Long-form detected → disabling pitch shift & timbre tweak for cleanliness.")

    chunk_wavs: List[torch.Tensor] = []

    for i, chunk in enumerate(chunks if chunks else [text], 1):
        # Safety: truncation guard if a single sentence still overflows
        inputs = processor(text=chunk, return_tensors="pt").to(device)
        if inputs["input_ids"].shape[1] > 600:
            if log_debug:
                print(f"[TTS] Truncating chunk {i} from {inputs['input_ids'].shape[1]} to 600 tokens.")
            inputs = processor(text=chunk, return_tensors="pt", max_length=600, truncation=True).to(device)

        # Try to include attention_mask if supported
        gen_kwargs = {}
        if hasattr(processor, "model_input_names") and "attention_mask" in getattr(processor, "model_input_names", []):
            if "attention_mask" in inputs:
                gen_kwargs["attention_mask"] = inputs["attention_mask"]

        with torch.inference_mode():
            try:
                wav = acoustic.generate_speech(
                    inputs["input_ids"],
                    speaker_embeddings=spk_emb,
                    vocoder=vocoder,
                    **gen_kwargs,
                )
            except TypeError:
                # Older transformers without attention_mask support
                wav = acoustic.generate_speech(
                    inputs["input_ids"],
                    speaker_embeddings=spk_emb,
                    vocoder=vocoder,
                )

        if wav.dim() > 1:
            wav = wav.squeeze(0)

        # Level-match each chunk to avoid loudness swings
        wav = _match_rms(wav, target_rms=0.045)
        chunk_wavs.append(wav.detach().cpu())

    # Concatenate all chunks with short pauses to avoid phoneme smearing
    waveform = _concat_with_pauses(chunk_wavs, sr=sr_out, pause_ms=120, edge_fade_ms=6)

    # Optional timbre/pitch post-processing (consider disabled for long text)
    if abs(pitch_shift_steps) > 1e-6:
        w = waveform.unsqueeze(0) if waveform.dim() == 1 else waveform
        ps = torchaudio.transforms.PitchShift(sample_rate=sr_out, n_steps=pitch_shift_steps)
        waveform = ps(w).squeeze(0)
    if male_timbre_tweak:
        waveform = _male_tone(waveform, sr_out, treble_cut_db, presence_cut_db, body_boost_db)

    sf.write(out_path, waveform.detach().cpu().numpy(), sr_out)
    return out_path, sr_out


# ---------------------- Public API used by routes ----------------------

def _resolve_ref_wavs(voice: Union[str, List[str]]) -> List[str]:
    # If the caller passes explicit file list, just use it
    if isinstance(voice, list):
        return [str(p) for p in voice if str(p).strip()]

    # 1) Explicit comma-separated list via env
    env_list = os.getenv("TTS_REF_WAVS")
    if env_list:
        return [p.strip() for p in env_list.split(",") if p.strip()]

    # 2) Explicit directory via env
    ref_dir = os.getenv("TTS_REF_DIR")
    if ref_dir and Path(ref_dir).exists():
        return sorted(str(p) for p in Path(ref_dir).glob("*.wav"))

    # 3) Default voice directory
    candidate_dir = DEFAULT_VOICE_REFS_ROOT / voice
    if candidate_dir.exists():
        return sorted(str(p) for p in candidate_dir.glob("*.wav"))

    # 4) Fallback: any wavs in default root
    if DEFAULT_VOICE_REFS_ROOT.exists():
        any_wavs = sorted(str(p) for p in DEFAULT_VOICE_REFS_ROOT.glob("*.wav"))
        if any_wavs:
            return any_wavs

    return []


def generate_tts_audio_safe(
    text: str,
    output_dir: Path,
    voice: Optional[Union[str, List[str]]] = None,
) -> Optional[str]:
    """
    Generate text-to-speech audio using local SpeechT5 pipeline, wrapped with robust error handling.
    Returns the path to the generated audio file (wav or mp3), or None on failure.
    """
    if not text or not text.strip():
        print("[TTS] No text provided for TTS generation")
        return None

    if voice is None:
        voice = TTS_VOICE

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Determine output extension/format
    ext = ".mp3" if TTS_OUT_FORMAT.lower() == "mp3" else ".wav"
    out_path = output_dir / f"{uuid.uuid4().hex}{ext}"

    # Resolve reference wavs
    ref_wavs = _resolve_ref_wavs(voice)
    require_real = True
    allow_rand = True
    if not ref_wavs:
        print("[TTS] No reference wavs found. Falling back to random embedding (voice cloning disabled).")
        require_real = False

    # If mp3 requested, synthesize wav first and convert via torchaudio if available
    tmp_wav_path = out_path.with_suffix(".wav") if ext == ".mp3" else out_path

    try:
        path, sr = tts_speecht5_hifigan(
            text=text,
            voice_ref_wavs=ref_wavs if ref_wavs else ["_dummy"],
            out_path=str(tmp_wav_path),
            require_real_embed=require_real,
            allow_random_fallback=allow_rand,
            pitch_shift_steps=-1.0,  # slightly lower pitch for a calmer tone; auto-disabled on long text
            log_debug=True,
        )
        # Convert to mp3 if requested
        if ext == ".mp3":
            try:
                wav, sr = torchaudio.load(path)
                torchaudio.save(str(out_path), wav, sr, format="mp3")
                try:
                    Path(path).unlink(missing_ok=True)
                except Exception:
                    pass
            except Exception as ce:
                print(f"[TTS] MP3 conversion failed ({ce}), keeping WAV instead.")
                out_path = Path(path)
        else:
            out_path = Path(path)

        return str(out_path)

    except Exception as e:
        print(f"[TTS] Error generating TTS: {e}")
        traceback.print_exc()
        return None


def generate_therapy_tts_safe(
    text: str,
    output_dir: Path,
    voice: Optional[Union[str, List[str]]] = None,
) -> Optional[str]:
    """
    Compatibility wrapper used by routes.
    """
    if not is_tts_enabled():
        print("[TTS] Disabled via ENABLE_TTS")
        return None
    return generate_tts_audio_safe(text, output_dir, voice=voice or TTS_VOICE)


def cleanup_old_tts_files(directory: Path, max_age_hours: int = 24) -> int:
    """
    Delete audio files in 'directory' older than max_age_hours.
    Returns the count of deleted files.
    """
    directory = Path(directory)
    if not directory.exists():
        return 0
    cutoff = time.time() - max_age_hours * 3600
    deleted = 0
    for p in directory.glob("*.*"):
        try:
            if p.is_file() and p.stat().st_mtime < cutoff:
                p.unlink()
                deleted += 1
        except Exception as e:
            print(f"[TTS] Cleanup warning: failed to delete {p}: {e}")
    if deleted:
        print(f"[TTS] Cleaned up {deleted} old TTS files from {directory}")
    return deleted


def generate_fallback_tts_html(text: str) -> str:
    """
    Very small HTML fallback that shows text if audio cannot be generated.
    """
    safe = (text or "").replace("<", "&lt;").replace(">", "&gt;")
    return f"<div class='tts-fallback'><p>{safe}</p></div>"


# --------------- Optional: pre-warm the embedding cache ----------------

def warm_speaker_embedding_cache(voice: Optional[Union[str, List[str]]] = None) -> None:
    """
    Precompute and cache the averaged speaker embedding for faster first TTS call.
    """
    try:
        final_voice = voice if voice is not None else TTS_VOICE
        ref_wavs = _resolve_ref_wavs(final_voice)
        backend = _get_speaker_embedder_backend(require_real=True, allow_random=True)
        _ = _get_cached_speaker_embedding(
            ref_wavs=ref_wavs,
            emb_backend=backend,
            min_ref_sec=5.0,
            max_ref_sec=20.0,
            require_real=True,
            allow_random=True,
            random_seed=0,
            log_debug=True,
        )
    except Exception as e:
        print(f"[TTS] Warm cache failed: {e}")


# ------------------------------ Self test ------------------------------

def test_tts_with_quota_check() -> bool:
    """
    Simple self-test: (1) check OpenAI (non-blocking), (2) try a local synth.
    """
    try:
        _ = check_openai_quota()
        # Optional: warm_speaker_embedding_cache()
        test_text = "This is a local SpeechT5 voice test."
        test_dir = Path("/tmp/tts_test")
        test_dir.mkdir(parents=True, exist_ok=True)
        result = generate_tts_audio_safe(test_text, test_dir)
        if result:
            print(f"✅ TTS test successful! Audio saved to: {result}")
            return True
        else:
            print("❌ TTS test failed!")
            return False
    except Exception as e:
        print(f"[TTS] Self-test error: {e}")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print(generate_therapy_tts_safe(bot_reply := "It's understandable that you're feeling anxious about finding affordable housing in Mannheim before your first day of university. You've got a big week ahead, and it's natural to feel stressed when facing uncertainty like this. Remember, many students secure housing after term starts through campus services or temporary arrangements. Here are some practical steps you can take today: 1) Reach out to the university's housing office for any available options or advice on local listings; 2) Explore online platforms and social media groups for roommates or sublets in your budget range; 3) Consider short-term solutions like staying with a friend, using campus facilities, or booking a temporary place until something more permanent becomes available. Keep in mind that it's okay if this process takes a few days – you're doing the best you can, and progress is what matters most.", tts_dir := Path("/tmp/tts_test")))
