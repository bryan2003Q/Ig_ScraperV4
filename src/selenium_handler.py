
import random

import json
from time import sleep

from selenium import webdriver  # Webdriver Selenium. Usado en login y extracción.
from selenium.webdriver.support.ui import WebDriverWait  # Espera elementos. Usado en login y extracción.
from selenium.webdriver.support import expected_conditions as EC  # Condiciones esperadas. Usado con WebDriverWait.
from selenium.webdriver.common.by import By  # Localización elementos. Usado en find_elements.
from selenium.common.exceptions import NoSuchElementException  # Excepciones Selenium. Usado en try-except.
from selenium.webdriver.chrome.service import Service  # Servicio Chrome. Usado en webdriver.Chrome.
from webdriver_manager.chrome import ChromeDriverManager  # Gestor driver Chrome. Usado en setup_selenium_driver.

from utils import human_delay, type_like_human



# ====================== SELENIUM: LOGIN Y EXTRACCIÓN DE LISTA ======================

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


def selenium_login(driver, logger, yourusername, yourpassword):
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


def handle_post_login_dialogs(driver, logger):
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


def scroll_modal_smart(driver, logger):
    """
    Hace scroll inteligente buscando el div correcto que scrollea
    Basado en técnica probada que busca divs con scrollHeight > clientHeight
    """
    try:
        scroll_script = """
        const dialog = document.querySelector('div[role="dialog"]');
        if (!dialog) return false;
        
        const divs = dialog.querySelectorAll('div');
        for (let div of divs) {
            if (div.scrollHeight > div.clientHeight * 1.2) {
                div.scrollTop = div.scrollHeight;
                return true;
            }
        }
        return false;
        """
        
        result = driver.execute_script(scroll_script)
        
        if result:
            sleep(random.uniform(1.5, 2.5))
            return True
        else:
            logger.debug("  ⚠ No se encontró div scrolleable")
            return False
        
    except Exception as e:
        logger.debug(f"  ✗ Error en scroll: {str(e)}")
        return False


def extract_followers_list_selenium(driver, account_name, page_type, target_count, logger):
    """Extrae lista de seguidores con Selenium y autoscroll mejorado"""
    try:
        logger.log(f"📋 Extrayendo lista de {page_type} de {account_name}...")
        logger.log(f"🎯 Objetivo: {target_count} usuarios")
        
        url = f'https://www.instagram.com/{account_name}/'
        driver.get(url)
        human_delay(5, 7)
        
        try:
            driver.find_element(By.XPATH, "//h2[contains(text(), 'Sorry')]")
            logger.error("❌ Cuenta no existe")
            return []
        except NoSuchElementException:
            logger.debug("✓ Cuenta accesible")
        
        logger.log(f"🔍 Buscando enlace de {page_type}...")
        link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, f'//a[contains(@href, "/{page_type}")]'))
        )
        
        try:
            link_text = link.text
            logger.log(f"📊 Información: {link_text}")
        except Exception:
            pass
        
        driver.execute_script("arguments[0].click();", link)
        logger.log("👆 Clic realizado, esperando modal...")
        human_delay(6, 8)
        
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
        
        logger.log("⏳ Esperando carga inicial de usuarios...")
        human_delay(2, 3)
        
        followers_list = []
        scraped = set()
        consecutive_no_progress = 0
        max_no_progress = 10
        scroll_attempts = 0
        max_scroll_attempts = 200
        
        logger.log("🔄 Iniciando extracción con scroll inteligente...")
        logger.log(f"   Max intentos sin progreso: {max_no_progress}")
        logger.log(f"   Max scrolls: {max_scroll_attempts}")
        logger.log("   Técnica: Búsqueda automática de div scrolleable")
        
        while len(followers_list) < target_count and consecutive_no_progress < max_no_progress and scroll_attempts < max_scroll_attempts:
            user_links = driver.find_elements(By.XPATH, "//div[@role='dialog']//a[contains(@href, '/')]")
            
            new_users_in_iteration = 0
            
            for link in user_links:
                try:
                    href = link.get_attribute('href')
                    if href and 'instagram.com/' in href:
                        username = href.split('instagram.com/')[-1].strip('/').split('/')[0]
                        
                        if (
                            username 
                            and username not in scraped 
                            and username != account_name
                            and not username.startswith('explore')
                            and not username.startswith('p/')
                            and not username.startswith('direct')
                        ):
                            scraped.add(username)
                            followers_list.append(username)
                            new_users_in_iteration += 1
                            
                            if len(followers_list) >= target_count:
                                logger.success(f"🎯 ¡Objetivo alcanzado! {len(followers_list)} usuarios")
                                break
                except Exception:
                    continue
            
            if new_users_in_iteration > 0:
                consecutive_no_progress = 0
                logger.log(f"  ✓ Progreso: {len(followers_list)}/{target_count} (+{new_users_in_iteration} nuevos)")
            else:
                consecutive_no_progress += 1
                if consecutive_no_progress <= 2:
                    logger.debug(f"  ⏳ Esperando carga... ({consecutive_no_progress}/{max_no_progress})")
                elif consecutive_no_progress <= 5:
                    logger.warning(f"  ⚠ Sin nuevos usuarios ({consecutive_no_progress}/{max_no_progress})")
                else:
                    logger.warning(f"  🛑 Sin progreso ({consecutive_no_progress}/{max_no_progress})")
            
            if len(followers_list) >= target_count:
                break
            
            scroll_attempts += 1
            
            if scroll_attempts % 10 == 1 or new_users_in_iteration > 0:
                logger.debug(f"  📜 Scroll #{scroll_attempts}")
            
            scroll_success = scroll_modal_smart(driver, logger)
            
            if not scroll_success and consecutive_no_progress > 3:
                logger.warning("  ⚠ Scroll no encontró div scrolleable y sin progreso")
                try:
                    modal = driver.find_element(By.CSS_SELECTOR, "div[role='dialog']")
                    driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", modal)
                    sleep(2)
                except Exception:
                    pass
            
            if consecutive_no_progress > 0 and consecutive_no_progress % 5 == 0:
                logger.warning(f"  📊 Estado: {len(followers_list)}/{target_count} extraídos")
                logger.warning(f"     {consecutive_no_progress} intentos sin progreso")
                if consecutive_no_progress == 5:
                    logger.warning("     Posibles causas:")
                    logger.warning("     - Fin real de la lista")
                    logger.warning("     - Instagram limitando carga")
                    logger.warning(f"     - Cuenta tiene pocos {page_type}")
        
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


def save_selenium_cookies(driver, filepath, logger):
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
