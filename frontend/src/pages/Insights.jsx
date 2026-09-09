import { useState, useEffect, useCallback } from 'react';
import { getInsights, updateInsight } from '../services/api';
import { Check, X } from 'lucide-react';

const priBadge = { urgent: 'badge-red', high: 'badge-amber', medium: 'badge-blue', low: 'badge-green' };
const statusBadge = { new: 'badge-green', reviewed: 'badge-blue', acted_on: 'badge-purple', dismissed: 'badge-amber' };

export default function Insights() {
  const [insights, setInsights] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');

  const fetchInsights = useCallback(async () => { setLoading(true); try { const r = await getInsights(); setInsights(r.data.results || r.data); } catch(e){ console.error(e); } finally { setLoading(false); } }, []);

  useEffect(() => { const timer = setTimeout(() => { fetchInsights(); }, 0); return () => clearTimeout(timer); }, [fetchInsights]);
  const handleStatus = async (id, status) => { try { await updateInsight(id, { status }); fetchInsights(); } catch(e){ console.error(e); } };

  const filtered = filter === 'all' ? insights : insights.filter(i => i.priority === filter);

  if (loading) return <div className="loading"><div className="spinner" /></div>;

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Insights</h1>
          <p className="page-desc">Rule-based hypotheses for review; scores are not calibrated probabilities</p>
        </div>
      </div>

      <div className="tabs">
        {['all', 'urgent', 'high', 'medium', 'low'].map(f => (
          <button key={f} className={`tab ${filter === f ? 'active' : ''}`} onClick={() => setFilter(f)} style={{ textTransform: 'capitalize' }}>
            {f}{f !== 'all' && ` (${insights.filter(i => i.priority === f).length})`}
          </button>
        ))}
      </div>

      {filtered.length === 0 ? <div className="empty-state"><h3>No insights found</h3><p>Run analysis on companies to generate.</p></div> :
        filtered.map(ins => (
          <div className="insight-card" key={ins.id}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 4 }}>
              <div>
                <div className="insight-title">{ins.title}</div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{ins.company_name} · {new Date(ins.created_at).toLocaleDateString()}</div>
              </div>
              <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                <span className={`badge ${priBadge[ins.priority]}`}>{ins.priority}</span>
                <span className={`badge ${statusBadge[ins.status]}`}>{ins.status.replace(/_/g,' ')}</span>
              </div>
            </div>
            <div className="insight-desc" style={{ marginTop: 8 }}>{ins.description}</div>
            {ins.recommendation && (
              <div style={{ padding: '10px 14px', background: 'var(--green-bg)', borderRadius: 5, marginBottom: 10, fontSize: 12, color: '#006644', borderLeft: '3px solid var(--green)' }}>
                <div style={{ fontWeight: 700, marginBottom: 6, color: 'var(--green)' }}>💡 Action Plan:</div>
                {ins.recommendation.includes('\n') ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                    {ins.recommendation.split('\n').filter(Boolean).map((line, i) => (
                      <div key={i} style={{ display: 'flex', gap: 6, lineHeight: 1.5 }}>
                        <span>{line}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <span>{ins.recommendation}</span>
                )}
              </div>
            )}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
              <div className="insight-meta">
                {ins.predicted_timeline && <span className="badge badge-cyan">⏱ {ins.predicted_timeline}</span>}
                <span className="badge badge-purple">{Math.round(ins.probability * 100)}% heuristic score</span>
              </div>
              {ins.status === 'new' && (
                <div style={{ display: 'flex', gap: 6 }}>
                  <button className="btn btn-sm btn-primary" onClick={() => handleStatus(ins.id, 'acted_on')}><Check size={12} /> Act On</button>
                  <button className="btn btn-sm btn-secondary" onClick={() => handleStatus(ins.id, 'dismissed')}><X size={12} /> Dismiss</button>
                </div>
              )}
            </div>
          </div>
        ))}
    </div>
  );
}
