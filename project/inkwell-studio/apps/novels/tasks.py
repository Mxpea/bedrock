import logging
from pathlib import Path

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=10)
def convert_document_to_html(self, source_path: str, output_dir: str) -> str:
    """
    Placeholder for LibreOffice conversion flow.
    In production replace this with subprocess call to headless libreoffice.
    """
    src = Path(source_path)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    target = out / f"{src.stem}.html"
    target.write_text(f"<p>Converted placeholder for {src.name}</p>", encoding="utf-8")

    logger.info("Document converted", extra={"source": source_path, "target": str(target)})
    return str(target)
