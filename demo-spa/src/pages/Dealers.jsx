import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Building2, Phone, Mail, MapPin, ChevronRight } from 'lucide-react'
import { DEALERS, STAGES } from '../data/mockData.js'

export default function Dealers({ ctx }) {
  const { orders, pipeline } = ctx
  const navigate = useNavigate()
  const [selId, setSelId] = useState(DEALERS[0].id)

  const sel = DEALERS.find(d => d.id === selId)
  const dealerOrders = orders.filter(o => o.dealer === selId)
  const totalSqf = dealerOrders.reduce((a, o) => a + (o.sqf || 0), 0)
  const totalAmount = totalSqf * sel.pricePerSqf
  const pending = dealerOrders.filter(o => o.paymentStatus === 'Pendiente')
  const pendingAmount = pending.reduce((a, o) => a + o.sqf * sel.pricePerSqf, 0)
  const enabledOpt = pipeline[selId] || []

  return (
    <>
      <div className="flow-note">
        <Building2 size={15} />
        <span>
          Mini-CRM de dealers. Cada dealer concentra contactos, tarifas, condiciones,
          historial de ordenes, deuda y flujo de produccion configurado.
        </span>
      </div>

      <div className="detail-grid">
        <div>
          <div className="panel">
            <h3>Dealers</h3>
            <ul className="dealer-list">
              {DEALERS.map(d => {
                const n = orders.filter(o => o.dealer === d.id).length
                return (
                  <li key={d.id}
                      className={'dealer-item' + (d.id === selId ? ' active' : '')}
                      onClick={() => setSelId(d.id)}>
                    <div>
                      <b>{d.name}</b>
                      <small>{d.contact}</small>
                    </div>
                    <span className="col-count">{n}</span>
                  </li>
                )
              })}
            </ul>
          </div>
        </div>

        <div>
          <div className="panel">
            <h3>{sel.name}</h3>
            <dl className="kv">
              <dt>Contacto</dt><dd>{sel.contact}</dd>
              <dt><Phone size={12} style={{ verticalAlign: -2 }} /> Telefono</dt>
              <dd>{sel.phone}</dd>
              <dt><Mail size={12} style={{ verticalAlign: -2 }} /> Email</dt>
              <dd>{sel.email}</dd>
              <dt><MapPin size={12} style={{ verticalAlign: -2 }} /> Direccion</dt>
              <dd>{sel.address}</dd>
              <dt>Tarifa</dt><dd>${sel.pricePerSqf} / SQF</dd>
              <dt>Condiciones</dt><dd>{sel.paymentTerms}</dd>
              <dt>Notas</dt><dd>{sel.notes}</dd>
            </dl>
          </div>

          <div className="kpis" style={{ gridTemplateColumns: 'repeat(3,1fr)' }}>
            <div className="kpi">
              <div className="l">Ordenes totales</div>
              <div className="v">{dealerOrders.length}</div>
            </div>
            <div className="kpi">
              <div className="l">Facturacion estimada</div>
              <div className="v">${totalAmount.toFixed(0)}</div>
            </div>
            <div className="kpi">
              <div className="l">Pendiente de cobro</div>
              <div className="v" style={{ color: pendingAmount ? 'var(--warn)' : 'inherit' }}>
                ${pendingAmount.toFixed(0)}
              </div>
            </div>
          </div>

          <div className="panel">
            <h3>Flujo configurado</h3>
            <div className="flow-preview-chain">
              {STAGES
                .filter(s => !s.optional || enabledOpt.includes(s.id))
                .map((s, i) => (
                  <span key={s.id} className={'chip' + (s.optional ? ' opt' : '')}>
                    {i + 1}. {s.name}
                  </span>
                ))}
            </div>
            <p className="muted" style={{ marginTop: 10 }}>
              Editable desde <a href="/pipeline" style={{ color: 'var(--azul)' }}>Config. de Pipeline</a>.
            </p>
          </div>

          <div className="panel">
            <h3>Ordenes recientes</h3>
            <table>
              <thead>
                <tr><th>#</th><th>Cliente</th><th>Diseño</th><th>Etapa</th>
                  <th className="right">SQF</th><th></th></tr>
              </thead>
              <tbody>
                {dealerOrders.slice(0, 8).map(o => (
                  <tr key={o.id} onClick={() => navigate(`/ordenes/${o.id}`)}
                      style={{ cursor: 'pointer' }}>
                    <td>{o.orderNumber}</td>
                    <td>{o.clientName}</td>
                    <td><span className="tag design">{o.designCode}</span></td>
                    <td><span className="pill ok">{o.stage}</span></td>
                    <td className="right">{o.sqf}</td>
                    <td className="right"><ChevronRight size={14} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </>
  )
}
