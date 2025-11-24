import os
import datetime

# ====================== LOGGER ======================
# Definición de clase Logger para manejo de logs
class Logger:
    def __init__(self, log_dir="logs", account=None):
        self.logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), log_dir)
        if not os.path.exists(self.logs_dir):
            os.makedirs(self.logs_dir)
        
        self.timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        self.log_file = os.path.join(self.logs_dir, f"hybrid_log_{self.timestamp}.txt")
        self.csv_file = None
        self.txt_file = None
        self.cookies_file = os.path.join(self.logs_dir, f"cookies_{self.timestamp}.json")

        # Los paths definitivos del CSV y TXT los asignará main.py
        if account:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            self.csv_file = os.path.join(base_dir, f"{account}_stats_hybrid_{self.timestamp}.csv")
            self.txt_file = os.path.join(base_dir, f"{account}_stats_hybrid_{self.timestamp}.txt")
        
    def set_account_files(self, account):
        """Permite asignar archivos CSV/TXT después de crear el logger."""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.csv_file = os.path.join(base_dir, f"{account}_stats_hybrid_{self.timestamp}.csv")
        self.txt_file = os.path.join(base_dir, f"{account}_stats_hybrid_{self.timestamp}.txt")

    def log(self, message, level="INFO"):
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        formatted_message = f"[{timestamp}] [{level}] {message}"
        print(formatted_message)
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(formatted_message + "\n")
    
    def error(self, message):
        self.log(message, "ERROR")
    
    def warning(self, message):
        self.log(message, "WARNING")
    
    def success(self, message):
        self.log(message, "SUCCESS")
    
    def debug(self, message):
        self.log(message, "DEBUG")
