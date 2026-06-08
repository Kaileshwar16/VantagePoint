import { useState, useEffect } from 'react';
import { getPatterns } from '../services/api';

const typeBadge = { trend: 'badge-blue', cycle: 'badge-cyan', anomaly: 'badge-red', correlation: 'badge-purple', strategy_shift: 'badge-amber' };

export default function Patterns() {
  const [patterns, setPatterns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    (async () => {
      setLoading(true);
      try { const r = await getPatterns(); setPatterns(r.data.results || r.data); }
      catch (e) { console.error(e); }
      finally { setLoading(false); }
    })();
  }, []);

  const filtered = filter === 'all' ? patterns : patterns.filter(p => p.pattern_type === filter);
  const types = ['all', ...new Set(patterns.map(p => p.pattern_type))];

  if (loading) return <div className="loading"><div className="spinner" /></div>;

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Patterns</h1>
          <p className="page-desc">Behavioral patterns detected across competitors</p>
        </div>
      </div>

      <div className="tabs">
        {types.map(f => (
          <button key={f} className={`tab ${filter === f ? 'active' : ''}`} onClick={() => setFilter(f)}>
            {f === 'all' ? 'All' : f.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
            {f !== 'all' && ` (${patterns.filter(p => p.pattern_type === f).length})`}
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <div className="empty-state"><h3>No patterns found</h3><p>Run analysis on companies to detect patterns.</p></div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Pattern</th>
                <th>Company</th>
                <th>Type</th>
                <th>Confidence</th>
                <th>Status</th>
                <th>Detected</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(p => (
                <tr key={p.id}>
                  <td>
                    <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: 2 }}>{p.name}</div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)', maxWidth: 360 }}>
                      {p.description.length > 80 ? p.description.slice(0, 80) + '...' : p.description}
                    </div>
                  </td>
                  <td style={{ fontWeight: 500, color: 'var(--text-primary)' }}>{p.company_name}</td>
                  <td><span className={`badge ${typeBadge[p.pattern_type] || 'badge-blue'}`}>{p.pattern_type?.replace(/_/g, ' ')}</span></td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <div style={{ width: 60, height: 5, background: 'var(--bg-muted)', borderRadius: 3, overflow: 'hidden' }}>
                        <div style={{
                          width: `${p.confidence * 100}%`, height: '100%', borderRadius: 3,
                          background: p.confidence > 0.7 ? 'var(--green)' : p.confidence > 0.5 ? 'var(--amber)' : 'var(--red)',
                        }} />
                      </div>
                      <span style={{ fontSize: 12, color: 'var(--text-secondary)', fontWeight: 600 }}>{Math.round(p.confidence * 100)}%</span>
                    </div>
                  </td>
                  <td>{p.is_active ? <span className="badge badge-green">Active</span> : <span className="badge badge-amber">Inactive</span>}</td>
                  <td style={{ fontSize: 12, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>{new Date(p.detected_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
