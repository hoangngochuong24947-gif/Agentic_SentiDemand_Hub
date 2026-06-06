import type { PropsWithChildren, ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { BarChart3, Brain, FileText, Home, ListChecks, Upload } from "lucide-react";

interface LayoutProps extends PropsWithChildren {
  eyebrow?: string;
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}

const navItems = [
  { to: "/", label: "Upload", icon: Upload },
  { to: "/runs", label: "Runs", icon: ListChecks },
  { to: "/workspace", label: "Tables", icon: FileText },
  { to: "/dashboard/latest", label: "Charts", icon: BarChart3 },
  { to: "/insights/latest", label: "Advice", icon: Brain }
];

export function Layout({ eyebrow, title, subtitle, actions, children }: LayoutProps) {
  return (
    <div className="app-shell">
      <header className="topbar">
        <NavLink className="brand" to="/" aria-label="SentiDemand home">
          <Home size={18} aria-hidden="true" />
          <span>SentiDemand</span>
        </NavLink>
        <nav className="nav-list" aria-label="Primary navigation">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}
              to={item.to}
            >
              <item.icon size={16} aria-hidden="true" />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>
      </header>

      <main className="main-content">
        <section className="page-head">
          <div>
            {eyebrow ? <span className="eyebrow">{eyebrow}</span> : null}
            <h1>{title}</h1>
            {subtitle ? <p>{subtitle}</p> : null}
          </div>
          {actions ? <div className="page-actions">{actions}</div> : null}
        </section>
        {children}
      </main>
    </div>
  );
}
