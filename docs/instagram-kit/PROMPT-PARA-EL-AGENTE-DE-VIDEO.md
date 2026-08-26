# Prompt para el agente del estudio de vídeo

Pegar tal cual en Claude Code abierto en `C:\merktop\video-production`.

Está escrito para que el agente **primero mire y después proponga**: el error
fácil aquí es que arranque a producir un reel genérico de "puertas de lujo"
sin haber visto que el cliente que paga es un dealer, no un dueño de casa.

---

```
Vas a trabajar para un cliente nuevo del estudio: Indigo Decors, un taller de
Miami que decora puertas de impacto. Todavía no existe `projects/indigo/`.

Antes de proponer nada, LEE estas tres cosas. Están fuera de este repo:

1. `C:\Trabajo\odoo-indigo\docs\instagram-kit\CONTEXTO-MARCA.md`
   Contexto de marca verificado contra el sistema de producción de la empresa:
   qué hace, quién es el cliente real, paleta, reglas del logo, escala real del
   negocio. Presta atención a la columna "verificado" de la paleta: no todo lo
   que circula como color de marca está realmente en uso.

2. `C:\Trabajo\odoo-indigo\docs\instagram-kit\PROMPTS.md` y la carpeta
   `generadas/` al lado. Son 29 piezas fijas ya producidas para Instagram,
   Facebook y LinkedIn: 9 publicaciones, portadas, destacadas y plantillas.
   Miralas de verdad, no solo el nombre del archivo.

3. `C:\Trabajo\odoo-indigo\docs\instagram-kit\API-GPT-IMAGE-2.md`
   Cómo se generaron y, sobre todo, qué NO se pudo generar y por qué. El
   hallazgo que más importa: el modelo conserva el ornamento real de la puerta
   mientras haya UNA sola puerta en la imagen; en cuanto se le piden dos o tres
   copias, se inventa la filigrana. Eso condiciona cualquier plano tuyo con
   varias puertas a la vez.

Lo que quiero de vos, en este orden:

**A. Una lectura crítica de lo que ya hay.**
No un resumen: una opinión. Qué piezas aguantan un frame de vídeo y cuáles se
notan generadas al moverse. Qué falta contar que las imágenes fijas no pueden.
Si algo te parece flojo, decilo con el nombre del archivo.

**B. Qué puede aportar el vídeo que la foto no.**
Aterrizado a lo que ESTE estudio sabe hacer hoy, no a lo que sería lindo:
narración (ElevenLabs o Chatterbox local), subtítulos, música, SFX,
transiciones, imágenes IA y clips image→video locales (LTX/ComfyUI, MiniMax
H3). Tenés 29 stills de partida, así que image→video es la vía obvia — decime
cuáles de esos stills se animan bien y cuáles no.

**C. Una propuesta concreta de piezas**, con formato y duración de las que el
motor ya produce (Reel/TikTok/Shorts vertical, cuadrado, YouTube horizontal;
completo, 30 s, 15 s). Para cada una: qué cuenta, con qué assets se arma, qué
hace falta grabar de verdad y qué se puede generar.

**D. Qué necesitás del cliente** para que esto no sea humo. Sé específico:
qué plano hay que ir a filmar al taller, cuántos segundos, con qué luz.

Tres cosas que tenés que tener presentes o la propuesta va a estar mal
enfocada:

- **El que compra es el dealer, no el dueño de casa.** Once dealers activos
  (Lock Tight, USA Windows, Safeguard Impact...). El dueño de casa ve el
  resultado; el que firma la orden es un profesional del rubro. LinkedIn e
  Instagram no piden el mismo vídeo.

- **La escala real es de taller, no de fábrica.** 185 puertas instaladas, 163
  diseños, 11 dealers. No inflar. El contenido tiene que sentirse artesanal y
  preciso; un vídeo con aire de multinacional le queda grande y suena falso.

- **No hay material filmado.** Cero. Todo lo visual existente es generado. Si
  tu propuesta depende de metraje real, decilo como requisito, no lo des por
  hecho.

Entregable de esta primera vuelta: **un documento con la propuesta, no código
ni renders**. Si conviene crear `projects/indigo/`, decímelo y lo hablamos
antes de que lo crees.
```

---

## Por qué está escrito así

**Lo obliga a mirar antes de opinar.** Un agente al que le pedís "hacé vídeos
para esta marca" produce un reel genérico en diez minutos. Uno al que le pedís
que primero critique lo existente tiene que abrir los archivos.

**Le da el límite técnico por adelantado.** El hallazgo de que el generador
pierde el ornamento con más de una puerta en cuadro está documentado y le
ahorra descubrirlo gastando tokens.

**Le prohíbe suponer que hay metraje.** Es la suposición que arruina estas
propuestas: se planifica sobre planos de taller que nadie grabó nunca.

**Pide documento, no producción.** La primera vuelta es para decidir, y un
render terminado es mucho más caro de tirar que un párrafo.
