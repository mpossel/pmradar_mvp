"""Módulo para extração de vagas em páginas de formulários e sites simples.

O foco deste MVP é capturar informações básicas de páginas de Google Forms,
Tally, Typeform e páginas genéricas de vagas.  Ele identifica o tipo de
fonte com base no domínio e extrai título, descrição/resumo e link.
"""

import os
from typing import Optional, Dict
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

from .utils import strip_html


# Carrega o User-Agent a partir do .env, ou usa um valor padrão
USER_AGENT = os.getenv("USER_AGENT", "PMRadarBot/1.0")


def fetch_html(url: str) -> str:
    """Baixa a página e retorna o HTML como texto.

    Args:
        url: URL do formulário ou página de vaga.
    Returns:
        HTML da página.
    Raises:
        requests.HTTPError se a requisição não for bem sucedida.
    """
    headers = {"User-Agent": USER_AGENT}
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.text


def _extract_title(soup: BeautifulSoup, suffix_to_remove: Optional[str] = None) -> str:
    """Extrai o título da página, removendo sufixos opcionais."""
    if not soup.title:
        return ""
    title = soup.title.get_text(strip=True)
    if suffix_to_remove and title.endswith(suffix_to_remove):
        title = title[:-len(suffix_to_remove)]
    return title.strip()


def scrape_gforms(html: str, url: str) -> Dict[str, Optional[str]]:
    """Extrai informações básicas de um Google Forms público."""
    soup = BeautifulSoup(html, "lxml")
    title = _extract_title(soup, " - Google Forms") or "Formulário (Google Forms)"
    # Descrição é o texto da página inteira truncado
    description = strip_html(html)[:1000]
    return {
        "title": title,
        "company": None,
        "description": description,
        "url": url,
        "source": "GForms",
    }


def scrape_tally(html: str, url: str) -> Dict[str, Optional[str]]:
    """Extrai informações básicas de um formulário Tally."""
    soup = BeautifulSoup(html, "lxml")
    title = _extract_title(soup) or "Formulário (Tally)"
    description = strip_html(html)[:1000]
    return {
        "title": title,
        "company": None,
        "description": description,
        "url": url,
        "source": "Tally",
    }


def scrape_typeform(html: str, url: str) -> Dict[str, Optional[str]]:
    """Extrai informações básicas de um formulário Typeform.

    Nota: Typeforms são carregados via JavaScript e podem não ter
    conteúdo legível no HTML inicial.  Este extrator retorna o texto
    bruto da página carregada, que pode ser limitado.
    """
    soup = BeautifulSoup(html, "lxml")
    title = _extract_title(soup) or "Formulário (Typeform)"
    description = strip_html(html)[:1000]
    return {
        "title": title,
        "company": None,
        "description": description,
        "url": url,
        "source": "Typeform",
    }


def scrape_default(html: str, url: str) -> Dict[str, Optional[str]]:
    """Extrai informações básicas de uma página genérica."""
    soup = BeautifulSoup(html, "lxml")
    title = _extract_title(soup) or "Vaga"
    description = strip_html(html)[:1000]
    parsed = urlparse(url)
    source = parsed.netloc
    return {
        "title": title,
        "company": None,
        "description": description,
        "url": url,
        "source": source,
    }


def scrape_url(url: str) -> Dict[str, Optional[str]]:
    """Determina o tipo da URL e aplica o extrator adequado.

    Args:
        url: Link para o formulário ou página de vaga.
    Returns:
        Dicionário com os campos extraídos.
    Raises:
        Qualquer exceção gerada por `fetch_html` ou
        outras funções será propagada para o chamador.
    """
    html = fetch_html(url)
    # Decide com base no domínio
    if "docs.google.com/forms" in url:
        return scrape_gforms(html, url)
    if "tally.so" in url:
        return scrape_tally(html, url)
    if "typeform.com" in url:
        return scrape_typeform(html, url)
    # Fallback genérico
    return scrape_default(html, url)
