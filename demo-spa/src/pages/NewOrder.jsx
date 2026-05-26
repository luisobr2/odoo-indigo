import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Zap, Check } from 'lucide-react'
import {
  DEALERS, DOOR_TYPES, COLORS, ROLES, DESIGN_CATALOG,
} from '../data/mockData.js'

const EMPTY = {
  clientName: '', clientPhone: '', clientAddress: '', clientEmail: '',
  clientRef: '', dealer: 'locktight', designCode: '', doorType: 'Single Door',
  color: 'White', glass: 'Clear', sqf: '', pieces: 1,
  paymentStatus: 'Pendiente', assignee: 'majela',
}

export default function NewOrder({ ctx }) {
  const { addOrder } = ctx
  const navigate = useNavigate()
  const [f, setF] = useState(EMPTY)
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })

  const submit = (e) => {
    e.preventDefault()
    const dealer = DEALERS.find(d => d.id === f.dealer)
    addOrder({
      ...f,
      sqf: Number(f.sqf) || 0,
      pieces: Number(f.pieces) || 1,
      orderNumber: 'NEW-' + Math.floor(1000 + Math.random() * 9000),
      // Flujo flexible: arranca en New Order; si el dealer no usa diseño,
      // el tablero lo deja saltar directo a CNC.
      stage: 'new',
    })
    navigate('/')
  }

  return (
    <form onSubmit={submit}>
      <div className="flow-note">
        <Zap size={15} />
        <span>
          Captura rápida: la orden se registra <b>una sola vez</b>. Sirve igual para
          pedidos del portal web, de WhatsApp o en papel.
        </span>
      </div>

      <div className="detail-grid">
        <div className="panel">
          <h3>Datos del cliente</h3>
          <label className="fld"><span>Nombre del cliente *</span>
            <input required value={f.clientName} onChange={set('clientName')} /></label>
          <label className="fld"><span>Teléfono</span>
            <input value={f.clientPhone} onChange={set('clientPhone')} /></label>
          <label className="fld"><span>Dirección</span>
            <input value={f.clientAddress} onChange={set('clientAddress')} /></label>
          <label className="fld"><span>Email</span>
            <input type="email" value={f.clientEmail} onChange={set('clientEmail')} /></label>
          <label className="fld" style={{ marginBottom: 0 }}><span>Código referencia del cliente</span>
            <input value={f.clientRef} onChange={set('clientRef')} /></label>
        </div>

        <div className="panel">
          <h3>Datos de la orden</h3>
          <label className="fld"><span>Compañía origen (dealer)</span>
            <select value={f.dealer} onChange={set('dealer')}>
              {DEALERS.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
            </select></label>
          <label className="fld"><span>Código de diseño</span>
            <input list="designs" placeholder="ej. ID70 / TD-SD-W06"
              value={f.designCode} onChange={set('designCode')} />
            <datalist id="designs">
              {DESIGN_CATALOG.map(d => <option key={d} value={d} />)}
            </datalist></label>
          <label className="fld"><span>Tipo de puerta</span>
            <select value={f.doorType} onChange={set('doorType')}>
              {DOOR_TYPES.map(d => <option key={d}>{d}</option>)}
            </select></label>
          <label className="fld"><span>Color / Finish</span>
            <select value={f.color} onChange={set('color')}>
              {COLORS.map(c => <option key={c}>{c}</option>)}
            </select></label>
          <div style={{ display: 'flex', gap: 10 }}>
            <label className="fld" style={{ flex: 1 }}><span>Área (SQF)</span>
              <input type="number" step="0.01" value={f.sqf} onChange={set('sqf')} /></label>
            <label className="fld" style={{ flex: 1 }}><span>Piezas</span>
              <input type="number" min="1" value={f.pieces} onChange={set('pieces')} /></label>
          </div>
          <label className="fld"><span>Estado del pago</span>
            <select value={f.paymentStatus} onChange={set('paymentStatus')}>
              <option>Pendiente</option><option>Pagado</option>
            </select></label>
          <label className="fld" style={{ marginBottom: 0 }}><span>Asignar a</span>
            <select value={f.assignee} onChange={set('assignee')}>
              {ROLES.map(r => <option key={r.id} value={r.id}>{r.name} — {r.role}</option>)}
            </select></label>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 8 }}>
        <button type="submit" className="btn"><Check size={15} strokeWidth={2.5} /> Crear orden</button>
        <button type="button" className="btn ghost" onClick={() => navigate('/')}>Cancelar</button>
      </div>
    </form>
  )
}
