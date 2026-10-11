"""Image captioning for extracted figures (multimodal RAG).

A vision model (default gemma3:4b via the Ollama REST API) transcribes all text in the figure and describes
what it shows. Captions are cached in data/extracted/captions.json keyed by the image's SHA-256, so
re-ingestion never re-captions unchanged images (captioning is the slowest step on a CPU).

    python -m supplykb.vision            # caption any new / changed images
"""

import base64
import hashlib
import json
import logging
from pathlib import Path

from langchain_core.messages import HumanMessage

from supplykb.config import get_settings

log = logging.getLogger(__name__)

CAPTION_PROMPT = (
    "This figure comes from a pharmaceutical supply-chain document. First transcribe ALL text in the image exactly, "
    "line by line, under 'Text:'. Then, under 'Description:', explain in 3-5 sentences what the figure shows: the "
    "decision flow or relationships, conditions and outcomes, and every number with its unit. Do not invent anything."
)


def clean_caption(text: str) -> str:
    """Drop model chatter ('Okay, here's ...') and Markdown emphasis so only transcription + description remain."""
    lines = [ln.replace("**", "").strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln and not ln.lower().startswith(("okay", "sure", "here's", "here is"))]
    return "\n".join(lines)


def cache_path() -> Path:
    return get_settings().extracted_dir / "captions.json"


def load_cache() -> dict:
    p = cache_path()
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def caption_image(path: Path, llm=None) -> str:
    from supplykb.llm import get_vision_model

    llm = llm or get_vision_model()
    b64 = base64.b64encode(Path(path).read_bytes()).decode()
    mime = "image/png" if str(path).endswith(".png") else "image/jpeg"
    msg = HumanMessage(content=[{"type": "text", "text": CAPTION_PROMPT},
                                {"type": "image_url", "image_url": f"data:{mime};base64,{b64}"}])
    return str(llm.invoke([msg]).content).strip()


def get_captions(images: list[dict], allow_model: bool = True, llm=None) -> dict[str, str]:
    """Return {image_id: caption}; caption new/changed images if a vision model is allowed and reachable."""
    cache = load_cache()
    changed = False
    out = {}
    for img in images:
        digest = sha256(img["path"])
        entry = cache.get(img["image_id"])
        if entry and entry.get("sha256") == digest:
            out[img["image_id"]] = clean_caption(entry["caption"])
            continue
        caption = None
        if allow_model:
            try:
                caption = caption_image(Path(img["path"]), llm)
                cache[img["image_id"]] = {"sha256": digest, "model": get_settings().ollama_vision_model, "caption": caption}
                changed = True
            except Exception as exc:  # noqa: BLE001 - ingestion continues without the caption
                log.warning("Captioning failed for %s: %s", img["image_id"], exc)
        out[img["image_id"]] = clean_caption(caption) if caption else "Figure (no caption available - vision model not run)."
    if changed:
        cache_path().parent.mkdir(parents=True, exist_ok=True)
        cache_path().write_text(json.dumps(cache, indent=2), encoding="utf-8")
    return out


if __name__ == "__main__":
    from supplykb.ingest import load_all

    logging.basicConfig(level=logging.INFO)
    docs = load_all()
    caps = get_captions([i for d in docs for i in d.images])
    for k, v in caps.items():
        print(f"--- {k}\n{v}\n")
