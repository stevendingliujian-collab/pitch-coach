import io
import subprocess
import tempfile
import os
from dataclasses import dataclass, field
from pathlib import Path
from pptx import Presentation
from pptx.util import Pt
from PIL import Image


@dataclass
class ParsedPage:
    page_number: int
    title: str
    content: str  # extracted text body
    speaker_notes: str
    thumbnail_bytes: bytes  # PNG


@dataclass
class ParsedPPT:
    page_count: int
    pages: list[ParsedPage] = field(default_factory=list)


def parse_pptx(file_bytes: bytes) -> ParsedPPT:
    """Parse a .pptx file: extract text per slide + render thumbnails via LibreOffice."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        pptx_path = os.path.join(tmp_dir, "deck.pptx")
        with open(pptx_path, "wb") as f:
            f.write(file_bytes)

        prs = Presentation(io.BytesIO(file_bytes))
        pages: list[ParsedPage] = []

        thumbnails = _render_thumbnails(pptx_path, tmp_dir, len(prs.slides))

        for idx, slide in enumerate(prs.slides):
            page_num = idx + 1
            title = _extract_title(slide)
            content = _extract_body(slide)
            notes = _extract_notes(slide)
            thumbnail = thumbnails.get(page_num, b"")
            pages.append(ParsedPage(
                page_number=page_num,
                title=title,
                content=content,
                speaker_notes=notes,
                thumbnail_bytes=thumbnail,
            ))

        return ParsedPPT(page_count=len(pages), pages=pages)


def _extract_title(slide) -> str:
    if slide.shapes.title and slide.shapes.title.has_text_frame:
        return slide.shapes.title.text_frame.text.strip()
    return ""


def _extract_body(slide) -> str:
    parts = []
    for shape in slide.shapes:
        if shape.has_text_frame and shape != slide.shapes.title:
            for para in shape.text_frame.paragraphs:
                text = para.text.strip()
                if text:
                    parts.append(text)
        if shape.has_table:
            for row in shape.table.rows:
                row_text = " | ".join(cell.text.strip() for cell in row.cells)
                if row_text.strip(" |"):
                    parts.append(row_text)
    return "\n".join(parts)


def _extract_notes(slide) -> str:
    if slide.has_notes_slide:
        notes_frame = slide.notes_slide.notes_text_frame
        if notes_frame:
            return notes_frame.text.strip()
    return ""


def _render_thumbnails(pptx_path: str, output_dir: str, page_count: int) -> dict[int, bytes]:
    """Use LibreOffice headless to convert PPTX slides to PNG images."""
    thumbnails: dict[int, bytes] = {}
    try:
        subprocess.run(
            [
                "libreoffice", "--headless", "--convert-to", "png",
                "--outdir", output_dir, pptx_path,
            ],
            capture_output=True,
            timeout=60,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return thumbnails

    # LibreOffice outputs deck-001.png, deck-002.png, ...
    for i in range(1, page_count + 1):
        candidates = [
            os.path.join(output_dir, f"deck-{i:03d}.png"),
            os.path.join(output_dir, f"deck{i}.png"),
        ]
        for path in candidates:
            if os.path.exists(path):
                thumbnails[i] = _resize_png(path, 640, 480)
                break

    return thumbnails


def _resize_png(path: str, width: int, height: int) -> bytes:
    with Image.open(path) as img:
        img.thumbnail((width, height), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return buf.getvalue()
