import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getDashboard, runAllAnalysis } from '../services/api';
import { Building2, Database, TrendingUp, Lightbulb, RefreshCw, ArrowRight } from 'lucide-react';
import { AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';

const COLORS = ['#ff5733', '#1976d2', '#00a67d', '#7b61ff', '#f5a623', '#0097a7', '#e53935', '#c2185b', '#6d4c41', '#455a64'];

const priorityMap = { urgent: 'badge-red', high: 'badge-amber', medium: 'badge-blue', low: 'badge-green' };

const tooltipStyle = { background: '#fff', border: '1px solid #e2e5ea', borderRadius: 6, boxShadow: '0 4px 12px rgba(0,0,0,0.08)', fontSize: 12 };

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const nav = useNavigate();

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    setLoading(true);
    try { const r = await getDashboard(); setData(r.data); }
    catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  const handleAnalyze = async () => {
    setAnalyzing(true);
    try { await runAllAnalysis(); await fetchData(); }
    catch (e) { console.error(e); }
    finally { setAnalyzing(false); }
  };

  if (loading) return <div className="loading"><div className="spinner" /></div>;
  if (!data) return <div className="empty-state"><h3>Failed to load dashboard</h3></div>;

  const catData = Object.entries(data.category_distribution || {}).map(([name, value]) => ({
    name: name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()), value
  }));
  const sentData = Object.entries(data.sentiment_distribution || {}).map(([name, value]) => ({ name, value }));
  const impactData = Object.entries(data.impact_distribution || {}).map(([name, value]) => ({
    name: name.charAt(0).toUpperCase() + name.slice(1), value
  }));
  const sentColors = { positive: '#00a67d', neutral: '#1976d2', negative: '#e53935' };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="page-desc">Overview of your competitive intelligence workspace</p>
        </div>
        <button className="btn btn-primary" onClick={handleAnalyze} disabled={analyzing}>
          <RefreshCw size={14} />
          {analyzing ? 'Running...' : 'Run Analysis'}
        </button>
      </div>

      <div className="stats-grid">
        {[
          { icon: Building2, label: 'Companies', value: data.total_companies, bg: '#ff573310', color: '#ff5733' },
          { icon: Database, label: 'Data Points', value: data.total_data_points, bg: '#1976d210', color: '#1976d2' },
          { icon: TrendingUp, label: 'Patterns', value: data.total_patterns, bg: '#7b61ff10', color: '#7b61ff' },
          { icon: Lightbulb, label: 'Insights', value: data.total_insights, sub: `${data.new_insights_count} new`, bg: '#00a67d10', color: '#00a67d' },
        ].map((s, i) => (
          <div className="stat-card" key={i}>
            <div className="stat-icon" style={{ background: s.bg }}>
              <s.icon size={16} style={{ color: s.color }} />
            </div>
            <div className="stat-label">{s.label}</div>
            <div className="stat-value">{s.value}</div>
            {s.sub && <div className="stat-change positive">{s.sub}</div>}
          </div>
        ))}
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-header"><span className="card-title">Activity · Last 30 Days</span></div>
          <div className="chart-container">
            <ResponsiveContainer>
              <AreaChart data={data.activity_timeline || []}>
                <defs>
                  <linearGradient id="aGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ff5733" stopOpacity={0.15} />
                    <stop offset="95%" stopColor="#ff5733" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#eef0f4" />
                <XAxis dataKey="date" tick={{ fill: '#8e8ea0', fontSize: 10 }} tickFormatter={d => d.slice(5)} />
                <YAxis tick={{ fill: '#8e8ea0', fontSize: 10 }} />
                <Tooltip contentStyle={tooltipStyle} />
                <Area type="monotone" dataKey="count" stroke="#ff5733" fill="url(#aGrad)" strokeWidth={2} dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card">
          <div className="card-header"><span className="card-title">Categories</span></div>
          <div className="chart-container">
            <ResponsiveContainer>
              <PieChart>
                <Pie data={catData} cx="50%" cy="50%" innerRadius={55} outerRadius={90} paddingAngle={2} dataKey="value" strokeWidth={0}>
                  {catData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip contentStyle={tooltipStyle} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px 12px', justifyContent: 'center', marginTop: 4 }}>
            {catData.slice(0, 6).map((c, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11, color: 'var(--text-muted)' }}>
                <div style={{ width: 8, height: 8, borderRadius: 2, background: COLORS[i % COLORS.length], flexShrink: 0 }} />
                {c.name}
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-header">
            <span className="card-title">Top Insights</span>
            <button className="btn btn-sm btn-secondary" onClick={() => nav('/insights')}>View All <ArrowRight size={12} /></button>
          </div>
          {(data.top_insights || []).length === 0 ? (
            <div className="empty-state"><p>No new insights. Run analysis to generate.</p></div>
          ) : data.top_insights.map(ins => (
            <div className="insight-card" key={ins.id}>
              <div className="insight-title">{ins.title}</div>
              <div className="insight-desc">{ins.description}</div>
              <div className="insight-meta">
                <span className={`badge ${priorityMap[ins.priority]}`}>{ins.priority}</span>
                {ins.predicted_timeline && <span className="badge badge-cyan">{ins.predicted_timeline}</span>}
                <span className="badge badge-purple">{Math.round(ins.probability * 100)}%</span>
              </div>
            </div>
          ))}
        </div>

        <div className="card">
          <div className="card-header"><span className="card-title">Sentiment & Impact</span></div>
          <div style={{ display: 'flex', gap: 10, marginBottom: 20 }}>
            {sentData.map(s => (
              <div key={s.name} style={{ flex: 1, textAlign: 'center', padding: '12px 0', background: 'var(--bg-muted)', borderRadius: 6, border: '1px solid var(--border-light)' }}>
                <div style={{ fontSize: 22, fontWeight: 700, color: sentColors[s.name] || 'var(--text-primary)' }}>{s.value}</div>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2, textTransform: 'capitalize', fontWeight: 500, letterSpacing: '0.3px' }}>{s.name}</div>
              </div>
            ))}
          </div>
          <div className="card-title" style={{ marginBottom: 12 }}>Impact Distribution</div>
          <ResponsiveContainer width="100%" height={140}>
            <BarChart data={impactData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eef0f4" />
              <XAxis dataKey="name" tick={{ fill: '#8e8ea0', fontSize: 10 }} />
              <YAxis tick={{ fill: '#8e8ea0', fontSize: 10 }} />
              <Tooltip contentStyle={tooltipStyle} />
              <Bar dataKey="value" fill="#7b61ff" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {(data.company_activity || []).length > 0 && (
        <div className="card">
          <div className="card-header"><span className="card-title">Company Activity</span></div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={data.company_activity} layout="vertical" margin={{ left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eef0f4" />
              <XAxis type="number" tick={{ fill: '#8e8ea0', fontSize: 10 }} />
              <YAxis type="category" dataKey="name" width={90} tick={{ fill: '#5e5e76', fontSize: 12, fontWeight: 500 }} />
              <Tooltip contentStyle={tooltipStyle} />
              <Bar dataKey="dp_count" fill="#ff5733" radius={[0, 3, 3, 0]} name="Data Points" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
