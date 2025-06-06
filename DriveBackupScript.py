from logging import exception
import os
import stat
import subprocess
import datetime
import shutil
import traceback
import zstandard
import tarfile

script_dir = os.path.dirname(os.path.realpath(__file__))
BACKUP_DIR = os.path.join(script_dir, "backups")
if not os.path.exists(BACKUP_DIR):
    os.makedirs(BACKUP_DIR)


# Configuración
REMOTE_NAME = "prueba2"  # Nombre del remoto configurado en rclone
MAX_COPIAS = 5  # Número máximo de copias a mantener
LOG_FILE = os.path.join(script_dir, "backup.log")  # Archivo de logs
CARPETAS = ["Asignación de Equipos"]  # Lista de carpetas que quieres respaldar


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

# Manejo de errores al eliminar directorios
def on_rm_error(func, path, exc_info):
    # Quitar solo lectura
    os.chmod(path, stat.S_IWRITE)
    func(path)

def clean_old_backup(carpeta):
    try:
        if os.path.isdir(carpeta):
            shutil.rmtree(carpeta, onerror=on_rm_error)
        else:
            os.remove(carpeta)
        with open(LOG_FILE, "a") as log:
            log.write(f"Eliminada copia antigua: {carpeta}\n")
    except Exception as e:
        with open(LOG_FILE, "a") as log:
            log.write(f"Error al eliminar la copia antigua: {carpeta}\n")
            log.write(f"Error: {e}\n")
            log.write(traceback.format_exc())
            exit(1)

# Limpia todas las copias antiguas excedentes
def clean_all_old_backups():
    for carpeta in CARPETAS:
        primeraCarpeta = carpeta.split("/")[0]
        listacarpetas = sorted([d for d in os.listdir(BACKUP_DIR) if primeraCarpeta in d], reverse=True)
        if len(listacarpetas) > MAX_COPIAS:
            for old_backup in listacarpetas[MAX_COPIAS:]:
                carpeta_a_borrar = os.path.join(BACKUP_DIR, old_backup)
                try:
                    if os.path.isdir(carpeta_a_borrar):
                        shutil.rmtree(carpeta_a_borrar, onerror=on_rm_error)
                    else:
                        os.remove(carpeta_a_borrar)
                    with open(LOG_FILE, "a") as log:
                        log.write(f"Eliminada copia antigua: {carpeta_a_borrar}\n")
                except Exception as e:
                    with open(LOG_FILE, "a") as log:
                        log.write(f"Error al eliminar la copia antigua: {carpeta_a_borrar}\n")
                        log.write(f"Error: {e}\n")
                        log.write(traceback.format_exc())
                    exit(1)

def comprimir_backup(carpeta):
    timestamp = get_timestamp()
    tar = carpeta + ".tar"
    zst = tar + ".zst"
    try:
        with open(LOG_FILE, "a") as log:
            log.write(f"{timestamp} Comprimiendo '{carpeta}'.\n")
        #shutil.make_archive(carpeta, 'zip',carpeta)

        # Comprimir usando zstandard
        with tarfile.open(tar, "w") as tarobj:
            tarobj.add(carpeta, arcname=os.path.basename(carpeta))
        cctx = zstandard.ZstdCompressor()
        with open(tar, 'rb') as f_in, open(zst, 'wb') as f_out:
            cctx.copy_stream(f_in, f_out)
        os.remove(tar)

        clean_old_backup(carpeta)  # Eliminar la carpeta original después de comprimir
    except subprocess.CalledProcessError as e:
        with open(LOG_FILE, "a") as log:
            log.write(f"Error al comprimir '{carpeta}': {e.stderr}\n")

# Main script
def main():
    check_rclone_installed()
    create_backup_dir()
    clean_all_old_backups() #llamada al comienzo y al final del script para limpiar copias antiguas


    timestamp = get_timestamp()
    start_log(timestamp)


    for carpeta in CARPETAS:
        # Crear subcarpeta para los backups de cada carpeta
        backup_subdir = os.path.join(BACKUP_DIR, f"backup_{timestamp}_{carpeta}")
        os.makedirs(backup_subdir, exist_ok=True)
        
        with open(LOG_FILE, "a") as log:
            log.write(f"Descargando '{carpeta}' en '{backup_subdir}'...\n")
        copy_folder(carpeta, backup_subdir)


    comprimir_backup(backup_subdir)  # Comprimir la carpeta después de copiarla
   # Limpiar copias antiguas
    clean_all_old_backups()
    with open(LOG_FILE, "a") as log:
        log.write(f"[{timestamp}] Proceso completado.\n")


if __name__ == "__main__":
    main()
