import random
import re
from time import sleep

# ====================== UTILIDADES ======================
# Humanización de delays y tipeo
def human_delay(min_seconds=1.0, max_seconds=3.0):
    sleep(random.uniform(min_seconds, max_seconds))

def type_like_human(element, text):
    for char in text:
        element.send_keys(char)
        sleep(random.uniform(0.05, 0.15))

def parse_follower_count(text):
    """
    Extrae el número de seguidores de un texto con máxima precisión
    Ejemplos: 
        "1,234 followers" -> 1234
        "3,223 followers" -> 3223
        "1.2M followers" -> 1200000
        "10.5K followers" -> 10500
        "1333 followers" -> 1333
    """
    if not text:
        return None
    # Normalizar texto
    text = text.lower().strip()
    
    # Patrones en orden de especificidad
    patterns = [
        (r'([\d,\.]+)\s*m\s*followers?', 'M'),  # Millones
        (r'([\d,\.]+)\s*k\s*followers?', 'K'),  # Miles
        (r'([\d,\.]+)\s*followers?', None),     # Número exacto
    ]
    
    for pattern, unit in patterns:
        match = re.search(pattern, text)
        if match:
            num_str = match.group(1)
            
            if unit == 'M':
                # Para millones: "1.2M" -> 1200000
                num = float(num_str.replace(',', '.'))
                return int(num * 1_000_000)
            
            elif unit == 'K':
                # Para miles: "10.5K" -> 10500
                num = float(num_str.replace(',', '.'))
                return int(num * 1_000)
            
            else:
                # Para números exactos sin K/M
                # Eliminar TODAS las comas y puntos (separadores de miles)
                # "1,234" -> "1234"
                # "3.223" (formato europeo) -> "3223"
                # "1,333" -> "1333"
                clean_num = num_str.replace(',', '').replace('.', '')
                
                # Validar que solo contenga dígitos
                if clean_num.isdigit():
                    return int(clean_num)
                else:
                    # Si no es un número válido, intentar parsearlo de todos modos
                    try:
                        return int(float(clean_num))
                    except ValueError:
                        continue
    
    return None
