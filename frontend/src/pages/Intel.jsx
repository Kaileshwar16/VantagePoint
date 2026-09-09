import { useState, useEffect } from 'react';
import { getDataPoints, updateDataPoint } from '../services/api';
import { Search, ChevronDown, ChevronUp, ExternalLink } from 'lucide-react';

const CAT_LABEL = {
  product_launch: 'Product Launch', pricing_change: 'Pricing Change', hiring: 'Hiring',
  partnership: 'Partnership', funding: 'Funding', acquisition: 'Acquisition',
  expansion: 'Expansion', leadership: 'Leadership', technology: 'Technology',
  marketing: 'Marketing', news: 'News', legal: 'Legal', patent: 'Patent', earnings: 'Earnings',
};
const CAT_BADGE = {
  product_launch: 'badge-green', pricing_change: 'badge-amber', hiring: 'badge-cyan',
  partnership: 'badge-purple', funding: 'badge-pink', acquisition: 'badge-red',
  expansion: 'badge-blue', leadership: 'badge-amber', technology: 'badge-cyan',
  marketing: 'badge-purple', news: 'badge-blue', legal: 'badge-red', patent: 'badge-purple', earnings: 'badge-green',
};
const SENT_LABEL = { positive: 'Positive', neutral: 'Neutral', negative: 'Negative' };
const SENT_BADGE = { positive: 'badge-green', neutral: 'badge-blue', negative: 'badge-red' };
const IMPACT_LABEL = { critical: 'Critical', high: 'High', medium: 'Medium', low: 'Low' };
const IMPACT_BADGE = { critical: 'badge-red', high: 'badge-amber', medium: 'badge-blue', low: 'badge-green' };

/** Extract display hostname from a URL */
function sourceDomain(url) {
  if (!url) return null;
  try { return new URL(url).hostname.replace(/^www\./, ''); } catch { return url.slice(0, 40); }
}

function ExpandableRow({ dp, onUpdate }) {
  const [reviewing, setReviewing] = useState(false);
  async function review() {
    setReviewing(true);
    try { const r = await updateDataPoint(dp.id, { is_verified: !dp.is_verified }); onUpdate({ ...dp, ...r.data }); }
    catch (e) { console.error(e); }
    finally { setReviewing(false); }
  }
  const [open, setOpen] = useState(false);
  const domain = sourceDomain(dp.source_url);

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
        <td><span className={`badge ${CAT_BADGE[dp.category] || 'badge-blue'}`}>{CAT_LABEL[dp.category] || dp.category}</span></td>
        <td><span className={`badge ${SENT_BADGE[dp.sentiment] || 'badge-blue'}`}>{SENT_LABEL[dp.sentiment] || dp.sentiment}</span></td>
        <td><span className={`badge ${IMPACT_BADGE[dp.impact] || 'badge-blue'}`}>{IMPACT_LABEL[dp.impact] || dp.impact}</span></td>
        <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>
          {dp.source_url ? (
            <a href={dp.source_url} target="_blank" rel="noreferrer" onClick={e => e.stopPropagation()} style={{ color: 'var(--accent)', display: 'inline-flex', alignItems: 'center', gap: 3, textDecoration: 'none' }}>
              {dp.source_name || domain || 'Source'} <ExternalLink size={10} />
            </a>
          ) : (
            <span>{dp.source_name || '—'}</span>
          )}
        </td>
        <td style={{ fontSize: 12, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>{dp.published_at ? new Date(dp.published_at).toLocaleDateString() : 'Publication date unknown'}</td>
      </tr>
      {open && (
        <tr>
          <td colSpan={7} style={{ padding: '0 14px 16px 38px', background: 'var(--bg-muted)', borderBottom: '1px solid var(--border)' }}>
            <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7, maxWidth: 900, paddingTop: 12 }}>
              <p><strong>{dp.is_verified && dp.source_url ? 'Reviewed with source' : 'Unverified'}</strong> · Collected {new Date(dp.created_at).toLocaleString()} · Automated classifications require review.</p>
              {dp.content || 'No additional content available for this data point.'}
            </div>
            <button className="btn btn-sm btn-secondary" disabled={reviewing || !dp.source_url} onClick={review}>{dp.is_verified ? 'Remove verification' : 'I checked the source — mark verified'}</button>
            {dp.source_url && (
              <a href={dp.source_url} target="_blank" rel="noreferrer" style={{ fontSize: 12, display: 'inline-flex', alignItems: 'center', gap: 4, marginTop: 10, color: 'var(--accent)' }}>
                Open original article on {domain} <ExternalLink size={11} />
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
          {categories.map(c => <option key={c} value={c}>{c === 'all' ? 'All Categories' : CAT_LABEL[c] || c}</option>)}
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
              {filtered.map(dp => <ExpandableRow key={dp.id} dp={dp} onUpdate={updated => setData(previous => previous.map(item => item.id === updated.id ? updated : item))} />)}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
