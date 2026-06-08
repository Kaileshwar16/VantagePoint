import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Building2, Lightbulb, TrendingUp, Database, Zap, Settings } from 'lucide-react';

const sections = [
  {
    label: 'OVERVIEW',
    links: [
      { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
    ],
  },
  {
    label: 'INTELLIGENCE',
    links: [
      { to: '/companies', icon: Building2, label: 'Companies' },
      { to: '/intel', icon: Database, label: 'Data Points' },
    ],
  },
  {
    label: 'ANALYSIS',
    links: [
      { to: '/patterns', icon: TrendingUp, label: 'Patterns' },
      { to: '/insights', icon: Lightbulb, label: 'Insights' },
    ],
  },
];

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <Zap size={18} />
          VantagePoint
        </div>
        <div className="sidebar-subtitle">Competitive Intel</div>
      </div>
      <nav className="sidebar-nav">
        {sections.map((section) => (
          <div key={section.label} style={{ marginBottom: 16 }}>
            <div style={{
              fontSize: 10, fontWeight: 600, color: 'rgba(255,255,255,0.25)',
              padding: '0 12px', marginBottom: 6, letterSpacing: '1px',
            }}>
              {section.label}
            </div>
            {section.links.map(({ to, icon: Icon, label }) => (
              <NavLink
                key={to} to={to} end
                className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
              >
                <Icon size={16} />
                {label}
              </NavLink>
            ))}
          </div>
        ))}
      </nav>
      <div className="sidebar-footer">
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'rgba(255,255,255,0.35)', fontSize: 11 }}>
          <Settings size={13} />
          VantagePoint v1.0
        </div>
      </div>
    </aside>
  );
}
