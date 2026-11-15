
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


def predict_image(image: Image.Image):
    """Return real/fake probabilities and Grad-CAM explanation."""
    model, image_transform = load_image_model()

    image = ImageOps.exif_transpose(image).convert("RGB")

    tensor = image_transform(image).unsqueeze(0).to(DEVICE)

    # Normal prediction
    with torch.inference_mode():
        logits = model(tensor)
        probabilities = torch.softmax(logits, dim=1)[0]

    real_probability = float(probabilities[0].item())
    fake_probability = float(probabilities[1].item())

    prediction = "fake" if fake_probability >= 0.5 else "real"

    # Explain the predicted class with Grad-CAM
    gradcam_overlay = generate_gradcam(model, tensor, image)

    return {
        "prediction": prediction,
        "real_probability": real_probability,
        "fake_probability": fake_probability,
        "model": "EfficientNet-B0",
        "input_size": _INPUT_SIZE,
        "explanation_method": "Grad-CAM",
        "gradcam_overlay": gradcam_overlay
    }
