# -*- coding: utf-8 -*-
"""Genera addons/indigo_decors/i18n/en.po a partir del .pot con traducciones a ingles."""
import os
import re

TRANSLATIONS = {
    # --- Acciones / botones / form headers ---
    "+ Agregar pieza": "+ Add piece",
    "+ Nueva orden": "+ New order",
    "Aprobar": "Approve",
    "Cancelar": "Cancel",
    "Pasar a borrador": "Set to draft",
    "Marcar pagada": "Mark as paid",
    "Consolidar": "Consolidate",
    "Subir foto": "Upload photo",
    "Crear orden": "Create order",
    "Volver": "Back",
    "Confirmar instalacion completada": "Confirm installation completed",

    # --- Modulo ---
    "Indigo Decors": "Indigo Decors",
    "Gestion de ordenes de puertas decorativas": "Decorative door order management",
    "Mis ordenes": "My orders",
    "Mis instalaciones": "My installations",
    "Ordenes asignadas a tu instalacion": "Orders assigned to your installation",
    "Ordenes registradas como dealer": "Orders registered as dealer",

    # --- Roles / grupos ---
    "User": "User",
    "Manager": "Manager",
    "Contractor (portal)": "Contractor (portal)",
    "Disenador": "Designer",
    "CNC / Router": "CNC / Router",
    "Pintor": "Painter",
    "Office / Administracion": "Office / Administration",

    # --- Modelos / titulos ---
    "Orden de trabajo Indigo": "Indigo work order",
    "Pieza / puerta de una orden Indigo": "Piece / door from an Indigo order",
    "Etapa del pipeline Indigo": "Indigo pipeline stage",
    "Diseno del catalogo Indigo": "Indigo catalog design",
    "Incidencia / anotacion sobre una orden Indigo": "Incident / annotation on an Indigo order",
    "Liquidacion a contratista (pintor / instalador)": "Contractor payout (painter / installer)",
    "Linea de liquidacion": "Payout line",
    "Tarifa de contratista (placeholder Fase 4)": "Contractor rate",
    "Consolidar liquidaciones por contratista en un periodo": "Consolidate payouts by contractor in a period",

    # --- Campos comunes ---
    "Nombre": "Name",
    "Codigo": "Code",
    "Codigo de dealer": "Dealer code",
    "Descripcion": "Description",
    "Etapa": "Stage",
    "Estado": "State",
    "Fecha": "Date",
    "Fecha emision": "Issue date",
    "Notas": "Notes",
    "Notas generales": "General notes",
    "Notas adicionales": "Additional notes",
    "Tipo": "Type",
    "Color": "Color",
    "Color custom": "Custom color",
    "Tipo de vidrio": "Glass type",
    "Tipo de puerta": "Door type",
    "Cantidad": "Quantity",
    "Cant.": "Qty",
    "Tarifa (USD)": "Rate (USD)",
    "Monto (USD)": "Amount (USD)",
    "Monto total (USD)": "Total amount (USD)",
    "Total a pagar (USD)": "Total to pay (USD)",
    "Ancho (in)": "Width (in)",
    "Alto (in)": "Height (in)",
    "Ancho": "Width",
    "Alto": "Height",
    "Imagen": "Image",
    "Es dealer Indigo": "Is Indigo dealer",
    "Precio por defecto por SQF": "Default price per SQF",
    "Precio por SQF al dealer (USD)": "Dealer price per SQF (USD)",
    "Total a cobrar al dealer (USD)": "Total to charge dealer (USD)",
    "Ref. interna (PRIV)": "Internal ref. (PRIV)",
    "Numero de orden": "Order number",
    "Dealer": "Dealer",
    "Referencia del dealer": "Dealer reference",
    "Cliente final": "End customer",
    "Telefono": "Phone",
    "Direccion": "Address",
    "Direccion de instalacion": "Installation address",
    "Etapas opcionales activas": "Active optional stages",
    "Opcional por dealer": "Optional per dealer",
    "Plegada en kanban": "Folded in kanban",
    "En espera / Pospuesta": "On hold / Postponed",
    "Motivo de espera": "Hold reason",
    "Estado de pago": "Payment state",
    "Sin pagar": "Unpaid",
    "Pago parcial": "Partial payment",
    "Pagado": "Paid",
    "Total de puertas": "Total doors",
    "Total SQF": "Total SQF",
    "Pago al pintor (USD)": "Painter payout (USD)",
    "Pago a instaladores (USD)": "Installer payout (USD)",
    "Pintor asignado": "Assigned painter",
    "Instaladores": "Installers",
    "Liquidaciones generadas": "Generated payouts",
    "Contratistas": "Contractors",
    "Contratista": "Contractor",
    "Asignados": "Assigned",
    "Asignacion interna / pago": "Internal assignment / payment",
    "Estado especial / Ref. interna": "Special state / Internal ref",
    "Asignacion / pago": "Assignment / payment",
    "Asignacion / pago - 2": "Assignment / payment",
    "Estado especial": "Special state",
    "Fotos del contrato / puerta": "Contract / door photos",
    "Fotos del contrato": "Contract photos",
    "Reportado por": "Reported by",
    "Categoria": "Category",
    "Medida": "Measurement",
    "Pintura": "Painting",
    "Cliente": "Customer",
    "Instalacion": "Installation",
    "Otro": "Other",
    "Pieza": "Piece",
    "Fecha del trabajo": "Work date",
    "Borrador": "Draft",
    "Aprobada": "Approved",
    "Pagada": "Paid",
    "Cancelada": "Cancelled",
    "Periodo desde": "Period from",
    "Periodo hasta": "Period to",
    "Desde": "From",
    "Hasta": "To",
    "Referencia": "Reference",
    "Lineas": "Lines",
    "Piezas": "Pieces",
    "Incidencias": "Incidents",
    "Liquidaciones": "Payouts",
    "Etapas": "Stages",
    "Dealers": "Dealers",
    "Catalogo de disenos": "Design catalog",
    "Configuracion": "Configuration",
    "Indigo": "Indigo",
    "Single Door": "Single Door",
    "Double Door": "Double Door",
    "Door with Sidelites": "Door with Sidelites",
    "Pintor": "Painter",
    "Instalador": "Installer",
    "Activo": "Active",
    "Imprimir": "Print",
    "Ordenes": "Orders",
    "Consolidar semanal": "Weekly settlement",
    "puertas": "doors",
    "Cliente:": "Customer:",
    "Cliente": "Customer",
    "Diseno": "Design",
    "Disenos": "Designs",
    "Vidrio": "Glass",
    "PRIV": "PRIV",
    "PRIV:": "PRIV:",
    "Total": "Total",
    "Lock Tight": "Lock Tight",
    "Indigo Order Sequence": "Indigo Order Sequence",
    "Indigo Payout Sequence": "Indigo Payout Sequence",
    "white": "white",
    "bronze": "bronze",
    "black": "black",
    "custom": "custom",
    "White": "White",
    "Bronze": "Bronze",
    "Black": "Black",
    "Custom": "Custom",
    "Custom color": "Custom color",
    "Plegada": "Folded",
    "Buscar...": "Search...",
    "Nuevo": "New",

    # --- Filtros / busqueda ---
    "En espera": "On hold",
    "Mis ordenes": "My orders",
    "Mis instalaciones": "My installations",
    "Sin pagar": "Unpaid",
    "Agrupar por": "Group by",
    "Aprobadas": "Approved",
    "Pagadas": "Paid",

    # --- Reportes ---
    "Ficha de orden": "Order Sheet",
    "Ficha de Orden": "Order Sheet",
    "Etiquetas del disenador": "Designer Labels",
    "Hoja del pintor": "Painter Sheet",
    "Hoja del Pintor": "Painter Sheet",
    "Direcciones de instalacion": "Installation Addresses",
    "Direcciones de Instalacion": "Installation Addresses",
    "Comprobante de liquidacion": "Payout Receipt",
    "Comprobante de Liquidacion": "Payout Receipt",
    "Tarifa fija: $8 USD / SQF": "Flat rate: $8 USD / SQF",
    "Pago contra entrega del trabajo terminado.": "Payment upon delivery of completed work.",
    "Reporte generado para coordinar las instalaciones programadas.": "Report generated to coordinate scheduled installations.",
    "Firma del contratista": "Contractor signature",
    "Firma Indigo Decors": "Indigo Decors signature",
    "TOTAL A PAGAR:": "TOTAL TO PAY:",
    "Totales:": "Totals:",
    "TOTAL:": "TOTAL:",
    "Order #": "Order #",
    "Client": "Client",
    "Door Type": "Door Type",
    "Price": "Price",
    "Total": "Total",
    "Company": "Company",
    "Detalle": "Details",
    "Etapa actual": "Current stage",
    "Pago": "Payment",
    "Cliente:": "Customer:",
    "Direccion:": "Address:",
    "Dealer:": "Dealer:",
    "Telefono:": "Phone:",
    "Email:": "Email:",
    "Pieza": "Piece",
    "Total puertas:": "Total doors:",
    "Total SQF:": "Total SQF:",
    "Total a pagar:": "Total to pay:",

    # --- Portal ---
    "No tienes ordenes asignadas.": "You have no orders assigned.",
    "No tienes ordenes registradas. Crea la primera con el boton de arriba.":
        "You have no orders registered. Create your first one with the button above.",
    "Piezas a instalar": "Pieces to install",
    "Subir foto del trabajo": "Upload work photo",
    "Marcar como instalada": "Mark as installed",
    "Nota (opcional)": "Note (optional)",
    "Nueva orden": "New order",
    "Nombre del cliente": "Customer name",
    "Tu referencia (dealer_ref)": "Your reference (dealer_ref)",
    "Cliente final": "End customer",

    # --- Mensajes / errores ---
    "Generada automaticamente al completar pintura de orden %s.":
        "Auto-generated upon completing painting of order %s.",
    "Generada automaticamente al completar instalacion de orden %s.":
        "Auto-generated upon completing installation of order %s.",
    "Pintura %s - %s %s": "Painting %s - %s %s",
    "Instalacion orden %s (%s puertas / %s instaladores)":
        "Installation order %s (%s doors / %s installers)",
    "No hay liquidaciones en borrador para %s entre %s y %s.":
        "No draft payouts for %s between %s and %s.",
    "Consolidacion automatica de %s liquidaciones (%s a %s).":
        "Automatic consolidation of %s payouts (%s to %s).",
    "Lineas movidas a liquidacion consolidada %s.":
        "Lines moved to consolidated payout %s.",
    "El codigo del diseno debe ser unico.":
        "Design code must be unique.",

    # --- Strings adicionales (segundo pase, completar a ~100%) ---
    "<strong>Cliente:</strong>": "<strong>Customer:</strong>",
    "<strong>Compania:</strong>": "<strong>Company:</strong>",
    "<strong>Dealer:</strong>": "<strong>Dealer:</strong>",
    "<strong>Direccion:</strong>": "<strong>Address:</strong>",
    "<strong>Email:</strong>": "<strong>Email:</strong>",
    "<strong>Estado:</strong>": "<strong>State:</strong>",
    "<strong>Etapa actual:</strong>": "<strong>Current stage:</strong>",
    "<strong>Fecha emision:</strong>": "<strong>Issue date:</strong>",
    "<strong>Nombre:</strong>": "<strong>Name:</strong>",
    "<strong>Notas:</strong>": "<strong>Notes:</strong>",
    "<strong>Pago:</strong>": "<strong>Payment:</strong>",
    "<strong>Periodo:</strong>": "<strong>Period:</strong>",
    "<strong>Ref. dealer:</strong>": "<strong>Dealer ref:</strong>",
    "<strong>Ref. tuya:</strong>": "<strong>Your ref:</strong>",
    "<strong>Telefono:</strong>": "<strong>Phone:</strong>",
    "<strong>Tipo:</strong>": "<strong>Type:</strong>",
    "<strong>Total SQF:</strong>": "<strong>Total SQF:</strong>",
    "<strong>Total a pagar:</strong> $": "<strong>Total to pay:</strong> $",
    "<strong>Total puertas:</strong>": "<strong>Total doors:</strong>",

    # Help texts / placeholders
    "Ej. ID01, TD-SD-W06": "E.g. ID01, TD-SD-W06",
    "Ej. ESW": "E.g. ESW",
    "Ej. JOB-2026-014": "E.g. JOB-2026-014",
    "Codigo o nombre que el dealer asigna al cliente final.":
        "Code or name the dealer assigns to the end customer.",
    "Identificador interno (ej. 'cnc', 'painting')":
        "Internal identifier (e.g. 'cnc', 'painting')",
    "Fotos firmadas del contrato y/o de la puerta del cliente final.":
        "Signed photos of the contract and/or the end customer's door.",
    "Instaladores que reciben pago por puerta al completar la instalacion.":
        "Installers who get paid per door when installation is completed.",
    "Precio que se cobra al dealer por SQF. Por defecto toma el del dealer.":
        "Price charged to the dealer per SQF. Defaults to dealer's price.",
    "Referencia privada/interna que sale en la etiqueta del disenador.":
        "Private/internal reference printed on the designer label.",
    "SQF para pintor, puertas para instalador.":
        "SQF for painter, doors for installer.",
    "Ancho x Alto x cantidad / 144.": "Width x Height x quantity / 144.",
    "Total SQF x $8 USD.": "Total SQF x $8 USD.",
    "Total de puertas x $35 USD.": "Total doors x $35 USD.",
    "Modulo de gestion de ordenes Indigo": "Indigo order management module",
    "Descripcion de la etapa...": "Stage description...",
    "Descripcion...": "Description...",
    "Notas generales sobre la orden...": "General notes about the order...",
    "Notas adicionales...": "Additional notes...",
    "Nombre del cliente *": "Customer name *",
    "Diseno (codigo)": "Design (code)",

    # Labels mixtos
    "Dealer / origen": "Dealer / origin",
    "Ref. dealer": "Dealer ref",
    "Indigo Dealer": "Indigo Dealer",
    "Indigo: cambio de etapa de orden": "Indigo: order stage change",
    "Orden": "Order",
    "Puertas": "Doors",
    "Medidas": "Measurements",
    "Adjuntos": "Attachments",
    "Monto": "Amount",
    "Tarifa": "Rate",
    "Unidad": "Unit",
    "Por SQF": "Per SQF",
    "Por pieza": "Per piece",
    "Tarifa fija: <strong>$8 USD / SQF</strong>": "Flat rate: <strong>$8 USD / SQF</strong>",
    "Parts:": "Parts:",
    "Secuencia": "Sequence",
    "Consolidar liquidaciones": "Consolidate payouts",
    "Consolidar liquidaciones semanales": "Consolidate weekly payouts",
    "Mueve todas las lineas de liquidaciones en":
        "Moves all draft payout lines for",

    # Print report names (Python expressions in ir.actions.report)
    "'Etiquetas %s' % (object.name or '')": "'Labels %s' % (object.name or '')",
    "'Ficha %s' % (object.name or '')": "'Sheet %s' % (object.name or '')",
    "'Liquidacion %s' % (object.name or '')": "'Payout %s' % (object.name or '')",

    # Badge "En espera" en kanban
    '<span class=\\"badge text-bg-warning\\">En espera</span>':
        '<span class=\\"badge text-bg-warning\\">On hold</span>',
}

# Leer .pot
HERE = os.path.dirname(os.path.abspath(__file__))
POT = os.path.join(HERE, "..", "addons", "indigo_decors", "i18n", "indigo_decors.pot")
EN_PO = os.path.join(HERE, "..", "addons", "indigo_decors", "i18n", "en.po")

with open(POT, "r", encoding="utf-8") as f:
    content = f.read()

# Reemplazar header
content = content.replace(
    '"Content-Type: text/plain; charset=UTF-8\\n"',
    '"Content-Type: text/plain; charset=UTF-8\\n"\n"Language: en\\n"',
)
content = content.replace('# Translations template', '# English translations')

# Reemplazar msgstr "" por la traduccion si existe
def replace_msgstr(match):
    msgid = match.group(1)
    if msgid in TRANSLATIONS:
        return 'msgid "%s"\nmsgstr "%s"' % (msgid, TRANSLATIONS[msgid])
    return match.group(0)

# Patron: msgid "..."\nmsgstr ""
pattern = re.compile(r'msgid "((?:[^"\\]|\\.)*)"\nmsgstr ""', re.MULTILINE)
new_content = pattern.sub(replace_msgstr, content)

with open(EN_PO, "w", encoding="utf-8") as f:
    f.write(new_content)

# Estadistica
total = len(re.findall(r'^msgid "', content, re.MULTILINE)) - 1  # restar header
translated = sum(1 for k in TRANSLATIONS if 'msgid "%s"' % k in content)
print("Generated en.po: %d/%d strings translated" % (translated, total))
