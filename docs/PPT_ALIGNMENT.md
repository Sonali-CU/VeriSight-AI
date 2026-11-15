# Alignment with supplied presentation

The dataset roles, 70/15/15 group-safe split, model candidates, feature ideas, evaluation metrics and human-review framing are transcribed from the supplied *Deepfake Detection for Cybersecurity* presentation.

Dataset plan:
- Train/validation: FaceForensics++ c23/c40, DFDC subset, ASVspoof 2019 LA, WaveFake.
- Cross-dataset / in-the-wild tests: Celeb-DF v2, Deepfake-Eval-2024, In-the-Wild audio dataset.

Model plan:
- EfficientNet-B0 or Xception on face crops; average scores across frames.
- ViT / TimeSformer / Video Swin for temporal patterns.
- XGBoost on documented handcrafted blink, lip-sync and spectral features.
- Mel-spectrogram + ResNet compared with fine-tuned Wav2Vec2.
- Weighted or logistic-regression late fusion.

Preprocessing ideas from presentation:
- Sample video at 5–10 fps.
- Face crops with MediaPipe / RetinaFace.
- Audio resampling to 16 kHz mono with ffmpeg.
- EAR/blink, lip motion, optical flow, FFT/DCT artifacts, MFCC and lip-sync.

The ZIP provides a scaffold and staged notebooks; it does not claim all these components are implemented.
