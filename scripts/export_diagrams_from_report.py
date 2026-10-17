"""Exporta sin redibujar las cinco vistas UML del informe final del equipo."""
from pathlib import Path
import hashlib
import json
import fitz

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'docs' / 'U3Ferremax_Informe.pdf'
OUT = ROOT / 'diagrams'
PAGES = {'D01': 12, 'D02': 17, 'D03': 18, 'D04': 19, 'D05': 20}

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {'report': 'docs/U3Ferremax_Informe.pdf',
                'report_sha256': sha256(REPORT), 'diagrams': []}
    with fitz.open(REPORT) as report:
        for diagram, page_number in PAGES.items():
            page = report[page_number - 1]
            images = [item for item in page.get_image_info(xrefs=True) if item['xref']]
            if not images:
                raise ValueError(f'Página {page_number} sin imagen de diagrama')
            item = max(images, key=lambda image: image['width'] * image['height'])
            pix = fitz.Pixmap(report, item['xref'])
            if pix.n > 4:
                pix = fitz.Pixmap(fitz.csRGB, pix)
            png = OUT / f'{diagram}.png'
            pix.save(png)
            clip = fitz.Rect(item['bbox'])
            with fitz.open() as exported:
                target = exported.new_page(width=clip.width, height=clip.height)
                target.show_pdf_page(target.rect, report, page_number - 1, clip=clip)
                exported.save(OUT / f'{diagram}.pdf', garbage=4, deflate=True)
            manifest['diagrams'].append({
                'id': diagram, 'page': page_number,
                'png': f'{diagram}.png', 'png_sha256': sha256(png),
                'pdf': f'{diagram}.pdf', 'pdf_sha256': sha256(OUT / f'{diagram}.pdf'),
                'plantuml': f'{diagram}.puml',
                'source_provenance': 'Reconstruida visualmente del diagrama del informe; no es el archivo original de Isaías.',
                'svg': f'{diagram}.svg',
            })
    (OUT / 'fuentes_informe.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Exportados {len(PAGES)} diagramas de {REPORT.name}')

if __name__ == '__main__':
    main()
