import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { getCompanies, createCompany, deleteCompany, triggerScrape } from '../services/api';
import { Plus, Trash2, Radar, Search, X, AlertTriangle } from 'lucide-react';

const threatBadge = { low: 'badge-green', medium: 'badge-amber', high: 'badge-pink', critical: 'badge-red' };

export default function Companies() {
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState(null);
  const [scraping, setScraping] = useState({});
  const [search, setSearch] = useState('');
  const [form, setForm] = useState({ name: '', domain: '', industry: 'tech', description: '', headquarters: '', employee_count: '' });
  const nav = useNavigate();


  const fetchCompanies = useCallback(async () => {
    setLoading(true);
    try { const r = await getCompanies(); setCompanies(r.data.results || r.data); }
    catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { const timer = setTimeout(() => { fetchCompanies(); }, 0); return () => clearTimeout(timer); }, [fetchCompanies]);

  const handleCreate = async (e) => {
    e.preventDefault();
    try { await createCompany(form); setShowModal(false); setForm({ name: '', domain: '', industry: 'tech', description: '', headquarters: '', employee_count: '' }); fetchCompanies(); }
    catch (e) { console.error(e); }
  };

  const handleDelete = async (id) => {
    try { await deleteCompany(id); setDeleteConfirm(null); fetchCompanies(); }
    catch (e) { console.error(e); }
  };

  const handleScrape = async (id) => {
    setScraping(p => ({ ...p, [id]: true }));
    try { await triggerScrape(id); fetchCompanies(); }
    catch (e) { console.error(e); }
    finally { setScraping(p => ({ ...p, [id]: false })); }
  };

  const filtered = companies.filter(c => c.name.toLowerCase().includes(search.toLowerCase()));

  if (loading) return <div className="loading"><div className="spinner" /></div>;

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Companies</h1>
          <p className="page-desc">{companies.length} competitors being tracked</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowModal(true)}><Plus size={14} /> Add Company</button>
      </div>

      <div style={{ marginBottom: 16 }}>
        <div style={{ position: 'relative', maxWidth: 360 }}>
          <Search size={14} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
          <input className="input" placeholder="Search companies..." value={search} onChange={e => setSearch(e.target.value)} style={{ paddingLeft: 34 }} />
        </div>
      </div>

      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>Company</th>
              <th>Industry</th>
              <th>Location</th>
              <th>Data Points</th>
              <th>Threat Level</th>
              <th>Latest Activity</th>
              <th style={{ width: 160 }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map(c => (
              <tr key={c.id} style={{ cursor: 'pointer' }} onClick={() => nav(`/companies/${c.id}`)}>
                <td>
                  <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{c.name}</div>
                  {c.domain && <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 1 }}>{c.domain.replace(/https?:\/\//, '')}</div>}
                </td>
                <td><span className="badge badge-blue">{c.industry}</span></td>
                <td style={{ color: 'var(--text-secondary)' }}>{c.headquarters || '—'}</td>
                <td><span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{c.data_points_count || 0}</span></td>
                <td><span className={`badge ${threatBadge[c.threat_level] || 'badge-green'}`}>{c.threat_level || 'low'}</span></td>
                <td style={{ maxWidth: 200 }}>
                  {c.latest_activity ? (
                    <span className={`badge ${c.latest_activity.category === 'product_launch' ? 'badge-green' : 'badge-blue'}`} style={{ marginRight: 4 }}>
                      {c.latest_activity.category?.replace(/_/g, ' ')}
                    </span>
                  ) : <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>No data</span>}
                </td>
                <td onClick={e => e.stopPropagation()}>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <button className="btn btn-sm btn-secondary" onClick={() => handleScrape(c.id)} disabled={scraping[c.id]}>
                      <Radar size={12} /> {scraping[c.id] ? '...' : 'Scrape'}
                    </button>
                    <button className="btn btn-sm btn-danger" onClick={() => setDeleteConfirm(c)}>
                      <Trash2 size={12} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length === 0 && <div className="empty-state" style={{ padding: 40 }}><h3>No companies found</h3></div>}
      </div>

      {/* Delete confirmation modal */}
      {deleteConfirm && (
        <div className="modal-overlay" onClick={() => setDeleteConfirm(null)}>
          <div className="modal" onClick={e => e.stopPropagation()} style={{ width: 380 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
              <div style={{ width: 36, height: 36, borderRadius: 8, background: 'var(--red-bg)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <AlertTriangle size={18} style={{ color: 'var(--red)' }} />
              </div>
              <div>
                <h2 style={{ fontSize: 16, fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>Delete Company</h2>
                <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: 0 }}>This action cannot be undone</p>
              </div>
            </div>
            <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 20 }}>
              Are you sure you want to delete <strong>{deleteConfirm.name}</strong> and all associated data points, patterns, and insights?
            </p>
            <div className="modal-actions" style={{ borderTop: 'none', paddingTop: 0, marginTop: 0 }}>
              <button className="btn btn-secondary" onClick={() => setDeleteConfirm(null)}>Cancel</button>
              <button className="btn btn-danger" style={{ background: 'var(--red)', color: 'white', border: 'none' }} onClick={() => handleDelete(deleteConfirm.id)}>Delete</button>
            </div>
          </div>
        </div>
      )}

      {/* Add company modal */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18 }}>
              <h2 className="modal-title" style={{ marginBottom: 0 }}>Add Company</h2>
              <button className="btn btn-sm btn-secondary" onClick={() => setShowModal(false)} style={{ padding: '4px 6px' }}><X size={14} /></button>
            </div>
            <form onSubmit={handleCreate}>
              <div className="form-group">
                <label className="form-label">Company Name *</label>
                <input className="input" required value={form.name} onChange={e => setForm(p => ({ ...p, name: e.target.value }))} placeholder="Acme Corp" />
              </div>
              <div className="form-group">
                <label className="form-label">Website</label>
                <input className="input" value={form.domain} onChange={e => setForm(p => ({ ...p, domain: e.target.value }))} placeholder="https://example.com" />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div className="form-group">
                  <label className="form-label">Industry</label>
                  <select className="select" value={form.industry} onChange={e => setForm(p => ({ ...p, industry: e.target.value }))}>
                    {['tech','finance','healthcare','retail','manufacturing','energy','media','education','other'].map(i => (
                      <option key={i} value={i}>{i.charAt(0).toUpperCase() + i.slice(1)}</option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Headquarters</label>
                  <input className="input" value={form.headquarters} onChange={e => setForm(p => ({ ...p, headquarters: e.target.value }))} placeholder="City, Country" />
                </div>
              </div>
              <div className="form-group">
                <label className="form-label">Description</label>
                <input className="input" value={form.description} onChange={e => setForm(p => ({ ...p, description: e.target.value }))} placeholder="What does this company do?" />
              </div>
              <div className="modal-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">Add Company</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
