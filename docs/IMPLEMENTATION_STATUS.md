# Implementation status

## Present in this ZIP
- FastAPI backend and API docs
- React/Vite status UI
- Explicit model registry with prediction disabled by default
- Upload validation and SHA-256 receipt endpoint
- Dataset registry aligned to the supplied presentation
- Official-reference reachability checker
- Manual licence/access approval gate for direct downloads
- Manifest validator with source-group leakage check
- Colab storage, image-baseline and video/audio planning notebooks
- Backend smoke tests

## Not present / not claimed
- No dataset binaries or extracted dataset samples
- No trained model weights
- No face detector / face-crop preprocessing implementation
- No completed temporal video model or audio model trainer
- No late-fusion model
- No Grad-CAM implementation
- No calibrated confidence estimates
- No actual deepfake predictions
- No dashboards, project report or viva guide

## Required development order
1. Run FastAPI + frontend smoke test.
2. Verify dataset access and licences manually.
3. Prepare dataset manifests and group-safe splits.
4. Train and evaluate image/frame baseline.
5. Add temporal video and audio models.
6. Evaluate cross-dataset and robustness.
7. Implement fusion and explanations.
8. Integrate validated inference adapters.
9. Only after working detection, build dashboards and reports.
