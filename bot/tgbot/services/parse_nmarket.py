import random
import sys
import subprocess
import time
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

from playwright.sync_api import Browser, Page, sync_playwright
from bot.tgbot.databases.database import DatabaseConnection

LOGIN_NMARKET = os.getenv("LOGIN_NMARKET", "user")
PASSWORD_NMARKET = os.getenv("PASSWORD_NMARKET", "password")

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = os.path.join(BASE_DIR, "databases", "nmarket.db")


def init_db(db_path: str = DB_PATH):
    """Создаёт таблицы в БД."""
    # Для nmarket.db используем SQLite напрямую, так как это отдельная база
    # Но используем DatabaseConnection для единообразия
    db = DatabaseConnection(db_path, schema=None)
    
    # Создаем таблицу complexes
    db.execute("""
        CREATE TABLE IF NOT EXISTS complexes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE,
            name TEXT,
            address TEXT,
            developer TEXT,
            floor_count TEXT,
            status TEXT,
            key_issue TEXT,
            parking TEXT,
            ceiling_height TEXT,
            finishing TEXT,
            contract_type TEXT,
            building_type TEXT,
            registration TEXT,
            payment_options TEXT,
            units_total TEXT,
            description TEXT,
            advantages TEXT,
            contact_name TEXT,
            contact_phone TEXT,
            contact_email TEXT
        )
    """)
    
    # Создаем таблицу units
    db.execute("""
        CREATE TABLE IF NOT EXISTS units (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            complex_id INTEGER,
            unit_type TEXT,
            building TEXT,
            section TEXT,
            floor TEXT,
            apartment_number TEXT,
            finishing TEXT,
            total_area REAL,
            living_area REAL,
            kitchen_area REAL,
            price_per_m2 REAL,
            price_full REAL,
            price_base REAL,
            FOREIGN KEY(complex_id) REFERENCES complexes(id)
        )
    """)
    
    return db


def ensure_chromium_installed():
    """Проверяет, установлен ли Chromium для Playwright, и при необходимости скачивает."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("✅ Chromium проверен/установлен")
        else:
            print("⚠️ Ошибка при установке Chromium:", result.stderr)
    except Exception as e:
        print("❌ Не удалось проверить/установить Chromium:", e)


def login(page: Page, username: str, password: str) -> None:
    """Выполняет вход на сайт Nmarket.PRO."""
    page.goto("https://auth.nmarket.pro/Account/Login", wait_until="domcontentloaded")
    try:
        page.locator("text=Принимаю").click(timeout=3000)
    except Exception:
        pass
    page.locator("text=Войти").first.click()
    page.wait_for_load_state("domcontentloaded")
    page.locator("text=По логину").click()
    page.locator("input[placeholder='Логин']").fill(username)
    page.locator("input[id='password']").fill(password)
    page.locator("button:has-text('Войти')").click()
    page.wait_for_load_state("networkidle")


def get_complex_links(page: Page) -> List[str]:
    """
    Возвращает список URL-адресов всех комплексов со всех страниц выдачи.
    """
    LISTING_URL = "https://ekb.nmarket.pro/search/complexesgrid?isSmartLineMode=false"
    page.goto(LISTING_URL, wait_until="networkidle")
    time.sleep(random.uniform(1, 2))

    try:
        page.locator("text=Принимаю").click(timeout=3000)
    except Exception:
        pass

    urls: set[str] = set()

    # TODO Нужно для тестов, чтобы не собирать все ссылки
    # while len(urls)<15:
    while True:
        links = page.locator("a[href*='/search/complex']")
        count = links.count()
        
        for i in range(count):
            href = links.nth(i).get_attribute("href")
            if href:
                url = href if href.startswith("http") else "https://ekb.nmarket.pro" + href
                urls.add(url)

        next_btn = page.locator("div.pagination__next-button").first
        try:
            if next_btn.is_visible():
                next_btn.click()
                page.wait_for_load_state("networkidle")
                time.sleep(random.uniform(1, 3))
            else:
                break
        except Exception:
            break

    return list(urls)


def parse_complex(page: Page, complex_url: str
                  ) -> Tuple[Dict[str, Optional[str]], List[Dict[str, Optional[str]]]]:
    """
    Извлекает информацию о ЖК и списке квартир.
    Возвращает общую информацию (general) и список квартир (units).
    """
    general_info: Dict[str, Optional[str]] = {
        "url": complex_url,
        "name": None,
        "address": None,
        "developer": None,
        "floor_count": None,
        "status": None,
        "key_issue": None,
        "parking": None,
        "ceiling_height": None,
        "finishing": None,
        "contract_type": None,
        "building_type": None,
        "registration": None,
        "payment_options": None,
        "units_total": None,
        "description": None,
        "advantages": None,
        "contact_name": None,
        "contact_phone": None,
        "contact_email": None,
    }


    page.goto(complex_url, wait_until="networkidle")
    try:
        page.locator("text=Принимаю").click(timeout=3000)
    except Exception:
        pass

    try:
        element = page.locator("h2.complex__title").first
        name_text = element.evaluate("el => el.childNodes[0].textContent.trim()")
        general_info["name"] = name_text
    except Exception:
        pass

    label_map = {
        "Застройщик": "developer",
        "Этажность": "floor_count",
        "Срок сдачи": "status",
        "Срок выдачи ключей": "key_issue",
        "Парковка": "parking",
        "Потолки": "ceiling_height",
        "Отделка": "finishing",
        "Договор": "contract_type",
        "Тип дома": "building_type",
        "Регистрация": "registration",
        "Варианты оплаты": "payment_options",
        "Всего в продаже": "units_total",
    }

    for ru_label, key in label_map.items():
        try:
            label_el = page.locator(f"text={ru_label}").first
            value = label_el.evaluate("el => el.nextElementSibling?.textContent")
            if value:
                general_info[key] = value.strip()
        except Exception:
            pass

    try:
        address = page.locator("div.complex__address").first.text_content().strip()
        general_info["address"] = address
    except Exception:
        pass

    try:
        desc_sec = page.locator("text=Описание комплекса").first
        desc_text = desc_sec.evaluate("el => el.nextElementSibling?.textContent")
        if desc_text:
            general_info["description"] = desc_text.strip()
    except Exception:
        pass
    try:
        adv_sec = page.locator("text=Преимущества").first
        adv_ul = adv_sec.evaluate("el => el.nextElementSibling?.querySelectorAll('li')")
        if adv_ul:
            adv_list = [li.textContent.strip() for li in adv_ul]
            general_info["advantages"] = "; ".join(adv_list)
    except Exception:
        pass

    try:
        name_el = page.locator("div.responsible-list__name").first
        phone_el = page.locator("a.responsible-list__phone").first
        email_el = page.locator("a.responsible-list__email").first
        if name_el:
            general_info["contact_name"] = name_el.text_content().strip()
        if phone_el:
            general_info["contact_phone"] = phone_el.text_content().strip()
        if email_el:
            general_info["contact_email"] = email_el.get_attribute("href").replace("mailto:", "")
    except Exception:
        pass

    try:
        units: List[Dict[str, Optional[str]]] = []

        try:
            objects_tab = page.locator("a.complex-menu__item-link[href*='#objects']").first
            if objects_tab.count() > 0:
                objects_tab.click()
                page.wait_for_load_state("domcontentloaded")
            else:
                page.evaluate("location.hash = 'objects'")
        except Exception:
            pass

        try:
            page.wait_for_selector("ul.phases", timeout=15000)
        except Exception:
            pass

        phases = page.locator("ul.phases > li.phases__item")
        
        for i in range(phases.count()):
            phase = phases.nth(i)

            groups = phase.locator("br-rooms-group-table")

            for g in range(groups.count()):
                group = groups.nth(g)
                try:
                    header_btn = group.locator("button.card__button")
                    if header_btn.count() > 0:
                        header_btn.click()
                        time.sleep(random.uniform(0.3, 0.8))

                    rows = group.locator("tbody tr.content")

                    for r in range(rows.count()):
                        row = rows.nth(r)
                        try:
                            unit_type = row.locator("span.content__rooms-name").first.text_content().strip()
                            building = row.locator("a.content__house-link").first.text_content().strip()
                            section = row.locator("td.content__cell_section").first.text_content().strip()
                            floor = row.locator("td.content__cell_floor").first.text_content().strip()
                            finishing = row.locator("td.content__cell_finishing").first.text_content().strip()
                            apartment_number = row.locator("td.content__cell_flat-num").first.text_content().strip()
                            total_area = row.locator("td.content__cell_total-square").first.text_content().strip()
                            living_area = row.locator("td.content__cell_living-square").first.text_content().strip()
                            kitchen_area = row.locator("td.content__cell_kitchen-square").first.text_content().strip()
                            price_per_m2 = row.locator("td.content__cell_metre-price").first.text_content().strip()
                            price_full = row.locator("td.content__cell_total-price").first.text_content().strip()
                            price_base = row.locator("td.content__cell_base-price").first.text_content().strip()

                            unit_data = {
                                "complex_id": None,
                                "unit_type": unit_type,
                                "building": building,
                                "section": section,
                                "floor": floor,
                                "apartment_number": apartment_number,
                                "finishing": finishing,
                                "total_area": total_area,
                                "living_area": living_area,
                                "kitchen_area": kitchen_area,
                                "price_per_m2": price_per_m2,
                                "price_full": price_full,
                                "price_base": price_base,
                            }
                            units.append(unit_data)
                        except Exception as e:
                            print(f"      Ошибка при обработке строки {r + 1} в группе {g + 1}: {e}")
                            continue
                except Exception as e:
                    print(f"    Ошибка при обработке группы {g + 1}: {e}")
                    continue

    except Exception as e:
        print("Ошибка при сборе данных:", e)


    return general_info, units


def save_to_db(db: DatabaseConnection,
               general: Dict[str, Optional[str]],
               units: List[Dict[str, Optional[str]]]) -> None:
    """Сохраняет данные ЖК и квартир в БД."""
    # Используем named parameters для совместимости
    # Для SQLite используем ? или named parameters, для PostgreSQL - %s
    # DatabaseConnection автоматически адаптирует запросы
    
    # Вставляем или обновляем комплекс
    # Для SQLite используем ON CONFLICT, для PostgreSQL - ON CONFLICT или отдельный UPDATE
    db.execute("""
        INSERT INTO complexes (
            url, name, address, developer, floor_count, status, key_issue,
            parking, ceiling_height, finishing, contract_type, building_type,
            registration, payment_options, units_total,
            description, advantages, contact_name, contact_phone, contact_email
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s, %s, %s
        )
    """, (
        general.get("url"), general.get("name"), general.get("address"), 
        general.get("developer"), general.get("floor_count"), general.get("status"), 
        general.get("key_issue"), general.get("parking"), general.get("ceiling_height"),
        general.get("finishing"), general.get("contract_type"), general.get("building_type"),
        general.get("registration"), general.get("payment_options"), general.get("units_total"),
        general.get("description"), general.get("advantages"), general.get("contact_name"),
        general.get("contact_phone"), general.get("contact_email")
    ))
    
    # Получаем complex_id
    result = db.fetchone("SELECT id FROM complexes WHERE url = %s", (general["url"],))
    if result:
        if isinstance(result, dict):
            complex_id = result.get('id')
        else:
            complex_id = result[0] if result else None
    else:
        # Если не нашли, значит была ошибка вставки
        return

    # Удаляем старые units
    db.execute("DELETE FROM units WHERE complex_id = %s", (complex_id,))
    
    # Вставляем новые units
    for unit in units:
        db.execute("""
            INSERT INTO units (
                complex_id, unit_type, building, section, floor, apartment_number,
                finishing, total_area, living_area, kitchen_area, price_per_m2,
                price_full, price_base
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """, (
            complex_id, unit.get("unit_type"), unit.get("building"), 
            unit.get("section"), unit.get("floor"), unit.get("apartment_number"),
            unit.get("finishing"), unit.get("total_area"), unit.get("living_area"),
            unit.get("kitchen_area"), unit.get("price_per_m2"), unit.get("price_full"),
            unit.get("price_base")
        ))

    # Обновляем units_total
    db.execute("""
        UPDATE complexes
        SET units_total = (
            SELECT COUNT(*) FROM units WHERE complex_id = %s
        )
        WHERE id = %s
    """, (complex_id, complex_id))


def main(username: str, password: str) -> None:
    """Точка входа."""
    db = init_db()
    ensure_chromium_installed()
    with sync_playwright() as p:
        browser: Browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        print("Вход на сайт...")
        login(page, username, password)
        time.sleep(random.uniform(2, 5))
        print("Авторизация прошла успешно. Получаем список комплексов...")
        # TODO Нужно для тестов, чтобы не крутить все комплексы
        complex_urls = get_complex_links(page)
        # complex_urls = complex_urls[:3]  # берем только первые 10 ЖК
        for idx, url in enumerate(complex_urls, start=1):
            print(f"[{idx}/{len(complex_urls)}] Обрабатываем {url}")
            time.sleep(random.uniform(1, 3))
            try:
                general, units = parse_complex(page, url)
                save_to_db(db, general, units)
                print(f"Данные для «{general.get('name', url)}» сохранены.")
                time.sleep(random.uniform(1, 2))
            except Exception as e:
                print(f"Ошибка при обработке {url}: {e}")
                continue
        print("Парсинг завершён.")
        browser.close()

if __name__ == "__main__":
    try:
        main(LOGIN_NMARKET, PASSWORD_NMARKET)
    except KeyboardInterrupt:
        print("Парсинг прерван пользователем.")
        sys.exit(0)
