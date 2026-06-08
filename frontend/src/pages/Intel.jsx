import { useState, useEffect } from 'react';
import { getDataPoints } from '../services/api';
import { Search, ChevronDown, ChevronUp, ExternalLink } from 'lucide-react';

const catBadge = { product_launch: 'badge-green', pricing_change: 'badge-amber', hiring: 'badge-cyan',
  partnership: 'badge-purple', funding: 'badge-pink', acquisition: 'badge-red', expansion: 'badge-blue',
  leadership: 'badge-amber', technology: 'badge-cyan', marketing: 'badge-purple', news: 'badge-blue', legal: 'badge-red' };

function ExpandableRow({ dp }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <tr onClick={() => setOpen(!open)} style={{ cursor: 'pointer' }}>
        <td style={{ fontWeight: 500, color: 'var(--text-primary)' }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 6 }}>
            {open ? <ChevronUp size={14} style={{ color: 'var(--text-muted)', flexShrink: 0, marginTop: 2 }} /> : <ChevronDown size={14} style={{ color: 'var(--text-muted)', flexShrink: 0, marginTop: 2 }} />}
            <span>{dp.title}</span>
          </div>
        </td>
        <td style={{ fontWeight: 600, color: 'var(--accent)', fontSize: 13 }}>{dp.company_name}</td>
        <td><span className={`badge ${catBadge[dp.category] || 'badge-blue'}`}>{dp.category?.replace(/_/g, ' ')}</span></td>
        <td><span className={`badge ${dp.sentiment === 'positive' ? 'badge-green' : dp.sentiment === 'negative' ? 'badge-red' : 'badge-blue'}`}>{dp.sentiment}</span></td>
        <td><span className={`badge ${dp.impact === 'critical' ? 'badge-red' : dp.impact === 'high' ? 'badge-amber' : dp.impact === 'medium' ? 'badge-blue' : 'badge-green'}`}>{dp.impact}</span></td>
        <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>{dp.source_name || '—'}</td>
        <td style={{ fontSize: 12, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>{dp.published_at ? new Date(dp.published_at).toLocaleDateString() : '—'}</td>
      </tr>
      {open && (
        <tr>
          <td colSpan={7} style={{ padding: '0 14px 16px 38px', background: 'var(--bg-muted)', borderBottom: '1px solid var(--border)' }}>
            <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7, maxWidth: 900, paddingTop: 12 }}>
              {dp.content || 'No additional content available for this data point.'}
            </div>
            {dp.source_url && (
              <a href={dp.source_url} target="_blank" rel="noreferrer" style={{ fontSize: 12, display: 'inline-flex', alignItems: 'center', gap: 4, marginTop: 10 }}>
                View Original Source <ExternalLink size={11} />
              </a>
            )}
          </td>
        </tr>
      )}
    </>
  );
}

export default function Intel() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [catFilter, setCatFilter] = useState('all');

  useEffect(() => {
    (async () => {
      setLoading(true);
      try { const r = await getDataPoints({ page_size: 100 }); setData(r.data.results || r.data); }
      catch (e) { console.error(e); }
      finally { setLoading(false); }
    })();
  }, []);

  const categories = ['all', ...new Set(data.map(d => d.category))];

  const filtered = data.filter(d => {
    const matchSearch = !search || d.title.toLowerCase().includes(search.toLowerCase()) || d.company_name?.toLowerCase().includes(search.toLowerCase());
    const matchCat = catFilter === 'all' || d.category === catFilter;
    return matchSearch && matchCat;
  });

  if (loading) return <div className="loading"><div className="spinner" /></div>;

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Data Points</h1>
          <p className="page-desc">{data.length} intelligence records collected · Click any row to expand</p>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 10, marginBottom: 16, alignItems: 'center' }}>
        <div style={{ position: 'relative', flex: 1, maxWidth: 340 }}>
          <Search size={14} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
          <input className="input" placeholder="Search by title or company..." value={search} onChange={e => setSearch(e.target.value)} style={{ paddingLeft: 34 }} />
        </div>
        <select className="select" value={catFilter} onChange={e => setCatFilter(e.target.value)} style={{ width: 180 }}>
          {categories.map(c => <option key={c} value={c}>{c === 'all' ? 'All Categories' : c.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</option>)}
        </select>
        <div style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--text-muted)' }}>
          Showing {filtered.length} of {data.length}
        </div>
      </div>

      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        {filtered.length === 0 ? (
          <div className="empty-state" style={{ padding: 40 }}><h3>No data points match your filters</h3></div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Title</th>
                <th>Company</th>
                <th>Category</th>
                <th>Sentiment</th>
                <th>Impact</th>
                <th>Source</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(dp => <ExpandableRow key={dp.id} dp={dp} />)}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
