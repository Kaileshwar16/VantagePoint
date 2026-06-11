import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Building2, Database, TrendingUp, Lightbulb, Radio, Shield, Navigation, GitCompare, Zap } from 'lucide-react';

const sections = [
  {
    label: 'OVERVIEW',
    items: [
      { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
    ],
  },
  {
    label: 'INTELLIGENCE',
    items: [
      { to: '/companies', icon: Building2, label: 'Companies' },
      { to: '/intel', icon: Database, label: 'Data Points' },
      { to: '/signals', icon: Radio, label: 'Signal Capture' },
    ],
  },
  {
    label: 'ANALYSIS',
    items: [
      { to: '/patterns', icon: TrendingUp, label: 'Patterns' },
      { to: '/insights', icon: Lightbulb, label: 'Insights' },
      { to: '/temporal', icon: GitCompare, label: 'Temporal Analysis' },
    ],
  },
  {
    label: 'STRATEGY',
    items: [
      { to: '/battlecards', icon: Shield, label: 'Battlecards' },
      { to: '/dead-reckoning', icon: Navigation, label: 'Dead Reckoning' },
    ],
  },
];

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <Zap size={18} />
          <span>VantagePoint</span>
        </div>
        <div className="sidebar-subtitle">COMPETITIVE INTEL</div>
      </div>

      <nav className="sidebar-nav">
        {sections.map(section => (
          <div key={section.label}>
            <div className="sidebar-section-label">{section.label}</div>
            {section.items.map(item => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
              >
                <item.icon size={16} />
                <span>{item.label}</span>
              </NavLink>
            ))}
          </div>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.35)', display: 'flex', alignItems: 'center', gap: 6 }}>
          <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#00a67d' }} />
          VantagePoint v2.0
        </div>
      </div>
    </aside>
  );
}
