import os
import datetime
import asyncio
import subprocess
from dotenv import load_dotenv

# Módulos propios
from logger_manager import Logger
from selenium_handler import (
    setup_selenium_driver,
    selenium_login,
    handle_post_login_dialogs,
    extract_followers_list_selenium,
    save_selenium_cookies,
)
from playwright_handler import analyze_profiles_parallel
from results_manager import save_results


# ====================== CARGAR CONFIGURACIÓN ======================
load_dotenv()

yourusername = os.getenv("IG_USERNAME")
yourpassword = os.getenv("IG_PASSWORD")
account = os.getenv("TARGET_ACCOUNT", "teeli__peachmuffin")
page = os.getenv("PAGE_TYPE", "followers")
count = int(os.getenv("FOLLOWER_COUNT", "50"))

MAX_CONCURRENT_WORKERS = int(os.getenv("MAX_WORKERS", "10"))

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


# ====================== INICIALIZAR LOGGER ======================
logger = Logger()
logger.set_account_files(account)


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
        
        # ====================== FASE 1: SELENIUM ======================
        logger.log("\n" + "="*80)
        logger.log("FASE 1: SELENIUM - LOGIN Y EXTRACCIÓN DE LISTA")
        logger.log("="*80)
        
        driver = setup_selenium_driver()
        logger.success("✓ Driver Selenium iniciado")
        
        if not selenium_login(driver, logger, yourusername, yourpassword):
            logger.error("❌ Login fallido")
            return
        
        handle_post_login_dialogs(driver, logger)
        
        followers_list = extract_followers_list_selenium(
            driver, account, page, count, logger
        )
        
        if not followers_list:
            logger.error("❌ No se pudieron extraer seguidores")
            return
        
        # Guardar cookies para Playwright
        if not save_selenium_cookies(driver, logger.cookies_file, logger):
            logger.error("❌ No se pudieron guardar cookies")
            return
        
        logger.success(f"✓ FASE 1 COMPLETADA: {len(followers_list)} usuarios extraídos")
        
        driver.quit()
        logger.log("✓ Driver Selenium cerrado")
        
        # ====================== FASE 2: PLAYWRIGHT ======================
        logger.log("\n" + "="*80)
        logger.log("FASE 2: PLAYWRIGHT - ANÁLISIS PARALELO DE PERFILES")
        logger.log("="*80)
        
        results = asyncio.run(
            analyze_profiles_parallel(
                logger.cookies_file,
                followers_list,
                MAX_CONCURRENT_WORKERS,
                logger
            )
        )
        
        results_dict = {username: count for username, count in results}
        
        # ====================== FASE 3: GUARDAR RESULTADOS ======================
        logger.log("\n" + "="*80)
        logger.log("FASE 3: GUARDANDO RESULTADOS")
        logger.log("="*80)
        
        save_results(account, results_dict, logger)
        
        # ====================== FASE 4: BENFORD ANALYZER ======================
        logger.log("\n" + "="*80)
        logger.log("FASE 4: EJECUTANDO BENFORD ANALYZER")
        logger.log("="*80)
        
        try:
            benford_path = os.path.join(os.path.dirname(__file__), "benford_analyzer.py")
            subprocess.run(["python", benford_path, logger.csv_file], check=True)
            logger.success("✓ Benford Analyzer ejecutado exitosamente")
        except subprocess.CalledProcessError as e:
            logger.error(f"Error ejecutando benford_analyzer.py: {e}")
        except FileNotFoundError:
            logger.error("benford_analyzer.py no encontrado en el directorio actual")
        
        # ====================== RESUMEN FINAL ======================
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
