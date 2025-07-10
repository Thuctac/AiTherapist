from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
import os
import soundfile as sf
import torch
import torch.nn.functional as F
from transformers import WhisperProcessor, WhisperModel
from peft import PeftModel
import json
import librosa
import logging
import time
from functools import lru_cache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(__file__)  
OUTPUT_DIR = os.path.join(BASE_DIR, "fine_tuned_whisper-base")
LABELS = ["neutral", "happy", "sad", "angry", "fearful", "disgust", "surprised", "calm"]

# Global model cache
_model = None
_processor = None

# Device selection with Docker optimization
if torch.cuda.is_available():
    device = torch.device("cuda")
    logger.info("Using CUDA device")
elif torch.backends.mps.is_available() and not os.environ.get('DOCKER_ENV'):
    # MPS might not work well in Docker
    device = torch.device("mps")
    logger.info("Using MPS device")
else:
    device = torch.device("cpu")
    # Optimize CPU usage
    torch.set_num_threads(int(os.environ.get('OMP_NUM_THREADS', '4')))
    logger.info(f"Using CPU device with {torch.get_num_threads()} threads")

class WhisperSERModel(torch.nn.Module):
    """Whisper-based Speech Emotion Recognition Model"""
    def __init__(self, encoder, num_labels):
        super().__init__()
        self.encoder = encoder
        self.config = encoder.config
        self.dropout = torch.nn.Dropout(0.1)
        hidden_size = encoder.config.d_model
        self.fc = torch.nn.Linear(hidden_size, num_labels)

    def forward(self, input_ids=None, input_values=None, **kwargs):
        if input_values is None:
            raise ValueError("Pass `input_values` (audio features).")
        outputs = self.encoder(input_values, output_hidden_states=False)
        hidden = outputs.last_hidden_state   # (B, T, D)
        pooled = hidden.mean(dim=1)          # (B, D)
        pooled = self.dropout(pooled)
        return self.fc(pooled)               # (B, num_labels)

@lru_cache(maxsize=1)
def load_ser_model(timeout=60):
    """Load SER model with timeout and caching"""
    global _model, _processor
    
    if _model is not None:
        return _model, _processor
    
    start_time = time.time()
    logger.info("Loading SER model...")
    
    try:
        # Load base Whisper with timeout check
        if time.time() - start_time > timeout * 0.3:
            raise TimeoutError("Model loading timeout")
            
        logger.info("Loading Whisper base model...")
        base = WhisperModel.from_pretrained(
            "openai/whisper-base",
            local_files_only=os.path.exists(os.path.expanduser("~/.cache/huggingface/hub/models--openai--whisper-base"))
        )
        num_labels = len(LABELS)

        # Create SER model
        ser = WhisperSERModel(encoder=base.encoder, num_labels=num_labels)
        
        # Check if LoRA weights exist
        if os.path.exists(OUTPUT_DIR):
            logger.info("Loading LoRA adapters...")
            if time.time() - start_time > timeout * 0.6:
                raise TimeoutError("Model loading timeout")
                
            try:
                ser = PeftModel.from_pretrained(ser, OUTPUT_DIR, local_files_only=True)
            except Exception as e:
                logger.warning(f"Failed to load LoRA adapters: {e}. Using base model.")
        else:
            logger.warning(f"LoRA weights not found at {OUTPUT_DIR}. Using base model.")

        # Fix for missing num_embeddings attribute
        embed_pos = ser.encoder.embed_positions
        if hasattr(embed_pos, 'weight') and not hasattr(embed_pos, 'num_embeddings'):
            embed_pos.num_embeddings = embed_pos.weight.shape[0]

        ser.eval()
        
        # Move to device with memory optimization
        if device.type == 'cpu':
            ser = ser.to(device)
        else:
            with torch.cuda.amp.autocast(enabled=False):
                ser = ser.to(device)

        # Inject id2label/label2id
        ser.config.id2label = {i: label for i, label in enumerate(LABELS)}
        ser.config.label2id = {label: i for i, label in enumerate(LABELS)}

        # Load processor
        logger.info("Loading Whisper processor...")
        if time.time() - start_time > timeout * 0.8:
            raise TimeoutError("Model loading timeout")
            
        if os.path.exists(OUTPUT_DIR):
            _processor = WhisperProcessor.from_pretrained(OUTPUT_DIR, local_files_only=True)
        else:
            _processor = WhisperProcessor.from_pretrained("openai/whisper-base")
        
        _model = ser
        
        elapsed = time.time() - start_time
        logger.info(f"Model loaded successfully in {elapsed:.2f} seconds")
        
        return _model, _processor
        
    except Exception as e:
        logger.error(f"Failed to load model: {str(e)}")
        raise

def detectEmotion(audio_file_path: str, timeout: int = 30) -> str:
    """Detect emotions with timeout and error handling"""
    start_time = time.time()
    
    try:
        # Load model
        model, processor = load_ser_model(timeout=timeout)
        
        # Check timeout
        if time.time() - start_time > timeout * 0.3:
            raise TimeoutError("Audio processing timeout")
        
        # Read and process audio
        logger.info(f"Processing audio file: {audio_file_path}")
        audio, sr = sf.read(audio_file_path)
        
        # Resample if needed
        if sr != 16000:
            logger.info(f"Resampling from {sr}Hz to 16000Hz")
            audio = librosa.resample(audio, orig_sr=sr, target_sr=16000)
            sr = 16000
        
        # Check timeout
        if time.time() - start_time > timeout * 0.6:
            raise TimeoutError("Audio processing timeout")
        
        # Preprocess
        inputs = processor(audio, sampling_rate=sr, return_tensors="pt")
        input_values = inputs.input_features.to(device)
        
        # Forward pass with mixed precision on GPU
        logger.info("Running inference...")
        with torch.no_grad():
            if device.type == 'cuda':
                with torch.cuda.amp.autocast():
                    logits = model(input_values=input_values)
            else:
                logits = model(input_values=input_values)
            
            probs = F.softmax(logits, dim=-1)[0].cpu()
        
        # Build result
        label_probs = {
            model.config.id2label[i]: round(probs[i].item() * 100, 1)
            for i in range(probs.shape[0])
        }
        
        elapsed = time.time() - start_time
        logger.info(f"Emotion detection completed in {elapsed:.2f} seconds")
        
        return json.dumps(label_probs)
        
    except TimeoutError:
        logger.error("Emotion detection timed out")
        # Return default distribution
        return json.dumps({label: 12.5 for label in LABELS})
    except Exception as e:
        logger.error(f"Error in emotion detection: {str(e)}")
        # Return default distribution
        return json.dumps({label: 12.5 for label in LABELS})

class MyCustomToolInput(BaseModel):
    """Input schema for VoiceEmotionDistributionTool."""
    audio_path: str = Field(..., description="Path to the audio file to analyze.")

class SERTool(BaseTool):
    name: str = "VoiceEmotionDistributionTool"
    description: str = (
        "Takes an audio_path and returns a full distribution of detected speech emotions as percentages in JSON format."
    )
    args_schema: Type[BaseModel] = MyCustomToolInput

    def _run(self, audio_path: str) -> str:
        # Use environment variable for timeout if available
        timeout = int(os.environ.get('SER_TIMEOUT', '30'))
        return detectEmotion(audio_file_path=audio_path, timeout=timeout)