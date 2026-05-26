import { useRef, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft, FileText, Tag, Paintbrush, Printer, X, Plus, Camera,
  CheckCircle2, Clock, MessageSquare, Trash2, ListTodo, Image as ImageIco,
} from 'lucide-react'
import {
  STAGES, ROLES, PAINTER_RATE,
  dealerName, roleName, stageName,
} from '../data/mockData.js'

// --- Documentos imprimibles ---------------------------------
function LabelDoc({ o }) {
  return (
    <div className="doc label">
      <div className="qr" />
      <h4>#{o.orderNumber}</h4>
      <div>{o.clientName} / {dealerName(o.dealer)}</div>
      <div>{o.designCode}</div>
      <div>{o.doorType} — {o.color} — {o.glass}</div>
      <div>Piezas: {o.pieces}</div>
      <div>Ref. cliente: {o.clientRef}</div>
    </div>
  )
}

function PainterDoc({ o }) {
  return (
    <div className="doc">
      <h4>Hoja del Pintor</h4>
      <table>
        <thead>
          <tr><th>Company</th><th>Order #</th><th>Client</th><th>Color</th>
            <th>Door</th><th className="right">SQF</th>
            <th className="right">Rate</th><th className="right">Total</th></tr>
        </thead>
        <tbody>
          <tr>
            <td>{dealerName(o.dealer)}</td>
            <td>{o.orderNumber}</td>
            <td>{o.clientName}</td>
            <td>{o.color}</td>
            <td>{o.doorType.includes('Double') ? 'DD' : 'SD'}</td>
            <td className="right">{o.sqf}</td>
            <td className="right">${PAINTER_RATE}</td>
            <td className="right"><b>${(o.sqf * PAINTER_RATE).toFixed(2)}</b></td>
          </tr>
        </tbody>
      </table>
      <p className="muted">Monto a pagar al pintor = SQF × tarifa.</p>
    </div>
  )
}

function OrderSheet({ o }) {
  return (
    <div className="doc">
      <h4>Ficha de Orden #{o.orderNumber}</h4>
      <div className="kv" style={{ gridTemplateColumns: '120px 1fr' }}>
        <dt>Cliente</dt><dd>{o.clientName}</dd>
        <dt>Teléfono</dt><dd>{o.clientPhone}</dd>
        <dt>Dirección</dt><dd>{o.clientAddress}</dd>
        <dt>Email</dt><dd>{o.clientEmail}</dd>
        <dt>Dealer</dt><dd>{dealerName(o.dealer)}</dd>
        <dt>Ref. cliente</dt><dd>{o.clientRef}</dd>
        <dt>Diseño</dt><dd>{o.designCode}</dd>
        <dt>Puerta</dt><dd>{o.doorType} — {o.color}</dd>
        <dt>Área</dt><dd>{o.sqf} SQF · {o.pieces} piezas</dd>
        <dt>Pago</dt><dd>{o.paymentStatus}</dd>
      </div>
    </div>
  )
}

const DOCS = {
  label:   { title: 'Etiqueta del Diseñador', render: LabelDoc },
  painter: { title: 'Hoja del Pintor',        render: PainterDoc },
  sheet:   { title: 'Ficha de Orden',         render: OrderSheet },
}

function Modal({ docKey, order, onClose }) {
  if (!docKey) return null
  const D = DOCS[docKey]
  const Body = D.render
  return (
    <div className="modal-bg" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-head">
          <h3>{D.title}</h3>
          <button className="x" onClick={onClose}><X size={18} /></button>
        </div>
        <div className="modal-body print-area">
          <Body o={order} />
          <div className="doc-actions no-print">
            <button className="btn ghost sm" onClick={onClose}>Cerrar</button>
            <button className="btn sm" onClick={() => window.print()}>
              <Printer size={14} /> Imprimir
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// --- Panel: Tareas -------------------------------------------------
function TasksPanel({ orderId, ctx }) {
  const { tasks, addTask, completeTask, updateTask } = ctx
  const myTasks = tasks.filter(t => t.orderId === orderId)
  const [adding, setAdding] = useState(false)
  const [draft, setDraft] = useState({ title: '', assignee: 'cnc', stage: 'cnc', deadline: '' })

  const save = () => {
    if (!draft.title.trim()) return
    addTask(orderId, draft)
    setDraft({ title: '', assignee: 'cnc', stage: 'cnc', deadline: '' })
    setAdding(false)
  }

  return (
    <div className="panel">
      <div className="panel-head">
        <h3><ListTodo size={15} style={{ verticalAlign: -2 }} /> Tareas ({myTasks.length})</h3>
        <button className="btn sm" onClick={() => setAdding(!adding)}>
          <Plus size={13} /> {adding ? 'Cancelar' : 'Nueva'}
        </button>
      </div>

      {adding && (
        <div className="task-form">
          <input placeholder="Que hay que hacer?"
                 value={draft.title} onChange={e => setDraft({ ...draft, title: e.target.value })} />
          <div style={{ display: 'flex', gap: 6 }}>
            <select value={draft.assignee}
                    onChange={e => setDraft({ ...draft, assignee: e.target.value })}>
              {ROLES.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
            </select>
            <select value={draft.stage}
                    onChange={e => setDraft({ ...draft, stage: e.target.value })}>
              {STAGES.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
            <input type="date" value={draft.deadline}
                   onChange={e => setDraft({ ...draft, deadline: e.target.value })} />
            <button className="btn sm" onClick={save}>Crear</button>
          </div>
        </div>
      )}

      {myTasks.length === 0 && !adding && (
        <p className="muted">Sin tareas. Agrega una para dividir el trabajo de la orden.</p>
      )}

      <ul className="task-list">
        {myTasks.map(t => (
          <li key={t.id} className={'task-item ' + t.status}>
            <button
              className={'task-check ' + (t.status === 'done' ? 'on' : '')}
              onClick={() => t.status === 'done'
                ? updateTask(t.id, { status: 'pending', completedAt: null })
                : completeTask(t.id)}
              title="Marcar"
            >
              {t.status === 'done' && <CheckCircle2 size={14} />}
            </button>
            <div className="task-body">
              <div className="task-title">{t.title}</div>
              <div className="task-meta">
                <span className="tag">{roleName(t.assignee)}</span>
                <span className="tag">{stageName(t.stage)}</span>
                {t.deadline && (
                  <span className="tag warn">
                    <Clock size={10} /> {t.deadline}
                  </span>
                )}
                {t.status === 'in_progress' && <span className="pill warn">En curso</span>}
                {t.status === 'done' && <span className="pill ok">Hecho</span>}
              </div>
              {t.notes && <div className="task-note">📝 {t.notes}</div>}
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}

// --- Panel: Comentarios + actividad --------------------------------
function CommentsPanel({ orderId, order, ctx }) {
  const { comments, addComment } = ctx
  const myComments = comments.filter(c => c.orderId === orderId)
  const [text, setText] = useState('')

  const send = () => {
    if (!text.trim()) return
    addComment(orderId, ctx.role ? roleName(ctx.role) : 'Administracion', text.trim())
    setText('')
  }

  // Mezcla cronologica: comentarios + cambios de etapa.
  const feed = [
    ...myComments.map(c => ({ type: 'comment', ...c })),
    ...order.history.map((h, i) => ({
      type: 'stage', id: 'h' + i,
      by: h.by, date: h.date, text: `Pasó a "${stageName(h.stage)}"`,
    })),
  ].sort((a, b) => (a.date > b.date ? -1 : 1))

  return (
    <div className="panel">
      <h3><MessageSquare size={15} style={{ verticalAlign: -2 }} /> Conversacion y actividad</h3>

      <div className="comment-input">
        <textarea rows="2" placeholder="Escribe un comentario al equipo…"
                  value={text} onChange={e => setText(e.target.value)} />
        <button className="btn sm" onClick={send}>Enviar</button>
      </div>

      <ul className="feed">
        {feed.map(f => (
          <li key={f.type + f.id} className={'feed-item ' + f.type}>
            <div className="feed-head">
              <b>{f.by}</b>
              <small>{f.date}</small>
            </div>
            <div className="feed-text">{f.text}</div>
          </li>
        ))}
      </ul>
    </div>
  )
}

// --- Panel: Fotos --------------------------------------------------
function PhotosPanel({ orderId, ctx }) {
  const { photos, addPhoto, deletePhoto, role } = ctx
  const myPhotos = photos.filter(p => p.orderId === orderId)
  const [open, setOpen] = useState(null)
  const fileRef = useRef(null)

  const onUpload = (e) => {
    const files = Array.from(e.target.files || [])
    files.forEach(f => addPhoto(orderId, f, role ? roleName(role) : 'Administracion'))
    e.target.value = ''
  }

  return (
    <div className="panel">
      <div className="panel-head">
        <h3><ImageIco size={15} style={{ verticalAlign: -2 }} /> Fotos ({myPhotos.length})</h3>
        <button className="btn sm" onClick={() => fileRef.current?.click()}>
          <Camera size={13} /> Subir
        </button>
        <input type="file" hidden multiple accept="image/*" ref={fileRef} onChange={onUpload} />
      </div>

      {myPhotos.length === 0 && (
        <p className="muted">Sin fotos. Adjuntá el contrato, medidas, avance o instalacion final.</p>
      )}

      <div className="photo-grid">
        {myPhotos.map(p => (
          <div key={p.id} className="photo-thumb">
            <img src={p.url} alt={p.name} onClick={() => setOpen(p)} />
            <div className="photo-info">
              <small>{p.uploadedBy} · {p.date}</small>
              <button className="x" onClick={() => deletePhoto(p.id)} title="Borrar">
                <Trash2 size={12} />
              </button>
            </div>
          </div>
        ))}
      </div>

      {open && (
        <div className="modal-bg" onClick={() => setOpen(null)}>
          <div className="lightbox" onClick={e => e.stopPropagation()}>
            <img src={open.url} alt={open.name} />
            <button className="x" onClick={() => setOpen(null)}><X size={18} /></button>
            <div className="lightbox-info">
              {open.name} · {open.uploadedBy} · {open.date}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// --- Pagina --------------------------------------------------------
export default function OrderDetail({ ctx }) {
  const { orders, moveOrder } = ctx
  const { id } = useParams()
  const navigate = useNavigate()
  const [doc, setDoc] = useState(null)
  const order = orders.find(o => o.id === Number(id))

  if (!order) return <p>Orden no encontrada.</p>

  return (
    <>
      <button className="btn ghost sm" onClick={() => navigate('/')}>
        <ArrowLeft size={14} /> Volver al tablero
      </button>

      <div className="detail-grid" style={{ marginTop: 14 }}>
        <div>
          <div className="panel">
            <h3>Orden #{order.orderNumber} · {order.designCode}</h3>
            <dl className="kv">
              <dt>Cliente</dt><dd>{order.clientName}</dd>
              <dt>Teléfono</dt><dd>{order.clientPhone}</dd>
              <dt>Dirección</dt><dd>{order.clientAddress}</dd>
              <dt>Email</dt><dd>{order.clientEmail}</dd>
              <dt>Dealer</dt><dd>{dealerName(order.dealer)}</dd>
              <dt>Ref. cliente</dt><dd>{order.clientRef}</dd>
              <dt>Tipo de puerta</dt><dd>{order.doorType}</dd>
              <dt>Color / Vidrio</dt><dd>{order.color} · {order.glass}</dd>
              <dt>Área</dt><dd>{order.sqf} SQF · {order.pieces} piezas</dd>
              <dt>Estado de pago</dt>
              <dd>
                <span className={'pill ' + (order.paymentStatus === 'Pagado' ? 'ok' : 'warn')}>
                  {order.paymentStatus}
                </span>
              </dd>
            </dl>
          </div>

          <TasksPanel orderId={order.id} ctx={ctx} />
          <PhotosPanel orderId={order.id} ctx={ctx} />
          <CommentsPanel orderId={order.id} order={order} ctx={ctx} />

          <div className="panel">
            <h3>Documentos</h3>
            <p className="muted">Se generan desde los datos de la orden — sin volver a escribir nada.</p>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <button className="btn ghost sm" onClick={() => setDoc('sheet')}>
                <FileText size={14} /> Ficha de orden
              </button>
              <button className="btn ghost sm" onClick={() => setDoc('label')}>
                <Tag size={14} /> Etiqueta del diseñador
              </button>
              <button className="btn ghost sm" onClick={() => setDoc('painter')}>
                <Paintbrush size={14} /> Hoja del pintor
              </button>
            </div>
          </div>
        </div>

        <div>
          <div className="panel">
            <h3>Etapa actual</h3>
            <p><span className="pill ok">{stageName(order.stage)}</span></p>
            <label className="fld">
              <span>Mover a otra etapa</span>
              <select
                value={order.stage}
                onChange={e => moveOrder(order.id, e.target.value)}
              >
                {STAGES.map(s => (
                  <option key={s.id} value={s.id}>
                    {s.name}{s.optional ? ' (opcional)' : ''}
                  </option>
                ))}
              </select>
            </label>
            <label className="fld" style={{ marginBottom: 0 }}>
              <span>Responsable asignado</span>
              <select defaultValue={order.assignee}>
                {ROLES.map(r => <option key={r.id} value={r.id}>{r.name} — {r.role}</option>)}
              </select>
            </label>
          </div>

          <div className="panel">
            <h3>Historial de etapas</h3>
            <ul className="timeline">
              {order.history.map((h, i) => (
                <li key={i} className={i < order.history.length - 1 ? 'done' : ''}>
                  <div>{stageName(h.stage)}</div>
                  <small>{h.by} · {h.date}</small>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      <Modal docKey={doc} order={order} onClose={() => setDoc(null)} />
    </>
  )
}
