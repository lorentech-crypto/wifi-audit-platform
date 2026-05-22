# Guía paso a paso: subir el proyecto a GitHub

## Requisitos previos

- Tener una cuenta en [github.com](https://github.com)
- Tener Git instalado en tu ordenador
- El fichero `wifi_audit_platform_git.zip` descargado

---

## Paso 1: Crear el repositorio en GitHub

1. Ve a [github.com](https://github.com) e inicia sesión
2. Haz clic en el botón verde **New** (o en el icono `+` arriba a la derecha → *New repository*)
3. Rellena el formulario:
   - **Repository name:** `wifi-audit-platform`
   - **Description:** `Plataforma portátil de auditoría automatizada de redes Wi-Fi sobre Raspberry Pi 4 — TFG`
   - Selecciona **Private** (para el TFG) o **Public** (si el tutor lo pide)
   - **⚠️ MUY IMPORTANTE:** NO marques ninguna de estas opciones:
     - ❌ Add a README file
     - ❌ Add .gitignore
     - ❌ Choose a license
     - Si marcas alguna, habrá conflicto al subir tu código
4. Haz clic en **Create repository**
5. GitHub te mostrará una página con la URL de tu repositorio. Cópiala, tiene este formato:
   ```
   https://github.com/TU_USUARIO/wifi-audit-platform.git
   ```

---

## Paso 2: Descomprimir el ZIP en tu ordenador

```bash
# Descomprime el fichero descargado
unzip wifi_audit_platform_git.zip

# Entra en el directorio del proyecto
cd wifi_audit_platform
```

Verifica que el repositorio Git ya está inicializado (debe mostrar la rama `main`):
```bash
git status
```
Deberías ver:
```
On branch main
nothing to commit, working tree clean
```

---

## Paso 3: Conectar tu repositorio local con GitHub

Sustituye `TU_USUARIO` por tu nombre de usuario de GitHub:

```bash
git remote add origin https://github.com/TU_USUARIO/wifi-audit-platform.git
```

Verifica que se añadió correctamente:
```bash
git remote -v
```
Debes ver algo como:
```
origin  https://github.com/TU_USUARIO/wifi-audit-platform.git (fetch)
origin  https://github.com/TU_USUARIO/wifi-audit-platform.git (push)
```

---

## Paso 4: Subir el código a GitHub

```bash
git push -u origin main
```

GitHub te pedirá tus credenciales:
- **Username:** tu nombre de usuario de GitHub
- **Password:** tu **token de acceso personal** (NO tu contraseña de GitHub)

### ¿Cómo obtener el token de acceso personal?

GitHub ya no acepta contraseñas normales. Necesitas un token:

1. En GitHub, ve a tu foto de perfil (arriba a la derecha) → **Settings**
2. En el menú izquierdo, baja hasta **Developer settings** → **Personal access tokens** → **Tokens (classic)**
3. Haz clic en **Generate new token (classic)**
4. Rellena:
   - **Note:** `TFG token`
   - **Expiration:** 90 days (suficiente para la entrega)
   - **Scopes:** marca solo `repo` (acceso completo a repositorios)
5. Haz clic en **Generate token**
6. **Copia el token ahora** — no lo verás de nuevo
7. Úsalo como contraseña al hacer `git push`

---

## Paso 5: Verificar que todo subió correctamente

Abre tu navegador y ve a:
```
https://github.com/TU_USUARIO/wifi-audit-platform
```

Debes ver:
- ✅ Todos los ficheros del proyecto
- ✅ El README.md renderizado automáticamente
- ✅ El historial de commits (haz clic en el número de commits)

Para ver el historial completo de commits con sus fechas:

```bash
git log --oneline --graph
```

---

## Paso 6: Compartir el repositorio con el tutor

Si el repositorio es **privado**, debes dar acceso al tutor:

1. En GitHub, ve a tu repositorio → pestaña **Settings**
2. En el menú izquierdo: **Collaborators** → **Add people**
3. Escribe el usuario o email de tu tutor
4. Selecciona el rol **Read** (solo lectura es suficiente)
5. Haz clic en **Add collaborator**
6. Tu tutor recibirá un email de invitación que debe aceptar

Si el repositorio es **público**, simplemente comparte la URL directamente.

---

## Comandos útiles para verificar la autoría

El tutor puede usar estos comandos para verificar que el código es tuyo:

```bash
# Ver todos los commits con fecha y autor
git log --format="%ad | %s" --date=short

# Ver cuántos ficheros y líneas modificó cada commit
git log --stat --oneline

# Ver el contenido completo de un commit concreto
git show HASH_DEL_COMMIT

# Ver las estadísticas globales del autor
git shortlog -s -n
```

---

## Resumen de comandos (todo en orden)

```bash
# 1. Descomprimir
unzip wifi_audit_platform_git.zip
cd wifi_audit_platform

# 2. Conectar con GitHub (sustituye TU_USUARIO)
git remote add origin https://github.com/TU_USUARIO/wifi-audit-platform.git

# 3. Subir
git push -u origin main

# 4. Verificar
git log --oneline
```

---

## Solución a problemas comunes

**Error: `src refspec main does not match any`**
```bash
# El repositorio local puede estar en rama 'master', renómbrala:
git branch -m master main
git push -u origin main
```

**Error: `failed to push some refs`**
```bash
# Ocurre si GitHub creó algún fichero automático. Forzar:
git push -u origin main --force
# ⚠️ Solo usar --force si el repositorio de GitHub está vacío/recién creado
```

**Error: `Authentication failed`**
```bash
# Asegúrate de usar el token, no tu contraseña.
# Si usas macOS, puede que el Keychain guardó la contraseña antigua:
git credential-osxkeychain erase
host=github.com
protocol=https
# Pulsa Enter dos veces
```

**Error: `remote: Repository not found`**
```bash
# Verifica que la URL es correcta:
git remote -v
# Si está mal, corrígela:
git remote set-url origin https://github.com/TU_USUARIO/wifi-audit-platform.git
```
