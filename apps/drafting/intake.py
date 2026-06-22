"""Brief intake — text extraction (incl. OCR) + classification (Wizard step 0).

Extraction is best-effort and provider-agnostic:
  - .txt/.md            → decoded directly
  - .pdf                → pdfminer.six (text layer); scanned pages fall to OCR
  - .docx               → python-docx
  - images (png/jpg…)   → Tesseract OCR via pytesseract

If an optional dependency or the Tesseract binary is missing, the extractor
degrades gracefully and reports the reason instead of raising — consistent with
the app's offline-resilient design.

Classification detects category, value band and complexity and pulls out a few
entities; an LLM pass refines it when the gateway is online.
"""
from __future__ import annotations

import io
import json
import re

from apps.llm.gateway import gateway

# ---- value parsing -------------------------------------------------------
_CRORE = re.compile(r"₹?\s*([\d,]+(?:\.\d+)?)\s*(crore|cr)\b", re.I)
_LAKH = re.compile(r"₹?\s*([\d,]+(?:\.\d+)?)\s*(lakh|lac)\b", re.I)


def _num(s: str) -> float:
    return float(s.replace(",", ""))


def parse_value_cr(text: str) -> float | None:
    m = _CRORE.search(text)
    if m:
        return round(_num(m.group(1)), 2)
    m = _LAKH.search(text)
    if m:
        return round(_num(m.group(1)) / 100.0, 4)
    return None


def value_band(value_cr: float | None) -> str:
    if value_cr is None:
        return "Unknown"
    if value_cr < 0.25:
        return "< ₹25 Lakh"
    if value_cr < 5:
        return "₹25 Lakh – ₹5 Cr"
    if value_cr < 50:
        return "₹5 Cr – ₹50 Cr"
    return "≥ ₹50 Cr"


# ---- text extraction -----------------------------------------------------
def extract_text(filename: str, content: bytes) -> tuple[str, str]:
    """Return (text, note). note records the path taken / any degradation."""
    name = (filename or "").lower()
    if name.endswith((".txt", ".md")) or not name:
        return content.decode("utf-8", "ignore"), "Decoded as plain text."
    if name.endswith(".docx"):
        try:
            import docx  # python-docx
            doc = docx.Document(io.BytesIO(content))
            return "\n".join(p.text for p in doc.paragraphs), "Extracted from DOCX."
        except Exception as exc:
            return "", f"DOCX extraction unavailable ({exc})."
    if name.endswith(".pdf"):
        text, note = _pdf_text(content)
        if text.strip():
            return text, note
        ocr, onote = _ocr_pdf(content)
        return ocr, f"{note} {onote}".strip()
    if name.endswith((".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp")):
        return _ocr_image(content)
    # Unknown type — try utf-8.
    return content.decode("utf-8", "ignore"), "Unknown type; decoded as text."


def _pdf_text(content: bytes) -> tuple[str, str]:
    try:
        from pdfminer.high_level import extract_text as _xt
        return _xt(io.BytesIO(content)) or "", "Extracted PDF text layer."
    except Exception as exc:
        return "", f"PDF text-layer extraction unavailable ({exc})."


def _ocr_image(content: bytes) -> tuple[str, str]:
    try:
        import pytesseract
        from PIL import Image
        img = Image.open(io.BytesIO(content))
        return pytesseract.image_to_string(img), "Extracted via OCR (Tesseract)."
    except Exception as exc:
        return "", f"OCR unavailable ({exc}). Install Tesseract + pytesseract for scans."


def _ocr_pdf(content: bytes) -> tuple[str, str]:
    try:
        from pdf2image import convert_from_bytes
        import pytesseract
        pages = convert_from_bytes(content)
        return "\n".join(pytesseract.image_to_string(p) for p in pages), "Scanned PDF → OCR."
    except Exception as exc:
        return "", f"Scanned-PDF OCR unavailable ({exc})."


# ---- classification ------------------------------------------------------
_GOODS = ("supply", "procure", "hardware", "server", "equipment", "device", "install")
_CONSULTING = ("consult", "advisory", "system integrator", "design", "audit", "study")


def _heuristic(text: str) -> dict:
    low = text.lower()
    if any(w in low for w in _CONSULTING):
        category = "Consulting"
    elif any(w in low for w in _GOODS):
        category = "Goods"
    else:
        category = "Goods"
    value = parse_value_cr(text)
    single_lot = "single lot" in low or "single-lot" in low
    multi_lot = "multi-lot" in low or "multiple lots" in low or "divisible" in low
    complexity = "Standard — single lot" if single_lot else ("Multi-lot" if multi_lot else "Standard")
    entities = []
    if value is not None:
        entities.append({"label": "Estimated value", "value": f"₹{value} Cr"})
    entities.append({"label": "Category detected", "value": f"{category} (high confidence)"})
    entities.append({"label": "Value band", "value": value_band(value)})
    entities.append({"label": "Complexity", "value": complexity})
    return {"category": category, "estimated_value_cr": value,
            "value_band": value_band(value), "complexity": complexity,
            "entities": entities, "source": "heuristic"}


_LLM_SYSTEM = (
    "You classify an Indian government procurement brief. Identify category "
    "(Goods|Consulting|Non-Consulting), estimated value in ₹ crore (number or null), "
    "and complexity. Respond ONLY as JSON: "
    '{"category": str, "estimated_value_cr": number|null, "complexity": str, '
    '"entities": [{"label": str, "value": str}]}'
)


def classify_brief(text: str) -> dict:
    base = _heuristic(text)
    try:
        raw = gateway.complete_json(_LLM_SYSTEM, text[:4000])
        data = json.loads(raw) if raw.strip().startswith("{") else {}
        if data.get("category"):
            base["category"] = data["category"]
            if data.get("estimated_value_cr") is not None:
                base["estimated_value_cr"] = data["estimated_value_cr"]
                base["value_band"] = value_band(data["estimated_value_cr"])
            if data.get("entities"):
                base["entities"] = data["entities"]
            base["source"] = "llm"
    except Exception:
        pass
    return base
