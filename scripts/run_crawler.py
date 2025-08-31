eimport os, json, logging
from pathlib import Path
import sys
# Ensure repository root is in sys.path for src import
sys.path.append(str(Path(__file__).resolve().parents[1]))
from src.web_crawler import WebCrawler



logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

def main():
    # Inputs via env (vêm do workflow)
    seeds_env = os.getenv("SEEDS", "").strip()
    if seeds_env:
        seeds = [s.strip() for s in seeds_env.split(",") if s.strip()]
    else:
        # fallback: usa data/urls.txt se existir
        urls_txt = Path("data/urls.txt")
        if urls_txt.exists():
            seeds = [l.strip() for l in urls_txt.read_text().splitlines() if l.strip() and not l.strip().startswith("#")]
        else:
            seeds = ["https://www.python.org/"]

    max_pages = int(os.getenv("MAX_PAGES", "20"))
    num_threads = int(os.getenv("NUM_THREADS", "4"))
    user_agent = os.getenv("USER_AGENT", "PMRadarCrawler/0.1 (+https://founderspm.com.br)")

    class SavingCrawler(WebCrawler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.results = []

        def process_url(self, url):
            from bs4 import BeautifulSoup
            from urllib.parse import urlparse, urljoin
            import requests, time

            domain = urlparse(url).netloc
            if domain not in self.robots_parsers:
                with self.visited_lock:
                    if domain not in self.robots_parsers:
                        self.fetch_robots(domain)

            rp = self.robots_parsers.get(domain)
            if rp and not rp.can_fetch(self.user_agent, url):
                logging.info(f"URL bloqueada por robots.txt: {url}")
                return

            if domain in self.last_fetch_time:
                elapsed = time.time() - self.last_fetch_time[domain]
                delay = self.crawl_delay.get(domain, 1)
                if elapsed < delay:
                    time.sleep(delay - elapsed)

            logging.info(f"Buscando: {url}")
            headers = {"User-Agent": self.user_agent}
            try:
                response = requests.get(url, headers=headers, timeout=10)
            except Exception as e:
                logging.warning(f"Falha ao requisitar {url}: {e}")
                return

            self.last_fetch_time[domain] = time.time()
            if response.status_code != 200:
                logging.warning(f"Status {response.status_code}: {url}")
                return

            soup = BeautifulSoup(response.text, "html.parser")
            data = self.extract_structured_data(soup)
            self.results.append({"url": url, **data})

            for tag_a in soup.find_all('a', href=True):
                new_url = urljoin(url, tag_a['href']).split('#')[0]
                if not new_url.startswith("http"):
                    continue
                with self.visited_lock:
                    if new_url in self.visited:
                        continue
                    if len(self.visited) >= self.max_pages:
                        self.stop_event.set()
                        return
                    self.visited.add(new_url)
                    self.queue.put(new_url)

    crawler = SavingCrawler(seeds, max_pages=max_pages, num_threads=num_threads, user_agent=user_agent)
    crawler.start()

    out_dir = Path("artifacts")
    out_dir.mkdir(exist_ok=True)
    (out_dir / "crawler_results.json").write_text(json.dumps(crawler.results, ensure_ascii=False, indent=2))
    print(f"✅ Resultados salvos em {out_dir / 'crawler_results.json'}")
    print(f"ℹ️  Seeds: {seeds} | max_pages={max_pages} | num_threads={num_threads} | user_agent={user_agent}")

        # Envia resultados para o Supabase, se configurado
    supabase_url = os.getenv("SUPABASE_URL")
      supabase_key = os.getenv("SUPABASE_ANON_KEY") or os.getenv("UPABASE_ANON_KEY") or os.getenv("SUPABASE_SERVICE_ROLE")

    if supabase_url and supabase_key:
        try:
            from src.supabase_client import upsert_job
        except Exception as e:
            logging.error(f"Erro ao importar supabase_client: {e}")
            upsert_job = None
        if upsert_job:
            import uuid, datetime
            for entry in crawler.results:
                record = {
                    "id": str(uuid.uuid4()),
                    "url": entry.get("url"),
                    "json_ld": json.dumps(entry.get("json_ld", []), ensure_ascii=False),
                    "microdata": json.dumps(entry.get("microdata", []), ensure_ascii=False),
                    "scraped_at": datetime.datetime.utcnow().isoformat() + "Z"
                }
                try:
                    upsert_job(record)
                    logging.info(f"Registro inserido no Supabase: {entry.get('url')}")
                except Exception as e:
                    logging.error(f"Falha ao inserir registro {entry.get('url')} no Supabase: {e}")
    else:
        logging.warning("Supabase não configurado (SUPABASE_URL ou chave de acesso ausentes). Resultados não foram enviados.")

if __name__ == "__main__":
    main()
