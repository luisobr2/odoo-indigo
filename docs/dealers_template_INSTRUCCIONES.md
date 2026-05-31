# Plantilla de dealers — instrucciones para el cliente

## Para Indigo Decors

Por favor completá este archivo `dealers_template.csv` con la información real
de **todos los dealers activos hoy** y mandanoslo de vuelta. Lo importamos al
sistema en 5 minutos y reemplazamos los dealers de prueba.

## Cómo abrirlo

- **Excel**: doble click → si pregunta separador, elegir **coma (,)** y
  codificación **UTF-8**
- **Google Sheets**: File → Import → Upload → seleccionar el csv → Replace
  spreadsheet
- **Numbers (Mac)**: doble click

## Columnas — qué llenar

| Columna | Obligatorio | Ejemplo | Notas |
|---|---|---|---|
| `name` | ✅ | `Lock Tight` | Razón social oficial. Sin "LLC" / "Inc" (se agrega después) |
| `indigo_dealer_code` | ✅ | `LT` | Código interno de 2-4 letras. Usar lo que ya usen hoy en sus papeles |
| `email` | ✅ | `orders@locktight.com` | Email principal donde reciben quotes y notificaciones de órdenes |
| `phone` | ✅ | `+1 305 555 0101` | Teléfono principal con código de país |
| `street` | ✅ | `7820 NW 33rd Street` | Calle y número |
| `city` | ✅ | `Doral` | Ciudad |
| `state_code` | ✅ | `FL` | Código de 2 letras del estado (FL, NY, CA, etc.) |
| `zip` | ✅ | `33122` | Código postal |
| `country_code` | ✅ | `US` | Código ISO de 2 letras (US, MX, CO, etc.) |
| `indigo_default_price_per_sqf` | ⚠️ | `12.00` | **Tarifa por pie cuadrado que le cobran HOY**. Solo dólares con punto decimal. Si NO cobran por SQF, dejar vacío y avisarnos cómo cobran (por puerta, contrato, etc.) |
| `notes` | Opcional | `High-volume dealer` | Cualquier nota interna sobre el dealer |

## Filas

Las primeras 3 filas son ejemplos editables. Las 7 filas vacías son para que
agreguen los suyos. Si necesitan más, simplemente agreguen filas hacia abajo.

## Ejemplo lleno

```csv
name,indigo_dealer_code,email,phone,street,city,state_code,zip,country_code,indigo_default_price_per_sqf,notes
Lock Tight,LT,orders@locktight.com,+1 305 555 0101,7820 NW 33rd Street,Doral,FL,33122,US,12.00,
USA Windows,USW,contact@usawindows.net,+1 305 555 0103,2400 SW 8th Street,Miami,FL,33135,US,11.50,Nuevo desde 2024
Web Indigo,WI,sales@webindigo.io,+1 786 555 0107,500 Brickell Key,Miami,FL,33131,US,11.00,
Premium Doors LLC,PD,info@premiumdoors.com,+1 305 555 0205,1234 Coral Way,Coral Gables,FL,33134,US,13.00,Nuevo prospecto 2026
```

## Importante

- Si **no cobran por SQF** sino por puerta o por contrato, **dejá vacía la columna `indigo_default_price_per_sqf`** y mandanos un mensaje aclarando el modelo. Lo ajustamos.
- Si **un dealer tiene varias direcciones** (warehouse + oficina), poné solo la de **facturación** acá. Las otras se cargan después como contactos hijos.
- Si **dejan de trabajar con un dealer**, NO lo borren — solo no lo agreguen a esta plantilla. Cuando los importemos, ese va a quedar fuera.

## ¿Listo? Mandanos el archivo

Email o WhatsApp al equipo de Indigo Publicity Corp:
- **sales@indigodecors.com**
- **+1 (305) 785-6666**
