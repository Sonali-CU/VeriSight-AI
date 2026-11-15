import React, { useState, useRef, useEffect } from 'react';
import { Volume2, Play, Pause, Waves, Radio, Activity, Cpu } from 'lucide-react';
import SpectrogramVisualizer3D from './3d/SpectrogramVisualizer3D';
import { AudioPredictionResult } from '../types';

interface AudioForensicViewProps {
  result: AudioPredictionResult;
  audioUrl?: string | null;
}

export default function AudioForensicView({ result, audioUrl }: AudioForensicViewProps) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [activeTab, setActiveTab] = useState<'spectrogram_2d' | 'spectrogram_3d'>('spectrogram_2d');
  const [currentTime, setCurrentTime] = useState(0);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const meta = result.metadata || {};
  const acoustic = result.acoustic_features || {};
  const duration = meta.duration_seconds || 2.0;

  // Render 2D Mel-Spectrogram Heatmap on Canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !result.spectrogram_preview?.data) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const data = result.spectrogram_preview.data;
    const rows = data.length;
    const cols = data[0]?.length || 0;
    if (rows === 0 || cols === 0) return;

    const width = canvas.width;
    const height = canvas.height;
    ctx.clearRect(0, 0, width, height);

    const cellW = width / cols;
    const cellH = height / rows;

    // Color gradient palette for forensic spectrogram: Deep indigo -> Cyan -> Magenta -> Lime
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        // Mel frequencies: row 0 is lowest frequency (drawn at bottom), row rows-1 is highest
        const val = data[rows - 1 - r][c];
        // Normalize roughly from [-2.5, 2.5] to [0, 1]
        const norm = Math.min(1, Math.max(0, (val + 2.0) / 4.0));

        // Color interpolation
        let red = 0, green = 0, blue = 0;
        if (norm < 0.25) {
          // Dark Navy to Violet
          const t = norm / 0.25;
          red = Math.floor(10 + t * 90);
          green = Math.floor(14 + t * 20);
          blue = Math.floor(40 + t * 150);
        } else if (norm < 0.55) {
          // Violet to Electric Cyan
          const t = (norm - 0.25) / 0.3;
          red = Math.floor(100 - t * 100);
          green = Math.floor(34 + t * 206);
          blue = Math.floor(190 + t * 65);
        } else if (norm < 0.85) {
          // Cyan to Laser Magenta
          const t = (norm - 0.55) / 0.3;
          red = Math.floor(t * 255);
          green = Math.floor(240 - t * 220);
          blue = Math.floor(255 - t * 127);
        } else {
          // Magenta to Electric Lime Peak
          const t = (norm - 0.85) / 0.15;
          red = Math.floor(255 - t * 255);
          green = Math.floor(20 + t * 235);
          blue = Math.floor(128 - t * 128);
        }

        ctx.fillStyle = `rgb(${red}, ${green}, ${blue})`;
        ctx.fillRect(c * cellW, r * cellH, cellW + 0.5, cellH + 0.5);
      }
    }

    // Draw playback cursor if active
    if (duration > 0 && currentTime > 0) {
      const cursorX = (currentTime / duration) * width;
      ctx.strokeStyle = '#00ff88';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(cursorX, 0);
      ctx.lineTo(cursorX, height);
      ctx.stroke();
    }
  }, [result.spectrogram_preview, currentTime, duration, activeTab]);

  function togglePlay() {
    if (!audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      audioRef.current.play().then(() => setIsPlaying(true)).catch(() => {});
    }
  }

  function handleTimeUpdate() {
    if (audioRef.current) {
      setCurrentTime(audioRef.current.currentTime);
    }
  }

  function handleAudioEnded() {
    setIsPlaying(false);
    setCurrentTime(0);
  }

  return (
    <div className="audio-forensic-deck">
      <div className="forensic-subcard-header">
        <div className="flex items-center gap-2">
          <Waves className="text-cyan" size={20} />
          <h3>AUDIO FORENSIC SPECTROGRAM & TELEMETRY</h3>
        </div>
        <div className="view-toggle-pills">
          <button
            className={`pill-btn ${activeTab === 'spectrogram_2d' ? 'active' : ''}`}
            onClick={() => setActiveTab('spectrogram_2d')}
          >
            2D Log-Mel Heatmap
          </button>
          <button
            className={`pill-btn ${activeTab === 'spectrogram_3d' ? 'active' : ''}`}
            onClick={() => setActiveTab('spectrogram_3d')}
          >
            3D Frequency Mesh
          </button>
        </div>
      </div>

      {/* Audio Playback Player */}
      {audioUrl && (
        <div className="audio-player-bar">
          <audio
            ref={audioRef}
            src={audioUrl}
            onTimeUpdate={handleTimeUpdate}
            onEnded={handleAudioEnded}
          />
          <button className="audio-play-trigger" onClick={togglePlay}>
            {isPlaying ? <Pause size={18} /> : <Play size={18} />}
          </button>
          <div className="player-meta">
            <Volume2 size={16} className="text-cyan" />
            <span className="cyber-mono text-sm">{meta.filename || 'Sample Audio'}</span>
          </div>
          <div className="player-progress-track">
            <div
              className="player-progress-fill"
              style={{ width: `${(currentTime / Math.max(0.1, duration)) * 100}%` }}
            />
          </div>
          <span className="cyber-mono text-xs text-muted">
            {currentTime.toFixed(1)}s / {duration.toFixed(1)}s
          </span>
        </div>
      )}

      {/* Spectrogram Container */}
      <div className="spectrogram-canvas-container">
        {activeTab === 'spectrogram_2d' ? (
          <div className="spectrogram-2d-view">
            <div className="spec-y-axis">
              <span>8.0 kHz</span>
              <span>4.0 kHz</span>
              <span>1.0 kHz</span>
              <span>0 Hz</span>
            </div>
            <div className="spec-canvas-wrapper">
              <canvas
                ref={canvasRef}
                width={700}
                height={220}
                className="spec-canvas"
              />
              <div className="spec-x-axis">
                <span>0.0s</span>
                <span>{(duration * 0.25).toFixed(1)}s</span>
                <span>{(duration * 0.5).toFixed(1)}s</span>
                <span>{(duration * 0.75).toFixed(1)}s</span>
                <span>{duration.toFixed(1)}s</span>
              </div>
            </div>
            <div className="spec-legend">
              <span className="text-xs cyber-mono text-muted">AMPLITUDE (dB)</span>
              <div className="legend-gradient" />
              <div className="legend-labels">
                <span>-80 dB</span>
                <span>-40 dB</span>
                <span>0 dB</span>
              </div>
            </div>
          </div>
        ) : (
          <SpectrogramVisualizer3D
            spectrogramData={result.spectrogram_preview?.data}
            audioDuration={duration}
          />
        )}
      </div>

      {/* Acoustic Telemetry Metrics Grid */}
      <div className="acoustic-telemetry-grid">
        <div className="telemetry-stat-card">
          <div className="stat-icon-wrapper text-cyan">
            <Activity size={18} />
          </div>
          <div className="stat-details">
            <small className="cyber-mono text-muted">RMS ENERGY</small>
            <strong className="text-white">{(acoustic.rms ?? 0).toFixed(4)}</strong>
            <span className="text-xs text-muted">Signal amplitude intensity</span>
          </div>
        </div>

        <div className="telemetry-stat-card">
          <div className="stat-icon-wrapper text-magenta">
            <Radio size={18} />
          </div>
          <div className="stat-details">
            <small className="cyber-mono text-muted">ZERO CROSSING RATE</small>
            <strong className="text-white">{(acoustic.zero_crossing_rate ?? 0).toFixed(4)}</strong>
            <span className="text-xs text-muted">High-freq noise density</span>
          </div>
        </div>

        <div className="telemetry-stat-card">
          <div className="stat-icon-wrapper text-lime">
            <Waves size={18} />
          </div>
          <div className="stat-details">
            <small className="cyber-mono text-muted">SPECTRAL CENTROID</small>
            <strong className="text-white">{Math.round(acoustic.spectral_centroid_approx_hz ?? 0)} Hz</strong>
            <span className="text-xs text-muted">Acoustic center of mass</span>
          </div>
        </div>

        <div className="telemetry-stat-card">
          <div className="stat-icon-wrapper text-purple">
            <Cpu size={18} />
          </div>
          <div className="stat-details">
            <small className="cyber-mono text-muted">CODEC & BITRATE</small>
            <strong className="text-white">{meta.format || 'PCM'} · {meta.sample_rate || 16000} Hz</strong>
            <span className="text-xs text-muted">{meta.channels === 1 ? 'Mono' : 'Stereo'} · {meta.subtype || '16-bit'}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
