import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import threading
import queue
import logging
import time
import json
from urllib.robotparser import RobotFileParser

class WebCrawler:
    def __init__(self, start_urls, max_pages=100, num_threads=5, user_agent="MyCrawlerBot/1.0"):
        """
        Inicializa o crawler com URLs de início e configurações.
        - start_urls: lista de URLs para começar a raspagem.
        - max_pages: número máximo de páginas a serem raspadas.
        - num_threads: número de threads para raspar em paralelo.
        - user_agent: string do User-Agent a ser usada nas requisições HTTP.
        """
        self.start_urls = start_urls
        self.max_pages = max_pages
        self.num_threads = num_threads
        self.user_agent = user_agent

        self.visited = set()
        self.queue = queue.Queue()
        self.visited_lock = threading.Lock()
        self.robots_parsers = {}
        self.last_fetch_time = {}
        self.crawl_delay = {}
        self.stop_event = threading.Event()

        logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
        logging.info("Crawler inicializado com %d threads.", num_threads)

    def add_url(self, url):
        parsed = urlparse(url)
        if not parsed.scheme:
            url = "http://" + url
            parsed = urlparse(url)
        if not parsed.netloc:
            return
        with self.visited_lock:
            if url not in self.visited:
                self.visited.add(url)
                self.queue.put(url)
                logging.debug("URL adicionada à fila: %s", url)

    def fetch_robots(self, domain):
        rp = RobotFileParser()
        rp.set_url(f"http://{domain}/robots.txt")
        try:
            rp.read()
            logging.info("robots.txt obtido para %s", domain)
        except Exception as e:
            logging.warning("Não foi possível obter robots.txt de %s: %s", domain, e)
        self.robots_parsers[domain] = rp
        delay = rp.crawl_delay(self.user_agent)
        if delay is None:
            delay = 1
        self.crawl_delay[domain] = delay
        self.last_fetch_time[domain] = 0

    def worker(self):
        while not self.stop_event.is_set():
            try:
                url = self.queue.get(timeout=1)
            except queue.Empty:
                break
            try:
                self.process_url(url)
            except Exception as e:
                logging.error("Erro ao processar %s: %s", url, e)
            finally:
                self.queue.task_done()
        logging.debug("Thread encerrada.")

    def process_url(self, url):
        domain = urlparse(url).netloc

        if domain not in self.robots_parsers:
            with self.visited_lock:
                if domain not in self.robots_parsers:
                    self.fetch_robots(domain)

        rp = self.robots_parsers.get(domain)
        if rp and not rp.can_fetch(self.user_agent, url):
            logging.info("URL bloqueada por robots.txt: %s", url)
            return

        if domain in self.last_fetch_time:
            elapsed = time.time() - self.last_fetch_time[domain]
            delay = self.crawl_delay.get(domain, 1)
            if elapsed < delay:
                wait_time = delay - elapsed
                logging.debug("Aguardando %.2fs para respeitar crawl-delay de %s", wait_time, domain)
                time.sleep(wait_time)

        logging.info("Buscando: %s", url)
        headers = {"User-Agent": self.user_agent}
        try:
            response = requests.get(url, headers=headers, timeout=10)
        except Exception as e:
            logging.warning("Falha ao requisitar %s: %s", url, e)
            return

        self.last_fetch_time[domain] = time.time()

        if response.status_code != 200:
            logging.warning("URL retornou status %s: %s", response.status_code, url)
            return

        content = response.text
        soup = BeautifulSoup(content, "html.parser")

        structured_data = self.extract_structured_data(soup)
        if structured_data["json_ld"]:
            logging.info("Dados JSON-LD encontrados em %s", url)
        if structured_data["microdata"]:
            logging.info("Microdados encontrados em %s", url)

        for tag_a in soup.find_all("a", href=True):
            new_url = urljoin(url, tag_a["href"])
            if new_url.startswith("javascript:") or new_url.startswith("mailto:"):
                continue
            new_url = new_url.split("#")[0]
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
                logging.debug("Novo link adicionado: %s", new_url)

    def extract_structured_data(self, soup):
        data = {"json_ld": [], "microdata": []}
        scripts = soup.find_all("script", type="application/ld+json")
        for script in scripts:
            if not script.string:
                continue
            try:
                json_data = json.loads(script.string)
                data["json_ld"].append(json_data)
            except Exception:
                data["json_ld"].append(script.string.strip())

        items = soup.find_all(attrs={"itemscope": True})
        for item in items:
            if item.find_parent(attrs={"itemscope": True}):
                continue
            item_data = {}
            if item.has_attr("itemtype"):
                item_data["type"] = item["itemtype"]
            props = item.find_all(attrs={"itemprop": True})
            for prop in props:
                if prop.has_attr("itemscope"):
                    continue
                key = prop["itemprop"]
                if prop.name.lower() == "meta" or prop.has_attr("content"):
                    value = prop.get("content", "")
                else:
                    value = prop.get_text(strip=True)
                if key in item_data:
                    if isinstance(item_data[key], list):
                        item_data[key].append(value)
                    else:
                        item_data[key] = [item_data[key], value]
                else:
                    item_data[key] = value
            data["microdata"].append(item_data)
        return data

    def start(self):
        for url in self.start_urls:
            self.add_url(url)
        logging.info("Iniciando crawler em %d URL(s)...", len(self.start_urls))
        threads = []
        for i in range(self.num_threads):
            t = threading.Thread(target=self.worker, daemon=True)
            t.start()
            threads.append(t)
        for t in threads:
            t.join()
        logging.info("Raspagem concluída. Total de URLs visitadas: %d", len(self.visited))
