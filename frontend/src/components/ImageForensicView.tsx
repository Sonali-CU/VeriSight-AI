import React, { useState } from 'react';
import { Eye, Layers, Maximize2, Shield } from 'lucide-react';
import { ImagePredictionResult } from '../types';

interface ImageForensicViewProps {
  result: ImagePredictionResult;
  previewUrl: string | null;
}

export default function ImageForensicView({ result, previewUrl }: ImageForensicViewProps) {
  const [overlayOpacity, setOverlayOpacity] = useState(0.85);
  const [viewMode, setViewMode] = useState<'overlay' | 'side_by_side'>('side_by_side');

  const gradcamUrl = result.gradcam_overlay;

  return (
    <div className="image-forensic-deck">
      <div className="forensic-subcard-header">
        <div className="flex items-center gap-2">
          <Eye className="text-cyan" size={20} />
          <h3>IMAGE FORENSIC NEURAL HEATMAP (GRAD-CAM)</h3>
        </div>
        <div className="view-toggle-pills">
          <button
            className={`pill-btn ${viewMode === 'side_by_side' ? 'active' : ''}`}
            onClick={() => setViewMode('side_by_side')}
          >
            Side-by-Side
          </button>
          <button
            className={`pill-btn ${viewMode === 'overlay' ? 'active' : ''}`}
            onClick={() => setViewMode('overlay')}
          >
            Alpha Overlay
          </button>
        </div>
      </div>

      {viewMode === 'overlay' && gradcamUrl && (
        <div className="opacity-slider-control">
          <Layers size={16} className="text-muted" />
          <span className="cyber-mono text-xs">GRAD-CAM INTENSITY: {Math.round(overlayOpacity * 100)}%</span>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={overlayOpacity}
            onChange={(e) => setOverlayOpacity(parseFloat(e.target.value))}
            className="cyber-range"
          />
        </div>
      )}

      <div className="image-comparison-grid">
        {viewMode === 'side_by_side' ? (
          <>
            <div className="image-card original-card">
              <div className="image-card-badge">INPUT MEDIA EVIDENCE</div>
              {previewUrl && (
                <img src={previewUrl} alt="Original forensic evidence" className="forensic-preview-img" />
              )}
            </div>

            <div className="image-card heatmap-card">
              <div className="image-card-badge text-magenta">GRAD-CAM ATTENTION MAP</div>
              {gradcamUrl ? (
                <img src={gradcamUrl} alt="Grad-CAM activation heatmap" className="forensic-preview-img" />
              ) : (
                <div className="empty-heatmap">Heatmap not generated</div>
              )}
            </div>
          </>
        ) : (
          <div className="image-card overlay-composite-card">
            <div className="image-card-badge">COMPOSITE NEURAL FOCUS</div>
            <div className="composite-container">
              {previewUrl && (
                <img src={previewUrl} alt="Original base" className="composite-base" />
              )}
              {gradcamUrl && (
                <img
                  src={gradcamUrl}
                  alt="Grad-CAM layer"
                  className="composite-layer"
                  style={{ opacity: overlayOpacity }}
                />
              )}
            </div>
          </div>
        )}
      </div>

      <div className="forensic-explanation-box">
        <Shield size={16} className="text-cyan inline mr-2" />
        <span className="text-xs text-muted">
          Grad-CAM highlights discriminative feature activations in the final convolutional layer of EfficientNet-B0.
          Warm red/yellow zones represent regions driving the classification verdict (e.g. facial boundary warping, synthetic blending edges, or texture anomalies).
        </span>
      </div>
    </div>
  );
}
