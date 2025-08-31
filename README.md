PMRadar MVP Backend
====================

Este projeto contém um backend mínimo viável (MVP) para o **PMRadar**.  O objetivo é fornecer
um coletor de vagas de Produto (Product Manager, Product Owner, Analista de Produto e
Analista de Negócios) a partir de páginas de formulários públicos e alguns boards de vagas,
e salvar essas vagas em uma tabela no Supabase.  Este backend **não** cobre scraping do
LinkedIn — ele se concentra em páginas acessíveis sem login, como Google Forms,
Tally, Typeform e sites simples de vagas.

### Principais componentes

* `src/main.py` – script de orquestração. Lê uma lista de URLs, realiza o
  scraping através do módulo `scraper`, normaliza os campos e envia para
  a tabela Supabase via `supabase_client`.
* `src/scraper.py` – contém funções para detectar o tipo de página e
  extrair os dados básicos (título, descrição/resumo e link). Atualmente
  implementa extratores simples para Google Forms, Tally e Typeform, com
  fallback genérico.
* `src/supabase_client.py` – funções para inserir (upsert) registros de vagas
  no Supabase usando a API REST.  Carrega as credenciais de
  `.env`.
* `src/utils.py` – funções auxiliares para limpeza de texto.

### Configuração

1. **Crie** um projeto no Supabase e adicione uma tabela chamada `job_postings` com,
   pelo menos, as seguintes colunas:

   | coluna        | tipo    | descrição                                      |
   |--------------|---------|------------------------------------------------|
   | `id`         | UUID    | Chave primária (gerada pelo banco)             |
   | `title`      | text    | Título da vaga                                 |
   | `company`    | text    | Nome da empresa (opcional)                     |
   | `description`| text    | Descrição ou resumo do formulário              |
   | `url`        | text    | Link original do formulário                    |
   | `source`     | text    | Domínio ou tipo de fonte (GForms, Typeform…)   |
   | `scraped_at` | timestamptz | Data/hora de coleta                             |

2. **Copie** o arquivo `.env.example` para `.env` e edite com as credenciais
   do seu projeto Supabase:

   ```env
   SUPABASE_URL=https://seu-projeto.supabase.co
   SUPABASE_ANON_KEY=chave-ouservice-role
   SUPABASE_TABLE=job_postings
   USER_AGENT=PMRadarBot/1.0
   ```

3. **Instale** as dependências dentro de um ambiente virtual:

   ```bash
   pip install -r requirements.txt
   ```

4. **Preencha** o arquivo `data/urls.txt` com uma URL por linha apontando para
   formulários ou páginas de vagas que você deseja raspar.

5. **Execute** o script principal:

   ```bash
   python -m pmradar_mvp.src.main data/urls.txt
   ```

### Evolução futura

Depois do MVP validado, você pode:

* Adicionar novos extratores em `scraper.py` para outros ATS (Lever, Greenhouse,
  Workable, etc.).
* Implementar um crawler automático para descobrir URLs (dorks ou seeds).
* Integrar com o frontend usando Lovable, exibindo as vagas com filtros e
  ordenações.
* Criar agendamentos (cron) para rodar o scraping diariamente.
