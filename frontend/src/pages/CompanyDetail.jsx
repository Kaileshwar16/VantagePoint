import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getCompany, getCompanyTimeline, getPatterns, getInsights, triggerScrape, runAnalysis } from '../services/api';
import { ArrowLeft, Radar, Brain, ExternalLink, Globe, MapPin, Users, Calendar, TrendingUp, ChevronDown, ChevronUp } from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar as ReRadar,
  PieChart, Pie, Cell, ScatterChart, Scatter, ZAxis, Treemap
} from 'recharts';

const tooltipStyle = { background: '#fff', border: '1px solid #e2e5ea', borderRadius: 6, boxShadow: '0 4px 12px rgba(0,0,0,0.08)', fontSize: 12 };
const COLORS = ['#ff5733', '#1976d2', '#00a67d', '#7b61ff', '#f5a623', '#0097a7', '#e53935', '#c2185b'];

const CAT_LABEL = { product_launch: 'Product Launch', pricing_change: 'Pricing Change', hiring: 'Hiring', partnership: 'Partnership', funding: 'Funding', acquisition: 'Acquisition', expansion: 'Expansion', leadership: 'Leadership', technology: 'Technology', marketing: 'Marketing', news: 'News', legal: 'Legal', patent: 'Patent', earnings: 'Earnings' };
const CAT_BADGE = { product_launch: 'badge-green', pricing_change: 'badge-amber', hiring: 'badge-cyan', partnership: 'badge-purple', funding: 'badge-pink', acquisition: 'badge-red', expansion: 'badge-blue', leadership: 'badge-amber', technology: 'badge-cyan', marketing: 'badge-purple', news: 'badge-blue', legal: 'badge-red' };
const SENT_LABEL = { positive: 'Positive', neutral: 'Neutral', negative: 'Negative' };
const IMPACT_LABEL = { critical: 'Critical', high: 'High', medium: 'Medium', low: 'Low' };
const PRIORITY_LABEL = { urgent: 'Urgent', high: 'High', medium: 'Medium', low: 'Low' };
const PTYPE_LABEL = { trend: 'Trend', anomaly: 'Anomaly', correlation: 'Correlation', cycle: 'Cycle' };

function sourceDomain(url) { if (!url) return null; try { return new URL(url).hostname.replace(/^www\./, ''); } catch { return null; } }

const GEO_DATA = {
  'San Francisco, CA': { region: 'North America', lat: 37.7, lng: -122.4 },
  'New York, NY': { region: 'North America', lat: 40.7, lng: -74 },
  'Cambridge, MA': { region: 'North America', lat: 42.3, lng: -71.1 },
  'Ottawa, Canada': { region: 'North America', lat: 45.4, lng: -75.7 },
  'London, UK': { region: 'Europe', lat: 51.5, lng: -0.1 },
  'Berlin, Germany': { region: 'Europe', lat: 52.5, lng: 13.4 },
  'Bangalore, India': { region: 'Asia Pacific', lat: 12.9, lng: 77.6 },
  'Tokyo, Japan': { region: 'Asia Pacific', lat: 35.7, lng: 139.7 },
  'Singapore': { region: 'Asia Pacific', lat: 1.3, lng: 103.8 },
  'Sydney, Australia': { region: 'Asia Pacific', lat: -33.9, lng: 151.2 },
};

function ExpandableRow({ dp }) {
  const [open, setOpen] = useState(false);
  const domain = sourceDomain(dp.source_url);
  return (
    <>
      <tr onClick={() => setOpen(!open)} style={{ cursor: 'pointer' }}>
        <td style={{ fontWeight: 500, color: 'var(--text-primary)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            {open ? <ChevronUp size={14} style={{ color: 'var(--text-muted)', flexShrink: 0 }} /> : <ChevronDown size={14} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />}
            {dp.title}
          </div>
        </td>
        <td><span className={`badge ${CAT_BADGE[dp.category] || 'badge-blue'}`}>{CAT_LABEL[dp.category] || dp.category}</span></td>
        <td><span className={`badge ${dp.sentiment === 'positive' ? 'badge-green' : dp.sentiment === 'negative' ? 'badge-red' : 'badge-blue'}`}>{SENT_LABEL[dp.sentiment] || dp.sentiment}</span></td>
        <td><span className={`badge ${dp.impact === 'critical' ? 'badge-red' : dp.impact === 'high' ? 'badge-amber' : 'badge-blue'}`}>{IMPACT_LABEL[dp.impact] || dp.impact}</span></td>
        <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>
          {dp.source_url ? (
            <a href={dp.source_url} target="_blank" rel="noreferrer" onClick={e => e.stopPropagation()} style={{ color: 'var(--accent)', display: 'inline-flex', alignItems: 'center', gap: 3, textDecoration: 'none' }}>
              {dp.source_name || domain || 'Source'} <ExternalLink size={10} />
            </a>
          ) : (
            <span>{dp.source_name || '—'}</span>
          )}
        </td>
        <td style={{ fontSize: 12, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>{dp.published_at ? new Date(dp.published_at).toLocaleDateString() : '—'}</td>
      </tr>
      {open && (
        <tr>
          <td colSpan={6} style={{ padding: '0 14px 14px 38px', background: 'var(--bg-muted)', borderBottom: '1px solid var(--border)' }}>
            <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7, maxWidth: 800, paddingTop: 10 }}>
              {dp.content || 'No additional content available.'}
            </div>
            {dp.source_url && (
              <a href={dp.source_url} target="_blank" rel="noreferrer" style={{ fontSize: 12, display: 'inline-flex', alignItems: 'center', gap: 4, marginTop: 8, color: 'var(--accent)' }}>
                Open article on {domain || 'source'} <ExternalLink size={11} />
              </a>
            )}
          </td>
        </tr>
      )}
    </>
  );
}

export default function CompanyDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const [company, setCompany] = useState(null);
  const [timeline, setTimeline] = useState(null);
  const [patterns, setPatterns] = useState([]);
  const [insights, setInsights] = useState([]);
  const [loading, setLoading] = useState(true);
  const [scraping, setScraping] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [tab, setTab] = useState('overview');

  useEffect(() => { fetchAll(); }, [id]);

  const fetchAll = async () => {
    setLoading(true);
    try {
      const [cR, tR, pR, iR] = await Promise.all([getCompany(id), getCompanyTimeline(id), getPatterns({ company: id }), getInsights({ company: id })]);
      setCompany(cR.data); setTimeline(tR.data);
      setPatterns(pR.data.results || pR.data); setInsights(iR.data.results || iR.data);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  const handleScrape = async () => { setScraping(true); try { await triggerScrape(id); await fetchAll(); } catch(e){} finally { setScraping(false); } };
  const handleAnalyze = async () => { setAnalyzing(true); try { await runAnalysis(id); await fetchAll(); } catch(e){} finally { setAnalyzing(false); } };

  if (loading) return <div className="loading"><div className="spinner" /></div>;
  if (!company) return <div className="empty-state"><h3>Company not found</h3></div>;

  const catBreakdown = (timeline?.category_breakdown || []).map(c => ({
    name: CAT_LABEL[c.category] || c.category, count: c.count
  }));

  // Build radar chart data from categories
  const allCats = ['Product Launch', 'Hiring', 'Funding', 'Technology', 'Marketing', 'Expansion', 'Partnership'];
  const radarData = allCats.map(cat => {
    const match = catBreakdown.find(c => c.name.toLowerCase().includes(cat.toLowerCase()));
    return { category: cat, value: match ? match.count : 0, fullMark: Math.max(...catBreakdown.map(c => c.count), 5) };
  });

  // Sentiment pie
  const sentimentData = (timeline?.timeline || []).reduce((acc, dp) => {
    acc[dp.sentiment] = (acc[dp.sentiment] || 0) + 1;
    return acc;
  }, {});
  const sentPie = Object.entries(sentimentData).map(([name, value]) => ({ name, value }));
  const sentColors = { positive: '#00a67d', neutral: '#1976d2', negative: '#e53935' };

  // Geographic presence — only use real data, no fake padding
  const hqGeo = GEO_DATA[company.headquarters] || { region: 'Unknown' };
  const expansionMentions = (timeline?.timeline || []).filter(dp => dp.category === 'expansion');
  const geoRegions = {};
  if (hqGeo.region && hqGeo.region !== 'Unknown') {
    geoRegions[hqGeo.region] = 5; // HQ is a real data point
  }
  expansionMentions.forEach(dp => {
    const text = (dp.title + ' ' + dp.content).toLowerCase();
    if (text.includes('europe') || text.includes('london') || text.includes('gdpr')) geoRegions['Europe'] = (geoRegions['Europe'] || 0) + 2;
    if (text.includes('asia') || text.includes('tokyo') || text.includes('india') || text.includes('apac')) geoRegions['Asia Pacific'] = (geoRegions['Asia Pacific'] || 0) + 2;
    if (text.includes('latin') || text.includes('brazil')) geoRegions['Latin America'] = (geoRegions['Latin America'] || 0) + 1;
    if (hqGeo.region && hqGeo.region !== 'Unknown') {
      geoRegions[hqGeo.region] = (geoRegions[hqGeo.region] || 0) + 1;
    }
  });
  const geoData = Object.entries(geoRegions).map(([name, value]) => ({ name, value }));

  // Impact over time (treemap-like)
  const impactCounts = (timeline?.timeline || []).reduce((acc, dp) => {
    acc[dp.impact] = (acc[dp.impact] || 0) + 1;
    return acc;
  }, {});
  const impactData = Object.entries(impactCounts).map(([name, value]) => ({
    name: name.charAt(0).toUpperCase() + name.slice(1), value
  }));

  // Activity by source
  const sourceCounts = (timeline?.timeline || []).reduce((acc, dp) => {
    const src = dp.source_name || 'Unknown';
    acc[src] = (acc[src] || 0) + 1;
    return acc;
  }, {});
  const sourceData = Object.entries(sourceCounts).map(([name, value]) => ({ name, value })).sort((a, b) => b.value - a.value).slice(0, 6);

  const dataTimeline = timeline?.timeline || [];

  return (
    <div>
      <div className="page-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button className="btn btn-sm btn-secondary" onClick={() => nav('/companies')} style={{ padding: '5px 8px' }}><ArrowLeft size={14} /></button>
          <div>
            <h1 className="page-title">{company.name}</h1>
            <div style={{ display: 'flex', gap: 12, marginTop: 2, fontSize: 12, color: 'var(--text-muted)', flexWrap: 'wrap', alignItems: 'center' }}>
              <span className="badge badge-blue" style={{ fontSize: 10 }}>{company.industry}</span>
              {company.headquarters && <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3 }}><MapPin size={11} /> {company.headquarters}</span>}
              {company.employee_count && <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3 }}><Users size={11} /> {company.employee_count}</span>}
              {company.founded_year && <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3 }}><Calendar size={11} /> Founded {company.founded_year}</span>}
              {company.domain && <a href={company.domain} target="_blank" rel="noreferrer" style={{ display: 'inline-flex', alignItems: 'center', gap: 3, fontSize: 12 }}><Globe size={11} /> Website <ExternalLink size={10} /></a>}
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn btn-secondary" onClick={handleScrape} disabled={scraping}><Radar size={14} /> {scraping ? 'Scraping...' : 'Scrape'}</button>
          <button className="btn btn-primary" onClick={handleAnalyze} disabled={analyzing}><Brain size={14} /> {analyzing ? 'Running...' : 'Analyze'}</button>
        </div>
      </div>

      <div className="stats-grid">
        <div className="stat-card"><div className="stat-label">Data Points</div><div className="stat-value">{company.data_points_count || 0}</div></div>
        <div className="stat-card"><div className="stat-label">Patterns</div><div className="stat-value">{company.patterns_count || 0}</div></div>
        <div className="stat-card"><div className="stat-label">Insights</div><div className="stat-value">{company.insights_count || 0}</div></div>
        <div className="stat-card"><div className="stat-label">HQ Region</div><div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)', marginTop: 4 }}>{hqGeo.region || 'N/A'}</div></div>
      </div>

      {company.description && <div className="card" style={{ marginBottom: 16 }}><p style={{ color: 'var(--text-secondary)', fontSize: 13, lineHeight: 1.6 }}>{company.description}</p></div>}

      <div className="tabs">
        {['overview', 'geography', 'insights', 'intel'].map(t => (
          <button key={t} className={`tab ${tab === t ? 'active' : ''}`} onClick={() => setTab(t)}>
            {t === 'overview' ? 'Overview' : t === 'geography' ? 'Geography & Market' : t === 'insights' ? `Insights (${insights.length})` : `Intel (${dataTimeline.length})`}
          </button>
        ))}
      </div>

      {tab === 'overview' && (
        <>
          <div className="grid-2">
            <div className="card">
              <div className="card-header"><span className="card-title">Strategic Focus Radar</span></div>
              <ResponsiveContainer width="100%" height={280}>
                <RadarChart data={radarData} cx="50%" cy="50%" outerRadius="70%">
                  <PolarGrid stroke="#e2e5ea" />
                  <PolarAngleAxis dataKey="category" tick={{ fill: '#5e5e76', fontSize: 11 }} />
                  <PolarRadiusAxis tick={false} axisLine={false} />
                  <ReRadar name="Activity" dataKey="value" stroke="#ff5733" fill="#ff5733" fillOpacity={0.15} strokeWidth={2} dot={{ r: 3, fill: '#ff5733' }} />
                </RadarChart>
              </ResponsiveContainer>
            </div>

            <div className="card">
              <div className="card-header"><span className="card-title">Activity by Category</span></div>
              {catBreakdown.length > 0 ? (
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={catBreakdown} layout="vertical" margin={{ left: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#eef0f4" />
                    <XAxis type="number" tick={{ fill: '#8e8ea0', fontSize: 10 }} />
                    <YAxis type="category" dataKey="name" width={100} tick={{ fill: '#5e5e76', fontSize: 11 }} />
                    <Tooltip contentStyle={tooltipStyle} />
                    <Bar dataKey="count" fill="#ff5733" radius={[0, 3, 3, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : <div className="empty-state"><p>No data yet. Click Scrape.</p></div>}
            </div>
          </div>

          <div className="grid-2">
            <div className="card">
              <div className="card-header"><span className="card-title">Sentiment Distribution</span></div>
              {sentPie.length > 0 ? (
                <div style={{ display: 'flex', alignItems: 'center' }}>
                  <ResponsiveContainer width="55%" height={200}>
                    <PieChart>
                      <Pie data={sentPie} cx="50%" cy="50%" innerRadius={45} outerRadius={75} paddingAngle={3} dataKey="value" strokeWidth={0}>
                        {sentPie.map((s, i) => <Cell key={i} fill={sentColors[s.name] || '#8e8ea0'} />)}
                      </Pie>
                      <Tooltip contentStyle={tooltipStyle} />
                    </PieChart>
                  </ResponsiveContainer>
                  <div style={{ flex: 1 }}>
                    {sentPie.map(s => (
                      <div key={s.name} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--border-light)' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <div style={{ width: 10, height: 10, borderRadius: 2, background: sentColors[s.name] }} />
                          <span style={{ fontSize: 13, textTransform: 'capitalize', color: 'var(--text-secondary)' }}>{s.name}</span>
                        </div>
                        <span style={{ fontWeight: 700, fontSize: 14, color: 'var(--text-primary)' }}>{s.value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : <div className="empty-state"><p>No sentiment data</p></div>}
            </div>

            <div className="card">
              <div className="card-header"><span className="card-title">Intel Sources</span></div>
              {sourceData.length > 0 ? (
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={sourceData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#eef0f4" />
                    <XAxis dataKey="name" tick={{ fill: '#8e8ea0', fontSize: 10 }} />
                    <YAxis tick={{ fill: '#8e8ea0', fontSize: 10 }} />
                    <Tooltip contentStyle={tooltipStyle} />
                    <Bar dataKey="value" fill="#7b61ff" radius={[3, 3, 0, 0]} name="Articles" />
                  </BarChart>
                </ResponsiveContainer>
              ) : <div className="empty-state"><p>No sources yet</p></div>}
            </div>
          </div>

          <div className="card">
            <div className="card-header"><span className="card-title">Detected Patterns</span></div>
            {patterns.length === 0 ? <div className="empty-state"><p>Run analysis to detect patterns.</p></div> :
              <table className="data-table">
                <thead><tr><th>Pattern</th><th>Type</th><th>Confidence</th><th>Detected</th></tr></thead>
                <tbody>
                  {patterns.map(p => (
                    <tr key={p.id}>
                      <td>
                        <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{p.name}</div>
                        <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>{p.description.slice(0, 100)}...</div>
                      </td>
                      <td><span className={`badge ${p.pattern_type === 'trend' ? 'badge-blue' : 'badge-amber'}`}>{PTYPE_LABEL[p.pattern_type] || p.pattern_type}</span></td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <div style={{ width: 50, height: 5, background: 'var(--bg-muted)', borderRadius: 3, overflow: 'hidden' }}>
                            <div style={{ width: `${p.confidence * 100}%`, height: '100%', borderRadius: 3, background: p.confidence > 0.7 ? 'var(--green)' : 'var(--amber)' }} />
                          </div>
                          <span style={{ fontSize: 12, fontWeight: 600 }}>{Math.round(p.confidence * 100)}%</span>
                        </div>
                      </td>
                      <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>{new Date(p.detected_at).toLocaleDateString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>}
          </div>
        </>
      )}

      {tab === 'geography' && (
        <>
          <div className="grid-2">
            <div className="card">
              <div className="card-header"><span className="card-title">Geographic Presence</span></div>
              {geoData.length > 0 ? (
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={geoData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#eef0f4" />
                  <XAxis dataKey="name" tick={{ fill: '#5e5e76', fontSize: 11 }} />
                  <YAxis tick={{ fill: '#8e8ea0', fontSize: 10 }} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Bar dataKey="value" radius={[3, 3, 0, 0]} name="Presence Score">
                    {geoData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
              ) : <div className="empty-state"><p>No geographic data available. Add company headquarters or scrape expansion signals.</p></div>}
              <div style={{ padding: '12px 0 0', fontSize: 12, color: 'var(--text-muted)', borderTop: '1px solid var(--border-light)', marginTop: 12 }}>
                <MapPin size={12} style={{ display: 'inline', marginRight: 4 }} />
                Headquarters: <strong style={{ color: 'var(--text-primary)' }}>{company.headquarters || 'Unknown'}</strong>
              </div>
            </div>

            <div className="card">
              <div className="card-header"><span className="card-title">Regional Breakdown</span></div>
              <div style={{ display: 'flex', alignItems: 'center' }}>
                <ResponsiveContainer width="50%" height={250}>
                  <PieChart>
                    <Pie data={geoData} cx="50%" cy="50%" innerRadius={50} outerRadius={85} paddingAngle={3} dataKey="value" strokeWidth={0}>
                      {geoData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                    </Pie>
                    <Tooltip contentStyle={tooltipStyle} />
                  </PieChart>
                </ResponsiveContainer>
                <div style={{ flex: 1 }}>
                  {geoData.map((g, i) => {
                    const total = geoData.reduce((s, x) => s + x.value, 0);
                    const pct = Math.round((g.value / total) * 100);
                    return (
                      <div key={g.name} style={{ marginBottom: 12 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
                          <span style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text-secondary)' }}>
                            <div style={{ width: 10, height: 10, borderRadius: 2, background: COLORS[i] }} />
                            {g.name}
                          </span>
                          <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{pct}%</span>
                        </div>
                        <div style={{ width: '100%', height: 6, background: 'var(--bg-muted)', borderRadius: 3, overflow: 'hidden' }}>
                          <div style={{ width: `${pct}%`, height: '100%', background: COLORS[i], borderRadius: 3, transition: 'width 0.5s ease' }} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-header"><span className="card-title">Impact Distribution</span></div>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={impactData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#eef0f4" />
                <XAxis dataKey="name" tick={{ fill: '#5e5e76', fontSize: 11 }} />
                <YAxis tick={{ fill: '#8e8ea0', fontSize: 10 }} />
                <Tooltip contentStyle={tooltipStyle} />
                <Bar dataKey="value" radius={[3, 3, 0, 0]} name="Count">
                  {impactData.map((entry, i) => {
                    const c = { Low: '#00a67d', Medium: '#1976d2', High: '#f5a623', Critical: '#e53935' };
                    return <Cell key={i} fill={c[entry.name] || '#8e8ea0'} />;
                  })}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="card" style={{ marginTop: 16 }}>
            <div className="card-header"><span className="card-title">Expansion Signals</span></div>
            {expansionMentions.length === 0 ? <div className="empty-state"><p>No expansion signals detected yet.</p></div> : (
              <table className="data-table">
                <thead><tr><th>Signal</th><th>Source</th><th>Date</th></tr></thead>
                <tbody>
                  {expansionMentions.map(dp => (
                    <tr key={dp.id}>
                      <td style={{ fontWeight: 500, color: 'var(--text-primary)' }}>{dp.title}</td>
                      <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>{dp.source_name}</td>
                      <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>{dp.published_at ? new Date(dp.published_at).toLocaleDateString() : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}

      {tab === 'insights' && (
        <div>
          {insights.length === 0 ? <div className="empty-state"><h3>No insights</h3><p>Scrape data then run analysis.</p></div> :
            insights.map(ins => (
              <div className="insight-card" key={ins.id}>
                <div className="insight-title">{ins.title}</div>
                <div className="insight-desc">{ins.description}</div>
                {ins.recommendation && <div style={{ padding: '8px 12px', background: 'var(--green-bg)', borderRadius: 5, marginBottom: 8, fontSize: 12, color: 'var(--green)', borderLeft: '3px solid var(--green)' }}>💡 <strong>Recommendation:</strong> {ins.recommendation}</div>}
                <div className="insight-meta">
                  <span className={`badge ${ins.priority === 'urgent' ? 'badge-red' : ins.priority === 'high' ? 'badge-amber' : 'badge-blue'}`}>{PRIORITY_LABEL[ins.priority] || ins.priority}</span>
                  {ins.predicted_timeline && <span className="badge badge-cyan">⏱ {ins.predicted_timeline}</span>}
                  <span className="badge badge-purple">{Math.round(ins.probability * 100)}% confidence</span>
                </div>
              </div>
            ))}
        </div>
      )}

      {tab === 'intel' && (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          {dataTimeline.length === 0 ? <div className="empty-state" style={{ padding: 40 }}><p>No data points. Click Scrape.</p></div> : (
            <table className="data-table">
              <thead><tr><th>Title</th><th>Category</th><th>Sentiment</th><th>Impact</th><th>Source</th><th>Date</th></tr></thead>
              <tbody>
                {dataTimeline.slice(0, 30).map(dp => <ExpandableRow key={dp.id} dp={dp} />)}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
