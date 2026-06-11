import { useState, useEffect } from 'react';
import { getDeadReckonings, getCompanies, runAdvancedAnalysis } from '../services/api';
import { Navigation, RefreshCw, TrendingUp, Users, Globe, Package, DollarSign, AlertTriangle } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell, RadarChart, PolarGrid, PolarAngleAxis, Radar as ReRadar } from 'recharts';

const tooltipStyle = { background: '#fff', border: '1px solid #e2e5ea', borderRadius: 6, boxShadow: '0 4px 12px rgba(0,0,0,0.08)', fontSize: 12 };

export default function DeadReckoningPage() {
  const [reckonings, setReckonings] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState({});
  const [selected, setSelected] = useState(null);

  useEffect(() => { fetchAll(); }, []);

  const fetchAll = async () => {
    setLoading(true);
    try {
      const [drR, cR] = await Promise.all([getDeadReckonings(), getCompanies()]);
      const data = drR.data.results || drR.data;
      setReckonings(data);
      setCompanies(cR.data.results || cR.data);
      if (data.length > 0 && !selected) setSelected(data[0]);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  const handleGenerate = async (companyId) => {
    setGenerating(p => ({ ...p, [companyId]: true }));
    try { await runAdvancedAnalysis(companyId); await fetchAll(); } catch (e) { console.error(e); }
    finally { setGenerating(p => ({ ...p, [companyId]: false })); }
  };

  if (loading) return <div className="loading"><div className="spinner" /></div>;

  const dr = selected;
  
  // Only include metrics that have real data (non-zero current values)
  const projectionBars = dr ? [
    dr.current_headcount > 0 && { metric: 'Headcount', current: dr.current_headcount, '6 Months': dr.projected_headcount_6m, '12 Months': dr.projected_headcount_12m },
    dr.current_product_count > 0 && { metric: 'Products', current: dr.current_product_count, '6 Months': dr.projected_products_6m, '12 Months': dr.projected_products_12m },
    dr.current_geo_markets > 0 && { metric: 'Markets', current: dr.current_geo_markets, '6 Months': dr.projected_markets_6m, '12 Months': dr.projected_markets_12m },
  ].filter(Boolean) : [];

  // Scale funding by actual amounts (now in real $M, not fictional $50M per event)
  const maxFunding = Math.max(dr?.funding_total || 1, 1);
  const velocityRadar = dr ? [
    { axis: 'Hiring', value: Math.min(10, dr.hiring_velocity) },
    { axis: 'Product', value: Math.min(10, dr.product_velocity * 5) },
    { axis: 'Expansion', value: Math.min(10, dr.expansion_velocity * 10) },
    { axis: 'Funding', value: Math.min(10, (dr.funding_total / maxFunding) * 8) },
    { axis: 'Confidence', value: dr.confidence * 10 },
  ] : [];

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Dead Reckoning</h1>
          <p className="page-desc">Forward projection — where competitors will be in 6-12 months</p>
        </div>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
          <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Generate new projection:</span>
          {companies.slice(0, 4).map(c => (
            <button key={c.id} className="btn btn-sm btn-secondary" onClick={() => handleGenerate(c.id)} disabled={generating[c.id]}>
              <Navigation size={12} /> {generating[c.id] ? '...' : c.name}
            </button>
          ))}
        </div>
      </div>

      {reckonings.length === 0 ? (
        <div className="card" style={{ padding: 40, textAlign: 'center' }}>
          <Navigation size={40} style={{ color: 'var(--text-muted)', marginBottom: 12 }} />
          <h3 style={{ color: 'var(--text-primary)', margin: '0 0 8px' }}>No Projections Yet</h3>
          <p style={{ color: 'var(--text-muted)', fontSize: 13, maxWidth: 400, margin: '0 auto' }}>Run Advanced Analysis on a company to generate forward projections based on observed signals and velocities.</p>
        </div>
      ) : (
        <>
          {/* Selector */}
          <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
            {reckonings.map(r => (
              <button key={r.id} className={`btn btn-sm ${selected?.id === r.id ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setSelected(r)}>
                {r.company_name}
              </button>
            ))}
          </div>

          {dr && (
            <>
              {/* Confidence bar */}
              <div className="card" style={{ marginBottom: 16, display: 'flex', alignItems: 'center', gap: 16 }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>{dr.company_name} — 12-Month Projection</div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Generated {new Date(dr.created_at).toLocaleDateString()}</div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Confidence</span>
                  <div style={{ width: 100, height: 8, background: 'var(--bg-muted)', borderRadius: 4, overflow: 'hidden' }}>
                    <div style={{ width: `${dr.confidence * 100}%`, height: '100%', borderRadius: 4, background: dr.confidence > 0.6 ? 'var(--green)' : dr.confidence > 0.4 ? 'var(--amber)' : 'var(--red)' }} />
                  </div>
                  <span style={{ fontWeight: 700, fontSize: 14 }}>{Math.round(dr.confidence * 100)}%</span>
                </div>
              </div>

              {/* Low confidence warning */}
              {dr.confidence < 0.4 && (
                <div className="card" style={{ marginBottom: 16, background: 'rgba(255,87,51,0.06)', border: '1px solid rgba(255,87,51,0.2)' }}>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
                    <AlertTriangle size={16} style={{ color: 'var(--red)', flexShrink: 0, marginTop: 1 }} />
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                      <strong style={{ color: 'var(--red)' }}>Low confidence projection.</strong> Not enough data to produce reliable numbers. Values shown as "Unknown" lack sufficient signal data. Scrape more intel or add company details (headcount, revenue range) to improve accuracy.
                    </div>
                  </div>
                </div>
              )}

              {/* Key metrics — show 'Unknown' for zero/missing data instead of fake numbers */}
              <div className="stats-grid">
                <div className="stat-card">
                  <Users size={16} style={{ color: 'var(--accent)', marginBottom: 4 }} />
                  <div className="stat-label">Headcount Now → 12mo</div>
                  <div className="stat-value">
                    {dr.current_headcount > 0
                      ? `${dr.current_headcount} → ${dr.projected_headcount_12m}`
                      : <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>Unknown</span>}
                  </div>
                </div>
                <div className="stat-card">
                  <DollarSign size={16} style={{ color: 'var(--green)', marginBottom: 4 }} />
                  <div className="stat-label">Est. ARR Now → 12mo</div>
                  <div className="stat-value">
                    {dr.current_arr > 0
                      ? `$${dr.current_arr.toFixed(1)}M → $${dr.projected_arr_12m.toFixed(1)}M`
                      : <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>Unknown</span>}
                  </div>
                </div>
                <div className="stat-card">
                  <Package size={16} style={{ color: '#7b61ff', marginBottom: 4 }} />
                  <div className="stat-label">Products Now → 12mo</div>
                  <div className="stat-value">
                    {dr.current_product_count > 0
                      ? `${dr.current_product_count} → ${dr.projected_products_12m}`
                      : <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>Unknown</span>}
                  </div>
                </div>
                <div className="stat-card">
                  <Globe size={16} style={{ color: '#0097a7', marginBottom: 4 }} />
                  <div className="stat-label">Markets Now → 12mo</div>
                  <div className="stat-value">{dr.current_geo_markets} → {dr.projected_markets_12m}</div>
                </div>
              </div>

              <div className="grid-2">
                {/* Projection chart */}
                <div className="card">
                  <div className="card-header"><span className="card-title">Growth Projections</span></div>
                  <ResponsiveContainer width="100%" height={260}>
                    <BarChart data={projectionBars}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#eef0f4" />
                      <XAxis dataKey="metric" tick={{ fill: '#5e5e76', fontSize: 11 }} />
                      <YAxis tick={{ fill: '#8e8ea0', fontSize: 10 }} />
                      <Tooltip contentStyle={tooltipStyle} />
                      <Bar dataKey="current" fill="#8e8ea0" name="Current" radius={[3,3,0,0]} />
                      <Bar dataKey="6 Months" fill="#f5a623" name="6 Months" radius={[3,3,0,0]} />
                      <Bar dataKey="12 Months" fill="#ff5733" name="12 Months" radius={[3,3,0,0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>

                {/* Velocity radar */}
                <div className="card">
                  <div className="card-header"><span className="card-title">Velocity Profile</span></div>
                  <ResponsiveContainer width="100%" height={260}>
                    <RadarChart data={velocityRadar} cx="50%" cy="50%" outerRadius="70%">
                      <PolarGrid stroke="#e2e5ea" />
                      <PolarAngleAxis dataKey="axis" tick={{ fill: '#5e5e76', fontSize: 11 }} />
                      <ReRadar name="Velocity" dataKey="value" stroke="#ff5733" fill="#ff5733" fillOpacity={0.15} strokeWidth={2} dot={{ r: 3, fill: '#ff5733' }} />
                    </RadarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Narrative */}
              <div className="card" style={{ marginTop: 16 }}>
                <div className="card-header"><span className="card-title">Projection Narrative</span></div>
                <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7, whiteSpace: 'pre-line' }}>{dr.projection_narrative}</div>
              </div>

              <div className="grid-2" style={{ marginTop: 16 }}>
                {/* Assumptions */}
                <div className="card">
                  <div className="card-header"><span className="card-title">Key Assumptions</span></div>
                  {(dr.key_assumptions || []).map((a, i) => (
                    <div key={i} style={{ fontSize: 12, color: 'var(--text-secondary)', padding: '6px 0', borderBottom: i < dr.key_assumptions.length - 1 ? '1px solid var(--border-light)' : 'none' }}>
                      {i + 1}. {a}
                    </div>
                  ))}
                </div>
                {/* Risks */}
                <div className="card">
                  <div className="card-header"><span className="card-title">Risk Factors</span></div>
                  {(dr.risk_factors || []).length === 0 ? <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>No significant risk factors identified.</div> :
                    (dr.risk_factors || []).map((r, i) => (
                      <div key={i} style={{ fontSize: 12, color: 'var(--red)', padding: '6px 0', borderBottom: i < dr.risk_factors.length - 1 ? '1px solid var(--border-light)' : 'none', display: 'flex', gap: 6, alignItems: 'flex-start' }}>
                        <AlertTriangle size={12} style={{ flexShrink: 0, marginTop: 1 }} /> {r}
                      </div>
                    ))}
                </div>
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}
