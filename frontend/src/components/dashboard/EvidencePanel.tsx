import React, { useState } from 'react';
import {
  Database,
  BookOpen,
  RefreshCw,
  Search,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Clock,
  Share2,
  Layers
} from 'lucide-react';
import { useIngestionSync } from '../../hooks/useIngestionSync';
import type { IngestionSource } from '../../types/ingestion';

const SUGGESTED_TOPICS = [
  'Lithium dendrite solid electrolyte interphase',
  'Cobalt-free cathode high capacity doping',
  'Silicon anode volume expansion mitigation',
  'Sodium-ion layered oxide structural stability',
  'Halide solid electrolytes ionic conductivity'
];

const STOP_REASONS: Record<string, string> = {
  quota_exhausted: 'LLM quota used up; the remaining chunks stay pending for the next run.',
  llm_unavailable: 'The LLM providers are unavailable; the remaining chunks stay pending.',
  neo4j_error: 'Neo4j rejected a write; the remaining chunks stay pending.',
};

const STORE_LABELS: Record<string, string> = { chroma: 'ChromaDB', neo4j: 'Neo4j' };

// null means the store could not be reached, which must not be shown as an empty store
const formatCount = (value: number | null | undefined, loading: boolean) =>
  loading ? '...' : value == null ? '\u2014' : value;

export default function EvidencePanel() {
  const [query, setQuery] = useState('');
  const [selectedSources, setSelectedSources] = useState<IngestionSource[]>(['all']);
  const {
    stats, loadingStats, statsUnavailable, refreshStats,
    isSyncing, activeTaskId, taskStatus, extractionStatus, errorMsg, startSync,
  } = useIngestionSync();
  const unreachableStores = stats ? Object.keys(stats.errors).map((key) => STORE_LABELS[key] ?? key) : [];

  const handleToggleSource = (source: IngestionSource) => {
    if (source === 'all') {
      setSelectedSources(['all']);
      return;
    }

    let updated = selectedSources.filter(s => s !== 'all');
    if (updated.includes(source)) {
      updated = updated.filter(s => s !== source);
    } else {
      updated.push(source);
    }

    if (updated.length === 0) {
      setSelectedSources(['all']);
    } else {
      setSelectedSources(updated);
    }
  };

  const handleStartSync = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!query.trim() || isSyncing) return;
    void startSync(query.trim(), selectedSources);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', maxWidth: '1080px', margin: '0 auto', width: '100%' }}>
      
      {/* Knowledge Base Overview Header */}
      <div style={{
        background: 'var(--surface-raised)',
        border: '1px solid var(--line)',
        borderRadius: '12px',
        padding: '1.5rem',
        boxShadow: '0 8px 32px rgba(0,0,0,0.2)'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.25rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', color: 'var(--brass-bright)' }}>
              <Database size={20} />
              <h2 style={{ margin: 0, fontSize: '1.25rem', fontFamily: 'var(--heading)', fontWeight: 600 }}>
                Evidence & Knowledge Base
              </h2>
            </div>
            <p style={{ margin: '0.4rem 0 0', color: 'var(--text-muted)', fontSize: '0.88rem' }}>
              Autonomous and on-demand synchronization with open scientific archives (arXiv, Wikipedia, Crossref, and PubMed NCBI).
            </p>
          </div>

          <button
            type="button"
            onClick={refreshStats}
            disabled={loadingStats}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              background: 'rgba(255,255,255,0.05)',
              border: '1px solid var(--line)',
              borderRadius: '8px',
              padding: '0.5rem 0.9rem',
              color: 'var(--text)',
              fontSize: '0.8rem',
              transition: 'all 0.2s ease'
            }}
          >
            <RefreshCw size={14} className={loadingStats ? 'animate-spin' : ''} />
            Refresh Stats
          </button>
        </div>

        {(statsUnavailable || unreachableStores.length > 0) && (
          <p style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', margin: '0 0 1rem', color: 'var(--danger)', fontSize: '0.8rem' }}>
            <AlertCircle size={14} />
            {statsUnavailable ? 'Knowledge base statistics are unavailable right now.' : `Could not reach: ${unreachableStores.join(', ')}.`}
          </p>
        )}

        {/* Metric Cards Grid */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '1rem'
        }}>
          <div style={{
            background: 'rgba(0,0,0,0.25)',
            border: '1px solid var(--line)',
            borderRadius: '10px',
            padding: '1rem'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--moss-light)', fontSize: '0.8rem', marginBottom: '0.4rem' }}>
              <BookOpen size={15} /> ChromaDB Vectors
            </div>
            <div style={{ fontSize: '1.6rem', fontWeight: 700, color: 'var(--paper)', fontFamily: 'var(--mono)' }}>
              {formatCount(stats?.chroma_literature_chunks, loadingStats)}
            </div>
            <small style={{ color: 'var(--text-dim)', fontSize: '0.72rem' }}>Indexed literature chunks</small>
          </div>

          <div style={{
            background: 'rgba(0,0,0,0.25)',
            border: '1px solid var(--line)',
            borderRadius: '10px',
            padding: '1rem'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--amber)', fontSize: '0.8rem', marginBottom: '0.4rem' }}>
              <Share2 size={15} /> Neo4j Entities
            </div>
            <div style={{ fontSize: '1.6rem', fontWeight: 700, color: 'var(--paper)', fontFamily: 'var(--mono)' }}>
              {formatCount(stats?.neo4j_nodes, loadingStats)}
            </div>
            <small style={{ color: 'var(--text-dim)', fontSize: '0.72rem' }}>Elements, materials, degradation nodes</small>
          </div>

          <div style={{
            background: 'rgba(0,0,0,0.25)',
            border: '1px solid var(--line)',
            borderRadius: '10px',
            padding: '1rem'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--brass-bright)', fontSize: '0.8rem', marginBottom: '0.4rem' }}>
              <Layers size={15} /> Neo4j Relationships
            </div>
            <div style={{ fontSize: '1.6rem', fontWeight: 700, color: 'var(--paper)', fontFamily: 'var(--mono)' }}>
              {formatCount(stats?.neo4j_relationships, loadingStats)}
            </div>
            <small style={{ color: 'var(--text-dim)', fontSize: '0.72rem' }}>Chemical & degradation pathways</small>
          </div>

          <div style={{
            background: 'rgba(0,0,0,0.25)',
            border: '1px solid var(--line)',
            borderRadius: '10px',
            padding: '1rem'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--moss)', fontSize: '0.8rem', marginBottom: '0.4rem' }}>
              <Clock size={15} /> Scheduled Sweep
            </div>
            <div style={{ fontSize: '1.05rem', fontWeight: 600, color: stats?.nightly_sweep_enabled ? 'var(--moss-light)' : 'var(--text-dim)', marginTop: '0.4rem' }}>
              {stats?.nightly_sweep_enabled ? 'Nightly (02:00 UTC)' : 'Off'}
            </div>
            <small style={{ color: 'var(--text-dim)', fontSize: '0.72rem' }}>
              {stats?.nightly_sweep_enabled ? 'Needs a running Celery Beat process' : 'Set NIGHTLY_HARVEST_ENABLED to schedule'}
            </small>
          </div>
        </div>
      </div>

      {/* Manual Ingestion Sync Box (Strategy 3) */}
      <div style={{
        background: 'var(--surface-raised)',
        border: '1px solid var(--line)',
        borderRadius: '12px',
        padding: '1.5rem',
        boxShadow: '0 8px 32px rgba(0,0,0,0.2)'
      }}>
        <h3 style={{ margin: '0 0 0.5rem', fontSize: '1.05rem', fontWeight: 600, color: 'var(--text)' }}>
          Sync Scientific Literature (On-Demand)
        </h3>
        <p style={{ margin: '0 0 1rem', color: 'var(--text-muted)', fontSize: '0.82rem' }}>
          Fetch recent papers, validate chemical formulas, generate embeddings, and extract knowledge triplets asynchronously without adding latency to the research chat.
        </p>

        <form onSubmit={handleStartSync} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
            <div style={{
              flex: 1,
              minWidth: '280px',
              display: 'flex',
              alignItems: 'center',
              background: 'var(--canvas-deep)',
              border: '1px solid var(--line)',
              borderRadius: '8px',
              padding: '0.6rem 0.9rem',
              gap: '0.5rem'
            }}>
              <Search size={16} color="var(--text-dim)" />
              <input
                type="text"
                placeholder="Enter battery chemistry topic (e.g. Cobalt-free cathode doping)..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--text)',
                  width: '100%',
                  outline: 'none',
                  fontSize: '0.9rem'
                }}
              />
            </div>

            <button
              type="submit"
              disabled={isSyncing || !query.trim()}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                background: isSyncing ? 'var(--surface-soft)' : 'var(--brass)',
                color: '#000',
                border: 'none',
                borderRadius: '8px',
                padding: '0.6rem 1.4rem',
                fontWeight: 600,
                fontSize: '0.9rem',
                cursor: (isSyncing || !query.trim()) ? 'not-allowed' : 'pointer',
                transition: 'all 0.2s ease',
                boxShadow: isSyncing ? 'none' : '0 4px 14px rgba(199, 152, 88, 0.3)'
              }}
            >
              {isSyncing ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  Syncing…
                </>
              ) : (
                <>
                  <RefreshCw size={16} />
                  Harvest Literature
                </>
              )}
            </button>
          </div>

          {/* Source Filter Selectors */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap', fontSize: '0.8rem' }}>
            <span style={{ color: 'var(--text-dim)', marginRight: '0.2rem' }}>Target Archives:</span>
            
            {(['all', 'arxiv', 'wikipedia', 'crossref', 'pubmed'] as IngestionSource[]).map((src) => {
              const isSelected = selectedSources.includes(src);
              const labelMap: Record<IngestionSource, string> = {
                all: 'All Sources',
                arxiv: 'arXiv (Preprints)',
                wikipedia: 'Wikipedia (Structural)',
                crossref: 'Crossref (DOIs)',
                pubmed: 'PubMed (NCBI)'
              };

              return (
                <button
                  key={src}
                  type="button"
                  onClick={() => handleToggleSource(src)}
                  style={{
                    background: isSelected ? 'rgba(199, 152, 88, 0.2)' : 'rgba(255,255,255,0.03)',
                    border: `1px solid ${isSelected ? 'var(--brass-bright)' : 'var(--line)'}`,
                    color: isSelected ? 'var(--brass-bright)' : 'var(--text-muted)',
                    borderRadius: '20px',
                    padding: '0.25rem 0.75rem',
                    fontSize: '0.78rem',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                >
                  {labelMap[src]}
                </button>
              );
            })}
          </div>

          {/* Quick Preset Topics */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap', fontSize: '0.75rem' }}>
            <span style={{ color: 'var(--text-dim)' }}>Suggestions:</span>
            {SUGGESTED_TOPICS.map((topic) => (
              <button
                key={topic}
                type="button"
                onClick={() => setQuery(topic)}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--moss-light)',
                  cursor: 'pointer',
                  textDecoration: 'underline',
                  padding: 0
                }}
              >
                {topic}
              </button>
            ))}
          </div>
        </form>

        {errorMsg && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            color: 'var(--danger)',
            fontSize: '0.85rem',
            marginTop: '1rem',
            background: 'rgba(213, 154, 114, 0.1)',
            padding: '0.6rem 0.9rem',
            borderRadius: '6px'
          }}>
            <AlertCircle size={16} />
            {errorMsg}
          </div>
        )}

        {/* Live Task Progress Card */}
        {taskStatus && (
          <div style={{
            marginTop: '1.25rem',
            background: 'rgba(0,0,0,0.3)',
            border: `1px solid ${taskStatus.status === 'Complete' ? 'var(--moss)' : taskStatus.status === 'Failed' ? 'var(--danger)' : 'var(--line-strong)'}`,
            borderRadius: '10px',
            padding: '1rem'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.6rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                {taskStatus.status === 'Complete' ? (
                  <CheckCircle2 size={18} color="var(--moss-light)" />
                ) : taskStatus.status === 'Failed' ? (
                  <AlertCircle size={18} color="var(--danger)" />
                ) : (
                  <Loader2 size={18} className="animate-spin" color="var(--brass-bright)" />
                )}
                <strong style={{ fontSize: '0.9rem', color: 'var(--paper)' }}>
                  {taskStatus.status === 'Complete' ? 'Synchronization Finished' : taskStatus.status === 'Failed' ? 'Synchronization Failed' : 'Sync in Progress'}
                </strong>
              </div>

              <span style={{
                fontSize: '0.75rem',
                padding: '0.2rem 0.6rem',
                borderRadius: '12px',
                background: taskStatus.status === 'Complete' ? 'rgba(143, 155, 104, 0.2)' : taskStatus.status === 'Failed' ? 'rgba(213, 154, 114, 0.15)' : 'rgba(199, 152, 88, 0.2)',
                color: taskStatus.status === 'Complete' ? 'var(--moss-light)' : taskStatus.status === 'Failed' ? 'var(--danger)' : 'var(--brass-bright)',
                textTransform: 'uppercase',
                letterSpacing: '0.04em',
                fontWeight: 600
              }}>
                {taskStatus.stage || taskStatus.status}
              </span>
            </div>

            <p style={{ margin: '0 0 0.75rem', color: 'var(--text-muted)', fontSize: '0.82rem' }}>
              {taskStatus.status === 'Failed' ? (taskStatus.error ?? taskStatus.message) : taskStatus.message}
            </p>

            <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap', fontSize: '0.78rem', color: 'var(--text-dim)', borderTop: '1px solid var(--line)', paddingTop: '0.6rem' }}>
              {activeTaskId && <div>Job ID: <code style={{ color: 'var(--paper)', fontSize: '0.75rem' }}>{activeTaskId.slice(0, 8)}</code></div>}
              <div>Found: <strong style={{ color: 'var(--paper)' }}>{taskStatus.papers_found ?? 0}</strong></div>
              <div>Newly Indexed: <strong style={{ color: 'var(--brass-bright)' }}>{taskStatus.new_papers_indexed ?? 0}</strong></div>
              {taskStatus.sources && (
                <div>Sources: <span style={{ color: 'var(--paper)' }}>{taskStatus.sources.join(', ')}</span></div>
              )}
            </div>

            {taskStatus.source_errors && Object.keys(taskStatus.source_errors).length > 0 && (
              <ul style={{ margin: '0.75rem 0 0', paddingLeft: '1.1rem', color: 'var(--danger)', fontSize: '0.78rem' }}>
                {Object.entries(taskStatus.source_errors).map(([source, reason]) => (
                  <li key={source}>{source}: {reason}</li>
                ))}
              </ul>
            )}

            {extractionStatus && (
              <div style={{ marginTop: '0.75rem', borderTop: '1px solid var(--line)', paddingTop: '0.6rem', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                <strong style={{ color: 'var(--paper)' }}>Graph extraction: </strong>
                {extractionStatus.status === 'Failed'
                  ? (extractionStatus.error ?? 'failed')
                  : extractionStatus.status === 'Complete'
                    ? `${extractionStatus.triplets_ingested ?? 0} triplets from ${extractionStatus.chunks_extracted ?? 0} chunks, ${extractionStatus.chunks_pending ?? 0} pending.`
                    : (extractionStatus.message ?? 'in progress...')}
                {extractionStatus.stopped_reason && ` ${STOP_REASONS[extractionStatus.stopped_reason] ?? extractionStatus.stopped_reason}`}
              </div>
            )}
          </div>
        )}
      </div>

    </div>
  );
}
