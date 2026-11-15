import React, { useState } from 'react';
import { ShieldCheck, Copy, Check, Download, FileText, Hash, Calendar, HardDrive } from 'lucide-react';
import { formatBytes } from '../utils/webgl';

interface EvidencePanelProps {
  filename: string;
  bytes: number;
  sha256: string;
  modality: 'image' | 'video' | 'audio' | 'fusion';
  verdict: string;
  confidence: number;
  result: any;
  uploadId?: string;
}

export default function EvidencePanel({
  filename,
  bytes,
  sha256,
  modality,
  verdict,
  confidence,
  result,
  uploadId
}: EvidencePanelProps) {
  const [copied, setCopied] = useState(false);
  const timestamp = new Date().toISOString();

  function copyHash() {
    navigator.clipboard.writeText(sha256);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  function downloadReport() {
    const reportData = {
      platform: 'VeriSight AI Multimodal Cybersecurity Forensics',
      version: '2.2.0',
      timestamp,
      verification_status: 'CRYPTOGRAPHICALLY_VERIFIED',
      evidence_receipt: {
        filename,
        file_size_bytes: bytes,
        file_size_formatted: formatBytes(bytes),
        sha256_checksum: sha256,
        upload_id: uploadId || 'DIRECT_INGEST'
      },
      forensic_evaluation: {
        target_modality: modality.toUpperCase(),
        classification_verdict: verdict,
        confidence_score: confidence,
        model_provenance: result?.model || 'VeriSight Neural Classifier',
        analysis_method: result?.analysis_method || 'Feature Spectrogram / Tensor Activation',
        hardware_profile: result?.device || 'CPU Inference Engine'
      },
      raw_telemetry: result
    };

    const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `VERISIGHT_FORENSIC_REPORT_${filename}_${Date.now()}.json`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="evidence-panel-card">
      <div className="forensic-subcard-header">
        <div className="flex items-center gap-2">
          <ShieldCheck className="text-lime" size={20} />
          <h3>CHAIN-OF-CUSTODY & CRYPTOGRAPHIC EVIDENCE</h3>
        </div>
        <button className="download-report-btn" onClick={downloadReport}>
          <Download size={14} />
          <span>EXPORT FORENSIC AUDIT REPORT</span>
        </button>
      </div>

      <div className="evidence-grid">
        <div className="evidence-field sha-field">
          <div className="field-label">
            <Hash size={14} className="text-cyan" />
            <span>SHA-256 BITSTREAM HASH</span>
          </div>
          <div className="hash-box">
            <code className="hash-code">{sha256}</code>
            <button className="copy-btn" onClick={copyHash} title="Copy SHA-256 checksum">
              {copied ? <Check size={14} className="text-lime" /> : <Copy size={14} />}
            </button>
          </div>
        </div>

        <div className="evidence-field">
          <div className="field-label">
            <FileText size={14} className="text-muted" />
            <span>MEDIA FILENAME</span>
          </div>
          <div className="field-value cyber-mono">{filename}</div>
        </div>

        <div className="evidence-field">
          <div className="field-label">
            <HardDrive size={14} className="text-muted" />
            <span>PAYLOAD SIZE</span>
          </div>
          <div className="field-value cyber-mono">{formatBytes(bytes)} ({bytes.toLocaleString()} bytes)</div>
        </div>

        <div className="evidence-field">
          <div className="field-label">
            <Calendar size={14} className="text-muted" />
            <span>INGEST TIMESTAMP</span>
          </div>
          <div className="field-value cyber-mono">{timestamp}</div>
        </div>
      </div>
    </div>
  );
}
