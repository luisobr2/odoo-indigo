// ============================================================
//  DATOS MOCK - Demo SPA Indigo / Impact Door Decoration
//  En produccion esto vendria de la API REST de WordPress.
// ============================================================

// Las 13 etapas del flujo de produccion.
// Las marcadas optional:true (2-5) solo aplican a dealers configurados asi.
export const STAGES = [
  { id: 'new',          name: 'New Order',                 optional: false },
  { id: 'design_pend',  name: 'Design Confirmation Pending', optional: true },
  { id: 'design_ok',    name: 'Design Confirmed',          optional: true },
  { id: 'measure_pend', name: 'Measurement Pending',       optional: true },
  { id: 'measured',     name: 'Measured',                  optional: true },
  { id: 'digit',        name: 'Ready for Digitalization',  optional: false },
  { id: 'cnc',          name: 'CNC / Router',              optional: false },
  { id: 'paint',        name: 'Painting',                  optional: false },
  { id: 'ready_inst',   name: 'Ready for Installation',    optional: false },
  { id: 'inst_sched',   name: 'Installation Scheduled',    optional: false },
  { id: 'installed',    name: 'Installed',                 optional: false },
  { id: 'invoiced',     name: 'Invoiced / Paid',           optional: false },
  { id: 'closed',       name: 'Closed',                    optional: false },
]

// ----------------------------------------------------------------------
// Dealers (mini-CRM). Antes era una lista simple; ahora tienen ficha
// completa con contacto, tarifas y condiciones — base del modulo CRM.
// ----------------------------------------------------------------------
export const DEALERS = [
  {
    id: 'locktight', name: 'Lock Tight',
    contact: 'Marlon Rivera', email: 'orders@locktight.com',
    phone: '(305) 555-0100', address: '7800 NW 36th St, Doral, FL 33166',
    pricePerSqf: 22, paymentTerms: 'Neto 15 dias',
    notes: 'Cliente principal — usa flujo completo con confirmacion de diseño y medicion.',
  },
  {
    id: 'webindigo', name: 'Web Indigo',
    contact: 'Sara Cohen', email: 'pedidos@webindigo.com',
    phone: '(786) 555-0211', address: '1450 Brickell Ave, Miami, FL 33131',
    pricePerSqf: 20, paymentTerms: 'Pago al pedir',
    notes: 'Pedidos rapidos, sin confirmacion previa. Pasa directo a CNC.',
  },
  {
    id: 'usawin',  name: 'USA Windows',
    contact: 'Daniel Pino', email: 'sales@usawindows.com',
    phone: '(954) 555-0190', address: '2100 N Federal Hwy, Fort Lauderdale, FL 33305',
    pricePerSqf: 21, paymentTerms: 'Neto 30 dias',
    notes: 'Suele mandar ordenes por WhatsApp. Confirmar medidas siempre.',
  },
  {
    id: 'safeguard', name: 'Safeguard',
    contact: 'Ana Torres', email: 'orders@safeguard.com',
    phone: '(305) 555-0303', address: '900 SW 8th St, Miami, FL 33130',
    pricePerSqf: 23, paymentTerms: 'Neto 15 dias',
    notes: 'Nuevo dealer 2026. Tarifa premium acordada.',
  },
]

// ----------------------------------------------------------------------
// Configuracion del pipeline POR DEALER — esto es lo que permite a la
// administracion activar/desactivar etapas opcionales SIN tocar codigo.
// Lo edita la pagina /pipeline.
// ----------------------------------------------------------------------
export const DEFAULT_PIPELINE = {
  locktight: ['design_pend', 'design_ok', 'measure_pend', 'measured'],
  webindigo: [],
  usawin:    ['measure_pend', 'measured'],
  safeguard: ['design_pend', 'design_ok', 'measure_pend', 'measured'],
}

// ----------------------------------------------------------------------
// Roles del sistema. ROLE_TYPE indica el tipo de acceso:
//   - full: ve todo (admin/dueño)
//   - office: ve todo el pipeline, gestiona ordenes (Majela, admin)
//   - shop: ve solo sus etapas (CNC, Pintor, Diseñador)
//   - field: portal movil — instaladores, medicion en obra (Javier)
// ----------------------------------------------------------------------
export const ROLES = [
  { id: 'admin',  name: 'Administracion', role: 'Acceso total',         type: 'full'   },
  { id: 'majela', name: 'Majela',         role: 'Confirmacion / Seguimiento', type: 'office' },
  { id: 'javier', name: 'Javier',         role: 'Medicion / Instalacion',     type: 'field'  },
  { id: 'design', name: 'Diseñador',      role: 'Digitalizacion',             type: 'shop'   },
  { id: 'cnc',    name: 'CNC / Router',   role: 'Corte',                      type: 'shop'   },
  { id: 'paint',  name: 'Pintor',         role: 'Pintura',                    type: 'shop'   },
]

export const DOOR_TYPES = ['Single Door', 'Double Door', 'Door with Sidelites']
export const COLORS = ['White', 'Bronze', 'Black']
export const GLASS_TYPES = ['Clear', 'ESW', 'Frosted', 'Tinted']

// Tarifa del pintor por SQF (configurable en el panel real).
export const PAINTER_RATE = 8
// Tarifa instalador por puerta (configurable por dealer y tipo).
export const INSTALLER_RATE = { SD: 90, DD: 140, Side: 180 }

const hist = (stage, by, date) => ({ stage, by, date })

// ----------------------------------------------------------------------
// ORDENES — base del sistema
// ----------------------------------------------------------------------
export const ORDERS = [
  {
    id: 1, orderNumber: 'S00401', designCode: 'ID70-DD-B',
    doorType: 'Double Door', color: 'Bronze', dealer: 'locktight',
    clientName: 'Virgen Cantera', clientPhone: '(786) 406-0271',
    clientAddress: '6424 Pierce St, Hollywood, FL 33021',
    clientEmail: 'v.cantera@example.com', clientRef: 'KONDAS 128433',
    paymentStatus: 'Pagado', stage: 'paint', assignee: 'paint',
    sqf: 9.42, pieces: 4, glass: 'ESW',
    createdAt: '2026-05-08',
    history: [
      hist('new', 'Majela', '2026-05-08'),
      hist('design_pend', 'Majela', '2026-05-08'),
      hist('design_ok', 'Majela', '2026-05-09'),
      hist('measure_pend', 'Javier', '2026-05-09'),
      hist('measured', 'Javier', '2026-05-10'),
      hist('digit', 'Diseñador', '2026-05-11'),
      hist('cnc', 'CNC / Router', '2026-05-12'),
      hist('paint', 'Pintor', '2026-05-13'),
    ],
  },
  {
    id: 2, orderNumber: 'S00383', designCode: 'ID26-DD-B',
    doorType: 'Double Door', color: 'Bronze', dealer: 'locktight',
    clientName: 'Mark Morera', clientPhone: '(305) 555-0182',
    clientAddress: '1820 NW 12th Ave, Miami, FL 33125',
    clientEmail: 'mmorera@example.com', clientRef: 'LT-7781',
    paymentStatus: 'Pendiente', stage: 'cnc', assignee: 'cnc',
    sqf: 10.28, pieces: 4, glass: 'Clear',
    createdAt: '2026-05-10',
    history: [
      hist('new', 'Majela', '2026-05-10'),
      hist('design_pend', 'Majela', '2026-05-10'),
      hist('design_ok', 'Majela', '2026-05-11'),
      hist('measure_pend', 'Javier', '2026-05-11'),
      hist('measured', 'Javier', '2026-05-12'),
      hist('digit', 'Diseñador', '2026-05-13'),
      hist('cnc', 'CNC / Router', '2026-05-14'),
    ],
  },
  {
    id: 3, orderNumber: 'S00394', designCode: 'TD-SD-W01',
    doorType: 'Single Door', color: 'Bronze', dealer: 'usawin',
    clientName: 'Javier Servigna', clientPhone: '(954) 555-0144',
    clientAddress: '3100 Sheridan St, Hollywood, FL 33021',
    clientEmail: 'jservigna@example.com', clientRef: 'USA-2204',
    paymentStatus: 'Pagado', stage: 'new', assignee: 'majela',
    sqf: 4.24, pieces: 2, glass: 'Clear',
    createdAt: '2026-05-14',
    history: [ hist('new', 'Majela', '2026-05-14') ],
  },
  {
    id: 4, orderNumber: 'WI-1098', designCode: 'TD-DED-B03',
    doorType: 'Double Door', color: 'Black', dealer: 'webindigo',
    clientName: 'Deepak Nair', clientPhone: '(646) 245-8968',
    clientAddress: '5064 SW 104th Ave, Miramar, FL 33027',
    clientEmail: 'dnair@example.com', clientRef: 'Nair, Deepak',
    paymentStatus: 'Pendiente', stage: 'digit', assignee: 'design',
    sqf: 8.10, pieces: 4, glass: 'Clear',
    createdAt: '2026-05-12',
    history: [
      hist('new', 'Majela', '2026-05-12'),
      hist('digit', 'Diseñador', '2026-05-13'),
    ],
  },
  {
    id: 5, orderNumber: 'S00377', designCode: 'ID01-SD-B',
    doorType: 'Single Door', color: 'White', dealer: 'locktight',
    clientName: 'Toni Sawczak', clientPhone: '(305) 555-0190',
    clientAddress: '740 NE 79th St, Miami, FL 33138',
    clientEmail: 'tsawczak@example.com', clientRef: 'LT-7720',
    paymentStatus: 'Pagado', stage: 'installed', assignee: 'javier',
    sqf: 5.56, pieces: 2, glass: 'ESW',
    createdAt: '2026-05-02',
    history: [
      hist('new', 'Majela', '2026-05-02'),
      hist('design_pend', 'Majela', '2026-05-02'),
      hist('design_ok', 'Majela', '2026-05-03'),
      hist('measure_pend', 'Javier', '2026-05-03'),
      hist('measured', 'Javier', '2026-05-04'),
      hist('digit', 'Diseñador', '2026-05-05'),
      hist('cnc', 'CNC / Router', '2026-05-06'),
      hist('paint', 'Pintor', '2026-05-07'),
      hist('ready_inst', 'Pintor', '2026-05-08'),
      hist('inst_sched', 'Javier', '2026-05-09'),
      hist('installed', 'Javier', '2026-05-11'),
    ],
  },
  {
    id: 6, orderNumber: 'WI-1102', designCode: 'ID24-DD-B',
    doorType: 'Double Door', color: 'Black', dealer: 'webindigo',
    clientName: 'Laura Pérez', clientPhone: '(786) 555-0167',
    clientAddress: '210 Brickell Ave, Miami, FL 33131',
    clientEmail: 'lperez@example.com', clientRef: 'Pérez 5521',
    paymentStatus: 'Pagado', stage: 'cnc', assignee: 'cnc',
    sqf: 11.40, pieces: 4, glass: 'Clear',
    createdAt: '2026-05-13',
    history: [
      hist('new', 'Majela', '2026-05-13'),
      hist('digit', 'Diseñador', '2026-05-14'),
      hist('cnc', 'CNC / Router', '2026-05-15'),
    ],
  },
  {
    id: 7, orderNumber: 'S00410', designCode: 'ID33-SD-B',
    doorType: 'Single Door', color: 'Bronze', dealer: 'locktight',
    clientName: 'Robert King', clientPhone: '(954) 555-0133',
    clientAddress: '1500 Hollywood Blvd, Hollywood, FL 33020',
    clientEmail: 'rking@example.com', clientRef: 'LT-7805',
    paymentStatus: 'Pendiente', stage: 'design_pend', assignee: 'majela',
    sqf: 6.20, pieces: 2, glass: 'ESW',
    createdAt: '2026-05-15',
    history: [
      hist('new', 'Majela', '2026-05-15'),
      hist('design_pend', 'Majela', '2026-05-15'),
    ],
  },
  {
    id: 8, orderNumber: 'USA-2210', designCode: 'ID17-DD-B',
    doorType: 'Door with Sidelites', color: 'White', dealer: 'usawin',
    clientName: 'Emily Carter', clientPhone: '(305) 555-0178',
    clientAddress: '88 SW 7th St, Miami, FL 33130',
    clientEmail: 'ecarter@example.com', clientRef: 'USA-2210',
    paymentStatus: 'Pagado', stage: 'invoiced', assignee: 'admin',
    sqf: 13.75, pieces: 6, glass: 'Clear',
    createdAt: '2026-04-28',
    history: [
      hist('new', 'Majela', '2026-04-28'),
      hist('digit', 'Diseñador', '2026-04-29'),
      hist('cnc', 'CNC / Router', '2026-04-30'),
      hist('paint', 'Pintor', '2026-05-02'),
      hist('ready_inst', 'Pintor', '2026-05-03'),
      hist('inst_sched', 'Javier', '2026-05-05'),
      hist('installed', 'Javier', '2026-05-07'),
      hist('invoiced', 'Administracion', '2026-05-09'),
    ],
  },
  {
    id: 9, orderNumber: 'S00415', designCode: 'ID09-SD-B',
    doorType: 'Single Door', color: 'Black', dealer: 'locktight',
    clientName: 'Grace Bennett', clientPhone: '(786) 555-0155',
    clientAddress: '925 Lincoln Rd, Miami Beach, FL 33139',
    clientEmail: 'gbennett@example.com', clientRef: 'LT-7822',
    paymentStatus: 'Pendiente', stage: 'measured', assignee: 'javier',
    sqf: 5.10, pieces: 2, glass: 'ESW',
    createdAt: '2026-05-14',
    history: [
      hist('new', 'Majela', '2026-05-14'),
      hist('design_pend', 'Majela', '2026-05-14'),
      hist('design_ok', 'Majela', '2026-05-15'),
      hist('measure_pend', 'Javier', '2026-05-15'),
      hist('measured', 'Javier', '2026-05-15'),
    ],
  },
  {
    id: 10, orderNumber: 'WI-1105', designCode: 'ID12-SD-B',
    doorType: 'Single Door', color: 'White', dealer: 'webindigo',
    clientName: 'Daniel Ortiz', clientPhone: '(954) 555-0121',
    clientAddress: '4001 N Ocean Dr, Hollywood, FL 33019',
    clientEmail: 'dortiz@example.com', clientRef: 'Ortiz 0091',
    paymentStatus: 'Pagado', stage: 'paint', assignee: 'paint',
    sqf: 4.85, pieces: 2, glass: 'Clear',
    createdAt: '2026-05-11',
    history: [
      hist('new', 'Majela', '2026-05-11'),
      hist('digit', 'Diseñador', '2026-05-12'),
      hist('cnc', 'CNC / Router', '2026-05-13'),
      hist('paint', 'Pintor', '2026-05-14'),
    ],
  },
  {
    id: 11, orderNumber: 'S00418', designCode: 'ID31-DD-B',
    doorType: 'Double Door', color: 'Bronze', dealer: 'locktight',
    clientName: 'Sophia Reyes', clientPhone: '(305) 555-0199',
    clientAddress: '6701 Collins Ave, Miami Beach, FL 33141',
    clientEmail: 'sreyes@example.com', clientRef: 'LT-7830',
    paymentStatus: 'Pendiente', stage: 'ready_inst', assignee: 'javier',
    sqf: 12.05, pieces: 4, glass: 'ESW',
    createdAt: '2026-05-06',
    history: [
      hist('new', 'Majela', '2026-05-06'),
      hist('design_pend', 'Majela', '2026-05-06'),
      hist('design_ok', 'Majela', '2026-05-07'),
      hist('measure_pend', 'Javier', '2026-05-07'),
      hist('measured', 'Javier', '2026-05-08'),
      hist('digit', 'Diseñador', '2026-05-09'),
      hist('cnc', 'CNC / Router', '2026-05-11'),
      hist('paint', 'Pintor', '2026-05-13'),
      hist('ready_inst', 'Pintor', '2026-05-14'),
    ],
  },
  {
    id: 12, orderNumber: 'USA-2215', designCode: 'ID22-SD-B',
    doorType: 'Single Door', color: 'Black', dealer: 'usawin',
    clientName: 'Michael Brown', clientPhone: '(786) 555-0140',
    clientAddress: '120 SW 8th St, Miami, FL 33130',
    clientEmail: 'mbrown@example.com', clientRef: 'USA-2215',
    paymentStatus: 'Pagado', stage: 'inst_sched', assignee: 'javier',
    sqf: 5.95, pieces: 2, glass: 'Clear',
    createdAt: '2026-05-07',
    history: [
      hist('new', 'Majela', '2026-05-07'),
      hist('digit', 'Diseñador', '2026-05-08'),
      hist('cnc', 'CNC / Router', '2026-05-10'),
      hist('paint', 'Pintor', '2026-05-12'),
      hist('ready_inst', 'Pintor', '2026-05-13'),
      hist('inst_sched', 'Javier', '2026-05-14'),
    ],
  },
]

// ----------------------------------------------------------------------
// TAREAS por orden — granularizan el trabajo de cada etapa.
// Una orden puede tener varias tareas en una misma etapa (varias piezas,
// varias personas). Cada tarea es asignable y tiene su propio estado.
// ----------------------------------------------------------------------
const TODAY = '2026-05-22'
export const TASKS = [
  // Orden 1 — en pintura
  { id: 1, orderId: 1, title: 'Pintar piezas Bronze (4)', stage: 'paint',
    assignee: 'paint', status: 'in_progress', deadline: '2026-05-23',
    createdAt: '2026-05-13', notes: 'Acabado mate' },
  { id: 2, orderId: 1, title: 'Inspeccion final antes de instalacion', stage: 'ready_inst',
    assignee: 'javier', status: 'pending', deadline: '2026-05-24',
    createdAt: '2026-05-13' },
  // Orden 2 — en CNC
  { id: 3, orderId: 2, title: 'Cortar piezas ID26-DD', stage: 'cnc',
    assignee: 'cnc', status: 'in_progress', deadline: '2026-05-22',
    createdAt: '2026-05-14' },
  // Orden 4 — en digitalizacion
  { id: 4, orderId: 4, title: 'Pasar diseño TD-DED-B03 a archivo CNC', stage: 'digit',
    assignee: 'design', status: 'in_progress', deadline: '2026-05-22',
    createdAt: '2026-05-13' },
  // Orden 9 — medida, esperando digitalizacion
  { id: 5, orderId: 9, title: 'Confirmar medidas finales con cliente', stage: 'measured',
    assignee: 'majela', status: 'done', deadline: '2026-05-16',
    createdAt: '2026-05-15', completedAt: '2026-05-16' },
  // Orden 11 — lista para instalar
  { id: 6, orderId: 11, title: 'Programar visita instalacion', stage: 'ready_inst',
    assignee: 'majela', status: 'pending', deadline: TODAY,
    createdAt: '2026-05-14', notes: 'Llamar al cliente media hora antes' },
  { id: 7, orderId: 11, title: 'Instalar puerta DD Bronze', stage: 'inst_sched',
    assignee: 'javier', status: 'pending', deadline: '2026-05-24',
    createdAt: '2026-05-14' },
  // Orden 12 — instalacion programada
  { id: 8, orderId: 12, title: 'Instalar puerta SD Black', stage: 'inst_sched',
    assignee: 'javier', status: 'in_progress', deadline: TODAY,
    createdAt: '2026-05-14', notes: 'Cliente confirmado a las 14:00' },
  // Orden 6 — en CNC
  { id: 9, orderId: 6, title: 'Cortar piezas ID24-DD', stage: 'cnc',
    assignee: 'cnc', status: 'pending', deadline: '2026-05-23',
    createdAt: '2026-05-15' },
  // Orden 10 — en pintura
  { id: 10, orderId: 10, title: 'Pintar puerta White', stage: 'paint',
    assignee: 'paint', status: 'in_progress', deadline: '2026-05-22',
    createdAt: '2026-05-14' },
]

// ----------------------------------------------------------------------
// COMENTARIOS por orden — log de conversacion del equipo
// ----------------------------------------------------------------------
export const COMMENTS = [
  { id: 1, orderId: 1,  by: 'Majela',     date: '2026-05-09 09:14',
    text: 'Cliente confirma diseño. Pago recibido por Zelle.' },
  { id: 2, orderId: 1,  by: 'Javier',     date: '2026-05-10 16:22',
    text: 'Medidas tomadas. Ancho 36", alto 80". Dejo fotos.' },
  { id: 3, orderId: 1,  by: 'Diseñador',  date: '2026-05-11 11:00',
    text: 'Archivo CNC listo. Subido a la carpeta del taller.' },
  { id: 4, orderId: 4,  by: 'Diseñador',  date: '2026-05-13 14:30',
    text: 'Pendiente confirmar tipo de vidrio antes de cortar.' },
  { id: 5, orderId: 11, by: 'Majela',     date: '2026-05-15 10:00',
    text: 'Llamar al cliente al 305-450-0860, media hora antes de llegar.' },
  { id: 6, orderId: 12, by: 'Javier',     date: '2026-05-21 18:00',
    text: 'Confirmado para mañana 2:00 PM. Llevar tornillos largos.' },
]

// ----------------------------------------------------------------------
// FOTOS por orden — en el demo son placeholders (SVG inline).
// En produccion serian uploads reales via API REST a Media Library.
// ----------------------------------------------------------------------
const placeholder = (label, bg = '#1f4486') =>
  `data:image/svg+xml;utf8,${encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" width="240" height="180" viewBox="0 0 240 180">
      <rect width="240" height="180" fill="${bg}"/>
      <text x="120" y="95" fill="white" font-family="Inter,Arial" font-size="14"
            text-anchor="middle" font-weight="700">${label}</text>
    </svg>`
  )}`

export const PHOTOS = [
  { id: 1, orderId: 1, taskId: null, name: 'contrato.jpg',
    url: placeholder('Contrato firmado', '#163566'),
    uploadedBy: 'Majela', date: '2026-05-08', kind: 'contract' },
  { id: 2, orderId: 1, taskId: null, name: 'medida-frontal.jpg',
    url: placeholder('Medida frontal', '#1f4486'),
    uploadedBy: 'Javier', date: '2026-05-10', kind: 'measurement' },
  { id: 3, orderId: 1, taskId: 1, name: 'pintura-base.jpg',
    url: placeholder('Pintura base', '#7a5230'),
    uploadedBy: 'Pintor', date: '2026-05-13', kind: 'progress' },
  { id: 4, orderId: 5, taskId: null, name: 'instalada-frente.jpg',
    url: placeholder('Instalada · frente', '#1f9d57'),
    uploadedBy: 'Javier', date: '2026-05-11', kind: 'installed' },
  { id: 5, orderId: 5, taskId: null, name: 'instalada-detalle.jpg',
    url: placeholder('Instalada · detalle', '#1f9d57'),
    uploadedBy: 'Javier', date: '2026-05-11', kind: 'installed' },
  { id: 6, orderId: 12, taskId: 8, name: 'sitio-instalacion.jpg',
    url: placeholder('Sitio de instalacion', '#163566'),
    uploadedBy: 'Javier', date: '2026-05-21', kind: 'pre' },
]

// ----------------------------------------------------------------------
// CATALOGO DE DISEÑOS — enriquecido. En produccion vendria del PDF/CMS.
// ----------------------------------------------------------------------
const _designColor = (code) =>
  code === 'ID70' ? '#163566' :
  code === 'ID01' ? '#7a5230' :
  code === 'ID26' ? '#222'    :
  code === 'ID24' ? '#444'    :
  code === 'ID17' ? '#aa8f6e' : '#1f4486'

export const DESIGNS = [
  'ID01','ID06','ID07','ID09','ID10','ID12','ID13','ID15','ID17','ID18',
  'ID20','ID21','ID22','ID23','ID24','ID26','ID27','ID29','ID31','ID32',
  'ID33','ID34','ID70',
].map((code, i) => ({
  code,
  name: `Indigo ${code.replace('ID', 'Series ')}`,
  variants: i % 3 === 0 ? ['SD', 'DD', 'Side'] : (i % 2 === 0 ? ['SD', 'DD'] : ['SD']),
  colors: ['White', 'Bronze', 'Black'],
  category: i % 4 === 0 ? 'Modern' : i % 4 === 1 ? 'Classic' : i % 4 === 2 ? 'Contemporary' : 'Premium',
  thumbnail: placeholder(code, _designColor(code)),
}))

// Lista plana para autocomplete (compatibilidad con NewOrder existente).
export const DESIGN_CATALOG = DESIGNS.map(d => d.code)

// Etapas "propias" de cada rol — para la vista "Viendo como..." y portal.
export const ROLE_STAGES = {
  majela: ['new', 'design_pend', 'design_ok'],
  javier: ['measure_pend', 'measured', 'ready_inst', 'inst_sched', 'installed'],
  design: ['digit'],
  cnc:    ['cnc'],
  paint:  ['paint'],
  admin:  ['invoiced', 'closed'],
}

// ----------------------------------------------------------------------
// HELPERS
// ----------------------------------------------------------------------
export const dealerName = (id) => (DEALERS.find(d => d.id === id) || {}).name || id
export const roleName   = (id) => (ROLES.find(r => r.id === id) || {}).name || id
export const stageName  = (id) => (STAGES.find(s => s.id === id) || {}).name || id
export const roleType   = (id) => (ROLES.find(r => r.id === id) || {}).type || 'full'
export const dealerById = (id) => DEALERS.find(d => d.id === id)

// Flujo aplicable a un dealer segun la config dinamica (pipeline configurator).
// pipelineConfig = { dealerId: [stageId opcionales habilitados...] }
export function flowForDealer(dealerId, pipelineConfig = DEFAULT_PIPELINE) {
  const enabled = pipelineConfig[dealerId] || []
  return STAGES.filter(s => !s.optional || enabled.includes(s.id))
}

// Siguiente etapa segun el flujo del dealer (o null si ya es la ultima).
export function nextStage(order, pipelineConfig = DEFAULT_PIPELINE) {
  const flow = flowForDealer(order.dealer, pipelineConfig)
  const i = flow.findIndex(s => s.id === order.stage)
  return i >= 0 && i < flow.length - 1 ? flow[i + 1].id : null
}

// Cuenta de tareas pendientes para un usuario (rol).
export function pendingTasksFor(roleId, tasks = TASKS) {
  return tasks.filter(t => t.assignee === roleId && t.status !== 'done')
}
