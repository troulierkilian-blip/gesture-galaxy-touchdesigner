"""Build an auditable project archive from an explicit public-file allowlist."""
import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = '1.0.0'
TOP = 'gesture-galaxy-touchdesigner'
ROOT_FILES = {
    '.gitignore', '.gitattributes', 'README.md', 'LICENSE', 'RELEASE_NOTES.md',
    'dependencies.json', 'Setup-Dependencies.ps1', 'Start-GestureParticles.cmd',
    'GestureParticles.toe',
}
DOC_FILES = {'docs/VALIDATION.md', 'docs/PACKAGING.md', 'docs/validation-summary.json'}
IMAGE_NAMES = {'oblique.png', 'front.png', 'side.png', 'back.png', 'fist.png', 'palm.png'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def public_files(root=ROOT):
    files = []
    for path in root.rglob('*'):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        name = rel.as_posix()
        if '__pycache__' in rel.parts or '.git' in rel.parts:
            continue
        allowed = name in ROOT_FILES or name in DOC_FILES
        allowed |= len(rel.parts) == 2 and rel.parts[0] == 'src' and path.suffix in {'.py', '.glsl', '.vert', '.frag'}
        allowed |= len(rel.parts) == 2 and rel.parts[0] == 'tests' and path.suffix == '.py'
        allowed |= len(rel.parts) == 2 and rel.parts[0] == 'tools' and path.suffix in {'.py', '.ps1'}
        allowed |= len(rel.parts) == 2 and rel.parts[0] == 'THIRD_PARTY_LICENSES' and path.suffix == '.txt'
        allowed |= name == 'build/Bootstrap.toe' or name == '.github/workflows/tests.yml'
        allowed |= rel.parent.as_posix() == 'docs/images' and path.name in IMAGE_NAMES
        if allowed:
            if path.is_symlink():
                raise ValueError('Symlinks are not published: ' + name)
            files.append(path)
    for required in ROOT_FILES | DOC_FILES | {'build/Bootstrap.toe'}:
        if not (root / required).is_file():
            raise ValueError('Required public file is missing: ' + required)
    return sorted(files, key=lambda p: p.relative_to(root).as_posix())


def audit(files, root=ROOT):
    for path in files:
        rel = path.relative_to(root).as_posix()
        if path.stat().st_size >= 100 * 1024 * 1024:
            raise ValueError('File is too large for this source repository: ' + rel)
        if path.suffix in {'.toe', '.png'}:
            continue
        text = path.read_text(encoding='utf-8-sig')
        if re.search(r'(?:github_pat_|gh[pousr]_)[A-Za-z0-9_]{20,}', text):
            raise ValueError('Potential GitHub credential in ' + rel)
        if re.search(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----', text):
            raise ValueError('Potential private key in ' + rel)
        if re.search(r'(?i)\b[A-Z]:[\\/](?:Users|Documents)[\\/]', text):
            raise ValueError('Personal absolute path in ' + rel)


def build(output_dir):
    files = public_files()
    audit(files)
    manifest = {
        'project': TOP, 'version': VERSION,
        'scope': 'Only public project files; excludes runtime, dependencies, caches and raw camera data.',
        'files': {
            p.relative_to(ROOT).as_posix(): {'bytes': p.stat().st_size, 'sha256': sha(p.read_bytes())}
            for p in files
        },
    }
    manifest_path = ROOT / 'FILE-MANIFEST.json'
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')
    files.append(manifest_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    archive = output_dir / (TOP + '-v' + VERSION + '.zip')
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for path in sorted(files, key=lambda p: p.relative_to(ROOT).as_posix()):
            rel = path.relative_to(ROOT).as_posix()
            info = zipfile.ZipInfo(TOP + '/' + rel, date_time=(2026, 11, 14, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, path.read_bytes())
    checksum = archive.with_suffix('.zip.sha256')
    checksum.write_text(sha(archive.read_bytes()) + '  ' + archive.name + '\n', encoding='ascii', newline='\n')
    print(json.dumps({'archive': str(archive), 'bytes': archive.stat().st_size,
                      'files': len(files), 'checksum': str(checksum)}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT.parent / 'dist')
    build(parser.parse_args().output.resolve())
