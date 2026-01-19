from typing import Optional

import pandas as pd
import gspread
from gspread.worksheet import Worksheet
import time
from google.oauth2.service_account import Credentials
import openpyxl
import requests
from openpyxl.styles import PatternFill
import traceback
from pathlib import Path
PATH_START = str(Path(__file__).parents[2])




def main():
    
    # Список_адресов (список адресов/база)
    
    url = 'https://docs.google.com/spreadsheets/d/13TIqojy2J-6BhPhLUy78gswZHH8USQl4dsK0otKtKMM/edit?gid=0#gid=0'
    worksheet = get_worksheet_by_url(url=url)
    data = worksheet.get_all_values()

    # Проверяем первую строку на пустоту
    if not any(data[0]):
        data = data[1:]  # Пропускаем первую строку

    # Создаем DataFrame
    address_base_df = pd.DataFrame(data[1:], columns=data[0])
    address_base_df = address_base_df.iloc[:, 1:]

# Удаляем вторую строку (если она содержит техническую информацию)
    address_base_df = address_base_df.drop(1).reset_index(drop=True)
     # Сбрасываем индексы
    address_base_df.columns = address_base_df.iloc[0]  # Берем первую строку как заголовки
    address_base_df = address_base_df.iloc[1:]
    #print(address_base_df)
# Функция преобразования строки в Markdown
    def row_to_md(row):
        bank_name = row.iloc[0]  # Название банка
        conditions = []
        for col_name, value in row.iloc[1:].items():
            if pd.notna(value):  # Только непустые значения
                conditions.append(f"- {col_name}: {value}")
        return f" {bank_name}\n" + "\n".join(conditions)

    # Генерация Markdown
    md_content = "Условия кредитования в банках\n\n"
    for _, row in address_base_df.iterrows():
        md_content += row_to_md(row) + "\n\n"

    # Сохранение
    with open(f"{PATH_START}/converted_docs/bank_credits.md", "w", encoding="utf-8") as f:
        f.write(md_content)

    """url = 'https://docs.google.com/spreadsheets/d/1QilOIpu6eHajeN-wZy0a_JyxkZNzVz2h2D5SJHRY6qw/edit?gid=1794356355#gid=1794356355'
    worksheet = get_worksheet_by_url(url=url)
    data = worksheet.get_all_values()

    # Проверяем первую строку на пустоту
    if not any(data[0]):
        data = data[1:]  # Пропускаем первую строку

    # Создаем DataFrame
    df = pd.DataFrame(data[1:], columns=data[0])
    df = df.iloc[:, 1:]

# Удаляем вторую строку (если она содержит техническую информацию)
    df = df.drop(1).reset_index(drop=True)
     # Сбрасываем индексы
    df.columns = df.iloc[0]  # Берем первую строку как заголовки
    df = df.iloc[1:]
    print(df)
# Функция преобразования строки в Markdown
    def row_to_md(row):
        bank_name = row.iloc[0]  # Название банка
        conditions = []
        for col_name, value in row.iloc[1:].items():
            if pd.notna(value):  # Только непустые значения
                conditions.append(f"- {col_name}: {value}")
        return f" {bank_name}\n" + "\n".join(conditions)

    # Генерация Markdown
    md_content1 = "информация о новостройках\n\n"
    for _, row in df.iterrows():
        md_content1 += row_to_md(row) + "\n\n"""

    # Сохранение
    #with open(f"{PATH_START}/converted_docs/newhouses.md", "w", encoding="utf-8") as f:
        #f.write(md_content1)
    url = 'https://docs.google.com/spreadsheets/d/1QilOIpu6eHajeN-wZy0a_JyxkZNzVz2h2D5SJHRY6qw/edit?gid=1794356355#gid=1794356355'
    worksheet = get_worksheet_by_url(url=url)
    data = worksheet.get_all_values()
    df = pd.DataFrame(data[1:], columns=data[0])  # первая строка — названия колонок

    # 2) Удаляем первые 3 строки после заголовка
    df = df.iloc[3:].reset_index(drop=True)

    # 3) Объединяем первые два столбца в один: project_name
    col1 = df.iloc[:, 0].fillna('').astype(str).str.strip()
    col2 = df.iloc[:, 1].fillna('').astype(str).str.strip()

    # Формируем единое имя проекта
    df['project_name'] = col1 + ' — ' + col2
    df = df.drop(df.columns[[0, 1]], axis=1)

    # 4) Генерация Markdown
    def row_to_md(row: pd.Series) -> str:
        lines = [f"## {row['project_name']}"]
        for col, val in row.drop('project_name').items():
            if pd.notna(val) and str(val).strip():
                lines.append(f"- {col}: {val}")
        return "\n".join(lines)

    md_lines = ["# Информация о новостройках\n"]
    for _, row in df.iterrows():
        md_lines.append(row_to_md(row))
        md_lines.append("")  # пустая строка между записями

    # 5) Сохраняем в файл
    with open(f"{PATH_START}/converted_docs/newhouses.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))
    #address_base_df.to_excel(f"{PATH_START}/325.xlsx", index=False)

    # df[''] = df['Исходный_адрес'].astype(str)
    # df['RestorauntGroup1'] = df['Нормал_Адрес'].astype(str)
    # df['id'] = df['ID_точки']
    # f = df[['RestorauntGroup', 'RestorauntGroup1', 'id']]
    # df.to_excel(f"{path}/322.xlsx", index=False)

    

        # Список_адресов (словарь адресов)
        




def get_worksheet_by_url(url: str, sheet_name: Optional[str] = None) -> Worksheet:
    """
    Возвращает объект Worksheet по переданному URL Google-таблицы.
    Если sheet_name не указан, возвращается первый лист (sheet1).

    :param url: Полная ссылка на Google-таблицу (spreadsheet).
    :param sheet_name: Название листа, если нужно выбрать конкретный (или None для первого листа).
    :return: Worksheet (лист Google-таблицы).
    """
    path_to_json = f"{PATH_START}/tgbot/services/service_account.json"
    scopes = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_file(path_to_json, scopes=scopes)
    gc = gspread.authorize(creds)
    sh = gc.open_by_url(url)
    if sheet_name:
        return sh.worksheet(sheet_name)
    return sh.sheet1




if __name__ == "__main__":
    main()