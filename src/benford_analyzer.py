import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import math
import sys
import os
import webbrowser
from datetime import datetime
from flask import Flask, send_file, render_template
import threading


# ===========================
#  FUNCIÓN PARA GUARDAR IMAGEN
# ===========================
def guardar_imagen(csv_path):
    carpeta = os.path.dirname(csv_path)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    nombre_archivo = f"benford_{timestamp}.png"
    ruta_guardado = os.path.join(carpeta, nombre_archivo)

    plt.savefig(ruta_guardado, dpi=300, bbox_inches="tight")
    print(f"\nImagen guardada en: {ruta_guardado}")

    return ruta_guardado


# ===========================
#   LEER ARCHIVO CSV
# ===========================
if len(sys.argv) > 1:
    file_path = sys.argv[1]
    print(f"Archivo proporcionado por argumento: {file_path}")
else:
    print("ERROR: Este script debe ejecutarse con un CSV como argumento.")
    sys.exit(1)

try:
    dataset = pd.read_csv(file_path)
except Exception as e:
    print(f"Error al leer archivo CSV: {e}")
    sys.exit(1)

print("\n¡Datos cargados correctamente!\n")


# ===========================
#   PROCESAMIENTO
# ===========================
primeros_digitos = dataset["First_Digit"].dropna().astype(int).tolist()
total = len(primeros_digitos)

frecuencias_reales = [primeros_digitos.count(d) for d in range(1, 10)]
porcentajes_reales = [(f / total) * 100 for f in frecuencias_reales]
porcentajes_benford = [(math.log10(1 + 1/d)) * 100 for d in range(1, 10)]

digitos = np.arange(1, 10)
plt.figure(figsize=(14, 6))

plt.bar(digitos, porcentajes_reales, alpha=0.6, label="Datos reales: Num_Followers")
plt.plot(digitos, porcentajes_benford, marker="o", linestyle="-", color="red", label="Ley de Benford (teórica)")
plt.plot(digitos, porcentajes_reales, marker="o", linestyle="-", color="black", label="Porcentaje real")

for i, valor in enumerate(porcentajes_reales):
    plt.text(digitos[i], valor + 0.5, f"{valor:.2f}%", ha='center', va='bottom', fontsize=10, color='blue')

plt.xticks(digitos)
plt.xlabel("Primer dígito")
plt.ylabel("Porcentaje (%)")
plt.title("Ley de Benford aplicada a número de seguidores")
plt.legend()
plt.grid(True)

# ===========================
#   TABLA LATERAL
# ===========================
tabla_data = []
for i in range(9):
    tabla_data.append([digitos[i], frecuencias_reales[i], f"{porcentajes_reales[i]:.2f}%", f"{porcentajes_benford[i]:.2f}%"])

tabla_data.append([
    "Total",
    sum(frecuencias_reales),
    f"{sum(porcentajes_reales):.2f}%",
    f"{sum(porcentajes_benford):.2f}%"
])

column_labels = ["Dígito","Frecuencia", "Porcentaje real", "Porcentaje Benford"]
table = plt.table(cellText=tabla_data,
                  colLabels=column_labels,
                  colColours=["lightblue"]*4,
                  cellLoc="center",
                  loc="right",
                  bbox=[1.05, 0.1, 0.45, 0.8])

table.auto_set_font_size(False)
table.set_fontsize(7)
plt.tight_layout()


# ===========================
#  GUARDAR PNG
# ===========================
ruta_png = guardar_imagen(file_path)


# ===========================
#   SERVIDOR WEB CON FLASK
# ===========================
app = Flask(__name__, template_folder="templates")


@app.route("/")
def index():
    return render_template("benford.html")


@app.route("/grafica")
def grafica():
    return send_file(ruta_png, mimetype='image/png')


def iniciar_flask():
    app.run(host="127.0.0.1", port=5000, debug=False)


# Iniciar Flask en un hilo separado
thread = threading.Thread(target=iniciar_flask)
thread.daemon = True
thread.start()

# Abrir navegador automáticamente
webbrowser.open("http://127.0.0.1:5000/")

print("\nServidor web iniciado en http://127.0.0.1:5000/")
print("Presiona CTRL+C para finalizar.")
thread.join()
