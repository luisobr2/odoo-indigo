import { Sliders, Info, Check } from 'lucide-react'
import { DEALERS, STAGES } from '../data/mockData.js'

// Etapas opcionales — son las unicas que se pueden activar/desactivar
// por dealer. Las obligatorias siempre van.
const OPTIONAL = STAGES.filter(s => s.optional)
const REQUIRED = STAGES.filter(s => !s.optional)

export default function PipelineConfig({ ctx }) {
  const { pipeline, togglePipelineStage } = ctx

  return (
    <>
      <div className="flow-note">
        <Info size={15} />
        <span>
          Cada dealer puede tener su propio flujo. Las etapas <b>obligatorias</b>{' '}
          (New Order → Digitalization → CNC → Painting → Installation → Invoice → Closed)
          siempre van. Las <b>opcionales</b> (Design Confirmation, Measurement) se activan
          aqui — sin tocar codigo. El tablero Kanban se ajusta automaticamente.
        </span>
      </div>

      <div className="panel">
        <h3><Sliders size={16} style={{ verticalAlign: '-3px', marginRight: 6 }} />
          Etapas opcionales habilitadas por dealer
        </h3>

        <table className="pipeline-tbl">
          <thead>
            <tr>
              <th>Dealer</th>
              {OPTIONAL.map(s => (
                <th key={s.id} className="center">{s.name}</th>
              ))}
              <th className="right">Etapas activas</th>
            </tr>
          </thead>
          <tbody>
            {DEALERS.map(d => {
              const enabled = pipeline[d.id] || []
              const total = REQUIRED.length + enabled.length
              return (
                <tr key={d.id}>
                  <td><b>{d.name}</b></td>
                  {OPTIONAL.map(s => {
                    const on = enabled.includes(s.id)
                    return (
                      <td key={s.id} className="center">
                        <button
                          className={'toggle' + (on ? ' on' : '')}
                          onClick={() => togglePipelineStage(d.id, s.id)}
                          title={on ? 'Desactivar' : 'Activar'}
                        >
                          {on ? <Check size={13} strokeWidth={3} /> : ''}
                        </button>
                      </td>
                    )
                  })}
                  <td className="right">
                    <span className="pill ok">{total} / {STAGES.length}</span>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <div className="panel">
        <h3>Vista previa del flujo</h3>
        {DEALERS.map(d => {
          const enabled = pipeline[d.id] || []
          const flow = STAGES.filter(s => !s.optional || enabled.includes(s.id))
          return (
            <div key={d.id} className="flow-preview">
              <div className="flow-preview-label">{d.name}</div>
              <div className="flow-preview-chain">
                {flow.map((s, i) => (
                  <span key={s.id} className={'chip' + (s.optional ? ' opt' : '')}>
                    {i + 1}. {s.name}
                  </span>
                ))}
              </div>
            </div>
          )
        })}
      </div>
    </>
  )
}
