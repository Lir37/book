#!/usr/bin/env python3
"""Validate 26 chapters, TXT/FB2 parity, and optionally FictionBook 2.1 XSD."""
from __future__ import annotations
import argparse
import re
from pathlib import Path
import xml.etree.ElementTree as ET

NS = '{http://www.gribuser.ru/xml/fictionbook/2.0}'
HEADING = re.compile(r'(?m)^Глава\s+(\d+)[^\n]*')

def norm(text: str) -> str:
    return ' '.join(text.replace('*', '').replace('_', '').split())

def run(root: Path, xsd_dir: Path | None) -> None:
    txt = (root / 'Книга про всякое, попытка 90123... (2).txt').read_text('utf8')
    if len(txt) < 350_000:
        raise ValueError('TXT below 350000 characters')
    headers = list(HEADING.finditer(txt))
    if [int(m.group(1)) for m in headers] != list(range(1, 27)):
        raise ValueError('expected exactly 26 TXT chapters')
    src = root / 'Фон эпоса.fb2'
    xml = ET.parse(src)
    sections = xml.getroot().findall('./' + NS + 'body/' + NS + 'section')
    if len(sections) != 26:
        raise ValueError(f'expected 26 FB2 sections, found {len(sections)}')
    for i, (header, section) in enumerate(zip(headers, sections)):
        if section.get('id') != f'chapter-{i+1}':
            raise ValueError(f'bad section id in chapter {i+1}')
        st = header.start()
        en = headers[i + 1].start() if i + 1 < 26 else len(txt)
        expect = norm(txt[st:en])
        found = norm(''.join(section.itertext()))
        if expect != found:
            j = next((k for k in range(min(len(expect), len(found))) if expect[k] != found[k]), min(len(expect), len(found)))
            raise ValueError(f'TXT/FB2 mismatch in chapter {i+1}, near normalized offset {j}')
    if re.search(r'\b(?:Интеллект|Удача)\s*[—:]|\bЗдоровье:\s*\d+', txt):
        raise ValueError('old stats or numeric HP remain')
    for required in ['Живучесть — 10.', 'Восприятие — 13.', '2525',
                     'выносливость 11, живучесть 11, дух 17']:
        if required not in txt:
            raise ValueError(f'canonical marker missing: {required}')
    print(f'OK: TXT {len(txt)} chars, 26 chapters, XML parsed, 26/26 parity, RPG markers')
    if xsd_dir is None:
        print('XSD NOT RUN: pass --xsd-dir with FictionBook2.1.xsd and its three imports')
    else:
        from lxml import etree
        schema = etree.XMLSchema(etree.parse(str(xsd_dir / 'FictionBook2.1.xsd')))
        document = etree.parse(str(src))
        if not schema.validate(document):
            raise ValueError('FictionBook 2.1 XSD error: ' + str(schema.error_log))
        print('OK: FictionBook 2.1 XSD, zero errors')

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', type=Path, default=Path(__file__).resolve().parent.parent)
    ap.add_argument('--xsd-dir', type=Path)
    args = ap.parse_args()
    run(args.repo, args.xsd_dir)
