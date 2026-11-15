import torch
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

checkpoint_path = (
    PROJECT_ROOT
    / "models"
    / "image"
    / "verisight_efficientnet_b0_ffpp_source_disjoint.pth"
)

checkpoint = torch.load(
    checkpoint_path,
    map_location="cpu",
    weights_only=False
)

print("Checkpoint type:", type(checkpoint))

if isinstance(checkpoint, dict):
    print("Checkpoint keys:", checkpoint.keys())

    state = checkpoint.get(
        "model_state_dict",
        checkpoint.get("state_dict", checkpoint)
    )

    if isinstance(state, dict):
        print("\nNumber of parameters:", len(state))
        print("\nFirst 10 parameter names:")
        for key in list(state.keys())[:10]:
            print(key)