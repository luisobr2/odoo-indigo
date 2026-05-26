import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { LayoutTemplate, Search as SearchIco } from 'lucide-react'
import { DESIGNS } from '../data/mockData.js'

const CATEGORIES = ['Todas', 'Modern', 'Classic', 'Contemporary', 'Premium']

export default function Designs({ ctx }) {
  const navigate = useNavigate()
  const [cat, setCat] = useState('Todas')
  const [q, setQ] = useState('')

  const filtered = DESIGNS.filter(d => {
    if (cat !== 'Todas' && d.category !== cat) return false
    if (q && !`${d.code} ${d.name}`.toLowerCase().includes(q.toLowerCase())) return false
    return true
  })

  return (
    <>
      <div className="flow-note">
        <LayoutTemplate size={15} />
        <span>
          Catalogo central de diseños — el mismo que usa la captura de orden,
          el portal del dealer y los reportes. Cada diseño tiene variantes
          (Single / Double / Sidelite) y colores disponibles.
        </span>
      </div>

      <div className="filters">
        <div className="search-box" style={{ width: 280 }}>
          <SearchIco size={14} />
          <input className="search" placeholder="Buscar codigo o nombre…"
                 value={q} onChange={e => setQ(e.target.value)} />
        </div>
        <select value={cat} onChange={e => setCat(e.target.value)}>
          {CATEGORIES.map(c => <option key={c}>{c}</option>)}
        </select>
        <span className="sp" />
        <span className="muted">{filtered.length} diseños</span>
        <button className="btn" onClick={() => navigate('/nueva')}>
          + Crear orden con un diseño
        </button>
      </div>

      <div className="design-grid">
        {filtered.map(d => (
          <div key={d.code} className="design-card">
            <img src={d.thumbnail} alt={d.code} />
            <div className="design-body">
              <div className="design-code">{d.code}</div>
              <div className="design-name">{d.name}</div>
              <div className="design-meta">
                <span className="tag design">{d.category}</span>
                {d.variants.map(v => (
                  <span key={v} className="tag">{v}</span>
                ))}
              </div>
              <div className="design-colors">
                {d.colors.map(c => (
                  <span key={c} className={'dot ' + c.toLowerCase()} title={c} />
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>
    </>
  )
}
