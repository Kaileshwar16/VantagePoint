import { useState, useEffect, useCallback } from 'react';
import { getSignals, getCompanies, captureSignals, getCompoundSignals } from '../services/api';
import { Radar, Search, Zap, DollarSign, FileText, Briefcase, ChevronDown, ChevronUp, ExternalLink } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, PieChart, Pie, Cell } from 'recharts';

const tooltipStyle = { background: '#fff', border: '1px solid #e2e5ea', borderRadius: 6, boxShadow: '0 4px 12px rgba(0,0,0,0.08)', fontSize: 12 };
const COLORS = ['#ff5733', '#1976d2', '#00a67d', '#7b61ff', '#f5a623', '#0097a7', '#e53935'];

// ─── Proper human-readable label maps ───
const TYPE_LABEL = {
  job_posting: 'Job Posting', patent_filing: 'Patent Filing', pricing_change: 'Pricing Change',
  earnings_keyword: 'Earnings Keyword', leadership_change: 'Leadership Change',
  funding_event: 'Funding Event', product_signal: 'Product Signal',
};
const TYPE_BADGE = {
  job_posting: 'badge-blue', patent_filing: 'badge-purple', pricing_change: 'badge-amber',
  earnings_keyword: 'badge-cyan', leadership_change: 'badge-red',
  funding_event: 'badge-green', product_signal: 'badge-pink',
};
const ROLE_LABEL = {
  engineering: 'Engineering', ai_ml: 'AI / ML', sales: 'Sales', marketing: 'Marketing',
  product: 'Product', data: 'Data', security: 'Security', support: 'Customer Success',
  executive: 'Executive', other: 'Other',
};
const SENIORITY_LABEL = {
  c_level: 'C-Level', vp: 'VP', director: 'Director', senior: 'Senior',
  mid: 'Mid-Level', entry: 'Entry-Level',
};
const SEV_LABEL = { critical: 'Critical', high: 'High', medium: 'Medium', low: 'Low' };
const SEV_BADGE = { critical: 'badge-red', high: 'badge-amber', medium: 'badge-blue', low: 'badge-green' };

function SignalRow({ s }) {
  const [open, setOpen] = useState(false);
  return (<>
    <tr onClick={() => setOpen(!open)} style={{ cursor: 'pointer' }}>
      <td style={{ fontWeight: 500, color: 'var(--text-primary)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          {open ? <ChevronUp size={13} style={{ color: 'var(--text-muted)', flexShrink: 0 }} /> : <ChevronDown size={13} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />}
          <span>{s.title}</span>
        </div>
      </td>
      <td style={{ fontWeight: 600, color: 'var(--accent)', fontSize: 13 }}>{s.company_name}</td>
      <td><span className={`badge ${TYPE_BADGE[s.signal_type] || 'badge-blue'}`}>{TYPE_LABEL[s.signal_type] || s.signal_type}</span></td>
      <td>
        {s.role_type && <span className="badge badge-blue">{ROLE_LABEL[s.role_type] || s.role_type}</span>}
        {s.keyword && <span className="badge badge-cyan">{s.keyword}</span>}
        {s.patent_category && <span className="badge badge-purple">{s.patent_category}</span>}
      </td>
      <td>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div style={{ width: 40, height: 5, background: 'var(--bg-muted)', borderRadius: 3, overflow: 'hidden' }}>
            <div style={{ width: `${s.strength * 100}%`, height: '100%', borderRadius: 3, background: s.strength > 0.7 ? 'var(--green)' : s.strength > 0.4 ? 'var(--amber)' : '#8e8ea0' }} />
          </div>
          <span style={{ fontSize: 11, fontWeight: 600 }}>{Math.round(s.strength * 100)}%</span>
        </div>
      </td>
      <td style={{ fontSize: 12, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>{new Date(s.captured_at).toLocaleDateString()}</td>
    </tr>
    {open && <tr><td colSpan={6} style={{ padding: '12px 14px 16px 38px', background: 'var(--bg-muted)', borderBottom: '1px solid var(--border)' }}>
      <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7 }}>
        {s.description || 'No additional details.'}

        {/* Structured metadata */}
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginTop: 10 }}>
          {s.seniority_level && (
            <div style={{ fontSize: 12 }}><span style={{ color: 'var(--text-muted)' }}>Seniority:</span> <strong>{SENIORITY_LABEL[s.seniority_level] || s.seniority_level}</strong></div>
          )}
          {s.role_type && (
            <div style={{ fontSize: 12 }}><span style={{ color: 'var(--text-muted)' }}>Department:</span> <strong>{ROLE_LABEL[s.role_type] || s.role_type}</strong></div>
          )}
          {s.quarter && (
            <div style={{ fontSize: 12 }}><span style={{ color: 'var(--text-muted)' }}>Quarter:</span> <strong>{s.quarter}</strong></div>
          )}
          {s.velocity !== 0 && s.velocity !== undefined && (
            <div style={{ fontSize: 12 }}><span style={{ color: 'var(--text-muted)' }}>Velocity:</span> <strong style={{ color: s.velocity > 0 ? 'var(--green)' : 'var(--red)' }}>{s.velocity > 0 ? '+' : ''}{(s.velocity * 100).toFixed(0)}%</strong></div>
          )}
          {s.anomaly_score > 0 && (
            <div style={{ fontSize: 12 }}><span style={{ color: 'var(--text-muted)' }}>Anomaly:</span> <strong style={{ color: 'var(--amber)' }}>{s.anomaly_score.toFixed(1)}σ</strong></div>
          )}
        </div>

        {/* Pricing diff */}
        {s.diff_summary && (
          <div style={{ marginTop: 10, padding: 10, background: '#fff', border: '1px solid var(--border)', borderRadius: 4, fontFamily: 'monospace', fontSize: 11, whiteSpace: 'pre-wrap', maxHeight: 200, overflow: 'auto' }}>{s.diff_summary}</div>
        )}

        {/* Source link */}
        {s.source_url && (
          <div style={{ marginTop: 10 }}>
            <a href={s.source_url} target="_blank" rel="noreferrer" style={{ fontSize: 12, display: 'inline-flex', alignItems: 'center', gap: 4, color: 'var(--accent)' }}>
              View Source <ExternalLink size={11} />
            </a>
          </div>
        )}
      </div>
    </td></tr>}
  </>);
}

export default function Signals() {
  const [signals, setSignals] = useState([]);
  const [compounds, setCompounds] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [capturing, setCapturing] = useState({});
  const [tab, setTab] = useState('all');
  const [search, setSearch] = useState('');


  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [sR, csR, coR] = await Promise.all([getSignals({ page_size: 200 }), getCompoundSignals(), getCompanies()]);
      setSignals(sR.data.results || sR.data);
      setCompounds(csR.data.results || csR.data);
      setCompanies(coR.data.results || coR.data);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { const timer = setTimeout(() => { fetchAll(); }, 0); return () => clearTimeout(timer); }, [fetchAll]);

  const handleCapture = async (companyId) => {
    setCapturing(p => ({ ...p, [companyId]: true }));
    try { await captureSignals(companyId); await fetchAll(); } catch (e) { console.error(e); }
    finally { setCapturing(p => ({ ...p, [companyId]: false })); }
  };

  const typeData = signals.reduce((acc, s) => { acc[s.signal_type] = (acc[s.signal_type] || 0) + 1; return acc; }, {});
  const typePie = Object.entries(typeData).map(([name, value]) => ({ name: TYPE_LABEL[name] || name, value }));

  const roleData = signals.filter(s => s.signal_type === 'job_posting' && s.role_type).reduce((acc, s) => { const label = ROLE_LABEL[s.role_type] || s.role_type; acc[label] = (acc[label] || 0) + 1; return acc; }, {});
  const roleBar = Object.entries(roleData).map(([name, count]) => ({ name, count })).sort((a, b) => b.count - a.count);

  const filtered = signals.filter(s => {
    if (tab !== 'all' && s.signal_type !== tab) return false;
    if (search && !s.title.toLowerCase().includes(search.toLowerCase()) && !s.company_name?.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  if (loading) return <div className="loading"><div className="spinner" /></div>;

  return (
    <div>
      <div className="card" style={{ marginBottom: 16 }}>Automated signal candidates require source review. A news mention does not confirm a job opening, patent filing, or earnings transcript. Scores are heuristic; dates show collection time.</div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Signal Capture</h1>
          <p className="page-desc">{signals.length} signals captured · {compounds.length} compound signals detected</p>
        </div>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {companies.slice(0, 4).map(c => (
            <button key={c.id} className="btn btn-sm btn-secondary" onClick={() => handleCapture(c.id)} disabled={capturing[c.id]}>
              <Radar size={12} /> {capturing[c.id] ? 'Scanning...' : c.name}
            </button>
          ))}
        </div>
      </div>

      {/* Stats */}
      <div className="stats-grid">
        <div className="stat-card"><Briefcase size={16} style={{ color: 'var(--accent)', marginBottom: 4 }} /><div className="stat-label">Job Postings</div><div className="stat-value">{typeData.job_posting || 0}</div></div>
        <div className="stat-card"><FileText size={16} style={{ color: '#7b61ff', marginBottom: 4 }} /><div className="stat-label">Patent Filings</div><div className="stat-value">{typeData.patent_filing || 0}</div></div>
        <div className="stat-card"><DollarSign size={16} style={{ color: 'var(--amber)', marginBottom: 4 }} /><div className="stat-label">Pricing Changes</div><div className="stat-value">{typeData.pricing_change || 0}</div></div>
        <div className="stat-card"><Zap size={16} style={{ color: '#0097a7', marginBottom: 4 }} /><div className="stat-label">Earnings Keywords</div><div className="stat-value">{typeData.earnings_keyword || 0}</div></div>
      </div>

      {/* Charts */}
      <div className="grid-2">
        <div className="card">
          <div className="card-header"><span className="card-title">Signals by Type</span></div>
          {typePie.length > 0 ? <ResponsiveContainer width="100%" height={220}>
            <PieChart><Pie data={typePie} cx="50%" cy="50%" innerRadius={45} outerRadius={80} paddingAngle={3} dataKey="value" strokeWidth={0}>
              {typePie.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
            </Pie><Tooltip contentStyle={tooltipStyle} /></PieChart>
          </ResponsiveContainer> : <div className="empty-state"><p>No signals yet</p></div>}
        </div>
        <div className="card">
          <div className="card-header"><span className="card-title">Hiring by Department</span></div>
          {roleBar.length > 0 ? <ResponsiveContainer width="100%" height={220}>
            <BarChart data={roleBar} layout="vertical"><CartesianGrid strokeDasharray="3 3" stroke="#eef0f4" />
              <XAxis type="number" tick={{ fill: '#8e8ea0', fontSize: 10 }} /><YAxis type="category" dataKey="name" width={110} tick={{ fill: '#5e5e76', fontSize: 11 }} />
              <Tooltip contentStyle={tooltipStyle} /><Bar dataKey="count" fill="#ff5733" radius={[0, 3, 3, 0]} />
            </BarChart>
          </ResponsiveContainer> : <div className="empty-state"><p>No job posting data yet. Click Capture.</p></div>}
        </div>
      </div>

      {/* Compound Signals */}
      {compounds.length > 0 && (
        <div className="card" style={{ marginBottom: 16, borderLeft: '3px solid var(--accent)' }}>
          <div className="card-header"><span className="card-title">⚡ Compound Signals</span></div>
          {compounds.map(cs => (
            <div key={cs.id} style={{ padding: '12px 0', borderBottom: '1px solid var(--border-light)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                <strong style={{ color: 'var(--text-primary)', fontSize: 14 }}>{cs.title}</strong>
                <div style={{ display: 'flex', gap: 6 }}>
                  <span className={`badge ${SEV_BADGE[cs.severity] || 'badge-blue'}`}>{SEV_LABEL[cs.severity] || cs.severity}</span>
                  <span className="badge badge-purple">{Math.round(cs.confidence * 100)}% conf.</span>
                </div>
              </div>
              <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.5, margin: 0 }}>{cs.hypothesis}</p>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>{cs.signal_count} independent signals in {cs.time_window_days}-day window · Detected {new Date(cs.detected_at).toLocaleDateString()}</div>
            </div>
          ))}
        </div>
      )}

      {/* Filter tabs */}
      <div className="tabs">
        {['all', ...Object.keys(typeData)].map(t => (
          <button key={t} className={`tab ${tab === t ? 'active' : ''}`} onClick={() => setTab(t)}>
            {t === 'all' ? `All (${signals.length})` : `${TYPE_LABEL[t] || t} (${typeData[t] || 0})`}
          </button>
        ))}
      </div>

      <div style={{ marginBottom: 12 }}>
        <div style={{ position: 'relative', maxWidth: 340 }}>
          <Search size={14} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
          <input className="input" placeholder="Search signals..." value={search} onChange={e => setSearch(e.target.value)} style={{ paddingLeft: 34 }} />
        </div>
      </div>

      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        {filtered.length === 0 ? <div className="empty-state" style={{ padding: 40 }}><h3>No signals</h3><p>Click company buttons above to capture signals.</p></div> : (
          <table className="data-table">
            <thead><tr><th>Signal</th><th>Company</th><th>Type</th><th>Detail</th><th>Strength</th><th>Date</th></tr></thead>
            <tbody>{filtered.map(s => <SignalRow key={s.id} s={s} />)}</tbody>
          </table>
        )}
      </div>
    </div>
  );
}
