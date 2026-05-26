import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Smartphone, Camera, CheckCircle2, Clock, MapPin, Phone, Image as ImageIco,
} from 'lucide-react'
import {
  ROLES, dealerName, stageName, roleName,
} from '../data/mockData.js'

// Portal movil simplificado para field workers (instaladores / medidor).
// Cuando el rol activo en la topbar es un instalador, esta vista muestra
// sus tareas del dia con accion de "marcar hecho" y "subir foto".
export default function Installer({ ctx }) {
  const { tasks, orders, photos, role, completeTask, addPhoto } = ctx
  const navigate = useNavigate()
  // Si el rol activo es field, lo usamos. Si no, mostramos Javier por defecto.
  const fieldRoles = ROLES.filter(r => r.type === 'field' || r.id === 'javier')
  const [who, setWho] = useState(role && fieldRoles.find(r => r.id === role) ? role : 'javier')

  const myTasks = tasks.filter(t => t.assignee === who && t.status !== 'done')
  const doneToday = tasks.filter(t => t.assignee === who && t.status === 'done')

  return (
    <div className="installer">
      <div className="installer-head">
        <div className="installer-avatar">
          <Smartphone size={20} />
        </div>
        <div>
          <b>{roleName(who)}</b>
          <small>Portal de campo · vista movil</small>
        </div>
        <select className="installer-who" value={who} onChange={e => setWho(e.target.value)}>
          {fieldRoles.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
        </select>
      </div>

      <div className="installer-stats">
        <div><span className="v">{myTasks.length}</span><span className="l">Pendientes</span></div>
        <div><span className="v">{doneToday.length}</span><span className="l">Completadas</span></div>
      </div>

      <h3 className="installer-title">Mis tareas</h3>
      {myTasks.length === 0 && (
        <p className="muted">No tienes tareas pendientes 🎉</p>
      )}
      {myTasks.map(t => {
        const o = orders.find(x => x.id === t.orderId)
        if (!o) return null
        const taskPhotos = photos.filter(p => p.orderId === o.id && p.taskId === t.id)
        return (
          <InstallerTask
            key={t.id} task={t} order={o} photos={taskPhotos}
            onOpen={() => navigate(`/ordenes/${o.id}`)}
            onComplete={() => completeTask(t.id)}
            onPhoto={(file) => addPhoto(o.id, file, roleName(who), t.id, 'field')}
          />
        )
      })}

      {doneToday.length > 0 && (
        <>
          <h3 className="installer-title" style={{ marginTop: 28 }}>Completadas</h3>
          {doneToday.map(t => {
            const o = orders.find(x => x.id === t.orderId)
            return (
              <div key={t.id} className="installer-card done">
                <div>
                  <b>{t.title}</b>
                  <small>#{o?.orderNumber} · {dealerName(o?.dealer)}</small>
                </div>
                <CheckCircle2 size={20} color="#1f9d57" />
              </div>
            )
          })}
        </>
      )}
    </div>
  )
}

function InstallerTask({ task, order, photos, onOpen, onComplete, onPhoto }) {
  const fileRef = useRef(null)
  const [busy, setBusy] = useState(false)

  return (
    <div className="installer-card">
      <div className="installer-card-head" onClick={onOpen}>
        <div>
          <b>{task.title}</b>
          <small>#{order.orderNumber} · {order.clientName}</small>
        </div>
        <span className="pill warn"><Clock size={11} /> {task.deadline}</span>
      </div>

      <div className="installer-card-info">
        <div><MapPin size={13} /> {order.clientAddress}</div>
        <div><Phone size={13} /> {order.clientPhone}</div>
        <div className="muted">Etapa: {stageName(task.stage)}</div>
        {task.notes && <div className="task-note">📝 {task.notes}</div>}
      </div>

      {photos.length > 0 && (
        <div className="installer-photos">
          {photos.map(p => (
            <img key={p.id} src={p.url} alt={p.name}
                 title={`${p.name} · ${p.uploadedBy}`} />
          ))}
        </div>
      )}

      <div className="installer-actions">
        <input
          type="file" accept="image/*" capture="environment" hidden ref={fileRef}
          onChange={e => {
            const file = e.target.files?.[0]
            if (!file) return
            setBusy(true)
            onPhoto(file)
            setTimeout(() => setBusy(false), 200)
            e.target.value = ''
          }}
        />
        <button className="btn ghost" onClick={() => fileRef.current?.click()} disabled={busy}>
          <Camera size={15} /> Subir foto
        </button>
        <button className="btn" onClick={onComplete}>
          <CheckCircle2 size={15} /> Marcar hecho
        </button>
      </div>
    </div>
  )
}
