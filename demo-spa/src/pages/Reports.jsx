import { STAGES, DEALERS, PAINTER_RATE, dealerName } from '../data/mockData.js'

function Bars({ title, data }) {
  const max = Math.max(1, ...data.map(d => d.n))
  return (
    <div className="panel">
      <h3>{title}</h3>
      {data.map(d => (
        <div className="bar-row" key={d.label}>
          <span className="lbl">{d.label}</span>
          <div className="bar-track">
            <div className="bar-fill" style={{ width: (d.n / max * 100) + '%' }} />
          </div>
          <span className="n">{d.n}</span>
        </div>
      ))}
    </div>
  )
}

export default function Reports({ ctx }) {
  const { orders } = ctx
  const open = orders.filter(o => !['closed'].includes(o.stage))
  const wip = orders.filter(o => !['new', 'invoiced', 'closed'].includes(o.stage))
  const sqfPainted = orders
    .filter(o => ['paint', 'ready_inst', 'inst_sched', 'installed', 'invoiced', 'closed'].includes(o.stage))
    .reduce((s, o) => s + o.sqf, 0)

  const byStage = STAGES
    .map(s => ({ label: s.name, n: orders.filter(o => o.stage === s.id).length }))
    .filter(d => d.n > 0)

  const byDealer = DEALERS.map(d => ({
    label: d.name, n: orders.filter(o => o.dealer === d.id).length,
  }))

  return (
    <>
      <div className="kpis">
        <div className="kpi"><div className="v">{orders.length}</div><div className="l">Órdenes totales</div></div>
        <div className="kpi"><div className="v">{open.length}</div><div className="l">Órdenes abiertas</div></div>
        <div className="kpi"><div className="v">{wip.length}</div><div className="l">En producción</div></div>
        <div className="kpi"><div className="v">${(sqfPainted * PAINTER_RATE).toFixed(0)}</div><div className="l">Pagos pintor (período)</div></div>
      </div>

      <div className="detail-grid">
        <Bars title="Órdenes por etapa" data={byStage} />
        <Bars title="Órdenes por dealer" data={byDealer} />
      </div>
    </>
  )
}
