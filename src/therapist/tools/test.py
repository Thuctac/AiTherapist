import torch
import torch.nn.functional as F
import librosa
import os

from transformers import WhisperProcessor, WhisperModel
from peft import PeftModel

# Your custom SER wrapper
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
            raise ValueError("Please pass `input_values` (audio features).")
        outputs = self.encoder(input_values, output_hidden_states=False)
        hidden = outputs.last_hidden_state        # (B, T, D)
        pooled = hidden.mean(dim=1)               # (B, D)
        pooled = self.dropout(pooled)
        return self.fc(pooled)                    # (B, num_labels)

# ---------- CONFIG ----------
OUTPUT_DIR = "/Users/thucnguyen/Documents/University/Semester5/BSP/AiTherapist/src/therapist/tools/fine_tuned_whisper-base"
assert os.path.isdir(OUTPUT_DIR), f"{OUTPUT_DIR} not found!"

# 1) Load base encoder
base = WhisperModel.from_pretrained("openai/whisper-base")

# 2) Wrap in your SER head (ensure num_labels matches what you trained with)
num_labels = 8
model = WhisperSERModel(encoder=base.encoder, num_labels=num_labels)

# 3) Attach your LoRA adapters from OUTPUT_DIR (local only)
model = PeftModel.from_pretrained(model, OUTPUT_DIR, local_files_only=True)
model.eval()

# 3b) **Inject your label map** (must match training)
labels = ['neutral', 'calm', 'happy', 'sad',
    'angry',
    'fear',
    'disgust',
    'surprise']
model.config.label2id = {label: i for i, label in enumerate(labels)}
model.config.id2label = {i: label for i, label in enumerate(labels)}

# 4) Load processor (feature-extractor + tokenizer)
processor = WhisperProcessor.from_pretrained(OUTPUT_DIR, local_files_only=True)

# 5) Read demo audio
audio, sr = librosa.load(
    "/Users/thucnguyen/Documents/University/Semester5/BSP/AiTherapist/src/therapist/tools/recording_1747175070.wav",
    sr=16000,       # target sampling rate
    mono=True       # ensure mono
)
assert sr == 16000, "Resample to 16 kHz!"

# 6) Create model inputs
inputs = processor(audio, sampling_rate=sr, return_tensors="pt")
input_values = inputs.input_features  # raw Whisper features

# 7) Forward → logits → softmax
with torch.no_grad():
    logits = model(input_values=input_values)
probs = F.softmax(logits, dim=-1)[0]  # (num_labels,)

# 8) Decode full distribution
label_probs = {
    model.config.id2label[i]: probs[i].item()
    for i in range(probs.shape[0])
}

print("Emotion distribution:")
for label, score in sorted(label_probs.items(), key=lambda kv: kv[1], reverse=True):
    print(f"  {label:8s}: {score*100:.1f}%")