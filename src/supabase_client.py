"""
Cliente simples para inserir registros de vagas no Supabase via API REST.

Carrega as configurações do arquivo `.env` via python-dotenv.  Para
 evitar duplicatas, utiliza o cabeçalho `Prefer: resolution=merge-duplicates`
 dado que a tabela deve possuir uma coluna única (por exemplo, o campo
 `url` ou um índice baseado em `url`).
"""
import os
import json
from typing import Dict, Any
import requests
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_TABLE = os.getenv("SUPABASE_TABLE", "job_postings")

# Cabeçalhos básicos para requisições REST
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    # resolution=merge-duplicates permite fazer upsert de registros duplicados
    "Prefer": "resolution=merge-duplicates",
}


def upsert_job(job_data: Dict[str, Any]) -> None:
    """Insere ou atualiza uma vaga no Supabase.

    Args:
        job_data: Dicionário com os campos da vaga.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("SUPABASE_URL ou SUPABASE_ANON_KEY não definidos no .env")

    endpoint = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}"
    # A API espera uma lista de objetos para inserts em lote
    payload = [job_data]
    response = requests.post(endpoint, headers=HEADERS, data=json.dumps(payload))
    try:
        response.raise_for_status()
    except requests.HTTPError as err:
        # Repassa a mensagem de erro para facilitar depuração
        raise RuntimeError(
            f"Erro ao inserir dados no Supabase: {response.text}") from err
