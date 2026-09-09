import { useEffect, useState } from 'react';
import { getDataQuality } from '../services/api';

export default function DataQuality() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(false);
  useEffect(() => { getDataQuality().then(r => setData(r.data)).catch(() => setError(true)); }, []);
  if (error) return <p role="alert">Could not load evidence quality. Reload to retry.</p>;
  if (!data) return <p>Loading evidence quality…</p>;
  const metrics = [['Total records', data.total_records], ['Verified with source', data.verified_records], ['Missing source links', data.missing_sources], ['Unknown publication dates', data.unknown_publication_dates], ['Published over 90 days ago', data.older_than_90_days], ['Future publication dates', data.future_publication_dates], ['Failed collections', data.failed_collections]];
  return <div><h1 className="page-title">Evidence Quality</h1><p className="page-desc">Check coverage and review gaps before using intelligence in business decisions.</p>
    <div className="stats-grid">{metrics.map(([label, value]) => <div className="stat-card" key={label}><div className="stat-label">{label}</div><div className="stat-value">{value}</div></div>)}</div>
    <div className="card"><p>{data.notice}</p><p>Last completed collection: {data.last_collection ? new Date(data.last_collection).toLocaleString() : 'No completed collection recorded'}</p><p>A verified record means a workspace reviewer checked its source. It is not an independent guarantee. Automated category, sentiment and impact labels need review.</p></div>
  </div>;
}
