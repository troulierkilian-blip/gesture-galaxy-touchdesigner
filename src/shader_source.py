"""Embed the same galaxy geometry definitions into both GPU programs."""
from pathlib import Path


def load_source(root, filename):
    source_dir = Path(root) / 'src'
    text = (source_dir / filename).read_text(encoding='utf-8')
    marker = '// @include galaxy_common.glsl'
    if marker in text:
        common = (source_dir / 'galaxy_common.glsl').read_text(encoding='utf-8')
        text = text.replace(marker, '// BEGIN shared galaxy geometry\n' + common + '\n// END shared galaxy geometry')
    return text
