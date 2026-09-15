import time
from playwright.sync_api import sync_playwright

# === НАСТРОЙКИ ===
# 1. Замените YOUR_USERNAME на ваше имя пользователя в Windows
USER_DATA_DIR = r"C:\Users\YOUR_USERNAME\AppData\Local\Google\Chrome\User Data"

# 2. Укажите ваши аккаунты и названия их профилей Chrome.
# Чтобы узнать название профиля: откройте нужный профиль Chrome, 
# введите в адресную строку chrome://version/ и посмотрите путь в строке "Profile Path"
ACCOUNTS = {
    # "anna.n.ekb@gmail.com": "Profile 1",
    # "rusttelegram@gmail.com": "Profile 2",
}

def automate_gcp(email, profile_dir):
    print(f"\n[{email}] === Запуск профиля: {profile_dir} ===")
    
    with sync_playwright() as p:
        try:
            # Запускаем браузер
            browser = p.chromium.launch_persistent_context(
                user_data_dir=USER_DATA_DIR,
                channel="chrome",
                headless=False, # Окно будет видно
                args=[f"--profile-directory={profile_dir}"]
            )
            page = browser.pages[0]
            
            # --- ШАГ 1: Создание проекта ---
            print(f"[{email}] Открываем страницу создания проекта...")
            page.goto("https://console.cloud.google.com/projectcreate")
            page.wait_for_load_state("networkidle")
            
            # Внимание: здесь бот ждет, пока вы сами проверите страницу.
            # Если Google Cloud просит принять соглашение — сделайте это руками.
            input(f"[{email}] ПАУЗА: Если нужно, создайте проект руками в открытом окне.\nНажмите Enter в этой консоли, когда проект будет создан...")

            # --- ШАГ 2: Включение API ---
            print(f"[{email}] Переходим к включению Gemini API...")
            # Замените ВАШ_ПРОЕКТ на реальный ID проекта, если хотите автоматизировать этот шаг
            # page.goto("https://console.cloud.google.com/apis/library/generativelanguage.googleapis.com")
            
            input(f"[{email}] ПАУЗА: Включите API и перейдите к Service Accounts.\nНажмите Enter для продолжения...")

            # --- ШАГ 3: Создание ключа ---
            print(f"[{email}] Открываем раздел IAM & Admin...")
            # page.goto("https://console.cloud.google.com/iam-admin/serviceaccounts")

            input(f"[{email}] ПАУЗА: Создайте ключ JSON, он скачается.\nНажмите Enter, чтобы закрыть этот аккаунт и перейти к следующему...")
            
        except Exception as e:
            print(f"[{email}] Произошла ошибка: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    if not ACCOUNTS:
        print("ВНИМАНИЕ: Вы не заполнили словарь ACCOUNTS в коде скрипта!")
    else:
        for email, profile in ACCOUNTS.items():
            automate_gcp(email, profile)
        print("\n=== ВСЕ АККАУНТЫ ОБРАБОТАНЫ ===")
