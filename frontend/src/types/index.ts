export type Health = {
  status: string;
  service: string;
  model_status: string;
  active_modalities?: string[];
};

export type Model = {
  modality: 'image' | 'video' | 'audio' | 'fusion';
  status: 'trained' | 'not_trained';
  architecture?: string;
  weights_path?: string;
  note: string;
  metrics?: Record<string, any>;
};

export type InspectResult = {
  status: string;
  filename: string;
  bytes: number;
  sha256: string;
  metadata?: Record<string, any>;
  prediction: null;
  message: string;
  upload_id: string;
};

export type FrameResult = {
  frame_number: number;
  prediction: string;
  real_probability: number;
  fake_probability: number;
};

export type AudioPredictionResult = {
  verdict: 'REAL-LIKE' | 'SPOOF-LIKE' | 'INCONCLUSIVE';
  prediction: 'real' | 'fake' | 'inconclusive';
  risk_level: 'LOW' | 'MODERATE' | 'HIGH';
  spoof_probability: number;
  real_probability: number;
  confidence: number;
  decision_threshold: number;
  sha256: string;
  metadata: {
    format: string;
    subtype: string;
    channels: number;
    sample_rate: number;
    samples: number;
    duration_seconds: number;
    file_size_bytes: number;
    filename: string;
  };
  acoustic_features: {
    rms: number;
    zero_crossing_rate: number;
    spectral_centroid_approx_hz: number;
  };
  spectrogram_preview: {
    shape: [number, number];
    data: number[][];
  };
  model: string;
  analysis_method: string;
  device: string;
  warning: string;
};

export type VideoPredictionResult = {
  prediction: string;
  real_probability: number;
  fake_probability: number;
  confidence?: number;
  model: string;
  analysis_method?: string;
  total_video_frames?: number;
  sampled_frames?: number;
  frames_analyzed?: number;
  device?: string;
  frame_results?: FrameResult[];
};

export type ImagePredictionResult = {
  prediction: string;
  real_probability: number;
  fake_probability: number;
  confidence?: number;
  model: string;
  input_size?: number;
  explanation_method?: string;
  gradcam_overlay?: string;
};

export type FusionPredictionResult = {
  verdict: 'REAL-LIKE' | 'SPOOF-LIKE' | 'INCONCLUSIVE';
  composite_spoof_probability: number;
  composite_real_probability: number;
  confidence: number;
  sha256: string;
  effective_weights: Record<string, number>;
  modality_scores: {
    visual_frame: number;
    temporal_sequence: number;
    audio_spoof: number | null;
  };
  sub_analyses: Record<string, any>;
  fusion_method: string;
  model: string;
  warning: string;
};

export type PredictionResponse = {
  status: string;
  filename: string;
  modality: 'image' | 'video' | 'audio' | 'fusion';
  model_type?: string;
  result: ImagePredictionResult & VideoPredictionResult & AudioPredictionResult & FusionPredictionResult;
};

export type AudioMetrics = {
  threshold_selected_on_dev: number;
  accuracy: number;
  balanced_accuracy: number;
  precision_spoof: number;
  recall_spoof: number;
  f1_spoof: number;
  roc_auc: number;
  pr_auc: number;
  eer_approx: number;
  confusion_matrix: {
    bonafide: { predicted_bonafide: number; predicted_spoof: number };
    spoof: { predicted_bonafide: number; predicted_spoof: number };
  };
  raw_confusion_matrix: number[][];
  dev_loss: number;
  dev_samples: number;
  train_samples: number;
};

export type AudioMetricsResponse = {
  status: string;
  model_name: string;
  dataset: string;
  architecture: string;
  metrics: AudioMetrics;
  history: Array<{
    epoch: number;
    train_loss: number;
    dev_loss: number;
    dev_auc: number;
    elapsed_sec: number;
  }>;
  limitations: string[];
};

export type AnalysisHistoryItem = {
  id: string;
  timestamp: string;
  filename: string;
  modality: 'image' | 'video' | 'audio' | 'fusion';
  verdict: 'REAL-LIKE' | 'SPOOF-LIKE' | 'INCONCLUSIVE';
  confidence: number;
  spoofProbability: number;
  sha256: string;
  fileSize: number;
  result: any;
};
