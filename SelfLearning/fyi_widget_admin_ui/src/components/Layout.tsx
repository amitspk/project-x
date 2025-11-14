import { NavLink } from 'react-router-dom';
import { ReactNode, useState } from 'react';
import { Bars3Icon } from '@heroicons/react/24/outline';

const navItems = [
  { to: '/', label: 'Dashboard' },
  { to: '/publishers', label: 'Publishers' },
  { to: '/jobs', label: 'Jobs & Queue' },
  { to: '/cleanup', label: 'Content Cleanup' },
  { to: '/settings', label: 'Settings' }
];

export const Layout: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  return (
    <div className="min-h-screen bg-slate-100 text-slate-900">
      <header className="bg-white shadow-sm sticky top-0 z-40">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4">
          <button
            className="md:hidden inline-flex items-center justify-center p-2 rounded-md text-slate-500 hover:text-slate-700 hover:bg-slate-100"
            aria-label="Toggle navigation"
            onClick={() => setMobileNavOpen(!mobileNavOpen)}
          >
            <Bars3Icon className="h-6 w-6" />
          </button>
          <h1 className="text-lg font-semibold">FYI Widget Admin</h1>
          <span className="hidden text-sm text-slate-500 md:inline">
            Manage publishers, monitor jobs, and perform maintenance
          </span>
        </div>
        <nav className={`${mobileNavOpen ? 'block' : 'hidden'} border-t bg-white md:block`}>
          <div className="mx-auto flex flex-col gap-2 px-4 py-4 md:max-w-6xl md:flex-row md:items-center md:gap-6 md:py-0">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                className={({ isActive }) =>
                  `rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                    isActive ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-slate-200 hover:text-slate-900'
                  }`
                }
                onClick={() => setMobileNavOpen(false)}
              >
                {item.label}
              </NavLink>
            ))}
          </div>
        </nav>
      </header>
      <main className="mx-auto max-w-6xl px-4 pb-16 pt-6 md:pt-10">
        {children}
      </main>
    </div>
  );
};
