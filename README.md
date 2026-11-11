# MediCitas

Aplicación web para gestionar las citas de un centro médico con varias especialidades. Un administrador registra especialidades, médicos, pacientes y citas, y el personal del centro puede consultar la agenda del día desde una vista pública, sin iniciar sesión, disponible solo desde la red interna.

El código de la aplicación fue generado con un asistente de IA a partir del diseño que está en `docs/diseno.md`.

## Tecnologías

- **Backend:** Python 3.14, FastAPI, SQLAlchemy 2, Pydantic v2, SQLite, PyJWT y bcrypt.
- **Frontend:** HTML, CSS y JavaScript sin frameworks.

El mismo servidor expone la API REST en `/api` y sirve las pantallas web.

## Funcionalidades

- Inicio de sesión del administrador con JWT.
- Gestión de especialidades, médicos y pacientes (crear, editar, activar y desactivar).
- Registro de citas en turnos de 30 minutos, de lunes a sábado: mañana de 08:00 a 13:00 y tarde de 14:00 a 17:00.
- Control de estado de las citas: agendada, cancelada, atendida o no asistió, con observaciones.
- Agenda pública por fecha (hoy por defecto) y filtrable por médico, accesible solo desde las redes internas configuradas.

## Requisitos

- Windows con PowerShell.
- Python 3.14 o superior.
- Git.

Para verificar la versión de Python:

```powershell
python --version
```

## Instalación

Clonar el repositorio:

```powershell
git clone https://github.com/artapia97/medicitas.git
```

Entrar a la carpeta del proyecto:

```powershell
cd medicitas
```

Crear el entorno virtual:

```powershell
python -m venv .venv
```

Activar el entorno virtual:

```powershell
.\.venv\Scripts\Activate.ps1
```

Si PowerShell no deja ejecutar el script de activación porque la ejecución de scripts está deshabilitada, se puede permitir solo para la terminal actual y volver a activar:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Este cambio desaparece al cerrar la terminal y no modifica la configuración del sistema.

Instalar las dependencias:

```powershell
pip install -r requirements.txt
```

## Configuración

Copiar el archivo de ejemplo:

```powershell
Copy-Item .env.example .env
```

Luego editar `.env` con cualquier editor de texto:

| Variable | Obligatoria | Descripción |
| --- | --- | --- |
| `SECRET_KEY` | Sí | Clave para firmar los tokens JWT. Debe ser larga y aleatoria. |
| `ADMIN_PASSWORD` | Sí | Contraseña del administrador. Se guarda cifrada con bcrypt al crear el administrador. |
| `ADMIN_USERNAME` | No | Usuario del administrador. Por defecto `admin`. |
| `ADMIN_FULL_NAME` | No | Nombre del administrador. Por defecto `Administrador MediCitas`. |
| `JWT_EXPIRATION_MINUTES` | No | Minutos de validez de la sesión. Por defecto `60`. |
| `DATABASE_FILENAME` | No | Nombre del archivo SQLite, ubicado en la raíz del proyecto. Por defecto `medicitas.db`. |
| `LOAD_SAMPLE_DATA` | No | Si es `true`, carga datos de ejemplo cuando la base está vacía. Por defecto `true`. |
| `INTERNAL_NETWORKS` | No | Redes separadas por coma desde las que se puede consultar la agenda pública. |

Si falta `SECRET_KEY` o `ADMIN_PASSWORD`, la aplicación no arranca.

Para generar un `SECRET_KEY` seguro, ejecutar este comando y copiar el resultado en el `.env`:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

## Ejecución

Con el entorno virtual activo y el `.env` configurado:

```powershell
python -m uvicorn app.main:app --reload
```

Al arrancar, la aplicación crea las tablas, crea el administrador si todavía no existe y, si corresponde, carga los datos de ejemplo.

| Pantalla | URL |
| --- | --- |
| Agenda pública | http://127.0.0.1:8000/ |
| Login del administrador | http://127.0.0.1:8000/login.html |
| Documentación de la API | http://127.0.0.1:8000/docs |

Se usa `python -m uvicorn` en lugar del comando `uvicorn` directo porque en algunos equipos Windows las políticas de seguridad bloquean los ejecutables instalados en el entorno virtual.

## Administrador

El usuario y la contraseña son los de `ADMIN_USERNAME` y `ADMIN_PASSWORD` en el `.env`. El administrador se crea solo la primera vez, cuando no existe en la base. Si después se cambia `ADMIN_PASSWORD` en el `.env`, la contraseña guardada no cambia; para aplicar la nueva hay que empezar con una base limpia.

## Datos de ejemplo

Con `LOAD_SAMPLE_DATA=true` y la base vacía, se cargan 4 especialidades, 4 médicos, 5 pacientes y algunas citas del día actual (incluyendo turnos que ya pasaron) y de los siguientes días hábiles. Reiniciar el servidor no duplica los datos.

Para empezar con una base limpia, detener el servidor con `Ctrl+C` y borrar el archivo de la base:

```powershell
Remove-Item medicitas.db
```

En el siguiente arranque se vuelven a crear las tablas y el administrador. Para una base sin datos de ejemplo, poner `LOAD_SAMPLE_DATA=false` antes de arrancar.

## Agenda pública y red interna

La página de la agenda (`/`) se puede abrir desde cualquier lugar, pero los datos los entrega el endpoint `/api/public-schedule`, que solo responde a equipos cuya IP esté dentro de `INTERNAL_NETWORKS`. Si alguien abre la página desde fuera de esas redes, la pantalla carga pero muestra el mensaje "La agenda pública solo está disponible desde la red interna del centro médico" y no muestra citas.

El valor por defecto es:

```
127.0.0.1,::1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16
```

Incluye el propio equipo y los rangos de redes privadas más comunes. Si el centro usa otro rango, se agrega a la lista separado por comas.

La IP se toma directamente de la conexión y no se leen cabeceras como `X-Forwarded-For`, así que la aplicación debe usarse directamente en la red interna, sin un proxy delante.

### Acceso desde otros equipos de la red

Por defecto el servidor solo acepta conexiones del mismo equipo. Para que otros equipos de la red puedan entrar, arrancarlo así:

```powershell
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Desde otro equipo se abre `http://IP-DEL-SERVIDOR:8000/`. La IP del servidor se puede ver con:

```powershell
ipconfig
```

Si Windows pregunta por el firewall, hay que permitir el acceso en redes privadas.

### Cambios en el `.env`

El `.env` se lee una sola vez al arrancar, y `--reload` solo reinicia el servidor cuando cambian archivos `.py`. Después de modificar el `.env`:

1. Detener el servidor con `Ctrl+C`.
2. Cerrar la terminal y abrir una nueva.
3. Activar el entorno virtual y arrancar otra vez el servidor.

## Estructura del proyecto

```
medicitas/
├── app/
│   ├── routers/        Endpoints de la API
│   ├── services/       Lógica de negocio
│   ├── config.py       Configuración y constantes de negocio
│   ├── database.py     Conexión y sesión de SQLAlchemy
│   ├── models.py       Entidades de la base de datos
│   ├── schemas.py      Validación de datos con Pydantic
│   ├── security.py     JWT, bcrypt y restricción por red
│   ├── seed.py         Administrador inicial y datos de ejemplo
│   └── main.py         Punto de entrada de la aplicación
├── docs/
│   └── diseno.md       Diseño del sistema
├── static/
│   ├── admin/          Pantallas del administrador
│   ├── css/            Estilos
│   ├── js/             Lógica del frontend
│   ├── index.html      Agenda pública
│   └── login.html      Inicio de sesión
├── .env.example        Plantilla de configuración
├── requirements.txt    Dependencias
└── README.md
```

El archivo `.env`, la base de datos y la carpeta `.venv` no se suben al repositorio.
