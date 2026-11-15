import React, { useEffect, useState, useRef } from 'react';
import {
  ShieldAlert,
  ShieldCheck,
  Globe,
  Scan,
  Activity,
  UploadCloud,
  FileAudio,
  FileVideo,
  FileImage,
  RefreshCw,
  BarChart2,
  History,
  Layers,
  Sparkles,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';

import HoloGlobe from './components/3d/HoloGlobe';
import CyberScanner3D from './components/3d/CyberScanner3D';
import VerdictBanner from './components/VerdictBanner';
import AudioForensicView from './components/AudioForensicView';
import ImageForensicView from './components/ImageForensicView';
import VideoForensicView from './components/VideoForensicView';
import MultimodalFusionView from './components/MultimodalFusionView';
import EvidencePanel from './components/EvidencePanel';
import ModelTelemetryModal from './components/ModelTelemetryModal';
import AnalysisHistoryDrawer from './components/AnalysisHistoryDrawer';
import {
  Health,
  Model,
  InspectResult,
  PredictionResponse,
  AnalysisHistoryItem
} from './types';
import { formatBytes } from './utils/webgl';

const API_BASE = 'http://127.0.0.1:8000';

export default function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [models, setModels] = useState<Model[]>([]);
  const [statusMessage, setStatusMessage] = useState('Initializing cyber forensic bridge...');

  const [activeModality, setActiveModality] = useState<'image' | 'video' | 'audio' | 'fusion'>('audio');
  const [videoMode, setVideoMode] = useState<'frame' | 'temporal'>('temporal');
  const [heroView, setHeroView] = useState<'globe' | 'scanner'>('globe');

  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const [isInspecting, setIsInspecting] = useState(false);
  const [isPredicting, setIsPredicting] = useState(false);
  const [diagnosticsLog, setDiagnosticsLog] = useState<string[]>([]);

  const [inspectResult, setInspectResult] = useState<InspectResult | null>(null);
  const [predictionData, setPredictionData] = useState<PredictionResponse | null>(null);

  const [isTelemetryOpen, setIsTelemetryOpen] = useState(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [historyItems, setHistoryItems] = useState<AnalysisHistoryItem[]>([]);

  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Fetch health and models from backend
  async function refreshSystem() {
    try {
      setStatusMessage('Querying neural forensic endpoints...');
      const [hRes, mRes] = await Promise.all([
        fetch(`${API_BASE}/health`),
        fetch(`${API_BASE}/api/v1/models`)
      ]);

      if (!hRes.ok || !mRes.ok) throw new Error('Failed to connect to backend.');

      const healthJson = await hRes.json();
      const modelsJson = await mRes.json();

      setHealth(healthJson);
      setModels(modelsJson.models || []);
      setStatusMessage('FastAPI forensic engine online. CPU inference ready.');
    } catch (err) {
      setHealth(null);
      setStatusMessage('Cannot connect to FastAPI at http://127.0.0.1:8000. Start backend server.');
    }
  }

  useEffect(() => {
    refreshSystem();
  }, []);

  // Sync preview URL with file object
  useEffect(() => {
    if (!file) {
      setPreviewUrl(null);
      return;
    }
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  function handleFileSelect(selected: File | null) {
    if (!selected) return;
    setFile(selected);
    setInspectResult(null);
    setPredictionData(null);
    setDiagnosticsLog([]);

    // Auto-detect modality by extension
    const ext = selected.name.substring(selected.name.lastIndexOf('.')).toLowerCase();
    if (['.wav', '.mp3', '.flac', '.m4a', '.ogg'].includes(ext)) {
      setActiveModality('audio');
    } else if (['.mp4', '.mov', '.avi'].includes(ext)) {
      setActiveModality('video');
    } else if (['.jpg', '.jpeg', '.png', '.webp'].includes(ext)) {
      setActiveModality('image');
    }
    setStatusMessage(`Bitstream loaded: ${selected.name} (${formatBytes(selected.size)}). Ready for forensic scan.`);
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  }

  // SHA-256 Inspection & Chain-of-Custody Hashing
  async function runInspection() {
    if (!file) return;
    setIsInspecting(true);
    setInspectResult(null);
    setDiagnosticsLog((prev) => [...prev, `[${new Date().toLocaleTimeString()}] INGEST: Parsing ${file.name}...`]);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch(`${API_BASE}/api/v1/inspect`, {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Inspection failed');

      setInspectResult(data);
      setDiagnosticsLog((prev) => [
        ...prev,
        `[${new Date().toLocaleTimeString()}] SHA-256 GENERATED: ${data.sha256.substring(0, 16)}...`,
        `[${new Date().toLocaleTimeString()}] INTEGRITY: Bitstream verified (${data.bytes} bytes).`
      ]);
      setStatusMessage('File inspection & cryptographic digest verified.');
    } catch (err: any) {
      setStatusMessage(`Inspection error: ${err.message}`);
    } finally {
      setIsInspecting(false);
    }
  }

  // Deepfake Classification Pipeline
  async function runPrediction() {
    if (!file) return;
    setIsPredicting(true);
    setPredictionData(null);
    setHeroView('scanner'); // Auto-switch to 3D scanner during analysis

    setDiagnosticsLog([
      `[${new Date().toLocaleTimeString()}] INITIALIZING ${activeModality.toUpperCase()} NEURAL INGESTION...`,
      `[${new Date().toLocaleTimeString()}] EXECUTING CPU-COMPLIANT FORWARD PASS...`
    ]);

    const formData = new FormData();
    formData.append('file', file);

    let endpoint = `${API_BASE}/api/v1/predict/${activeModality}`;
    if (activeModality === 'video' && videoMode === 'temporal') {
      endpoint = `${API_BASE}/api/v1/predict/video/temporal`;
    }

    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Prediction failed');

      setPredictionData(data);
      const resObj = data.result;

      setDiagnosticsLog((prev) => [
        ...prev,
        `[${new Date().toLocaleTimeString()}] INFERENCE COMPLETED IN CPU RUNTIME.`,
        `[${new Date().toLocaleTimeString()}] VERDICT: ${resObj.verdict || resObj.prediction?.toUpperCase()} (CONFIDENCE: ${(
          (resObj.confidence || resObj.fake_probability || 0) * 100
        ).toFixed(1)}%)`
      ]);

      setStatusMessage(`${activeModality.toUpperCase()} forensic analysis complete.`);

      // Append to session history
      const historyItem: AnalysisHistoryItem = {
        id: Math.random().toString(36).substring(2, 9),
        timestamp: new Date().toLocaleTimeString(),
        filename: file.name,
        modality: activeModality,
        verdict: (resObj.verdict || (resObj.prediction === 'fake' ? 'SPOOF-LIKE' : 'REAL-LIKE')) as any,
        confidence: resObj.confidence || Math.max(resObj.real_probability || 0, resObj.fake_probability || 0),
        spoofProbability: resObj.spoof_probability ?? resObj.fake_probability ?? 0,
        sha256: resObj.sha256 || inspectResult?.sha256 || 'CALCULATED_IN_MEMORY',
        fileSize: file.size,
        result: resObj
      };
      setHistoryItems((prev) => [historyItem, ...prev]);
    } catch (err: any) {
      setStatusMessage(`Prediction error: ${err.message}`);
      setDiagnosticsLog((prev) => [...prev, `[ERROR] ${err.message}`]);
    } finally {
      setIsPredicting(false);
    }
  }

  // Restore analysis from session history
  function handleSelectHistoryItem(item: AnalysisHistoryItem) {
    setActiveModality(item.modality);
    setPredictionData({
      status: 'success',
      filename: item.filename,
      modality: item.modality,
      result: item.result
    });
    setStatusMessage(`Restored analysis for ${item.filename} from session audit log.`);
  }

  const result = predictionData?.result;
  const currentVerdict = result
    ? result.verdict || (result.prediction === 'fake' ? 'SPOOF-LIKE' : 'REAL-LIKE')
    : null;
  const realProb = result?.real_probability ?? (result?.prediction === 'real' ? 1.0 - (result.fake_probability || 0) : 0);
  const spoofProb = result?.spoof_probability ?? result?.fake_probability ?? 0;
  const confidenceVal = result?.confidence ?? Math.max(realProb, spoofProb);
  const sha256Val = result?.sha256 || inspectResult?.sha256 || '';

  return (
    <div className="verisight-cyber-shell">
      {/* Background Cyber Grid Lines */}
      <div className="ambient-background-grid" />
      <div className="ambient-radial-glow glow-top-left" />
      <div className="ambient-radial-glow glow-bottom-right" />

      {/* Top Cyber Command Header */}
      <header className="cyber-header">
        <div className="header-brand-cluster">
          <div className="brand-logo-hex">
            <ShieldAlert size={28} className="logo-icon-neon" />
          </div>
          <div>
            <div className="header-eyebrow">
              <span className="cyber-badge-glow">DEFENSE FORENSICS</span>
              <span className="cyber-mono text-muted text-xs">MULTIMODAL DEEPFAKE ENGINE v2.2</span>
            </div>
            <h1 className="header-title">
              VERISIGHT <span className="title-accent-cyan">AI</span>
            </h1>
          </div>
        </div>

        {/* Global Telemetry Chips */}
        <div className="header-action-cluster">
          <div className="system-status-indicator">
            <span className={`status-dot ${health?.status === 'ok' ? 'dot-active' : 'dot-offline'}`} />
            <span className="cyber-mono text-xs text-white">
              {health?.status === 'ok' ? 'FASTAPI READY' : 'OFFLINE'}
            </span>
            <span className="text-muted text-xs cyber-mono">· CPU ENGINE</span>
          </div>

          <button className="cyber-btn-outline" onClick={() => setIsTelemetryOpen(true)}>
            <BarChart2 size={15} />
            <span>MODEL TELEMETRY</span>
          </button>

          <button className="cyber-btn-outline" onClick={() => setIsHistoryOpen(true)}>
            <History size={15} />
            <span>LOGS ({historyItems.length})</span>
          </button>

          <button className="cyber-btn-icon" onClick={refreshSystem} title="Ping API Bridge">
            <RefreshCw size={16} />
          </button>
        </div>
      </header>

      {/* Main Command Center Deck */}
      <main className="command-center-grid">
        {/* Left Column: Interactive 3D Holographic Visualizer */}
        <section className="central-3d-visualizer-card">
          <div className="card-top-controls">
            <div className="flex items-center gap-2">
              <Sparkles size={16} className="text-cyan" />
              <span className="cyber-mono text-xs font-bold tracking-wider">3D HOLOGRAPHIC SURVEILLANCE</span>
            </div>
            <div className="view-toggle-pills">
              <button
                className={`pill-btn ${heroView === 'globe' ? 'active' : ''}`}
                onClick={() => setHeroView('globe')}
              >
                <Globe size={13} className="inline mr-1" /> Threat Globe
              </button>
              <button
                className={`pill-btn ${heroView === 'scanner' ? 'active' : ''}`}
                onClick={() => setHeroView('scanner')}
              >
                <Scan size={13} className="inline mr-1" /> Forensic Scanner
              </button>
            </div>
          </div>

          <div className="interactive-3d-canvas-wrap">
            {heroView === 'globe' ? (
              <HoloGlobe activeThreatCount={8} />
            ) : (
              <CyberScanner3D isScanning={isPredicting || isInspecting} modality={activeModality} />
            )}
          </div>

          {/* Real-time Diagnostics Terminal */}
          <div className="diagnostics-terminal-panel">
            <div className="terminal-header">
              <span className="terminal-dot red" />
              <span className="terminal-dot yellow" />
              <span className="terminal-dot green" />
              <span className="cyber-mono text-xs text-muted ml-2">CYBER DIAGNOSTICS STREAM</span>
            </div>
            <div className="terminal-output-body">
              <div className="terminal-line text-cyan font-mono text-xs">&gt; {statusMessage}</div>
              {diagnosticsLog.map((log, i) => (
                <div key={i} className="terminal-line text-muted font-mono text-xs">&gt; {log}</div>
              ))}
            </div>
          </div>
        </section>

        {/* Right Column: Ingest & Forensic Analysis Workspace */}
        <section className="forensic-workspace-card">
          {/* Modality Selector Tabs */}
          <div className="modality-nav-tabs">
            <button
              className={`modality-tab ${activeModality === 'audio' ? 'active-tab' : ''}`}
              onClick={() => {
                setActiveModality('audio');
                setFile(null);
                setPredictionData(null);
              }}
            >
              <FileAudio size={18} className="text-cyan" />
              <div>
                <strong>AUDIO FORENSICS</strong>
                <small>ASVspoof 2019 Log-Mel CNN</small>
              </div>
            </button>

            <button
              className={`modality-tab ${activeModality === 'video' ? 'active-tab' : ''}`}
              onClick={() => {
                setActiveModality('video');
                setFile(null);
                setPredictionData(null);
              }}
            >
              <FileVideo size={18} className="text-magenta" />
              <div>
                <strong>VIDEO FORENSICS</strong>
                <small>Frame & Temporal BiLSTM</small>
              </div>
            </button>

            <button
              className={`modality-tab ${activeModality === 'image' ? 'active-tab' : ''}`}
              onClick={() => {
                setActiveModality('image');
                setFile(null);
                setPredictionData(null);
              }}
            >
              <FileImage size={18} className="text-lime" />
              <div>
                <strong>IMAGE FORENSICS</strong>
                <small>EfficientNet-B0 + Grad-CAM</small>
              </div>
            </button>

            <button
              className={`modality-tab ${activeModality === 'fusion' ? 'active-tab' : ''}`}
              onClick={() => {
                setActiveModality('fusion');
                setFile(null);
                setPredictionData(null);
              }}
            >
              <Layers size={18} className="text-purple" />
              <div>
                <strong>MULTIMODAL FUSION</strong>
                <small>Visual + Temporal + Acoustic</small>
              </div>
            </button>
          </div>

          {/* Video Sub-Mode Selector */}
          {activeModality === 'video' && (
            <div className="video-mode-selector-bar">
              <span className="cyber-mono text-xs text-muted">DETECTION PIPELINE:</span>
              <button
                className={`mode-pill ${videoMode === 'temporal' ? 'active' : ''}`}
                onClick={() => setVideoMode('temporal')}
              >
                Temporal BiLSTM Sequence (16 Frames)
              </button>
              <button
                className={`mode-pill ${videoMode === 'frame' ? 'active' : ''}`}
                onClick={() => setVideoMode('frame')}
              >
                Sampled Frame Ensemble (8 Frames)
              </button>
            </div>
          )}

          {/* Drag & Drop Upload Zone */}
          <div
            className={`dropzone-card ${isDragging ? 'drag-active' : ''}`}
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              type="file"
              ref={fileInputRef}
              style={{ display: 'none' }}
              accept={
                activeModality === 'audio'
                  ? 'audio/wav,audio/mp3,audio/flac,audio/ogg,audio/x-m4a,.wav,.mp3,.flac,.m4a'
                  : (activeModality === 'video' || activeModality === 'fusion')
                  ? 'video/mp4,video/quicktime,video/x-msvideo,.mp4,.mov,.avi'
                  : 'image/jpeg,image/png,image/webp,.jpg,.jpeg,.png,.webp'
              }
              onChange={(e) => handleFileSelect(e.target.files?.[0] ?? null)}
            />

            <UploadCloud size={42} className="dropzone-icon" />
            <div className="dropzone-text">
              <h4>DROP {activeModality.toUpperCase()} BITSTREAM HERE OR CLICK TO BROWSE</h4>
              <p className="text-xs text-muted">
                {activeModality === 'audio' && 'Supported: WAV, MP3, FLAC, M4A · 16 kHz Log-Mel Extraction'}
                {activeModality === 'video' && 'Supported: MP4, MOV, AVI · Inter-frame Facial Artifact Analysis'}
                {activeModality === 'image' && 'Supported: JPG, JPEG, PNG, WEBP · Spatial Gradient Heatmap'}
              </p>
            </div>

            {file && (
              <div className="selected-file-chip" onClick={(e) => e.stopPropagation()}>
                <CheckCircle2 size={16} className="text-lime" />
                <span className="cyber-mono text-xs text-white">{file.name}</span>
                <span className="text-xs text-muted">({formatBytes(file.size)})</span>
              </div>
            )}
          </div>

          {/* Action Trigger Buttons */}
          <div className="action-trigger-row">
            <button
              className="action-btn-inspect"
              disabled={!file || isInspecting || isPredicting}
              onClick={runInspection}
            >
              <Activity size={16} />
              <span>{isInspecting ? 'HASHING BITSTREAM...' : 'INSPECT BITSTREAM'}</span>
            </button>

            <button
              className="action-btn-analyze"
              disabled={!file || isInspecting || isPredicting}
              onClick={runPrediction}
            >
              <Scan size={18} />
              <span>
                {isPredicting
                  ? 'SCANNING FORENSIC SIGNALS...'
                  : `ANALYZE ${activeModality.toUpperCase()}`}
              </span>
            </button>
          </div>

          {/* Inspection Receipt Card (When inspected without predicting) */}
          {inspectResult && !predictionData && (
            <div className="inspect-receipt-callout">
              <div className="flex items-center gap-2 mb-2">
                <CheckCircle2 size={18} className="text-cyan" />
                <strong className="cyber-mono text-sm">BITSTREAM RECEIPT VERIFIED</strong>
              </div>
              <p className="text-xs text-muted mb-2">{inspectResult.message}</p>
              <div className="hash-inline-box">
                <span className="text-muted text-xs cyber-mono">SHA-256:</span>
                <code className="text-cyan text-xs cyber-mono">{inspectResult.sha256}</code>
              </div>
            </div>
          )}

          {/* Forensic Results & Analysis Deck */}
          {currentVerdict && (
            <div className="forensic-verdict-section">
              <VerdictBanner
                verdict={currentVerdict}
                confidence={confidenceVal}
                realProbability={realProb}
                spoofProbability={spoofProb}
                threshold={result?.decision_threshold || 0.5}
                riskLevel={result?.risk_level}
                modality={activeModality}
                modelName={result?.model}
              />

              {/* Modality Specific Views */}
              {activeModality === 'audio' && result && (
                <AudioForensicView result={result as any} audioUrl={previewUrl} />
              )}

              {activeModality === 'image' && result && (
                <ImageForensicView result={result as any} previewUrl={previewUrl} />
              )}

              {activeModality === 'video' && result && (
                <VideoForensicView result={result as any} previewUrl={previewUrl} videoMode={videoMode} />
              )}

              {activeModality === 'fusion' && result && (
                <MultimodalFusionView result={result as any} previewUrl={previewUrl} />
              )}

              {/* Chain of Custody Evidence & Report Download */}
              <EvidencePanel
                filename={file?.name || predictionData?.filename || 'evidence_stream'}
                bytes={file?.size || inspectResult?.bytes || 0}
                sha256={sha256Val}
                modality={activeModality}
                verdict={currentVerdict}
                confidence={confidenceVal}
                result={result}
                uploadId={inspectResult?.upload_id}
              />
            </div>
          )}
        </section>
      </main>

      {/* Footer System Provenance */}
      <footer className="cyber-footer">
        <div className="footer-left">
          <span className="cyber-mono text-xs text-muted">
            VERISIGHT AI DEFENSE FORENSICS · CPU-ONLY REPRODUCIBLE PIPELINE · ASVSPOOF 2019 LA
          </span>
        </div>
        <div className="footer-right">
          <span className="cyber-mono text-xs text-muted">
            FORENSIC SIGNALS REQUIRE HUMAN-IN-THE-LOOP VALIDATION · ZERO FABRICATED DATA
          </span>
        </div>
      </footer>

      {/* Modals & Drawers */}
      <ModelTelemetryModal
        isOpen={isTelemetryOpen}
        onClose={() => setIsTelemetryOpen(false)}
        models={models}
        apiBase={API_BASE}
      />

      <AnalysisHistoryDrawer
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
        items={historyItems}
        onSelect={handleSelectHistoryItem}
        onClear={() => setHistoryItems([])}
      />
    </div>
  );
}
