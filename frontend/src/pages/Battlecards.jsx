import { useState, useEffect } from 'react';
import { getBattlecards, getCompanies, runAdvancedAnalysis } from '../services/api';
import { Shield, TrendingUp, TrendingDown, Minus, RefreshCw, AlertTriangle } from 'lucide-react';

const trajIcon = { growing: <TrendingUp size={14} style={{ color: 'var(--green)' }} />, declining: <TrendingDown size={14} style={{ color: 'var(--red)' }} />, stable: <Minus size={14} style={{ color: 'var(--text-muted)' }} /> };
const trajBadge = { growing: 'badge-green', declining: 'badge-red', stable: 'badge-blue' };
const TRAJ_LABEL = { growing: 'Growing', declining: 'Declining', stable: 'Stable' };
const CAT_LABEL = { product_launch: 'Product Launch', pricing_change: 'Pricing', hiring: 'Hiring', partnership: 'Partnership', funding: 'Funding', acquisition: 'Acquisition', expansion: 'Expansion', leadership: 'Leadership', technology: 'Technology', marketing: 'Marketing', news: 'News', patent: 'Patent', earnings: 'Earnings', legal: 'Legal' };

export default function Battlecards() {
  const [cards, setCards] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState({});

  useEffect(() => { fetchAll(); }, []);

  const fetchAll = async () => {
    setLoading(true);
    try {
      const [bR, cR] = await Promise.all([getBattlecards(), getCompanies()]);
      setCards(bR.data.results || bR.data);
      setCompanies(cR.data.results || cR.data);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  const handleUpdate = async (companyId) => {
    setUpdating(p => ({ ...p, [companyId]: true }));
    try { await runAdvancedAnalysis(companyId); await fetchAll(); } catch (e) { console.error(e); }
    finally { setUpdating(p => ({ ...p, [companyId]: false })); }
  };

  if (loading) return <div className="loading"><div className="spinner" /></div>;

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Battlecards</h1>
          <p className="page-desc">Auto-updating competitive intelligence cards · {cards.length} active</p>
        </div>
      </div>

      {cards.length === 0 ? (
        <div className="card" style={{ padding: 40, textAlign: 'center' }}>
          <Shield size={40} style={{ color: 'var(--text-muted)', marginBottom: 12 }} />
          <h3 style={{ color: 'var(--text-primary)', margin: '0 0 8px' }}>No Battlecards Yet</h3>
          <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>Run Advanced Analysis on any company to auto-generate battlecards.</p>
          <div style={{ display: 'flex', gap: 6, justifyContent: 'center', marginTop: 16, flexWrap: 'wrap' }}>
            {companies.slice(0, 5).map(c => (
              <button key={c.id} className="btn btn-sm btn-primary" onClick={() => handleUpdate(c.id)} disabled={updating[c.id]}>
                <RefreshCw size={12} /> {updating[c.id] ? 'Generating...' : `Generate for ${c.name}`}
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(500px, 1fr))', gap: 16 }}>
          {cards.map(bc => (
            <div className="card" key={bc.id} style={{ padding: 0, overflow: 'hidden' }}>
              {/* Header */}
              <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontWeight: 700, fontSize: 16, color: 'var(--text-primary)' }}>{bc.company_name}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>Updated {new Date(bc.last_updated).toLocaleDateString()} · {bc.auto_update_count} auto-updates</div>
                </div>
                <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                  {trajIcon[bc.current_trajectory]}
                  <span className={`badge ${trajBadge[bc.current_trajectory] || 'badge-blue'}`}>{TRAJ_LABEL[bc.current_trajectory] || bc.current_trajectory}</span>
                  <button className="btn btn-sm btn-secondary" onClick={() => handleUpdate(bc.company)} disabled={updating[bc.company]}>
                    <RefreshCw size={12} />
                  </button>
                </div>
              </div>

              {/* Threat assessment */}
              {bc.threat_assessment && (
                <div style={{ padding: '10px 20px', fontSize: 13, color: bc.threat_assessment.startsWith('HIGH') ? 'var(--red)' : bc.threat_assessment.startsWith('MODERATE') ? 'var(--amber)' : 'var(--green)', background: bc.threat_assessment.startsWith('HIGH') ? 'var(--red-bg)' : bc.threat_assessment.startsWith('MODERATE') ? 'var(--amber-bg)' : 'var(--green-bg)', fontWeight: 600, borderBottom: '1px solid var(--border)' }}>
                  <AlertTriangle size={12} style={{ display: 'inline', marginRight: 4 }} /> {bc.threat_assessment}
                </div>
              )}

              <div style={{ padding: '16px 20px' }}>
                {/* Signal summary */}
                {bc.signal_summary && <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 14, lineHeight: 1.5 }}>{bc.signal_summary}</div>}

                {/* Recent moves */}
                {bc.recent_moves?.length > 0 && (
                  <div style={{ marginBottom: 14 }}>
                    <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px', color: 'var(--text-muted)', marginBottom: 6 }}>Recent Moves</div>
                    {bc.recent_moves.map((m, i) => (
                      <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 0', fontSize: 12 }}>
                        <span className="badge badge-blue" style={{ fontSize: 9 }}>{CAT_LABEL[m.category] || m.category}</span>
                        <span style={{ color: 'var(--text-secondary)' }}>{m.title}</span>
                        <span style={{ marginLeft: 'auto', color: 'var(--text-muted)', fontSize: 10, whiteSpace: 'nowrap' }}>{m.date}</span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Strengths & Weaknesses */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                  <div>
                    <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px', color: 'var(--green)', marginBottom: 6 }}>Strengths</div>
                    {(bc.strengths || []).slice(0, 3).map((s, i) => (
                      <div key={i} style={{ fontSize: 11, color: 'var(--text-secondary)', padding: '3px 0', borderLeft: '2px solid var(--green)', paddingLeft: 8, marginBottom: 4 }}>{s}</div>
                    ))}
                    {(!bc.strengths || bc.strengths.length === 0) && <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>No data yet</div>}
                  </div>
                  <div>
                    <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px', color: 'var(--red)', marginBottom: 6 }}>Weaknesses</div>
                    {(bc.weaknesses || []).slice(0, 3).map((w, i) => (
                      <div key={i} style={{ fontSize: 11, color: 'var(--text-secondary)', padding: '3px 0', borderLeft: '2px solid var(--red)', paddingLeft: 8, marginBottom: 4 }}>{w}</div>
                    ))}
                    {(!bc.weaknesses || bc.weaknesses.length === 0) && <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>No data yet</div>}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
