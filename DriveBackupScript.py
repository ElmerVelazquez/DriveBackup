import os
import subprocess
import datetime
import shutil


script_dir = os.path.dirname(os.path.realpath(__file__))
BACKUP_DIR = os.path.join(script_dir, "backups")
if not os.path.exists(BACKUP_DIR):
    os.makedirs(BACKUP_DIR)


# Configuración
REMOTE_NAME = "CNCDrive"  # Nombre del remoto configurado en rclone
MAX_COPIAS = 5  # Número máximo de copias a mantener
LOG_FILE = os.path.join(BACKUP_DIR, "backup.log")  # Archivo de logs


# Lista de carpetas específicas a respaldar
CARPETAS = ["PROYECTOS/RIGTH CONSTRUCTION"]  # Lista de carpetas que quieres respaldar


# Verifica que rclone esté instalado
def check_rclone_installed():
    try:
        subprocess.run(["rclone", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError:
        with open(LOG_FILE, "a") as log:
            log.write("Error: rclone no está instalado. Instálalo y vuelve a intentarlo.\n")
        exit(1)


# Crea el directorio de copias si no existe
def create_backup_dir():
    os.makedirs(BACKUP_DIR, exist_ok=True)


# Obtiene la fecha y hora actual
def get_timestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


# Inicia el log
def start_log(timestamp):
    with open(LOG_FILE, "a") as log:
        log.write(f"[{timestamp}] Iniciando proceso de copia de seguridad...\n")


# Copiar carpeta
def copy_folder(carpeta, destino):
    result = subprocess.run(
        ["rclone", "copy", f"{REMOTE_NAME}:{carpeta}", destino, "--drive-shared-with-me", "-P"],
        capture_output=True, text=True)
    with open(LOG_FILE, "a") as log:
        if result.returncode == 0:
            log.write(f"Copia de '{carpeta}' completada.\n")
        else:
            log.write(f"Error al copiar '{carpeta}': {result.stderr}\n")


# Limpiar copias antiguas
def clean_old_backups(carpeta):
    carpeta_backup = os.path.join(BACKUP_DIR, f"backup{carpeta}")
    os.makedirs(carpeta_backup, exist_ok=True)
    
    carpetas = sorted([d for d in os.listdir(carpeta_backup) if d.startswith(carpeta)], reverse=True)
    if len(carpetas) > MAX_COPIAS:
        for old_backup in carpetas[MAX_COPIAS:]:
            shutil.rmtree(os.path.join(carpeta_backup, old_backup))
            with open(LOG_FILE, "a") as log:
                log.write(f"Eliminada copia antigua: {old_backup}\n")


# Main script
def main():
    check_rclone_installed()
    create_backup_dir()


    timestamp = get_timestamp()
    start_log(timestamp)


    for carpeta in CARPETAS:
        # Crear subcarpeta para los backups de cada carpeta
        backup_subdir = os.path.join(BACKUP_DIR, f"backup_{timestamp}{carpeta}")
        os.makedirs(backup_subdir, exist_ok=True)
        
        with open(LOG_FILE, "a") as log:
            log.write(f"Descargando '{carpeta}' en '{backup_subdir}'...\n")
        copy_folder(carpeta, backup_subdir)


        # Limpiar copias antiguas
        clean_old_backups(carpeta)


    with open(LOG_FILE, "a") as log:
        log.write(f"[{timestamp}] Proceso completado.\n")


if __name__ == "__main__":
    main()
