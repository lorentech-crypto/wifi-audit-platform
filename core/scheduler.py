# ─────────────────────────────────────────────────────────────────
# core/scheduler.py  —  Planificador de tareas periódicas
#
# Descripción:
#   Permite registrar tareas que se ejecutan automáticamente cada
#   cierto número de segundos, de forma paralela al hilo principal.
#
#   Uso típico:
#     scheduler = Scheduler()
#     scheduler.every(30, reporter.export_json)   # exportar cada 30s
#     scheduler.every(60, rf.get_summary)         # resumen cada 60s
#     scheduler.start()
# ─────────────────────────────────────────────────────────────────

# threading: para ejecutar las tareas en hilos separados
import threading

# time: para las pausas entre ejecuciones
import time

# Importamos el logger del sistema
from utils.logger import get_logger

# Logger para este módulo
log = get_logger(__name__)


class Scheduler:
    """
    Planificador de tareas periódicas basado en hilos.

    Permite registrar funciones que se ejecutan automáticamente
    con una frecuencia definida, sin bloquear el hilo principal.
    """

    def __init__(self):
        """
        Constructor del planificador.
        Inicializa la lista de tareas y el flag de control.
        """
        # Lista de tareas registradas.
        # Cada elemento es un diccionario: {'interval': N, 'func': f, 'name': s}
        self.tasks = []

        # Flag de control: True mientras el planificador está activo
        self.running = False

        log.debug("Scheduler inicializado.")

    def every(self, interval_seconds, func, name=None):
        """
        Registra una función para ejecutarse cada N segundos.

        Parámetros:
            interval_seconds (int|float): intervalo en segundos entre ejecuciones.
            func (callable): función a ejecutar periódicamente.
                             No debe recibir parámetros.
            name (str): nombre descriptivo de la tarea (para logs).
                        Si es None, usa el nombre de la función.
        """
        # Usamos el nombre de la función si no se especificó uno
        task_name = name or func.__name__

        # Añadimos la tarea a la lista con su intervalo y función
        self.tasks.append({
            'interval': interval_seconds,
            'func':     func,
            'name':     task_name
        })

        log.debug(f"Tarea registrada: '{task_name}' cada {interval_seconds}s")

    def start(self):
        """
        Lanza un hilo independiente para cada tarea registrada.

        Cada tarea corre en su propio hilo demonio, ejecutándose
        indefinidamente con el intervalo configurado.
        """
        self.running = True

        for task in self.tasks:
            # Creamos un hilo para esta tarea específica
            thread = threading.Thread(
                target=self._run_task,   # Función que ejecuta el hilo
                args=(task,),            # Le pasamos el diccionario de la tarea
                daemon=True,             # Hilo demonio: muere con el proceso
                name=f"Scheduler-{task['name']}"
            )
            thread.start()
            log.debug(f"Hilo planificado iniciado: '{task['name']}'")

        log.info(f"Scheduler iniciado con {len(self.tasks)} tarea(s).")

    def _run_task(self, task):
        """
        Bucle de ejecución de una tarea periódica.

        Se ejecuta en un hilo separado. Llama a la función registrada
        cada 'interval' segundos hasta que self.running sea False.

        Parámetros:
            task (dict): diccionario con 'interval', 'func' y 'name'.
        """
        while self.running:
            # Esperamos el intervalo antes de ejecutar
            time.sleep(task['interval'])

            # Solo ejecutamos si el scheduler sigue activo
            if not self.running:
                break

            try:
                # Ejecutamos la función registrada
                task['func']()

            except Exception as e:
                # Si la tarea falla, la registramos pero continuamos
                # No queremos que un error en una tarea detenga el scheduler
                log.error(f"Error en tarea '{task['name']}': {e}")

    def stop(self):
        """
        Detiene el planificador. Los hilos terminarán en su próxima iteración.
        """
        self.running = False
        log.info("Scheduler detenido.")
