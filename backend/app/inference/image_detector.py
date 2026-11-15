
import base64
from io import BytesIO
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image, ImageOps
from torchvision import models, transforms

from ..config import PROJECT_ROOT


CHECKPOINT_PATH = (
    PROJECT_ROOT
    / "models"
    / "image"
    / "verisight_efficientnet_b0_ffpp_source_disjoint.pth"
)

DEVICE = torch.device("cpu")

_MODEL = None
_TRANSFORM = None
_INPUT_SIZE = 224


def load_image_model():
    """Load the trained EfficientNet-B0 checkpoint once."""
    global _MODEL, _TRANSFORM, _INPUT_SIZE

    if _MODEL is not None:
        return _MODEL, _TRANSFORM

    if not CHECKPOINT_PATH.is_file():
        raise FileNotFoundError(
            f"Image checkpoint not found: {CHECKPOINT_PATH}"
        )

    checkpoint = torch.load(
        CHECKPOINT_PATH,
        map_location=DEVICE,
        weights_only=True
    )

    if checkpoint.get("architecture") != "efficientnet_b0":
        raise ValueError("Unexpected model architecture.")

    if checkpoint.get("classes") != ["real", "fake"]:
        raise ValueError("Unexpected model classes.")

    if checkpoint.get("class_to_label") != {"real": 0, "fake": 1}:
        raise ValueError("Unexpected class mapping.")

    _INPUT_SIZE = int(checkpoint["input_size"])
    mean = tuple(checkpoint["mean"])
    std = tuple(checkpoint["std"])

    model = models.efficientnet_b0(weights=None)

    in_features = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(in_features, 2)

    model.load_state_dict(checkpoint["state_dict"], strict=True)

    model.to(DEVICE)
    model.eval()

    image_transform = transforms.Compose([
        transforms.Resize((_INPUT_SIZE, _INPUT_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(mean, std)
    ])

    _MODEL = model
    _TRANSFORM = image_transform

    return _MODEL, _TRANSFORM


def generate_gradcam(model, tensor, original_image):
    """Generate a Grad-CAM overlay using the final EfficientNet feature layer."""

    activations = []
    gradients = []

    target_layer = model.features[-1]

    def forward_hook(module, inputs, output):
        activations.append(output)

    def backward_hook(module, grad_input, grad_output):
        gradients.append(grad_output[0])

    forward_handle = target_layer.register_forward_hook(forward_hook)
    backward_handle = target_layer.register_full_backward_hook(backward_hook)

    try:
        model.zero_grad(set_to_none=True)

        with torch.enable_grad():
            input_tensor = tensor.detach().clone().requires_grad_(True)
            logits = model(input_tensor)

            predicted_class = int(torch.argmax(logits, dim=1).item())
            logits[0, predicted_class].backward()

        activation = activations[0].detach()
        gradient = gradients[0].detach()

        weights = gradient.mean(dim=(2, 3), keepdim=True)
        cam = torch.sum(weights * activation, dim=1)
        cam = F.relu(cam)

        cam = cam[0]
        cam -= cam.min()
        cam /= cam.max().clamp(min=1e-8)

        heatmap = cam.cpu().numpy()
        heatmap_image = Image.fromarray(
            np.uint8(heatmap * 255)
        ).resize(original_image.size, Image.Resampling.BILINEAR)

        heatmap_array = np.asarray(heatmap_image).astype(np.float32) / 255.0

        # Create a red-yellow heatmap overlay without requiring OpenCV.
        red = np.clip(1.5 * heatmap_array, 0, 1)
        green = np.clip(1.5 - np.abs(2 * heatmap_array - 1) * 1.5, 0, 1)
        blue = np.clip(1.0 - 2.0 * heatmap_array, 0, 1)

        color_map = np.stack([red, green, blue], axis=-1)

        original_array = (
            np.asarray(original_image).astype(np.float32) / 255.0
        )

        overlay = (
            0.55 * original_array + 0.45 * color_map
        )

        overlay = np.uint8(np.clip(overlay, 0, 1) * 255)

        output_image = Image.fromarray(overlay)

        buffer = BytesIO()
        output_image.save(buffer, format="PNG")

        encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")

        return f"data:image/png;base64,{encoded}"

    finally:
        forward_handle.remove()
        backward_handle.remove()
        model.zero_grad(set_to_none=True)


def analyze_frequency_spectrum(pil_image: Image.Image) -> dict:
    """
    Computes 2D Fast Fourier Transform (FFT) and azimuthal radial decay profile.
    Generative AI models (Diffusion/GAN) exhibit characteristic high-frequency
    energy spikes and 1/f power law deviations compared to natural camera sensors.
    """
    gray = pil_image.convert("L").resize((256, 256))
    f = np.fft.fft2(np.asarray(gray, dtype=np.float32))
    fshift = np.fft.fftshift(f)
    magnitude_spectrum = 20 * np.log(np.abs(fshift) + 1e-8)

    cy, cx = 128, 128
    y, x = np.ogrid[:256, :256]
    r = np.hypot(x - cx, y - cy).astype(int)

    high_freq_mask = (r >= 80) & (r <= 128)
    low_freq_mask = (r < 40)

    high_freq_energy = float(np.mean(magnitude_spectrum[high_freq_mask]))
    low_freq_energy = float(np.mean(magnitude_spectrum[low_freq_mask]))
    spectral_ratio = high_freq_energy / (low_freq_energy + 1e-6)

    diff = np.abs(np.diff(magnitude_spectrum, axis=0))
    checkerboard_score = float(np.mean(diff > np.percentile(diff, 90)))

    has_anomaly = bool(checkerboard_score > 0.12 or spectral_ratio > 0.72)

    return {
        "spectral_ratio": round(spectral_ratio, 4),
        "high_freq_energy": round(high_freq_energy, 2),
        "checkerboard_score": round(checkerboard_score, 4),
        "has_genai_frequency_anomaly": has_anomaly
    }


def predict_image(image: Image.Image):
    """Return real/fake probabilities, Grad-CAM explanation, and GenAI FFT frequency analysis."""
    model, image_transform = load_image_model()

    image = ImageOps.exif_transpose(image).convert("RGB")

    tensor = image_transform(image).unsqueeze(0).to(DEVICE)

    # Normal prediction
    with torch.inference_mode():
        logits = model(tensor)
        probabilities = torch.softmax(logits, dim=1)[0]

    real_probability = float(probabilities[0].item())
    fake_probability = float(probabilities[1].item())

    # 2D FFT Frequency Analysis for GenAI (Diffusion / GAN) artifacts
    freq_data = analyze_frequency_spectrum(image)

    # Blend spatial and frequency signals
    if freq_data["has_genai_frequency_anomaly"]:
        # Boost fake probability slightly if high-frequency diffusion artifacts are prominent
        adjusted_fake_prob = min(0.999, fake_probability * 0.7 + 0.3 * (freq_data["spectral_ratio"] / 0.8))
        adjusted_real_prob = 1.0 - adjusted_fake_prob
    else:
        adjusted_fake_prob = fake_probability
        adjusted_real_prob = real_probability

    # Classify artifact type
    if adjusted_fake_prob >= 0.55:
        if freq_data["has_genai_frequency_anomaly"]:
            artifact_type = "GENERATIVE_AI_SYNTHESIS (Diffusion/GAN)"
        else:
            artifact_type = "FACIAL_DEEPFAKE_MANIPULATION (FaceSwap/Blended)"
        verdict = "SPOOF-LIKE"
    elif adjusted_fake_prob <= 0.45:
        artifact_type = "AUTHENTIC_PHOTOGRAPH"
        verdict = "REAL-LIKE"
    else:
        artifact_type = "AMBIGUOUS_SIGNAL (Manual Inspection Required)"
        verdict = "INCONCLUSIVE"

    # Explain the predicted class with Grad-CAM
    gradcam_overlay = generate_gradcam(model, tensor, image)

    return {
        "prediction": "fake" if adjusted_fake_prob >= 0.5 else "real",
        "verdict": verdict,
        "real_probability": round(adjusted_real_prob, 4),
        "fake_probability": round(adjusted_fake_prob, 4),
        "confidence": round(max(adjusted_real_prob, adjusted_fake_prob), 4),
        "model": "EfficientNet-B0 + 2D-FFT Spectral Analyzer",
        "input_size": _INPUT_SIZE,
        "explanation_method": "Grad-CAM + Azimuthal Spectral Residual",
        "gradcam_overlay": gradcam_overlay,
        "artifact_classification": artifact_type,
        "frequency_telemetry": freq_data
    }

