Ejecuta el flujo completo de deploy a producción: commit, push y redeploy en la VPS.

## Pasos a seguir EN ORDEN:

### 1. Verificar cambios
Ejecuta `git status` y `git diff --stat` para ver qué cambió.
Si no hay cambios, informa al usuario y detente.

### 2. Generar mensaje de commit
Analiza los cambios con `git diff` (staged y unstaged) y genera un mensaje de commit descriptivo en español, siguiendo el formato convencional: `tipo: descripción corta`.
Tipos válidos: `feat`, `fix`, `refactor`, `config`, `docs`, `infra`.

### 3. Commit y push
```bash
git add -A
git commit -m "<mensaje generado>"
git push origin main
```
Si el push falla, muestra el error y detente.

### 4. Sincronizar knowledge files al VPS
Los archivos de knowledge no están en git (son privados). Sincronizarlos antes del rebuild:
```bash
sshpass -p 'Xb5==?o![As@,Z}m' rsync -avz --progress \
  -e "ssh -o StrictHostKeyChecking=no" \
  /Users/carlos/Desktop/chk-whatsapp-bot/knowledge/*.md \
  root@207.246.116.220:/opt/chk-whatsapp-bot/knowledge/
```
Si no hay archivos .md en knowledge/ local, mostrar advertencia pero continuar.

### 5. Redeploy en VPS
Conéctate a la VPS y ejecuta el redeploy:
```bash
sshpass -p 'Xb5==?o![As@,Z}m' ssh -o StrictHostKeyChecking=no root@207.246.116.220 "cd /opt/chk-whatsapp-bot && git pull && docker compose up -d --build 2>&1"
```
Muestra el output del deploy para confirmar que los contenedores levantaron correctamente.

### 6. Verificar contenedores
```bash
sshpass -p 'Xb5==?o![As@,Z}m' ssh -o StrictHostKeyChecking=no root@207.246.116.220 "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
```

### 7. Resultado final
Muestra un resumen con:
- Commit hash generado
- Archivos desplegados
- Estado de los contenedores en producción
- URL: https://chkbotdev.zunamicorp.com

## Reglas:
- Habla siempre en español
- NUNCA incluyas los archivos `.env` ni `deploy.md` en el commit
- Si cualquier paso falla, muestra el error claramente y detente
- No pidas confirmación — ejecuta todo directo
