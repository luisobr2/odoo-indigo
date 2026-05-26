import { Info, Printer } from 'lucide-react'
import { PAINTER_RATE, dealerName } from '../data/mockData.js'

// Etapas en las que la pieza ya pasó (o está en) pintura.
const PAINTED = ['paint', 'ready_inst', 'inst_sched', 'installed', 'invoiced', 'closed']

export default function Payments({ ctx }) {
  const { orders } = ctx
  const rows = orders
    .filter(o => PAINTED.includes(o.stage))
    .map(o => ({ ...o, pay: o.sqf * PAINTER_RATE }))

  const total = rows.reduce((s, r) => s + r.pay, 0)
  const sqfTotal = rows.reduce((s, r) => s + r.sqf, 0)

  return (
    <>
      <div className="flow-note">
        <Info size={15} />
        <span>
          El pago al pintor se calcula automáticamente: <b>SQF × ${PAINTER_RATE}</b>.
          Cero cálculos a mano.
        </span>
      </div>

      <div className="kpis" style={{ gridTemplateColumns: 'repeat(3,1fr)' }}>
        <div className="kpi"><div className="v">{rows.length}</div><div className="l">Piezas pintadas (período)</div></div>
        <div className="kpi"><div className="v">{sqfTotal.toFixed(2)}</div><div className="l">SQF total</div></div>
        <div className="kpi"><div className="v">${total.toFixed(2)}</div><div className="l">A pagar al Pintor</div></div>
      </div>

      <div className="panel">
        <h3>Liquidación — Pintor · período 01–15 May 2026</h3>
        <table>
          <thead>
            <tr>
              <th>Company</th><th>Order #</th><th>Client</th>
              <th>Color</th><th>Door</th>
              <th className="right">SQF</th><th className="right">Rate</th>
              <th className="right">Total</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(r => (
              <tr key={r.id}>
                <td>{dealerName(r.dealer)}</td>
                <td>{r.orderNumber}</td>
                <td>{r.clientName}</td>
                <td>{r.color}</td>
                <td>{r.doorType.includes('Double') ? 'DD' : 'SD'}</td>
                <td className="right">{r.sqf.toFixed(2)}</td>
                <td className="right">${PAINTER_RATE}</td>
                <td className="right"><b>${r.pay.toFixed(2)}</b></td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <td colSpan={5}><b>Total a pagar</b></td>
              <td className="right"><b>{sqfTotal.toFixed(2)}</b></td>
              <td></td>
              <td className="right"><b>${total.toFixed(2)}</b></td>
            </tr>
          </tfoot>
        </table>
        <div className="doc-actions">
          <button className="btn sm" onClick={() => window.print()}>
            <Printer size={14} /> Imprimir liquidación
          </button>
        </div>
      </div>
    </>
  )
}
