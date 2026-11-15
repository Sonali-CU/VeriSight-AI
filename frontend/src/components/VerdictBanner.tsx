import React from 'react';
import { ShieldCheck, ShieldAlert, AlertTriangle, Activity } from 'lucide-react';

interface VerdictBannerProps {
  verdict: 'REAL-LIKE' | 'SPOOF-LIKE' | 'INCONCLUSIVE' | string;
  confidence: number;
  realProbability: number;
  spoofProbability: number;
  threshold?: number;
  riskLevel?: 'LOW' | 'MODERATE' | 'HIGH' | string;
  modality: 'image' | 'video' | 'audio' | 'fusion';
  modelName?: string;
}

export default function VerdictBanner({
  verdict,
  confidence,
  realProbability,
  spoofProbability,
  threshold = 0.5,
  riskLevel,
  modality,
  modelName
}: VerdictBannerProps) {
  const normVerdict = verdict.toUpperCase();
  const isReal = normVerdict === 'REAL-LIKE' || normVerdict === 'REAL';
  const isSpoof = normVerdict === 'SPOOF-LIKE' || normVerdict === 'FAKE';
  const isInconclusive = normVerdict === 'INCONCLUSIVE';

  const themeClass = isSpoof
    ? 'verdict-spoof'
    : isReal
    ? 'verdict-real'
    : 'verdict-inconclusive';

  const risk = riskLevel || (isSpoof ? 'HIGH' : isReal ? 'LOW' : 'MODERATE');

  return (
    <div className={`verdict-banner-card ${themeClass}`}>
      <div className="verdict-banner-header">
        <div className="verdict-title-area">
          <div className="verdict-icon-container">
            {isReal && <ShieldCheck className="verdict-icon icon-real" size={36} />}
            {isSpoof && <ShieldAlert className="verdict-icon icon-spoof" size={36} />}
            {isInconclusive && <AlertTriangle className="verdict-icon icon-inconclusive" size={36} />}
          </div>
          <div>
            <div className="verdict-eyebrow">
              <span className="cyber-mono">{modality.toUpperCase()} FORENSIC CLASSIFICATION</span>
              <span className={`risk-tag tag-${risk.toLowerCase()}`}>
                RISK: {risk}
              </span>
            </div>
            <h2 className="verdict-text">{normVerdict}</h2>
          </div>
        </div>

        <div className="verdict-confidence-badge">
          <span className="confidence-label">DETECTION CONFIDENCE</span>
          <span className="confidence-value">{(confidence * 100).toFixed(1)}%</span>
          <small className="cyber-mono text-muted">MODEL: {modelName || 'VeriSight Neural Engine'}</small>
        </div>
      </div>

      <div className="verdict-probability-grid">
        <div className="prob-meter-group">
          <div className="prob-labels">
            <span className="text-lime cyber-mono">REAL PROBABILITY</span>
            <strong className="text-lime">{(realProbability * 100).toFixed(1)}%</strong>
          </div>
          <div className="prob-track">
            <div
              className="prob-bar-fill fill-lime"
              style={{ width: `${Math.min(100, Math.max(0, realProbability * 100))}%` }}
            />
          </div>
        </div>

        <div className="prob-meter-group">
          <div className="prob-labels">
            <span className="text-magenta cyber-mono">SPOOF PROBABILITY</span>
            <strong className="text-magenta">{(spoofProbability * 100).toFixed(1)}%</strong>
          </div>
          <div className="prob-track">
            <div
              className="prob-bar-fill fill-magenta"
              style={{ width: `${Math.min(100, Math.max(0, spoofProbability * 100))}%` }}
            />
            {threshold && (
              <div
                className="threshold-marker"
                style={{ left: `${threshold * 100}%` }}
                title={`Optimal Decision Threshold: ${(threshold * 100).toFixed(1)}%`}
              />
            )}
          </div>
          <div className="threshold-legend">
            <small className="cyber-mono text-muted">
              Threshold Marker: {(threshold * 100).toFixed(1)}%
            </small>
          </div>
        </div>
      </div>

      <div className="verdict-footer-notice">
        <Activity size={14} className="text-cyan inline mr-1" />
        <span>
          A model prediction is a forensic evidence signal, not absolute legal proof.
          Human examiner verification remains mandatory for forensic attribution.
        </span>
      </div>
    </div>
  );
}
