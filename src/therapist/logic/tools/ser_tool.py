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

BASE_DIR = os.path.dirname(__file__)  

OUTPUT_DIR = os.path.join(BASE_DIR, "fine_tuned_whisper-base")


LABELS = ["neutral", "happy", "sad", "angry", "fearful", "disgust", "surprised", "calm"]


_model = None
_processor = None

if torch.cuda.is_available():
    device = torch.device("cuda")
elif torch.backends.mps.is_available():
    device = torch.device("mps")
else:
    device = torch.device("cpu")

def _load_ser_model():
    global _model, _processor
    if _model is None:
        base = WhisperModel.from_pretrained("openai/whisper-base")
        num_labels = len(LABELS)
        class WhisperSERModel(torch.nn.Module):
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

        ser = WhisperSERModel(encoder=base.encoder, num_labels=num_labels)

        # 3) attach LoRA adapters
        ser = PeftModel.from_pretrained(ser, OUTPUT_DIR, local_files_only=True)
        ser.eval()
        # move model to selected device
        ser.to(device)

        # 4) inject id2label/label2id
        ser.config.id2label = {i: label for i, label in enumerate(LABELS)}
        ser.config.label2id = {label: i for i, label in enumerate(LABELS)}

        # 5) load processor
        _processor = WhisperProcessor.from_pretrained(OUTPUT_DIR, local_files_only=True)
        _model = ser

    return _model, _processor

def detectEmotion(audio_file_path: str) -> str:
    model, processor = _load_ser_model()

    # read audio  
    audio, sr = sf.read(audio_file_path)
    if sr != 16000:
        audio = librosa.resample(audio, orig_sr=sr, target_sr=16000)
        sr = 16000

    # preprocess
    inputs = processor(audio, sampling_rate=sr, return_tensors="pt")
    # move inputs to the same device as the model
    input_values = inputs.input_features.to(device)

    # forward + softmax
    with torch.no_grad():
        logits = model(input_values=input_values)
        probs = torch.nn.functional.softmax(logits, dim=-1)[0].cpu()

    # build full distribution
    label_probs = {
        model.config.id2label[i]: round(probs[i].item() * 100, 1)
        for i in range(probs.shape[0])
    }

    return json.dumps(label_probs)

class MyCustomToolInput(BaseModel):
    """Input schema for SERTool."""
    audio_path: str = Field(..., description="Path to the audio file to analyze.")

class SERTool(BaseTool):
    name: str = "VoiceEmotionDistributionTool"
    description: str = (
        "Takes an audio_path and returns a full distribution of detected speech emotions as percentages in JSON format."
    )
    args_schema: Type[BaseModel] = MyCustomToolInput

    def _run(self, audio_path: str) -> str:
        return detectEmotion(audio_file_path=audio_path)
