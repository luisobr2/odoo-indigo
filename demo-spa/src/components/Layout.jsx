import { NavLink, Outlet, useLocation } from 'react-router-dom'
import {
  LayoutGrid, PlusCircle, DollarSign, BarChart3, Search,
  LayoutTemplate, Building2, Sliders, Smartphone,
} from 'lucide-react'
import { ROLES } from '../data/mockData.js'

// Grupos de navegacion (separadores visuales).
const NAV = [
  { group: 'Operacion', items: [
    { to: '/',          Ico: LayoutGrid,      label: 'Tablero de Producción', end: true },
    { to: '/nueva',     Ico: PlusCircle,      label: 'Nueva Orden' },
    { to: '/instalador',Ico: Smartphone,      label: 'Portal Instalador' },
  ]},
  { group: 'Catalogos', items: [
    { to: '/disenos',   Ico: LayoutTemplate,  label: 'Catálogo Diseños' },
    { to: '/dealers',   Ico: Building2,       label: 'Dealers (CRM)' },
  ]},
  { group: 'Administracion', items: [
    { to: '/pagos',     Ico: DollarSign,      label: 'Pagos Contratistas' },
    { to: '/reportes',  Ico: BarChart3,       label: 'Reportes' },
    { to: '/pipeline',  Ico: Sliders,         label: 'Config. de Pipeline' },
  ]},
]

const TITLES = {
  '/':            'Tablero de Producción',
  '/nueva':       'Nueva Orden',
  '/disenos':     'Catálogo de Diseños',
  '/dealers':     'Dealers (mini-CRM)',
  '/pipeline':    'Configuración de Pipeline',
  '/instalador':  'Portal del Instalador',
  '/pagos':       'Pagos a Contratistas',
  '/reportes':    'Reportes',
}

export default function Layout({ role, setRole, search, setSearch }) {
  const { pathname } = useLocation()
  const title = TITLES[pathname]
    || (pathname.startsWith('/ordenes') ? 'Detalle de Orden' : 'Indigo')

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <div className="logo">iD</div>
          <div>
            <b>Indigo Decors</b>
            <span>Gestión de Producción</span>
          </div>
        </div>
        <nav className="nav">
          {NAV.map(g => (
            <div key={g.group} className="nav-group">
              <div className="nav-group-label">{g.group}</div>
              {g.items.map(n => (
                <NavLink key={n.to} to={n.to} end={n.end}>
                  <span className="ico"><n.Ico size={17} strokeWidth={2} /></span>
                  <span className="label-txt">{n.label}</span>
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
      </aside>

      <div className="main">
        <div className="demo-banner">
          DEMO INTERACTIVO · datos de ejemplo — Sistema de gestión de producción
          propuesto para Indigo Decors
        </div>
        <header className="topbar">
          <h1>{title}</h1>
          <div className="topbar-tools">
            <div className="search-box">
              <Search size={15} strokeWidth={2.2} />
              <input
                className="search"
                placeholder="Buscar orden, cliente o diseño…"
                value={search}
                onChange={e => setSearch(e.target.value)}
              />
            </div>
            <div className="role-switch">
              <span>Viendo como</span>
              <select value={role} onChange={e => setRole(e.target.value)}>
                <option value="">Administración · acceso total</option>
                {ROLES.filter(r => r.id !== 'admin').map(r => (
                  <option key={r.id} value={r.id}>{r.name} — {r.role}</option>
                ))}
              </select>
            </div>
            <span className="demo-tag">DEMO</span>
          </div>
        </header>
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
