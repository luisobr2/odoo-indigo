import { useNavigate } from 'react-router-dom'
import { X, ChevronRight, ArrowRight } from 'lucide-react'
import {
  PAINTER_RATE, dealerName, stageName, nextStage,
} from '../data/mockData.js'

// Panel deslizante de vista rapida: ver un pedido sin salir del tablero.
export default function QuickView({ order, onClose, onAdvance }) {
  const navigate = useNavigate()
  if (!order) return null

  const ns = nextStage(order)

  return (
    <div className="drawer-bg" onClick={onClose}>
      <aside className="drawer" onClick={e => e.stopPropagation()}>
        <div className="drawer-head">
          <div>
            <b>Orden #{order.orderNumber}</b>
            <div className="muted">{order.designCode} · {dealerName(order.dealer)}</div>
          </div>
          <button className="x" onClick={onClose}><X size={18} /></button>
        </div>

        <div className="drawer-body">
          <span className="pill ok">{stageName(order.stage)}</span>

          <dl className="kv" style={{ marginTop: 14 }}>
            <dt>Cliente</dt><dd>{order.clientName}</dd>
            <dt>Teléfono</dt><dd>{order.clientPhone}</dd>
            <dt>Dirección</dt><dd>{order.clientAddress}</dd>
            <dt>Ref. cliente</dt><dd>{order.clientRef}</dd>
            <dt>Puerta</dt><dd>{order.doorType} — {order.color}</dd>
            <dt>Área</dt><dd>{order.sqf} SQF · {order.pieces} piezas</dd>
            <dt>Pago pintor</dt><dd>${(order.sqf * PAINTER_RATE).toFixed(2)}</dd>
            <dt>Estado pago</dt>
            <dd>
              <span className={'pill ' + (order.paymentStatus === 'Pagado' ? 'ok' : 'warn')}>
                {order.paymentStatus}
              </span>
            </dd>
          </dl>
        </div>

        <div className="drawer-foot">
          {ns && (
            <button className="btn" onClick={() => onAdvance(order.id)}>
              <ChevronRight size={15} strokeWidth={2.5} /> Avanzar a {stageName(ns)}
            </button>
          )}
          <button className="btn ghost" onClick={() => navigate('/ordenes/' + order.id)}>
            Abrir ficha completa <ArrowRight size={15} />
          </button>
        </div>
      </aside>
    </div>
  )
}
