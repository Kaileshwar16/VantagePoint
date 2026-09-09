import { useState, useEffect, useCallback } from 'react';
import { getDeadReckonings, getCompanies, runAdvancedAnalysis } from '../services/api';

export default function DeadReckoningPage() {
  const [reports, setReports] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const refresh = useCallback(async () => {
    try {
      const [r, c] = await Promise.all([getDeadReckonings(), getCompanies()]);
      // API orders newest first; display the latest report per company.
      const seen = new Set();
      setReports(r.data.results.filter(item => { if (seen.has(item.company)) return false; seen.add(item.company); return true; }));
      setCompanies(c.data.results);
    } catch { setError('Could not load reports. Reload to retry.'); }
  }, []);
  useEffect(() => { const timer = setTimeout(refresh, 0); return () => clearTimeout(timer); }, [refresh]);
  async function generate(event) {
    event.preventDefault(); setBusy(true); setError('');
    try { await runAdvancedAnalysis(new FormData(event.currentTarget).get('company')); await refresh(); }
    catch { setError('Report generation failed. Please retry.'); }
    finally { setBusy(false); }
  }
  return <div>
    <h1 className="page-title">Dead Reckoning</h1>
    <p className="page-desc">Observed activity and forecast readiness</p>
    <div className="card" style={{ marginBottom: 16 }}><strong>Forecasts unavailable</strong><p>Revenue, headcount, product and market projections require sourced inputs and a validated model. Article counts cannot establish these values. Missing values are unknown, not zero.</p></div>
    {error && <p role="alert">{error}</p>}
    <form onSubmit={generate} style={{ display: 'flex', gap: 12, marginBottom: 20 }}>
      <select name="company" className="select" aria-label="Company" required>{companies.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}</select>
      <button className="btn btn-primary" disabled={busy || !companies.length}>{busy ? 'Generating…' : 'Generate observation report'}</button>
    </form>
    {!reports.length && <p>No observation reports yet.</p>}
    {reports.map(r => <article className="card" key={r.id} style={{ marginBottom: 16 }}>
      <h2>{r.company_name}</h2><p>Generated {new Date(r.created_at).toLocaleString()}</p><p>{r.projection_narrative}</p>
      <dl><dt>Job postings collected in 30 days</dt><dd>{r.hiring_velocity ?? 'Unknown'}</dd><dt>Verified product reports in 90 days</dt><dd>{r.product_velocity ?? 'Unknown'}</dd><dt>Verified expansion reports, annualized from 180 days</dt><dd>{r.expansion_velocity ?? 'Unknown'}</dd></dl>
      <p>Method and limitations</p><ul>{[...(r.key_assumptions || []).filter(a => !a.startsWith('methodology:')), ...(r.risk_factors || [])].map((a, i) => <li key={i}>{a}</li>)}</ul>
    </article>)}
  </div>;
}
