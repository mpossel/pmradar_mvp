"""
Script principal para orquestrar o scraping e envio para Supabase.

Uso:
  python -m pmradar_mvp.src.main <arquivo-de-urls>

O arquivo de URLs deve conter uma URL por linha, podendo incluir
comentários iniciados por `#`.  As vagas são coletadas e inseridas
no Supabase na tabela configurada no `.env`.
"""
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import List

from tqdm import tqdm

from .scraper import scrape_url
from .supabase_client import upsert_job


def read_urls(file_path: str) -> List[str]:
    """Lê um arquivo de texto retornando as URLs (não vazias, ignorando comentários)."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
    urls: List[str] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            urls.append(line)
    return urls


def main(file_path: str) -> None:
    urls = read_urls(file_path)
    if not urls:
        print("Nenhuma URL para processar.")
        return
    total, sucessos, falhas = 0, 0, 0
    for url in tqdm(urls, desc="Processando links"):
        total += 1
        try:
            data = scrape_url(url)
            # Adiciona timestamp de coleta
            data["scraped_at"] = datetime.now(timezone.utc).isoformat()
            # Upsert no Supabase
            upsert_job(data)
            sucessos += 1
        except Exception as exc:
            print(f"Erro ao processar {url}: {exc}")
            falhas += 1
    print(f"Concluído. Total: {total}, Sucessos: {sucessos}, Falhas: {falhas}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python -m pmradar_mvp.src.main <arquivo-de-urls>")
        sys.exit(1)
    main(sys.argv[1])
