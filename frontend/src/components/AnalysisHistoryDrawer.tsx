import React from 'react';
import { X, History, FileAudio, FileVideo, FileImage, ShieldCheck, ShieldAlert, AlertTriangle } from 'lucide-react';
import { AnalysisHistoryItem } from '../types';
import { formatBytes } from '../utils/webgl';

interface AnalysisHistoryDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  items: AnalysisHistoryItem[];
  onSelect: (item: AnalysisHistoryItem) => void;
  onClear: () => void;
}

export default function AnalysisHistoryDrawer({
  isOpen,
  onClose,
  items,
  onSelect,
  onClear
}: AnalysisHistoryDrawerProps) {
  if (!isOpen) return null;

  return (
    <div className="history-drawer-backdrop" onClick={onClose}>
      <aside className="history-drawer-panel" onClick={(e) => e.stopPropagation()}>
        <div className="history-drawer-header">
          <div className="flex items-center gap-2">
            <History size={20} className="text-cyan" />
            <div>
              <h3>FORENSIC AUDIT LOG</h3>
              <span className="cyber-mono text-xs text-muted">{items.length} SESSION RECORDS</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {items.length > 0 && (
              <button className="clear-history-btn" onClick={onClear}>
                Clear
              </button>
            )}
            <button className="drawer-close-btn" onClick={onClose}>
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="history-drawer-list">
          {items.length === 0 ? (
            <div className="empty-history-notice">
              <History size={36} className="text-muted mb-2 mx-auto" />
              <p>No media files analyzed yet in this session.</p>
              <small className="text-muted">Uploaded investigations will be logged here with SHA-256 hashes.</small>
            </div>
          ) : (
            items.map((item) => {
              const isSpoof = item.verdict === 'SPOOF-LIKE';
              const isReal = item.verdict === 'REAL-LIKE';

              return (
                <div
                  key={item.id}
                  className="history-item-card"
                  onClick={() => {
                    onSelect(item);
                    onClose();
                  }}
                >
                  <div className="item-header">
                    <div className="flex items-center gap-2">
                      {item.modality === 'audio' && <FileAudio size={16} className="text-cyan" />}
                      {item.modality === 'video' && <FileVideo size={16} className="text-magenta" />}
                      {item.modality === 'image' && <FileImage size={16} className="text-lime" />}
                      <strong className="item-name truncate max-w-[150px]">{item.filename}</strong>
                    </div>
                    <span className={`verdict-pill-mini ${isSpoof ? 'pill-spoof' : isReal ? 'pill-real' : 'pill-inconclusive'}`}>
                      {item.verdict}
                    </span>
                  </div>

                  <div className="item-meta">
                    <span className="cyber-mono text-xs text-muted">{formatBytes(item.fileSize)}</span>
                    <span className="cyber-mono text-xs text-cyan">{(item.confidence * 100).toFixed(1)}% CONF</span>
                    <span className="cyber-mono text-xs text-muted">{item.timestamp}</span>
                  </div>

                  <div className="item-hash">
                    <code className="text-xs text-muted truncate">{item.sha256}</code>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </aside>
    </div>
  );
}
