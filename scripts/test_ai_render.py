"""
One-off test: take an existing Lock Tight design image, ask GPT-4o to
describe the decorative pattern, then generate 3 realistic colour
variations (Bronze PMS 440C, White, Black) with DALL-E 3.

Outputs:
  out/ai_test/source.jpg            — original Lock Tight image
  out/ai_test/pattern.txt           — GPT-4o pattern description
  out/ai_test/<code>__bronze.png    — DALL-E 3 bronze render
  out/ai_test/<code>__white.png     — DALL-E 3 white render
  out/ai_test/<code>__black.png     — DALL-E 3 black render
  out/ai_test/cost.txt              — estimated API cost

Usage:
  python scripts/test_ai_render.py [--code TD-DD-B04]
"""
import argparse
import base64
import os
import shutil
import sys
from pathlib import Path

import requests
from openai import OpenAI

ROOT = Path(__file__).parent.parent
KEY_PATH = ROOT / '.openai_key'
OUT = ROOT / 'out' / 'ai_test'

# Pricing (per image) as of late 2025 — adjust if OpenAI ships a new tier.
# gpt-image-1 medium quality ~ $0.042 / 1024x1024 (per OpenAI Apr-2025 pricing)
DALLE3_STANDARD_1024 = 0.042
GPT4O_VISION_PER_CALL = 0.005  # ballpark


def load_key() -> str:
    return KEY_PATH.read_text().strip()


def describe_pattern(client: OpenAI, image_path: Path) -> str:
    """Use GPT-4o vision to capture the decorative pattern in 2-3 sentences,
    ignoring colour/watermarks/glass so DALL-E can replicate the geometry."""
    img_b64 = base64.b64encode(image_path.read_bytes()).decode()
    resp = client.chat.completions.create(
        model='gpt-4o',
        messages=[{
            'role': 'user',
            'content': [
                {
                    'type': 'text',
                    'text': (
                        'Describe ONLY the decorative metal pattern on this '
                        'exterior double door — the shapes, lines, geometry '
                        'and decorative elements that frame the glass panels. '
                        'Ignore any watermark text ("designs", "decoration"). '
                        'Ignore the colour. Ignore the frosted glass interior. '
                        'Be concise: 2-3 sentences focusing on the silhouette '
                        'so a designer could re-draw the same door. Use plain '
                        'visual language, no flowery prose.'
                    ),
                },
                {
                    'type': 'image_url',
                    'image_url': {
                        'url': f'data:image/jpeg;base64,{img_b64}',
                    },
                },
            ],
        }],
        max_tokens=250,
    )
    return resp.choices[0].message.content.strip()


def generate_variation(client: OpenAI, pattern: str, color_phrase: str,
                       door_type_phrase: str) -> str:
    """Returns the URL of the DALL-E 3 generated image."""
    prompt = (
        f'Photorealistic product photography of an exterior {door_type_phrase} '
        f'with {color_phrase} finish, frosted glass panels behind the metal pattern. '
        f'\n\nDecorative pattern to replicate exactly: {pattern}\n\n'
        f'Centered symmetric composition, modern entryway setting, soft '
        f'natural daylight from above, neutral light-gray studio background, '
        f'clean professional product photo. No watermarks, no text overlays, '
        f'no logos. Sharp focus, magazine quality.'
    )
    img = client.images.generate(
        model='gpt-image-1',
        prompt=prompt,
        n=1,
        size='1024x1024',
        quality='medium',
    )
    # gpt-image-1 returns base64 by default (not a URL like DALL-E 3 did).
    return img.data[0].b64_json


def save_b64_image(b64: str, target: Path):
    """gpt-image-1 returns base64 directly — decode + write."""
    target.write_bytes(base64.b64decode(b64))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--code', default='TD-DD-B04',
                        help='Source design code (must exist in out/images/).')
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)

    src = ROOT / 'out' / 'images' / f'{args.code}.jpg'
    if not src.exists():
        print(f'Source image missing: {src}', file=sys.stderr)
        sys.exit(1)

    door_type_phrase = (
        'double door (two symmetric panels)'
        if '-DD-' in args.code
        else 'single door'
    )

    client = OpenAI(api_key=load_key())

    # 1. Copy source for side-by-side comparison.
    shutil.copy(src, OUT / 'source.jpg')

    # 2. Describe pattern.
    print(f'Describing pattern of {args.code} with GPT-4o…')
    pattern = describe_pattern(client, src)
    print(f'  → {pattern}\n')
    (OUT / 'pattern.txt').write_text(pattern, encoding='utf-8')

    # 3. Generate 3 colour variations.
    variations = [
        ('bronze', 'dark bronze metal Pantone PMS 440C (#382E2C), warm '
                   'brown-black with subtle bronze highlights'),
        ('white',  'pure clean white painted metal'),
        ('black',  'matte deep black metal'),
    ]
    cost_estimate = GPT4O_VISION_PER_CALL + DALLE3_STANDARD_1024 * len(variations)
    for color_name, color_phrase in variations:
        out_path = OUT / f'{args.code}__{color_name}.png'
        print(f'Generating {color_name} variation…')
        b64 = generate_variation(client, pattern, color_phrase, door_type_phrase)
        save_b64_image(b64, out_path)
        print(f'  → saved {out_path}')

    (OUT / 'cost.txt').write_text(
        f'Estimated cost for this run: ${cost_estimate:.3f} USD\n'
        f'  - 1 GPT-4o vision call:  ~${GPT4O_VISION_PER_CALL:.3f}\n'
        f'  - 3 DALL-E 3 standard:   ${DALLE3_STANDARD_1024 * 3:.3f}\n'
        f'\nProjected full catalog (455 designs × 3 colours):\n'
        f'  ~${DALLE3_STANDARD_1024 * 455 * 3 + GPT4O_VISION_PER_CALL * 455:.2f} USD\n',
        encoding='utf-8',
    )
    print()
    print(f'Cost estimate written to {OUT / "cost.txt"}')
    print(f'Total this run: ${cost_estimate:.3f} USD')


if __name__ == '__main__':
    main()
