import random
import sys
import subprocess
import time
from typing import Dict, List, Optional, Tuple

from playwright.sync_api import Browser, Page, sync_playwright
from bot.tgbot.databases.database import DatabaseConnection

DB_PATH = "tradeagent.db"

def init_db(db_path: str = DB_PATH):
    """Создаёт таблицы в БД."""
    db = DatabaseConnection(db_path, schema=None)
    
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


def ensure_no_city_popup(page: Page) -> None:
    """Закрывает оверлей выбора города/попап, если он перекрывает клики."""
    try:
        overlay = page.locator("#navbar .popup__overlay_opened, #navbar .countries__content").first
        if overlay.count() > 0 and overlay.is_visible():
            close_btn = page.locator("#navbar button.btn_clear.btn_onlyicon").first
            if close_btn.count() > 0:
                close_btn.click()
                try:
                    overlay.wait_for(state="detached", timeout=5000)
                except Exception:
                    pass
    except Exception:
        pass

def login(page: Page, username: str, password: str) -> None:
    """Выполняет вход на сайт TrendAgent."""
    page.goto("https://sso.trendagent.ru/login", wait_until="domcontentloaded")
    try:
        page.locator("text=Принять все файлы cookie").click(timeout=3000)
    except Exception:
        pass
    page.locator("text=Войти").first.click()
    page.wait_for_load_state("domcontentloaded")
    page.locator("input[placeholder='+7 000 000 00 00']").fill(username)
    page.locator("input[placeholder='Пароль']").fill(password)
    page.locator("button:has-text('Войти')").click()
    # page.wait_for_load_state("domcontentloaded")
    page.wait_for_load_state("networkidle")


def get_complex_links(page: Page) -> List[str]:
    """
    Возвращает список URL-адресов всех комплексов со всех страниц выдачи.
    """
    time.sleep(random.uniform(1, 3))
    LISTING_URL = "https://ekb.trendagent.ru/objects/list/?apartments-premiseType=apartment"
    try:
        page.goto(LISTING_URL, wait_until="commit")
    except:
        page.goto(LISTING_URL, wait_until="domcontentloaded")

    if "ekb.trendagent.ru" not in page.url:
        page.goto(LISTING_URL, wait_until="domcontentloaded")

    ensure_no_city_popup(page)

    try:
        page.locator("text=Подписать и продолжить").click(timeout=3000)
    except Exception:
        pass


    urls: set[str] = set()

    # TODO Нужно для тестов, чтобы не собирать все ссылки
    # while len(urls)<20:
    while True:
        links = page.locator("a.objects-list__item[href*='/object/']")
        count = links.count()
        
        for i in range(count):
            href = links.nth(i).get_attribute("href")
            if href:
                url = href if href.startswith("http") else "https://ekb.trendagent.ru" + href
                urls.add(url)

        next_btn = page.locator("button:has-text('Следующая')").first
        
        try:
            if next_btn.is_visible():
                next_btn.click()
                page.wait_for_load_state("domcontentloaded")
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


    page.goto(complex_url, wait_until="domcontentloaded")

    try:
        element = page.locator("h1")
        text = element.inner_text()
        general_info["name"] = text
    except Exception:
        pass

    label_map = {
        "Застройщик": "developer",
        "Старт продаж": "status",
        "Срок передачи ключей": "key_issue",
        "Паркинг": "parking",
        "Отделка": "finishing",
        "Договор": "contract_type",
        "Тип дома": "building_type",
        "Оплата": "payment_options",
        "Всего в продаже": "units_total",
    }

    rows = page.locator("div.object-passport__row")
    for i in range(rows.count()):
        row = rows.nth(i)
        label = row.locator(".object-passport__name").inner_text().strip()
        value = row.locator(".object-passport__text").inner_text().strip()
        if label in label_map:
            general_info[label_map[label]] = value

    try:
        address = page.locator("div.object-address__info").first.text_content().strip()
        general_info["address"] = address
    except Exception:
        pass

    try:
        description = page.locator("div.object-about__description").first.text_content().strip()
        general_info["description"] = description
    except Exception:
        pass


    try:
        page.locator("a.object-navigation__item[href='#apartments']").click()
        phases = page.locator("div.page-layout__col--full > div.page-layout__row")
        units: List[Dict[str, Optional[str]]] = []
        for i in range(1, phases.count()):
            # print(f'Очередь: {i}')
            phase = phases.nth(i)
            groups = phase.locator("div.object-apartments__row")

            for g in range(groups.count()):
                # print(f'Группа: {g+1}')
                group = groups.nth(g)
                unit_type_for_group = group.locator("div.col").first.inner_text().strip()
                try:
                    ensure_no_city_popup(page)

                    group.scroll_into_view_if_needed()
                    try:
                        group.click(timeout=2000)
                    except Exception:
                        group.click(force=True, timeout=2000)

                    rows = group.locator(":scope + div.scrollable-table .table-body .table-row")
                    try:
                        rows.first.wait_for(state="visible", timeout=10000)
                    except Exception:
                        rows = group.locator(":scope ~ div.scrollable-table .table-body .table-row")
                        rows.first.wait_for(state="visible", timeout=10000)
                    
                    for r in range(rows.count()):
                        # print(f'Строка: {r+1}')
                        row = rows.nth(r)
                        try:
                            cells = row.locator("td.table-cell")
                            cells.first.wait_for(state="visible", timeout=5000)

                            unit_type = unit_type_for_group
                            building = cells.nth(1).inner_text().strip() if cells.count() > 0 else None
                            section = cells.nth(2).inner_text().strip() if cells.count() > 1 else None
                            floor = cells.nth(3).inner_text().strip() if cells.count() > 2 else None
                            apartment_number = cells.nth(4).inner_text().strip() if cells.count() > 3 else None
                            total_area = cells.nth(5).inner_text().strip() if cells.count() > 4 else None
                            kitchen_area = cells.nth(6).inner_text().strip() if cells.count() > 5 else None
                            finishing = cells.nth(7).inner_text().strip() if cells.count() > 6 else None
                            price_base = cells.nth(8).inner_text().strip() if cells.count() > 7 else None
                            price_full = cells.nth(9).inner_text().strip() if cells.count() > 8 else None
                            price_per_m2 = cells.nth(10).inner_text().strip() if cells.count() > 9 else None
                            living_area = None

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
                            # print(f'{unit_data=}')
                            units.append(unit_data)
                        except Exception as e:
                            print(f"      Ошибка при обработке строки {r + 1} в группе {g + 1}: {e}")
                            continue
                except Exception as e:
                    print(f"    Ошибка при обработке группы {g + 1}: {e}")
                    continue
    except Exception as e:
        print("Ошибка при сборе данных:", e)


    # print(f'{general_info=}')
    # print(f'{units=}')
    return general_info, units


def save_to_db(db: DatabaseConnection,
               general: Dict[str, Optional[str]],
               units: List[Dict[str, Optional[str]]]) -> None:
    """Сохраняет данные ЖК и квартир в БД."""
    # Вставляем или обновляем комплекс
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
        # browser: Browser = p.chromium.launch(headless=True)
        browser: Browser = p.chromium.launch(headless=False, slow_mo=1000)
        context = browser.new_context()
        page = context.new_page()
        print("Вход на сайт...")
        login(page, username, password)
        time.sleep(random.uniform(1, 3))
        print("Авторизация прошла успешно. Получаем список комплексов...")
        complex_urls = get_complex_links(page)
        # TODO Нужно для тестов, чтобы не крутить все комплексы
        # complex_urls = complex_urls[:1]
        for idx, url in enumerate(complex_urls, start=1):
            print(f"[{idx}/{len(complex_urls)}] Обрабатываем {url}")
            time.sleep(random.uniform(1, 3))  
            try:
                general, units = parse_complex(page, url)
                save_to_db(db, general, units)
                print(f"Данные для «{general.get('name', url)}» сохранены.")
            except Exception as e:
                print(f"Ошибка при обработке {url}: {e}")
                continue
        print("Парсинг завершён.")
        browser.close()

if __name__ == "__main__":
    try:
        main("+79634450770", "VHYh8VY")
    except KeyboardInterrupt:
        print("Парсинг прерван пользователем.")
        sys.exit(0)
