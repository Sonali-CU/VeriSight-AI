
import json
from pathlib import Path

REGISTRY_PATH = (
    Path(__file__).resolve().parents[2]
    / "configs"
    / "model_registry.json"
)


def read_registry():
    if not REGISTRY_PATH.exists():
        raise FileNotFoundError(
            f"Model registry not found: {REGISTRY_PATH}"
        )

    with REGISTRY_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def modality_status(modality: str):
    item = read_registry().get(modality, {})

    return {
        "modality": modality,
        "status": item.get("status", "not_trained"),
        "architecture": item.get("architecture"),
        "weights_path": item.get("weights_path"),
        "note": item.get(
            "note",
            "No validated model is registered."
        )
    }
