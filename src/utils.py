"""
Funções auxiliares para limpeza de HTML e normalização de texto.
"""
from bs4 import BeautifulSoup


def strip_html(html: str) -> str:
    """Remove tags HTML e reduz espaços."""
    if not html:
        return ""
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(" ", strip=True)
    # Remove espaços duplicados
    return " ".join(text.split())
