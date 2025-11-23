import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import math
import tkinter as tk # Importa la librería tkinter
from tkinter import filedialog # Importa el módulo filedialog
import sys
import os 
from datetime import datetime



def guardar_imagen(csv_path):
    """
    Guarda la imagen generada en la misma carpeta del archivo CSV.
    El nombre será benford_plot.png
    """
    carpeta = os.path.dirname(csv_path)  # Obtiene la carpeta del CSV
    
    # Fecha y hora actual (ej: 2025-11-23_10-42-55)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    nombre_archivo = f"benford_{timestamp}.png"
    ruta_guardado = os.path.join(carpeta, nombre_archivo)

    plt.savefig(ruta_guardado, dpi=300, bbox_inches="tight")
    print(f"\nImagen guardada en: {ruta_guardado}")



### Dataset
#dataset = pd.read_csv("teeli__peachmuffin_stats_hybrid_20251109-221258.csv")

# Verificar si se pasó un path como argumento
if len(sys.argv) > 1:
    file_path = sys.argv[1]
    print(f"Archivo proporcionado por argumento: {file_path}")
else:
    root = tk.Tk()
    root.withdraw()

    # Abre el diálogo para seleccionar el archivo
    file_path = filedialog.askopenfilename(
        title="Selecciona el archivo CSV de estadísticas",
        filetypes=(("Archivos CSV", "*.csv"), ("Todos los archivos", "*.*"))
    )

# Verifica si se seleccionó un archivo
if file_path:
    print(f"Archivo seleccionado: {file_path}")

    ## 📊 Carga del Dataset
    try:
        dataset = pd.read_csv(file_path)
    except Exception as e:
        print(f"Error al leer el archivo: {e}")
        # Termina el script si hay un error de lectura
        exit()

    print("\n¡Datos cargados y columna 'Num_Followers' extraída con éxito!")
    # Puedes continuar con el resto de tu análisis usando 'dataset' y 'numeros'

else:
    print("No se seleccionó ningún archivo. El script ha terminado.")
    exit()

### Extraer columna Num_Followers
numeros = dataset["Num_Followers"].dropna()  # eliminar NaN


# --- Usar la columna "Primer_Digito" directamente ---
primeros_digitos = dataset["First_Digit"].dropna().astype(int).tolist()


### Calcular frecuencia y porcentaje reales
total = len(primeros_digitos)
frecuencias_reales = [primeros_digitos.count(d) for d in range(1, 10)]
porcentajes_reales = [(f / total) * 100 for f in frecuencias_reales]

### Ley de Benford (teórica)
porcentajes_benford = [(math.log10(1 + 1/d)) * 100 for d in range(1, 10)]

### Graficar
digitos = np.arange(1, 10)
plt.figure(figsize=(14, 6))

# Barras para datos reales
plt.bar(digitos, porcentajes_reales, alpha=0.6, label="Datos reales: Num_Followers")

# Curva de Benford
plt.plot(digitos, porcentajes_benford, marker="o", linestyle="-", color="red", label="Ley de Benford (teórica)")
plt.plot(digitos, porcentajes_reales, marker="o", linestyle="-", color="black", label="Porcentaje real")

# Agregar porcentaje real encima de cada marcador
for i, valor in enumerate(porcentajes_reales):
    plt.text(digitos[i], valor + 0.5, f"{valor:.2f}%", ha='center', va='bottom', fontsize=10, color='blue')


plt.xticks(digitos)
plt.xlabel("Primer dígito")
plt.ylabel("Porcentaje (%)")
plt.title("Ley de Benford aplicada a número de seguidores")
plt.legend()
plt.grid(True)

# --- Crear tabla con frecuencia y porcentaje ---
# Formatear los datos de la tabla
tabla_data = []
for i in range(9):
    tabla_data.append([digitos[i], frecuencias_reales[i], f"{porcentajes_reales[i]:.2f}%", f"{porcentajes_benford[i]:.2f}%"])

# --- Agregar fila Total ---
total_frecuencia = sum(frecuencias_reales)
total_porcentaje_real = sum(porcentajes_reales)
total_porcentaje_benford = sum(porcentajes_benford)

tabla_data.append([
    "Total",                 # Columna Dígito
    total_frecuencia,        # Suma de frecuencias
    f"{total_porcentaje_real:.2f}%",   # Total porcentaje real
    f"{total_porcentaje_benford:.2f}%" # Total porcentaje Benford
])

# Añadir tabla al lado derecho del gráfico
column_labels = ["Dígito","Frecuencia", "Porcentaje real", "Porcentaje Benford"]
table = plt.table(cellText=tabla_data,
                  colLabels=column_labels,
                  colColours=["lightblue"]*4,
                  cellLoc="center",
                  loc="right",
                  bbox=[1.05, 0.1, 0.45, 0.8])  # [x, y, ancho, alto]


# Aumentar tamaño de letra
table.auto_set_font_size(False)
table.set_fontsize(7) 
plt.tight_layout()

guardar_imagen(file_path)

plt.show()
