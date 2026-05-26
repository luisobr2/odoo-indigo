import { useState } from 'react'
import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import Kanban from './pages/Kanban.jsx'
import OrderDetail from './pages/OrderDetail.jsx'
import NewOrder from './pages/NewOrder.jsx'
import Payments from './pages/Payments.jsx'
import Reports from './pages/Reports.jsx'
import Designs from './pages/Designs.jsx'
import Dealers from './pages/Dealers.jsx'
import PipelineConfig from './pages/PipelineConfig.jsx'
import Installer from './pages/Installer.jsx'
import {
  ORDERS, TASKS, COMMENTS, PHOTOS, DEFAULT_PIPELINE, nextStage,
} from './data/mockData.js'

export default function App() {
  // ----- Estado en memoria: simula la base de datos (Woo API real) -----
  const [orders,   setOrders]   = useState(ORDERS)
  const [tasks,    setTasks]    = useState(TASKS)
  const [comments, setComments] = useState(COMMENTS)
  const [photos,   setPhotos]   = useState(PHOTOS)
  const [pipeline, setPipeline] = useState(DEFAULT_PIPELINE)
  const [role,     setRole]     = useState('') // '' = Admin / acceso total
  const [search,   setSearch]   = useState('')

  // ----- Ordenes -----
  const moveOrder = (id, stage, by = 'Demo') =>
    setOrders(prev => prev.map(o =>
      o.id === id
        ? { ...o, stage, history: [...o.history, { stage, by, date: '2026-05-22' }] }
        : o,
    ))

  const advanceOrder = (id) => {
    const o = orders.find(x => x.id === id)
    const ns = o && nextStage(o, pipeline)
    if (ns) moveOrder(id, ns)
  }

  const addOrder = (data) =>
    setOrders(prev => [
      { id: Math.max(...prev.map(o => o.id)) + 1,
        history: [{ stage: 'new', by: 'Majela', date: '2026-05-22' }],
        ...data },
      ...prev,
    ])

  // ----- Tareas -----
  const addTask = (orderId, data) =>
    setTasks(prev => [
      ...prev,
      { id: Math.max(0, ...prev.map(t => t.id)) + 1,
        orderId, status: 'pending', createdAt: '2026-05-22', ...data },
    ])

  const updateTask = (id, patch) =>
    setTasks(prev => prev.map(t => t.id === id ? { ...t, ...patch } : t))

  const completeTask = (id) =>
    updateTask(id, { status: 'done', completedAt: '2026-05-22' })

  // ----- Comentarios -----
  const addComment = (orderId, by, text) =>
    setComments(prev => [
      ...prev,
      { id: Math.max(0, ...prev.map(c => c.id)) + 1,
        orderId, by, text,
        date: new Date().toISOString().slice(0, 16).replace('T', ' ') },
    ])

  // ----- Fotos (mock con FileReader/object URLs) -----
  const addPhoto = (orderId, file, by, taskId = null, kind = 'photo') => {
    const url = URL.createObjectURL(file)
    setPhotos(prev => [
      ...prev,
      { id: Math.max(0, ...prev.map(p => p.id)) + 1,
        orderId, taskId, name: file.name, url, uploadedBy: by,
        date: '2026-05-22', kind },
    ])
  }
  const deletePhoto = (id) => setPhotos(prev => prev.filter(p => p.id !== id))

  // ----- Pipeline configurator -----
  const togglePipelineStage = (dealerId, stageId) =>
    setPipeline(prev => {
      const cur = prev[dealerId] || []
      const next = cur.includes(stageId)
        ? cur.filter(s => s !== stageId)
        : [...cur, stageId]
      return { ...prev, [dealerId]: next }
    })

  const ctx = {
    // datos
    orders, tasks, comments, photos, pipeline,
    // ordenes
    moveOrder, advanceOrder, addOrder,
    // tareas
    addTask, updateTask, completeTask,
    // comentarios
    addComment,
    // fotos
    addPhoto, deletePhoto,
    // pipeline
    togglePipelineStage,
    // ui
    role, search,
  }

  return (
    <Routes>
      <Route element={<Layout role={role} setRole={setRole}
                              search={search} setSearch={setSearch} />}>
        <Route index               element={<Kanban       ctx={ctx} />} />
        <Route path="ordenes/:id"  element={<OrderDetail  ctx={ctx} />} />
        <Route path="nueva"        element={<NewOrder     ctx={ctx} />} />
        <Route path="disenos"      element={<Designs      ctx={ctx} />} />
        <Route path="dealers"      element={<Dealers      ctx={ctx} />} />
        <Route path="pipeline"     element={<PipelineConfig ctx={ctx} />} />
        <Route path="instalador"   element={<Installer    ctx={ctx} />} />
        <Route path="pagos"        element={<Payments     ctx={ctx} />} />
        <Route path="reportes"     element={<Reports      ctx={ctx} />} />
      </Route>
    </Routes>
  )
}
