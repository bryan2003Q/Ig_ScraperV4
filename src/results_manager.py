import csv
import datetime



# ====================== GUARDAR RESULTADOS ======================
def save_results(account_name, results_dict, logger):
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
