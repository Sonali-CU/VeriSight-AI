import React from 'react';
import { Layers, Cpu, Waves, Film, CheckCircle2, AlertOctagon } from 'lucide-react';
import { FusionPredictionResult } from '../types';

interface MultimodalFusionViewProps {
  result: FusionPredictionResult;
  previewUrl: string | null;
}

export default function MultimodalFusionView({ result, previewUrl }: MultimodalFusionViewProps) {
  const scores = result.modality_scores || {};
  const weights = result.effective_weights || {};

  return (
    <div className="fusion-forensic-deck">
      <div className="forensic-subcard-header">
        <div className="flex items-center gap-2">
          <Layers className="text-cyan" size={20} />
          <h3>MULTIMODAL LATE FUSION SYNTHESIS</h3>
        </div>
        <div className="badge-chip text-magenta">
          DYNAMIC CALIBRATED WEIGHTS
        </div>
      </div>

      {previewUrl && (
        <div className="video-preview-wrapper">
          <video src={previewUrl} controls className="video-element" />
        </div>
      )}

      {/* Dynamic Weight & Modality Breakdown */}
      <div className="fusion-breakdown-grid">
        <div className="fusion-stream-card">
          <div className="stream-header">
            <Film size={16} className="text-lime" />
            <span className="cyber-mono text-xs">VISUAL STREAM</span>
            <span className="weight-badge">{Math.round((weights.visual || 0.35) * 100)}% WEIGHT</span>
          </div>
          <div className="stream-score">
            <span className="text-muted text-xs">Spoof Risk:</span>
            <strong className={scores.visual_frame && scores.visual_frame > 0.5 ? 'text-magenta' : 'text-lime'}>
              {scores.visual_frame !== null && scores.visual_frame !== undefined
                ? `${(scores.visual_frame * 100).toFixed(1)}%`
                : 'N/A'}
            </strong>
          </div>
          <small className="cyber-mono text-muted text-xs">Model: EfficientNet-B0 Frame Ensemble</small>
        </div>

        <div className="fusion-stream-card">
          <div className="stream-header">
            <Cpu size={16} className="text-cyan" />
            <span className="cyber-mono text-xs">TEMPORAL STREAM</span>
            <span className="weight-badge">{Math.round((weights.temporal || 0.35) * 100)}% WEIGHT</span>
          </div>
          <div className="stream-score">
            <span className="text-muted text-xs">Spoof Risk:</span>
            <strong className={scores.temporal_sequence && scores.temporal_sequence > 0.5 ? 'text-magenta' : 'text-lime'}>
              {scores.temporal_sequence !== null && scores.temporal_sequence !== undefined
                ? `${(scores.temporal_sequence * 100).toFixed(1)}%`
                : 'N/A'}
            </strong>
          </div>
          <small className="cyber-mono text-muted text-xs">Model: BiLSTM 16-Frame Sequence</small>
        </div>

        <div className="fusion-stream-card">
          <div className="stream-header">
            <Waves size={16} className="text-purple" />
            <span className="cyber-mono text-xs">ACOUSTIC STREAM</span>
            <span className="weight-badge">{Math.round((weights.audio || 0.30) * 100)}% WEIGHT</span>
          </div>
          <div className="stream-score">
            <span className="text-muted text-xs">Spoof Risk:</span>
            <strong className={scores.audio_spoof && scores.audio_spoof > 0.5 ? 'text-magenta' : 'text-lime'}>
              {scores.audio_spoof !== null && scores.audio_spoof !== undefined
                ? `${(scores.audio_spoof * 100).toFixed(1)}%`
                : 'NO AUDIO TRACK'}
            </strong>
          </div>
          <small className="cyber-mono text-muted text-xs">Model: ASVspoof 2019 AudioSpoofCNN</small>
        </div>
      </div>

      <div className="fusion-synthesis-callout">
        <Layers size={18} className="text-cyan inline mr-2" />
        <span>
          Multimodal late fusion evaluates cross-stream consistency. When synthetic speech or unnatural facial
          dynamics are detected, modality scores are calibrated and combined using normalized weights to produce a
          single unified manipulation index while preventing single-modality bias.
        </span>
      </div>
    </div>
  );
}
