import { useEffect, useState } from 'react';
import { getSession, signIn, signOut } from '../services/api';

export default function SessionGate({ children }) {
  const [session, setSession] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    getSession().then(r => setSession(r.data)).catch(() => setError('Cannot reach the server. Reload to retry.'));
    const onError = e => setError(e.detail);
    window.addEventListener('api-error', onError);
    return () => window.removeEventListener('api-error', onError);
  }, []);
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError('');
    const values = Object.fromEntries(new FormData(event.currentTarget));
    try { setSession((await signIn(values)).data); }
    catch (e) { setError(e.response?.data?.detail || 'Sign-in failed. Try again.'); }
    finally { setBusy(false); }
  }
  async function leave() {
    try { setSession((await signOut()).data); setError(''); }
    catch { setError('Sign-out failed. Retry.'); }
  }
  return <>
    {error && <div role="alert" style={{ padding: 12, background: '#fff0ed', color: '#9b2616', position: 'sticky', top: 0, zIndex: 100 }}>{error} <button onClick={() => setError('')}>Dismiss</button></div>}
    {session?.authenticated ? <><div style={{ textAlign: 'right', padding: '8px 20px' }}>{session.username} · <button className="btn btn-sm" onClick={leave}>Sign out</button></div>{children}</> : session ?
      <form onSubmit={submit} className="card" style={{ maxWidth: 400, margin: '10vh auto', display: 'grid', gap: 16 }}>
        <h1>VantagePoint</h1><p>Sign in to your organization’s private workspace.</p>
        <label>Username<input className="input" name="username" autoComplete="username" required /></label>
        <label>Password<input className="input" name="password" type="password" autoComplete="current-password" required /></label>
        <button className="btn btn-primary" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button>
      </form> : <p style={{ padding: 40 }}>Connecting to workspace…</p>}
  </>;
}
