import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ChevronRight, Info, UserCheck, Plus } from 'lucide-react'
import {
  STAGES, DEALERS, ROLES, ROLE_STAGES,
  dealerName, roleName, nextStage, stageName,
} from '../data/mockData.js'
import QuickView from '../components/QuickView.jsx'

const colorClass = (c) => c.toLowerCase()

function Card({ order, onOpen, onAdvance, onDragStart, pipeline }) {
  const ns = nextStage(order, pipeline)
  return (
    <div
      className="card"
      draggable
      onDragStart={() => onDragStart(order.id)}
      onClick={() => onOpen(order.id)}
    >
      <div className="num">#{order.orderNumber}</div>
      <div className="client">{order.clientName}</div>
      <div className="meta">
        <span className="tag design">{order.designCode}</span>
        <span className="tag">{order.doorType.replace('Door', 'D.')}</span>
        <span className="tag">
          <span className={'dot ' + colorClass(order.color)} /> {order.color}
        </span>
        <span className="tag">{order.sqf} SQF</span>
        <span className="tag">{dealerName(order.dealer)}</span>
      </div>
      {ns && (
        <button
          className="card-advance"
          title={'Avanzar a ' + stageName(ns)}
          onClick={(e) => { e.stopPropagation(); onAdvance(order.id) }}
        >
          <ChevronRight size={13} strokeWidth={2.5} /> Avanzar
        </button>
      )}
    </div>
  )
}

export default function Kanban({ ctx }) {
  const { orders, moveOrder, advanceOrder, role, search, pipeline } = ctx
  const navigate = useNavigate()
  const [fDealer, setFDealer] = useState('')
  const [dragId, setDragId] = useState(null)
  const [overCol, setOverCol] = useState(null)
  const [quickId, setQuickId] = useState(null)

  const q = search.trim().toLowerCase()
  const filtered = orders.filter(o => {
    if (fDealer && o.dealer !== fDealer) return false
    if (role && o.assignee !== role) return false
    if (q && ![o.orderNumber, o.clientName, o.designCode]
      .some(v => v.toLowerCase().includes(q))) return false
    return true
  })

  // En vista por rol, resaltar solo las columnas que le pertenecen al rol.
  const myStages = role ? (ROLE_STAGES[role] || []) : null
  const myCount = role
    ? orders.filter(o => o.assignee === role && myStages.includes(o.stage)).length
    : 0

  const drop = (stageId) => {
    if (dragId != null) moveOrder(dragId, stageId)
    setDragId(null)
    setOverCol(null)
  }

  const quickOrder = orders.find(o => o.id === quickId) || null

  return (
    <>
      {role ? (
        <div className="flow-note role">
          <UserCheck size={15} />
          <span>
            Estás viendo el tablero como <b>{roleName(role)}</b>.
            Tenés <b>{myCount}</b> {myCount === 1 ? 'orden' : 'órdenes'} en tus etapas.
            Las columnas que te corresponden van resaltadas.
          </span>
        </div>
      ) : (
        <div className="flow-note">
          <Info size={15} />
          <span>
            Flujo flexible: las etapas <b>OPC</b> (Design / Measurement) solo aplican a
            los dealers configurados así; los demás pasan de <b>New Order</b> directo a
            <b> CNC / Router</b>. Usá <b>"Viendo como"</b> para ver el tablero de cada rol.
          </span>
        </div>
      )}

      <div className="filters">
        <select value={fDealer} onChange={e => setFDealer(e.target.value)}>
          <option value="">Todos los dealers</option>
          {DEALERS.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
        </select>
        <span className="sp" />
        <span className="muted">
          {filtered.length} órdenes · arrastrá las tarjetas o usá el botón Avanzar
        </span>
        <button className="btn" onClick={() => navigate('/nueva')}>
          <Plus size={15} strokeWidth={2.5} /> Nueva Orden
        </button>
      </div>

      <div className="kanban">
        {STAGES.map(stage => {
          const cards = filtered.filter(o => o.stage === stage.id)
          const mine = myStages && myStages.includes(stage.id)
          const dim = myStages && !mine
          return (
            <div
              key={stage.id}
              className={'col' + (stage.optional ? ' optional' : '')
                + (mine ? ' mine' : '') + (dim ? ' dim' : '')}
              onDragOver={e => { e.preventDefault(); setOverCol(stage.id) }}
              onDrop={() => drop(stage.id)}
            >
              <div className="col-head">
                <span>
                  {stage.name}{' '}
                  {stage.optional && <span className="opt-badge">OPC</span>}
                </span>
                <span className="col-count">{cards.length}</span>
              </div>
              <div className={'col-body' + (overCol === stage.id ? ' drop' : '')}>
                {cards.map(o => (
                  <Card
                    key={o.id}
                    order={o}
                    pipeline={pipeline}
                    onOpen={setQuickId}
                    onAdvance={advanceOrder}
                    onDragStart={setDragId}
                  />
                ))}
              </div>
            </div>
          )
        })}
      </div>

      <QuickView
        order={quickOrder}
        onClose={() => setQuickId(null)}
        onAdvance={(id) => { advanceOrder(id); setQuickId(null) }}
      />
    </>
  )
}
