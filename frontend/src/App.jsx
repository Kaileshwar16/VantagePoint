import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import Companies from './pages/Companies';
import CompanyDetail from './pages/CompanyDetail';
import Insights from './pages/Insights';
import Patterns from './pages/Patterns';
import Intel from './pages/Intel';
import { ChevronRight } from 'lucide-react';
import './index.css';

const pageTitles = {
  '/': 'Dashboard',
  '/companies': 'Companies',
  '/insights': 'Insights',
  '/patterns': 'Patterns',
  '/intel': 'Data Points',
};

function TopBar() {
  const location = useLocation();
  const path = location.pathname;

  // Handle company detail pages
  const isCompanyDetail = path.startsWith('/companies/');
  const crumbs = isCompanyDetail
    ? [{ label: 'Companies', path: '/companies' }, { label: 'Detail' }]
    : [{ label: pageTitles[path] || 'Page' }];

  return (
    <div className="top-bar">
      <div className="top-bar-left">
        <div className="breadcrumb">
          <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>Workspace</span>
          {crumbs.map((c, i) => (
            <span key={i} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <ChevronRight size={12} style={{ color: 'var(--text-muted)' }} />
              <span style={{ fontWeight: i === crumbs.length - 1 ? 600 : 400, color: i === crumbs.length - 1 ? 'var(--text-primary)' : 'var(--text-muted)' }}>
                {c.label}
              </span>
            </span>
          ))}
        </div>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <div style={{
          width: 30, height: 30, borderRadius: '50%', background: 'var(--accent)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: 'white', fontSize: 12, fontWeight: 700,
        }}>
          VP
        </div>
      </div>
    </div>
  );
}

function AppContent() {
  return (
    <div className="app-layout">
      <Sidebar />
      <main className="main-content">
        <TopBar />
        <div className="page-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/companies" element={<Companies />} />
            <Route path="/companies/:id" element={<CompanyDetail />} />
            <Route path="/insights" element={<Insights />} />
            <Route path="/patterns" element={<Patterns />} />
            <Route path="/intel" element={<Intel />} />
          </Routes>
        </div>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppContent />
    </BrowserRouter>
  );
}
