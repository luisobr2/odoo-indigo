# Lo generado en Higgsfield, descargado en local

Todo lo que se ha generado en Higgsfield para Indigo está aquí, **en su
versión original tal como la devolvió el servicio** (los clips en HEVC 10
bits, las ampliaciones a tamaño completo). Las versiones ya usadas en los
vídeos (transcodificadas, montadas sobre fondo, recortadas) viven en
`C:\merktop\video-production\public\projects\indigo\{generated,animated}\`.

Los PNG y MP4 no van al repo (`.gitignore`), pero sí este índice. Si hay que
regenerar algo, el `job id` permite reutilizarlo en Higgsfield sin volver a
pagar (se pasa como `value` en `medias`).

## fotos-reales/ — fotos de instalación mejoradas (reel `dealers`)

| Archivo | Qué es | Créditos |
|---|---|---|
| `02-dd-negra-interior-ampliada-4k.png` | Foto 02 ampliada (bytedance 4k) | 2 |
| `02-dd-negra-interior-extendida-9x16.png` | Foto 02 extendida a vertical (`outpaint`, job `d91f46d7`) | 2 |
| `06-sd-blanca-geometrica-ampliada-4k.png` | Foto 06 ampliada | 2 |
| `07-sd-negra-ovalo-ampliada-4k.png` | Foto 07 ampliada | 2 |

## renders-4k/ — renders del catálogo ampliados (tomas de estudio)

`id34dd, id36dd, id41, id46dd, id47, id51dd, id56, id57` a 4k (2 cr cada
uno). Son la fuente de `hero-puerta.py` (`SRC=`) y de `puerta-en-escena.py`.
Los demás diseños siguen en `scraping/output/variant_images/` a 1024 px.

## fondos/ — casas generadas con gpt_image_2_5 (sin puerta)

| Archivo | Job | Uso |
|---|---|---|
| `privacidad-recibidor(-2k).png` | `2a7c2ad9` | reel `privacidad`, ID47 montada encima |
| `privacidad-fachada-noche(-2k).png` | `3846093f` | reel `privacidad`, ID56 montada encima |
| `../casas/01..05*.png` (+`-2k`) | `7dd04d6d, b712fa4c, 19ae19d6, 6174e5de, f48c781c` | carrusel `casas` |

## clips-seedance/ — vídeo (seedance_2_5, 1080p 9:16, 5 s, 60 cr cada uno)

**Vienen en HEVC 10 bits**: Remotion no los lee. Convertir antes de usar:
`ffmpeg -i in.mp4 -c:v libx264 -pix_fmt yuv420p -crf 18 out.mp4`.

| Archivo | Job | De qué imagen | Usado en |
|---|---|---|---|
| `dealers-07-ovalo.mp4` | `e94bb77f` | foto 07 ampliada | reel `dealers` (aclarado gamma 1,18) |
| `dealers-06-blanca.mp4` | `e04b651c` | foto 06 ampliada | reel `dealers` |
| `dealers-02-doble.mp4` | `1f459de1` | foto 02 extendida | reel `dealers` |
| `entrada-id46dd.mp4` | `cf95b64f` | hero ID46-DD negra 4k | reel `entrada` (reencuadrado ×1,45) |
| `entrada-id34dd.mp4` | `47d615f6` | hero ID34-DD bronce 4k | reel `entrada` (reencuadrado ×1,25) |
| `privacidad-recibidor.mp4` | `25fd263d` | recibidor + ID47 | reel `privacidad` |
| `privacidad-fachada-noche.mp4` | `ce738ff2` | fachada + ID56 | reel `privacidad` |

## Regla

Cada vez que se genere algo nuevo en Higgsfield, **descargarlo aquí en el
mismo turno** y añadir la fila. La carpeta temporal de la sesión de Claude se
borra; esta no.
