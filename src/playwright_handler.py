import asyncio
import random
import datetime
import json

from playwright.async_api import async_playwright

from utils import parse_follower_count



# ====================== PLAYWRIGHT: ANÁLISIS PARALELO ======================

async def get_follower_count_playwright(context, username, worker_id, logger):
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
        
        for selector in selectors:
            try:
                element = await page.wait_for_selector(selector, timeout=12000)
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


async def process_batch(context, batch, worker_id, semaphore, logger):
    """Procesa un lote de usuarios con un worker"""
    async with semaphore:
        results = []
        for username in batch:
            result = await get_follower_count_playwright(context, username, worker_id, logger)
            results.append(result)
            await asyncio.sleep(random.uniform(0.5, 1.5))
        return results


async def analyze_profiles_parallel(cookies_file, followers_list, max_workers, logger):
    """
    Analiza perfiles en paralelo usando Playwright
    """
    logger.log("="*80)
    logger.log(f"🚀 INICIANDO ANÁLISIS PARALELO CON {max_workers} WORKERS")
    logger.log("="*80)
    
    # Cargar cookies
    with open(cookies_file, 'r', encoding='utf-8') as f:
        selenium_cookies = json.load(f)
    
    # Dividir lista en lotes
    batch_size = len(followers_list) // max_workers
    if batch_size == 0:
        batch_size = 1
    
    batches = [followers_list[i:i+batch_size] for i in range(0, len(followers_list), batch_size)]
    
    logger.log(f"📦 {len(followers_list)} usuarios divididos en {len(batches)} lotes")
    
    results = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        
        # Convertir cookies Selenium → Playwright
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
        
        semaphore = asyncio.Semaphore(max_workers)
        
        tasks = []
        for worker_id, batch in enumerate(batches, 1):
            task = process_batch(context, batch, worker_id, semaphore, logger)
            tasks.append(task)
        
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
