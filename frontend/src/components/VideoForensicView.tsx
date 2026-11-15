import React from 'react';
import { Film, Clock, Cpu, BarChart2, CheckCircle2, AlertOctagon } from 'lucide-react';
import { VideoPredictionResult } from '../types';

interface VideoForensicViewProps {
  result: VideoPredictionResult;
  previewUrl: string | null;
  videoMode: 'frame' | 'temporal';
}

export default function VideoForensicView({ result, previewUrl, videoMode }: VideoForensicViewProps) {
  const frames = result.frame_results || [];

  return (
    <div className="video-forensic-deck">
      <div className="forensic-subcard-header">
        <div className="flex items-center gap-2">
          <Film className="text-cyan" size={20} />
          <h3>VIDEO FORENSIC SEQUENCE ANALYSIS</h3>
        </div>
        <div className="badge-chip text-magenta">
          {videoMode === 'temporal' ? 'TEMPORAL BiLSTM SEQUENCE' : 'FRAME ENSEMBLE SAMPLING'}
        </div>
      </div>

      {previewUrl && (
        <div className="video-preview-wrapper">
          <video src={previewUrl} controls className="video-element" />
        </div>
      )}

      <div className="video-telemetry-strip">
        <div className="v-stat">
          <Clock size={16} className="text-cyan" />
          <span>FRAMES ANALYZED: <strong>{result.frames_analyzed || frames.length || 16}</strong></span>
        </div>
        <div className="v-stat">
          <Cpu size={16} className="text-magenta" />
          <span>ARCHITECTURE: <strong>{result.model}</strong></span>
        </div>
        <div className="v-stat">
          <BarChart2 size={16} className="text-lime" />
          <span>DEVICE: <strong>{(result.device || 'CPU').toUpperCase()}</strong></span>
        </div>
      </div>

      {/* Frame-by-Frame Timeline (when frame-based detection is run) */}
      {frames.length > 0 && (
        <div className="frames-timeline-container">
          <h4 className="cyber-mono text-xs text-muted mb-3">SAMPLED FRAME TEMPORAL DISTRIBUTION</h4>
          <div className="frames-grid">
            {frames.map((frame) => {
              const isFrameFake = frame.prediction.toLowerCase() === 'fake';
              return (
                <div
                  key={frame.frame_number}
                  className={`frame-card ${isFrameFake ? 'frame-risk-high' : 'frame-risk-low'}`}
                >
                  <div className="frame-card-header">
                    <span className="cyber-mono text-xs">FRAME #{frame.frame_number}</span>
                    {isFrameFake ? (
                      <AlertOctagon size={14} className="text-magenta" />
                    ) : (
                      <CheckCircle2 size={14} className="text-lime" />
                    )}
                  </div>
                  <div className="frame-prob-mini">
                    <div className="text-xs flex justify-between">
                      <span className="text-muted">Fake Prob:</span>
                      <strong className={isFrameFake ? 'text-magenta' : 'text-muted'}>
                        {(frame.fake_probability * 100).toFixed(0)}%
                      </strong>
                    </div>
                    <div className="mini-track">
                      <div
                        className={`mini-fill ${isFrameFake ? 'bg-magenta' : 'bg-lime'}`}
                        style={{ width: `${frame.fake_probability * 100}%` }}
                      />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {videoMode === 'temporal' && (
        <div className="temporal-sequence-callout">
          <Cpu size={20} className="text-cyan inline mr-2" />
          <span>
            Temporal BiLSTM analyzes frame-to-frame feature transitions across 16 sequential timestamps to detect
            inter-frame flickering, unnatural facial muscle dynamics, and temporal synthesis artifacts.
          </span>
        </div>
      )}
    </div>
  );
}
