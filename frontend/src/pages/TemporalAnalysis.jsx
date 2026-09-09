import { useState, useEffect } from 'react';
import { getCompanies, getTimelineOverlay } from '../services/api';
import { GitCompare, } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from 'recharts';

const COLORS = ['#ff5733', '#1976d2', '#00a67d', '#7b61ff', '#f5a623', '#0097a7'];
const tooltipStyle = { background: '#fff', border: '1px solid #e2e5ea', borderRadius: 6, boxShadow: '0 4px 12px rgba(0,0,0,0.08)', fontSize: 12 };
const CAT_BADGE = { product_launch: 'badge-green', pricing_change: 'badge-amber', hiring: 'badge-cyan', partnership: 'badge-purple', funding: 'badge-pink', expansion: 'badge-blue', job_posting: 'badge-blue', patent_filing: 'badge-purple', earnings_keyword: 'badge-cyan', technology: 'badge-cyan', leadership: 'badge-amber', news: 'badge-blue', signal: 'badge-purple' };
const CAT_LABEL = { product_launch: 'Product Launch', pricing_change: 'Pricing Change', hiring: 'Hiring', partnership: 'Partnership', funding: 'Funding', expansion: 'Expansion', job_posting: 'Job Posting', patent_filing: 'Patent Filing', earnings_keyword: 'Earnings', technology: 'Technology', leadership: 'Leadership', news: 'News', signal: 'Signal', acquisition: 'Acquisition', marketing: 'Marketing', legal: 'Legal' };

export default function TemporalAnalysis() {
  const [companies, setCompanies] = useState([]);
  const [selected, setSelected] = useState([]);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [days, setDays] = useState(180);

  useEffect(() => {
    (async () => {
      try { const r = await getCompanies(); setCompanies(r.data.results || r.data); } catch (e) { console.error(e); }
    })();
  }, []);

  const toggleCompany = (id) => {
    setSelected(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]);
  };

  const runOverlay = async () => {
    if (selected.length < 2) return;
    setLoading(true);
    try {
      const r = await getTimelineOverlay(selected, days);
      setData(r.data);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  // Build chart data — events per day for each company
  const buildChartData = () => {
    if (!data) return [];
    const allDates = new Set();
    const companyNames = Object.keys(data);

    companyNames.forEach(name => {
      data[name].events.forEach(e => allDates.add(e.date));
    });

    const sortedDates = [...allDates].sort();

    // Group by week for cleaner visualization
    const weeks = {};
    sortedDates.forEach(d => {
      const dt = new Date(d);
      const weekStart = new Date(dt);
      weekStart.setDate(dt.getDate() - dt.getDay());
      const key = weekStart.toISOString().slice(0, 10);
      if (!weeks[key]) weeks[key] = { date: key };
      companyNames.forEach(name => {
        if (!weeks[key][name]) weeks[key][name] = 0;
        const dayEvents = data[name].events.filter(e => e.date === d).length;
        weeks[key][name] += dayEvents;
      });
    });

    return Object.values(weeks).sort((a, b) => a.date.localeCompare(b.date));
  };

  const chartData = buildChartData();
  const companyNames = data ? Object.keys(data) : [];

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Temporal Analysis</h1>
          <p className="page-desc">Timeline overlay — compare competitor signal histories side-by-side</p>
        </div>
      </div>

      {/* Company selector */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div className="card-header"><span className="card-title">Select Companies to Compare (min 2)</span></div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
          {companies.map(c => (
            <button key={c.id} className={`btn btn-sm ${selected.includes(c.id) ? 'btn-primary' : 'btn-secondary'}`} onClick={() => toggleCompany(c.id)}>
              {c.name}
            </button>
          ))}
        </div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <select className="select" value={days} onChange={e => setDays(Number(e.target.value))} style={{ width: 150 }}>
            <option value={90}>Last 90 days</option>
            <option value={180}>Last 180 days</option>
            <option value={365}>Last year</option>
          </select>
          <button className="btn btn-primary" onClick={runOverlay} disabled={selected.length < 2 || loading}>
            <GitCompare size={14} /> {loading ? 'Loading...' : 'Compare'}
          </button>
        </div>
      </div>

      {data && (
        <>
          {/* Activity over time chart */}
          <div className="card" style={{ marginBottom: 16 }}>
            <div className="card-header"><span className="card-title">Signal Activity Over Time (Weekly)</span></div>
            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#eef0f4" />
                  <XAxis dataKey="date" tick={{ fill: '#8e8ea0', fontSize: 10 }} />
                  <YAxis tick={{ fill: '#8e8ea0', fontSize: 10 }} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Legend />
                  {companyNames.map((name, i) => (
                    <Line key={name} type="monotone" dataKey={name} stroke={COLORS[i % COLORS.length]} strokeWidth={2} dot={{ r: 3 }} />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            ) : <div className="empty-state"><p>No overlapping data</p></div>}
          </div>

          {/* Summary stats */}
          <div className="stats-grid">
            {companyNames.map((name, i) => (
              <div className="stat-card" key={name}>
                <div style={{ width: 8, height: 8, borderRadius: '50%', background: COLORS[i], marginBottom: 4 }} />
                <div className="stat-label">{name}</div>
                <div className="stat-value">{data[name].count} events</div>
              </div>
            ))}
          </div>

          {/* Side-by-side event timelines */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 12, marginTop: 16 }}>
            {companyNames.map((name, i) => (
              <div className="card" key={name} style={{ padding: 0, overflow: 'hidden' }}>
                <div style={{ padding: '10px 14px', borderBottom: '1px solid var(--border)', background: 'var(--bg-muted)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <div style={{ width: 8, height: 8, borderRadius: '50%', background: COLORS[i] }} />
                    <span style={{ fontWeight: 700, fontSize: 13, color: 'var(--text-primary)' }}>{name}</span>
                    <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 'auto' }}>{data[name].count} events</span>
                  </div>
                </div>
                <div style={{ maxHeight: 400, overflow: 'auto' }}>
                  {data[name].events.slice(0, 30).map((e, j) => (
                    <div key={j} style={{ padding: '8px 14px', borderBottom: '1px solid var(--border-light)', fontSize: 12 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
                        <span className={`badge ${CAT_BADGE[e.category] || 'badge-blue'}`} style={{ fontSize: 9 }}>{CAT_LABEL[e.category] || e.category}</span>
                        <span style={{ color: 'var(--text-muted)', fontSize: 10 }}>{e.date}</span>
                      </div>
                      <div style={{ color: 'var(--text-secondary)', lineHeight: 1.4 }}>{e.title}</div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
