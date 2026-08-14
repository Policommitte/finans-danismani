import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Briefcase, LineChart, ShieldAlert, MessageCircle } from 'lucide-react';
import { cn } from '../lib/utils';

const links = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/portfoy', label: 'Portföy', icon: Briefcase },
  { to: '/piyasa', label: 'Piyasa', icon: LineChart },
  { to: '/risk', label: 'Risk', icon: ShieldAlert },
  { to: '/ai-chat', label: 'AI Chat', icon: MessageCircle },
];

export default function Sidebar() {
  return (
    <nav className="w-64 h-screen bg-card border-r border-border p-4 flex flex-col gap-1">
      {links.map(({ to, label, icon: Icon, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          className={({ isActive }) =>
            cn(
              'flex items-center gap-3 px-3 py-2 text-sm font-medium transition-colors',
              isActive
                ? 'bg-primary text-primary-foreground'
                : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
            )
          }
        >
          <Icon className="h-4 w-4" />
          {label}
        </NavLink>
      ))}
    </nav>
  );
}
