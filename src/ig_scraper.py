"""
Instagram Follower Stats Scraper - VERSIÓN HÍBRIDA OPTIMIZADA
Selenium para login + extracción inicial
Playwright paralelo para análisis de perfiles (10x más rápido)
"""

from selenium import webdriver  # Webdriver Selenium. Usado en login y extracción.
#from selenium.webdriver.common.keys import Keys  # Teclas especiales. Usado en type_like_human.
#from selenium.webdriver.chrome.options import Options  # Opciones Chrome. Usado en setup_selenium_driver.
from selenium.webdriver.support.ui import WebDriverWait  # Espera elementos. Usado en login y extracción.
from selenium.webdriver.support import expected_conditions as EC  # Condiciones esperadas. Usado con WebDriverWait.
from selenium.webdriver.common.by import By  # Localización elementos. Usado en find_elements.
from selenium.common.exceptions import NoSuchElementException  # Excepciones Selenium. Usado en try-except.

from webdriver_manager.chrome import ChromeDriverManager  # Gestor driver Chrome. Usado en setup_selenium_driver.
from selenium.webdriver.chrome.service import Service  # Servicio Chrome. Usado en webdriver.Chrome.

from playwright.async_api import async_playwright  # Playwright asíncrono. Usado en análisis paralelo.
import asyncio  # Asincronía. Usado en analyze_profiles_parallel.

from time import sleep  # Pausas. Usado en delays humanos.
import os  # Sistema operativo. Usado en rutas y variables entorno.
import datetime  # Fechas y horas. Usado en logs y timestamps.
import random  # Números aleatorios. Usado en delays y selecciones.
import csv  # CSV. Usado en save_results.
import re  # Expresiones regulares. Usado en parse_follower_count.
import json  # JSON. Usado en cookies.
from dotenv import load_dotenv  # Variables entorno. Usado al inicio.

# Cargar variables de entorno
load_dotenv()

# ====================== CONFIGURACIÓN ======================
# Cargar toda la configuración desde .env
yourusername = os.getenv("IG_USERNAME")
yourpassword = os.getenv("IG_PASSWORD")
account = os.getenv("TARGET_ACCOUNT", "teeli__peachmuffin")  # Cuenta objetivo
page = os.getenv("PAGE_TYPE", "followers")  # "followers" o "following"
count = int(os.getenv("FOLLOWER_COUNT", "50"))  # Número de seguidores a analizar

# Configuración de paralelización
MAX_CONCURRENT_WORKERS = int(os.getenv("MAX_WORKERS", "10"))
# Recomendado: 5-10 (seguro), 15-20 (arriesgado pero rápido)

# Validación de credenciales
if not yourusername or not yourpassword:
    print("❌ ERROR: Credenciales no configuradas")
    print("Crea un archivo .env con:")
    print("IG_USERNAME=tu_usuario")
    print("IG_PASSWORD=tu_contraseña")
    print("TARGET_ACCOUNT=cuenta_objetivo")
    print("PAGE_TYPE=followers")
    print("FOLLOWER_COUNT=50")
    exit(1)

# ====================== LOGGER ======================
#Definición de clase Logger para manejo de logs
class Logger:
    def __init__(self, log_dir="logs"):
        self.logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), log_dir)
        if not os.path.exists(self.logs_dir):
            os.makedirs(self.logs_dir)
        
        self.timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        self.log_file = os.path.join(self.logs_dir, f"hybrid_log_{self.timestamp}.txt")
        self.csv_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 
            f"{account}_stats_hybrid_{self.timestamp}.csv"
        )
        self.txt_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 
            f"{account}_stats_hybrid_{self.timestamp}.txt"
        )
        self.cookies_file = os.path.join(self.logs_dir, f"cookies_{self.timestamp}.json")
        
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

logger = Logger()

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

# ====================== SELENIUM: LOGIN Y EXTRACCIÓN DE LISTA ======================
#Para configuración del driver Selenium
def setup_selenium_driver():
    """Configura driver de Selenium"""
    options = webdriver.ChromeOptions()
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    options.add_experimental_option('useAutomationExtension', False)
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.maximize_window()
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver
#Para manejo de cookies
def handle_cookies(driver):
    """Maneja cookies"""
    cookie_selectors = [
        (By.XPATH, "//button[contains(text(),'Allow essential and optional cookies')]"),
        (By.XPATH, "//button[contains(text(),'Accept')]"),
    ]
    
    for by, selector in cookie_selectors:
        try:
            btn = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((by, selector)))
            btn.click()
            human_delay(1, 2)
            return True
        except Exception:
            continue
    return False

def selenium_login(driver):
    """Login con Selenium"""
    try:
        logger.log("🔐 Iniciando login con Selenium...")
        driver.get('https://www.instagram.com/')
        human_delay(5, 7)
        
        handle_cookies(driver)
        
        # Buscar campos de login
        username_input = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='username']"))
        )
        password_input = driver.find_element(By.CSS_SELECTOR, "input[name='password']")
        
        type_like_human(username_input, yourusername)
        human_delay(0.5, 1)
        type_like_human(password_input, yourpassword)
        human_delay(1, 2)
        
        login_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']"))
        )
        login_button.click()
        logger.log("Esperando respuesta del login...")
        human_delay(10, 15)
        
        # Verificar login
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Search' or @aria-label='Search input']"))
            )
            logger.success("✓ Login exitoso")
            return True
        except Exception:
            logger.warning("Continuando sin verificación definitiva...")
            return True
            
    except Exception as e:
        logger.error(f"Error en login: {str(e)}")
        return False

def handle_post_login_dialogs(driver):
    """Cerrar diálogos post-login"""
    dialog_buttons = [
        (By.XPATH, "//button[contains(text(),'Not Now')]"),
        (By.XPATH, "//button[contains(text(),'Ahora no')]"),
    ]
    
    for _ in range(2):
        human_delay(2, 3)
        for by, selector in dialog_buttons:
            try:
                btn = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((by, selector)))
                btn.click()
                logger.debug("Diálogo cerrado")
                break
            except Exception:
                continue

def scroll_modal_smart(driver):
    """
    Hace scroll inteligente buscando el div correcto que scrollea
    Basado en técnica probada que busca divs con scrollHeight > clientHeight
    """
    try:
        # JavaScript que busca automáticamente el div scrolleable correcto
        scroll_script = """
        const dialog = document.querySelector('div[role="dialog"]');
        if (!dialog) return false;
        
        // Buscar el div que realmente scrollea
        const divs = dialog.querySelectorAll('div');
        for (let div of divs) {
            // Si el div tiene contenido scrolleable (20% más alto que visible)
            if (div.scrollHeight > div.clientHeight * 1.2) {
                div.scrollTop = div.scrollHeight;
                return true;
            }
        }
        return false;
        """
        
        result = driver.execute_script(scroll_script)
        
        if result:
            # Pausa para que Instagram cargue más datos
            sleep(random.uniform(1.5, 2.5))
            return True
        else:
            logger.debug("  ⚠ No se encontró div scrolleable")
            return False
        
    except Exception as e:
        logger.debug(f"  ✗ Error en scroll: {str(e)}")
        return False

def extract_followers_list_selenium(driver, account_name, page_type, target_count):
    """Extrae lista de seguidores con Selenium y autoscroll mejorado"""
    try:
        logger.log(f"📋 Extrayendo lista de {page_type} de {account_name}...")
        logger.log(f"🎯 Objetivo: {target_count} usuarios")
        
        url = f'https://www.instagram.com/{account_name}/'
        driver.get(url)
        human_delay(5, 7)
        
        # Verificar cuenta existe
        try:
            driver.find_element(By.XPATH, "//h2[contains(text(), 'Sorry')]")
            logger.error("❌ Cuenta no existe")
            return []
        except NoSuchElementException:
            logger.debug("✓ Cuenta accesible")
        
        # Click en followers
        logger.log(f"🔍 Buscando enlace de {page_type}...")
        link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, f'//a[contains(@href, "/{page_type}")]'))
        )
        
        # Obtener el número total de followers (si es visible)
        try:
            link_text = link.text
            logger.log(f"📊 Información: {link_text}")
        except Exception:
            pass
        
        driver.execute_script("arguments[0].click();", link)
        logger.log("👆 Clic realizado, esperando modal...")
        human_delay(6, 8)
        
        # Buscar modal con múltiples estrategias
        modal = None
        modal_selectors = [
            (By.CSS_SELECTOR, "div[role='dialog']"),
            (By.XPATH, "//div[@role='dialog']"),
        ]
        
        for by, selector in modal_selectors:
            try:
                modal = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((by, selector))
                )
                logger.success(f"✓ Modal encontrado: {selector}")
                break
            except Exception:
                continue
        
        if not modal:
            logger.error("❌ No se encontró el modal")
            return []
        
        # Esperar a que carguen los primeros elementos
        logger.log("⏳ Esperando carga inicial de usuarios...")
        human_delay(2, 3)
        
        # Variables para extracción
        followers_list = []
        scraped = set()
        consecutive_no_progress = 0  # Cambio de nombre para claridad
        max_no_progress = 10  # Intentos consecutivos sin progreso
        scroll_attempts = 0
        max_scroll_attempts = 200  # Aumentado siguiendo el ejemplo compartido
        
        logger.log("🔄 Iniciando extracción con scroll inteligente...")
        logger.log(f"   Max intentos sin progreso: {max_no_progress}")
        logger.log(f"   Max scrolls: {max_scroll_attempts}")
        logger.log("   Técnica: Búsqueda automática de div scrolleable")
        
        while len(followers_list) < target_count and consecutive_no_progress < max_no_progress and scroll_attempts < max_scroll_attempts:
            # Encontrar todos los enlaces de usuarios visibles
            user_links = driver.find_elements(By.XPATH, "//div[@role='dialog']//a[contains(@href, '/')]")
            
            new_users_in_iteration = 0
            
            
            for link in user_links:
                try:
                    href = link.get_attribute('href')
                    if href and 'instagram.com/' in href:
                        username = href.split('instagram.com/')[-1].strip('/').split('/')[0]
                        
                        # Filtrar usernames válidos
                        if (username and 
                            username not in scraped and 
                            username != account_name and
                            not username.startswith('explore') and
                            not username.startswith('p/') and
                            not username.startswith('direct')):
                            
                            scraped.add(username)
                            followers_list.append(username)
                            new_users_in_iteration += 1
                            
                            if len(followers_list) >= target_count:
                                logger.success(f"🎯 ¡Objetivo alcanzado! {len(followers_list)} usuarios")
                                break
                except Exception :
                    continue
            
            # Gestión de progreso
            if new_users_in_iteration > 0:
                consecutive_no_progress = 0  # Reset si hay progreso
                logger.log(f"  ✓ Progreso: {len(followers_list)}/{target_count} (+{new_users_in_iteration} nuevos)")
            else:
                consecutive_no_progress += 1
                if consecutive_no_progress <= 2:
                    logger.debug(f"  ⏳ Esperando carga... ({consecutive_no_progress}/{max_no_progress})")
                elif consecutive_no_progress <= 5:
                    logger.warning(f"  ⚠ Sin nuevos usuarios ({consecutive_no_progress}/{max_no_progress})")
                else:
                    logger.warning(f"  🛑 Sin progreso ({consecutive_no_progress}/{max_no_progress})")
            
            # Si ya alcanzamos el objetivo, salir
            if len(followers_list) >= target_count:
                break
            
            # Hacer scroll inteligente
            scroll_attempts += 1
            
            # Logging cada 10 scrolls o cuando hay progreso
            if scroll_attempts % 10 == 1 or new_users_in_iteration > 0:
                logger.debug(f"  📜 Scroll #{scroll_attempts}")
            
            # Usar el nuevo método de scroll inteligente
            scroll_success = scroll_modal_smart(driver)
            
            if not scroll_success and consecutive_no_progress > 3:
                logger.warning("  ⚠ Scroll no encontró div scrolleable y sin progreso")
                # Intentar método de respaldo
                try:
                    modal = driver.find_element(By.CSS_SELECTOR, "div[role='dialog']")
                    driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", modal)
                    sleep(2)
                except Exception:
                    pass
            
            # Advertencia cada 5 intentos sin progreso
            if consecutive_no_progress > 0 and consecutive_no_progress % 5 == 0:
                logger.warning(f"  📊 Estado: {len(followers_list)}/{target_count} extraídos")
                logger.warning(f"     {consecutive_no_progress} intentos sin progreso")
                if consecutive_no_progress == 5:
                    logger.warning("     Posibles causas:")
                    logger.warning("     - Fin real de la lista")
                    logger.warning("     - Instagram limitando carga")
                    logger.warning(f"     - Cuenta tiene pocos {page_type}")
        
        # Resumen final
        logger.log("="*60)
        if len(followers_list) >= target_count:
            logger.success(f"✅ ÉXITO: {len(followers_list)} usuarios extraídos")
        elif len(followers_list) > 0:
            logger.warning(f"⚠️ PARCIAL: {len(followers_list)}/{target_count} usuarios")
            if consecutive_no_progress >= max_no_progress:
                logger.warning(f"   Razón: {max_no_progress} intentos consecutivos sin progreso")
                logger.warning(f"   Probable: La cuenta solo tiene {len(followers_list)} {page_type} accesibles")
            else:
                logger.warning(f"   Razón: Límite de {scroll_attempts} scrolls alcanzado")
        else:
            logger.error("❌ FALLO: No se extrajeron usuarios")
            logger.error("   Revisa los logs y screenshots generados")
        
        logger.log(f"   Total scrolls realizados: {scroll_attempts}")
        logger.log("="*60)
        
        return followers_list
        
    except Exception as e:
        logger.error(f"❌ Error extrayendo lista: {str(e)}")
        import traceback
        logger.debug(f"Traceback: {traceback.format_exc()}")
        return []

def save_selenium_cookies(driver, filepath):
    """Guarda cookies de Selenium para reutilizarlas en Playwright"""
    try:
        cookies = driver.get_cookies()
        with open(filepath, 'w') as f:
            json.dump(cookies, f)
        logger.success(f"✓ Cookies guardadas: {filepath}")
        return True
    except Exception as e:
        logger.error(f"Error guardando cookies: {str(e)}")
        return False

# ====================== PLAYWRIGHT: ANÁLISIS PARALELO ======================
async def get_follower_count_playwright(context, username, worker_id):
    """
    Obtiene el número de seguidores de un usuario usando Playwright
    """
    page = None
    try:
        page = await context.new_page()
        
        # Bloquear recursos innecesarios para mayor velocidad
        await page.route("**/*.{png,jpg,jpeg,gif,svg,mp4,webm}", lambda route: route.abort())
        await page.route("**/static/**", lambda route: route.abort())
        
        url = f'https://www.instagram.com/{username}/'
        await page.goto(url, wait_until='domcontentloaded', timeout=15000)
        
        # Esperar un poco para que cargue
        await page.wait_for_timeout(2000)
        
        # Verificar si existe
        try:
            error = await page.query_selector("h2:has-text('Sorry')")
            if error:
                logger.warning(f"  [Worker {worker_id}] ⚠ {username} no existe/privado")
                return username, None
        except Exception:
            pass
        
        # Buscar número de seguidores
        selectors = [
            f'a[href="/{username}/followers/"]',
            'a[href*="/followers/"]',
        ]
        # Para cada selector posible intentar extraer el número
        for selector in selectors:
            try:
                element = await page.wait_for_selector(selector, timeout=5000)
                if element:
                    text = await element.inner_text()
                    count = parse_follower_count(text)
                    
                    if count is not None:
                        logger.success(f"  [Worker {worker_id}] ✓ {username}: {count:,}")
                        return username, count
                    
                    # Intentar con title
                    title = await element.get_attribute('title')
                    if title:
                        count = parse_follower_count(title)
                        if count is not None:
                            logger.success(f"  [Worker {worker_id}] ✓ {username}: {count:,}")
                            return username, count
            except Exception:
                continue
        
        # Método alternativo: buscar en todo el texto
        try:
            body_text = await page.inner_text('body')
            if 'followers' in body_text.lower():
                lines = body_text.split('\n')
                for line in lines:
                    if 'follower' in line.lower():
                        count = parse_follower_count(line)
                        if count is not None:
                            logger.success(f"  [Worker {worker_id}] ✓ {username}: {count:,} (alt)")
                            return username, count
        except Exception:
            pass
        
        logger.warning(f"  [Worker {worker_id}] ⚠ No se pudo obtener de {username}")
        return username, None
        
    except Exception as e:
        logger.debug(f"  [Worker {worker_id}] ✗ Error en {username}: {str(e)}")
        return username, None
    finally:
        if page:
            await page.close()

async def process_batch(context, batch, worker_id, semaphore):
    """Procesa un lote de usuarios con un worker"""
    async with semaphore:
        results = []
        for username in batch:
            result = await get_follower_count_playwright(context, username, worker_id)
            results.append(result)
            # Pequeña pausa entre perfiles del mismo worker
            await asyncio.sleep(random.uniform(0.5, 1.5))
        return results

async def analyze_profiles_parallel(cookies_file, followers_list, max_workers):
    """
    Analiza perfiles en paralelo usando Playwright
    """
    logger.log("="*80)
    logger.log(f"🚀 INICIANDO ANÁLISIS PARALELO CON {max_workers} WORKERS")
    logger.log("="*80)
    
    # Cargar cookies
    with open(cookies_file, 'r', encoding='utf-8') as f:
        selenium_cookies = json.load(f)
    
    # Dividir la lista en lotes para cada worker
    batch_size = len(followers_list) // max_workers
    if batch_size == 0:
        batch_size = 1
    
    batches = [followers_list[i:i+batch_size] for i in range(0, len(followers_list), batch_size)]
    
    logger.log(f"📦 {len(followers_list)} usuarios divididos en {len(batches)} lotes")
    
    results = []
    
    async with async_playwright() as p:
        # Lanzar navegador
        browser = await p.chromium.launch(
            headless=True,  # Cambiar a False para ver el proceso
            args=['--disable-blink-features=AutomationControlled']
        )
        
        # Crear contexto con cookies
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        
        # Añadir cookies de Selenium a Playwright
        playwright_cookies = []
        for cookie in selenium_cookies:
            playwright_cookie = {
                'name': cookie['name'],
                'value': cookie['value'],
                'domain': cookie['domain'],
                'path': cookie['path'],
            }
            if 'expiry' in cookie:
                playwright_cookie['expires'] = cookie['expiry']
            if 'secure' in cookie:
                playwright_cookie['secure'] = cookie['secure']
            if 'httpOnly' in cookie:
                playwright_cookie['httpOnly'] = cookie['httpOnly']
            
            playwright_cookies.append(playwright_cookie)
        
        await context.add_cookies(playwright_cookies)
        logger.success("✓ Cookies cargadas en Playwright")
        
        # Semáforo para limitar concurrencia
        semaphore = asyncio.Semaphore(max_workers)
        
        # Crear tareas para cada lote
        tasks = []
        for worker_id, batch in enumerate(batches, 1):
            task = process_batch(context, batch, worker_id, semaphore)
            tasks.append(task)
        
        # Ejecutar todas las tareas en paralelo
        logger.log(f"⏱️  Tiempo estimado: ~{len(followers_list) * 2 / max_workers / 60:.1f} minutos")
        start_time = datetime.datetime.now()
        
        batch_results = await asyncio.gather(*tasks)
        
        end_time = datetime.datetime.now()
        elapsed = (end_time - start_time).total_seconds()
        
        # Consolidar resultados
        for batch_result in batch_results:
            results.extend(batch_result)
        
        await browser.close()
        
        logger.log("="*80)
        logger.success("✅ ANÁLISIS PARALELO COMPLETADO")
        logger.log(f"⏱️  Tiempo real: {elapsed/60:.1f} minutos")
        logger.log(f"🚀 Velocidad: {len(results)/(elapsed/60):.1f} perfiles/minuto")
        logger.log("="*80)
    
    return results

# ====================== GUARDAR RESULTADOS ======================
def save_results(account_name, results_dict):
    """Guarda resultados en CSV y TXT"""
    
# --- Nueva función auxiliar ---
    def get_first_digit(number):
        """Devuelve el primer dígito del número de seguidores."""
        try:
            return int(str(abs(int(number)))[0])
        except Exception:
            return None

    # --- Preparar lista de resultados con First_Digit ---
    results_list = []
    for username, count in results_dict.items():
        first_digit = get_first_digit(count)
        results_list.append([account_name, username, count, first_digit])

    # --- Guardar en CSV ---
    try:
        with open(logger.csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Username', 'Username_Follower', 'Num_Followers', 'First_Digit'])
            writer.writerows(results_list)
        logger.success(f"📊 CSV: {logger.csv_file}")
    except Exception as e:
        logger.error(f"Error CSV: {str(e)}")

    # --- Guardar en TXT ---
    try:
        with open(logger.txt_file, 'w', encoding='utf-8') as f:
            f.write(f"{'='*100}\n")
            f.write(f"ANÁLISIS DE SEGUIDORES (HÍBRIDO) - {account_name}\n")
            f.write(f"Fecha: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'='*100}\n\n")

            f.write(f"{'Username':<20} | {'Follower':<25} | {'Num Seguidores':>15} | {'First_Digit':>12}\n")
            f.write(f"{'-'*20}-+-{'-'*25}-+-{'-'*15}-+-{'-'*12}\n")

            for username, follower, num_followers, first_digit in results_list:
                num_str = f"{num_followers:,}" if num_followers is not None else "N/A"
                f.write(f"{username:<20} | {follower:<25} | {num_str:>15} | {str(first_digit):>12}\n")

        logger.success(f"📄 TXT: {logger.txt_file}")
    except Exception as e:
        logger.error(f"Error TXT: {str(e)}")

# ====================== MAIN ======================
def main():
    driver = None
    
    try:
        start_time = datetime.datetime.now()
        
        logger.log("="*80)
        logger.log("🎯 SCRAPER HÍBRIDO: SELENIUM + PLAYWRIGHT PARALELO")
        logger.log("="*80)
        logger.log("📊 Configuración:")
        logger.log(f"   - Cuenta objetivo: {account}")
        logger.log(f"   - Tipo: {page}")
        logger.log(f"   - Cantidad: {count}")
        logger.log(f"   - Workers paralelos: {MAX_CONCURRENT_WORKERS}")
        logger.log("="*80)
        
        # FASE 1: SELENIUM - Login y extracción de lista
        logger.log("\n" + "="*80)
        logger.log("FASE 1: SELENIUM - LOGIN Y EXTRACCIÓN DE LISTA")
        logger.log("="*80)
        
        driver = setup_selenium_driver()
        logger.success("✓ Driver Selenium iniciado")
        
        if not selenium_login(driver):
            logger.error("❌ Login fallido")
            return
        
        handle_post_login_dialogs(driver)
        
        followers_list = extract_followers_list_selenium(driver, account, page, count)
        
        if not followers_list:
            logger.error("❌ No se pudieron extraer seguidores")
            return
        
        # Guardar cookies para Playwright
        if not save_selenium_cookies(driver, logger.cookies_file):
            logger.error("❌ No se pudieron guardar cookies")
            return
        
        logger.success(f"✓ FASE 1 COMPLETADA: {len(followers_list)} usuarios extraídos")
        
        # Cerrar Selenium
        driver.quit()
        logger.log("✓ Driver Selenium cerrado")
        
        # FASE 2: PLAYWRIGHT - Análisis paralelo
        logger.log("\n" + "="*80)
        logger.log("FASE 2: PLAYWRIGHT - ANÁLISIS PARALELO DE PERFILES")
        logger.log("="*80)
        
        # Ejecutar análisis paralelo
        results = asyncio.run(
            analyze_profiles_parallel(logger.cookies_file, followers_list, MAX_CONCURRENT_WORKERS)
        )
        
        # Convertir resultados a diccionario
        results_dict = {username: count for username, count in results}
        
        # FASE 3: Guardar resultados
        logger.log("\n" + "="*80)
        logger.log("FASE 3: GUARDANDO RESULTADOS")
        logger.log("="*80)

        save_results(account, results_dict)

        # FASE 4: Ejecutar Benford Analyzer
        logger.log("\n" + "="*80)
        logger.log("FASE 4: EJECUTANDO BENFORD ANALYZER")
        logger.log("="*80)

        import subprocess
        try:
            logger.log(f"Ejecutando benford_analyzer.py con CSV: {logger.csv_file}")
            subprocess.run(["python", "benford_analyzer.py", logger.csv_file], check=True)
            logger.success("✓ Benford Analyzer ejecutado exitosamente")
        except subprocess.CalledProcessError as e:
            logger.error(f"Error ejecutando benford_analyzer.py: {e}")
        except FileNotFoundError:
            logger.error("benford_analyzer.py no encontrado en el directorio actual")
        
        # RESUMEN FINAL
        end_time = datetime.datetime.now()
        total_elapsed = (end_time - start_time).total_seconds()
        
        successful = sum(1 for count in results_dict.values() if count is not None)
        failed = len(results_dict) - successful
        
        logger.log("\n" + "="*80)
        logger.success("🎉 PROCESO COMPLETADO")
        logger.log("="*80)
        logger.log(f"⏱️  Tiempo total: {total_elapsed/60:.1f} minutos")
        logger.log(f"🚀 Velocidad promedio: {len(results_dict)/(total_elapsed/60):.1f} perfiles/min")
        logger.log("📊 Estadísticas:")
        logger.log(f"   - Total analizado: {len(results_dict)}")
        logger.log(f"   - ✓ Exitosos: {successful}")
        logger.log(f"   - ✗ Fallidos: {failed}")
        logger.log(f"   - Tasa de éxito: {successful/len(results_dict)*100:.1f}%")
        logger.log("📁 Archivos generados:")
        logger.log(f"   - CSV: {logger.csv_file}")
        logger.log(f"   - TXT: {logger.txt_file}")
        logger.log(f"   - LOG: {logger.log_file}")
        logger.log("="*80)
        
        # Estimación para 500 perfiles
        if count < 500:
            estimated_time = (total_elapsed / count) * 500 / 60
            logger.log(f"\n💡 Estimación para 500 perfiles: ~{estimated_time:.1f} minutos")
        
    except KeyboardInterrupt:
        logger.warning("\n⚠️ Proceso interrumpido por el usuario")
    except Exception as e:
        logger.error(f"\n❌ Error crítico: {str(e)}")
        import traceback
        logger.error(f"Traceback:\n{traceback.format_exc()}")
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

if __name__ == "__main__":
    main()