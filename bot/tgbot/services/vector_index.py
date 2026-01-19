import os
import sys
import sqlite3
from typing import Iterable, List, Tuple

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    PyPDFLoader,
    UnstructuredWordDocumentLoader,
    UnstructuredExcelLoader,
    TextLoader,
)

from dotenv import load_dotenv
load_dotenv()


def _connect(db_path: str) -> sqlite3.Connection:
    return sqlite3.connect(db_path)


def load_lectures_documents(db_path_audio: str) -> List[Document]:
    """
    Извлекает лекции из БД audio_files (поля: file_name, audio_text)
    и преобразует их в список Document c метаданными.
    """
    if not os.path.exists(db_path_audio):
        return []

    conn = _connect(db_path_audio)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT file_name, audio_text FROM audio_files")
        rows: List[Tuple[str, str]] = cursor.fetchall()
    finally:
        conn.close()

    documents: List[Document] = []
    for file_name, audio_text in rows:
        if not audio_text:
            continue
        title = str(file_name).rsplit(".", 1)[0]
        metadata = {
            "segment": "lectures",
            "title": title,
            "source": file_name,
            "table": "audio_files",
            "row_id": None,
        }
        documents.append(Document(page_content=audio_text, metadata=metadata))
    return documents


def load_real_estate_documents(db_path_nmarket: str) -> List[Document]:
    """
    Извлекает сведения о ЖК/квартирах из nmarket.db (таблицы complexes и units)
    и формирует текстовые описания для индексации.
    Даже если у ЖК нет квартир, он всё равно попадет в документы.
    """
    if not os.path.exists(db_path_nmarket):
        return []

    conn = _connect(db_path_nmarket)
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT 
                c.id,
                c.name,
                c.url,
                c.address,
                c.developer,
                c.floor_count,
                c.status,
                c.key_issue,
                c.parking,
                c.ceiling_height,
                c.finishing,
                c.contract_type,
                c.building_type,
                c.registration,
                c.payment_options,
                c.units_total,
                u.unit_type,
                u.building,
                u.section,
                u.floor,
                u.apartment_number,
                u.finishing,
                u.total_area,
                u.living_area,
                u.kitchen_area,
                u.price_full,
                u.price_per_m2,
                u.price_base
            FROM complexes c
            LEFT JOIN units u ON u.complex_id = c.id
            """
        )
        rows = cursor.fetchall()
    finally:
        conn.close()

    documents: List[Document] = []
    for (
        complex_id,
        name,
        building_url,
        address,
        developer,
        floor_count,
        status,
        key_issue,
        parking,
        ceiling_height,
        building_finishing,
        contract_type,
        building_type,
        registration,
        payment_options,
        units_total,
        unit_type,
        building,
        section,
        floor,
        apartment_number,
        floor_finishing,
        total_area,
        living_area,
        kitchen_area,
        price_full,
        price_per_m2,
        price_base,
    ) in rows:
        # Подчищаем None → ""
        def safe(v): return str(v) if v is not None else ""

        text_lines = [
            f"Название ЖК: {safe(name)}",
            f"Ссылка на жк: {safe(building_url)}",
            f"Адрес: {safe(address)}",
            f"Застройщик: {safe(developer)}",
            f"Этажность: {safe(floor_count)}",
            f"Срок сдачи квартир: {safe(status)}",
            f"Срок выдачи ключей: {safe(key_issue)}",
            f"Паркинг: {safe(parking)}",
            f"Высота потолков: {safe(ceiling_height)}",
            f"Отделка в ЖК: {safe(building_finishing)}",
            f"Тип договора: {safe(contract_type)}",
            f"Тип дома: {safe(building_type)}",
            f"Регион/город: {safe(registration)}",
            f"Тип оплаты: {safe(payment_options)}",
            f"Доступно квартир в ЖК: {safe(units_total)}",
            f"Корпус: {safe(building)}, секция: {safe(section)}, этаж: {safe(floor)}, кв: {safe(apartment_number)}",
            f"Отделка в квартире: {safe(floor_finishing)}",
            f"Тип квартиры: {safe(unit_type)}, Общая площадь: {safe(total_area)} м², Площадь кухни: {safe(kitchen_area)} м², Жилая площадь: {safe(living_area)} м²",
            f"Полная цена: {safe(price_full)}",
            f"Цена за кв.метр: {safe(price_per_m2)}",
            f"Базовая цена: {safe(price_base)}"
        ]
        content = "\n".join([x for x in text_lines if x.strip()])

        if not content.strip():
            continue  # пропускаем совсем пустые

        metadata = {
            "segment": "real_estate",
            "table": "complexes_units",
            "row_id": int(complex_id) if complex_id is not None else None,
            "title": name,
            "url": building_url,
        }
        documents.append(Document(page_content=content, metadata=metadata))

    # Логируем для отладки
    print(f"[RealEstate] Собрано документов: {len(documents)}")

    return documents



def chunk_documents(documents: List[Document], chunk_size: int = 800, chunk_overlap: int = 100) -> List[Document]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunks = splitter.split_documents(documents)
    # Фильтруем пустые куски
    chunks = [d for d in chunks if d.page_content and d.page_content.strip()]
    return chunks


def upsert_to_faiss(chunks: List[Document], index_dir: str) -> None:
    vector_index_path = index_dir
    os.makedirs(vector_index_path, exist_ok=True)

    index_file = os.path.join(vector_index_path, "index.faiss")
    pkl_file = os.path.join(vector_index_path, "index.pkl")

    # более дешёвая и быстрая модель эмбеддингов
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

    batch_size = 128  # безопасный размер партии

    if os.path.exists(index_file) and os.path.exists(pkl_file):
        vectordb = FAISS.load_local(
            str(vector_index_path),
            embeddings,
            allow_dangerous_deserialization=True,
        )
        for i in range(0, len(chunks), batch_size):
            vectordb.add_documents(chunks[i:i+batch_size])
    else:
        # создаём индекс с первой партией, затем дозаливаем
        first = chunks[:batch_size] if chunks else []
        if not first:
            return
        vectordb = FAISS.from_documents(first, embeddings)
        for i in range(batch_size, len(chunks), batch_size):
            vectordb.add_documents(chunks[i:i+batch_size])

    vectordb.save_local(str(vector_index_path))


def build_vector_index_from_sqlite(
    db_path_audio: str,
    db_path_nmarket: str,
    index_dir: str,
    include_lectures: bool = True,
    include_real_estate: bool = True,
) -> None:
    """
    Главная функция построения индекса: собирает документы из SQLite, чанкует и апсеррит их в FAISS.
    """
    documents: List[Document] = []
    if include_lectures:
        documents.extend(load_lectures_documents(db_path_audio))
    if include_real_estate:
        documents.extend(load_real_estate_documents(db_path_nmarket))

    if not documents:
        return

    chunks = chunk_documents(documents)
    upsert_to_faiss(chunks, index_dir)

def load_documents_from_path(path: str) -> List[Document]:
    ext_local = os.path.splitext(path)[1].lower()
    print(f"[LOAD] Загружаем документы из {path} (тип {ext_local})")

    if ext_local == ".pdf":
        loader_local = PyPDFLoader(path)
        return loader_local.load()
    elif ext_local in [".doc", ".docx"]:
        loader_local = UnstructuredWordDocumentLoader(path)
        return loader_local.load()
    elif ext_local in [".xlsx", ".xls"]:
        loader_local = UnstructuredExcelLoader(path)
        return loader_local.load()
    elif ext_local == ".txt":
        loader_local = TextLoader(path)
        return loader_local.load()
    elif ext_local in [".db", ".sqlite"]:
        docs: List[Document] = []
        try:
            loaded = load_lectures_documents(path)
            print(f"[LOAD] Найдено {len(loaded)} лекций")
            docs.extend(loaded)
        except Exception as e:
            print(f"[LOAD] Ошибка при загрузке лекций: {e}")
        try:
            loaded = load_real_estate_documents(path)
            print(f"[LOAD] Найдено {len(loaded)} объектов недвижимости")
            docs.extend(loaded)
        except Exception as e:
            print(f"[LOAD] Ошибка при загрузке недвижимости: {e}")
        if not docs:
            raise ValueError("В SQLite не найдены поддерживаемые таблицы (audio_files, complexes/units)")
        return docs
    else:
        raise ValueError(f"Неподдерживаемый формат файла {ext_local}")


def create_index_from_file(
    file_path,
    vector_dir: str,
    model: str = "text-embedding-3-small",
    chunk_size: int = 500,
    chunk_overlap: int = 100,
) -> None:
    """
    Создаёт/обновляет индекс FAISS на основе одного или нескольких путей.
    Поддерживаемые форматы: .db/.sqlite, .pdf, .doc/.docx, .xlsx/.xls, .txt
    """


    # Нормализуем вход в список путей
    paths: List[str] = file_path if isinstance(file_path, list) else [file_path]

    # Подготовка каталога индекса
    vector_index_path = vector_dir
    os.makedirs(vector_index_path, exist_ok=True)
    index_file = os.path.join(vector_index_path, "index.faiss")
    pkl_file = os.path.join(vector_index_path, "index.pkl")

    embeddings = OpenAIEmbeddings(model=model)
    batch_size = 128

    # Ленивая инициализация индекса
    vectordb = None
    if os.path.exists(index_file) and os.path.exists(pkl_file):
        print(f"[INDEX] Загружаем существующий индекс из {vector_index_path}")
        vectordb = FAISS.load_local(
            str(vector_index_path), embeddings, allow_dangerous_deserialization=True
        )

    # Обрабатываем каждый путь: load → split → filter/meta → upsert
    for path in paths:
        documents: List[Document] = load_documents_from_path(path)
        print(f"[INDEX] Загружено документов: {len(documents)} из {path}")

        splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        chunks = splitter.split_documents(documents)
        print(f"[INDEX] Разбито на чанки: {len(chunks)}")

        filename = os.path.basename(path)
        filtered: List[Document] = []
        for ch in chunks:
            if not ch.page_content or not ch.page_content.strip():
                continue
            # сохраняем метаданные и расширяем новыми
            ch.metadata = ch.metadata or {}
            ch.metadata.update({
                "source": filename,
                "file_path": path,
            })
            filtered.append(ch)

        print(f"[INDEX] После фильтрации: {len(filtered)} чанков")

        if not filtered:
            print(f"[INDEX] Пропущено, так как нет валидных чанков для {path}")
            continue

        if vectordb is None:
            print(f"[INDEX] Создаём новый FAISS-индекс с {len(filtered)} чанками")
            first = filtered[:batch_size]
            vectordb = FAISS.from_documents(first, embeddings)
            for i in range(batch_size, len(filtered), batch_size):
                batch = filtered[i:i+batch_size]
                print(f"[INDEX] Добавляем {len(batch)} чанков в индекс")
                vectordb.add_documents(batch)
        else:
            for i in range(0, len(filtered), batch_size):
                batch = filtered[i:i+batch_size]
                print(f"[INDEX] Добавляем {len(batch)} чанков в существующий индекс")
                vectordb.add_documents(batch)

    if vectordb:
        vectordb.save_local(str(vector_index_path))
        print(f"[INDEX] Индекс сохранён в {vector_index_path}")
    else:
        print("[INDEX] Ничего не сохранено: индекс пустой")



if __name__ == "__main__":
    BASE_DIR = os.path.dirname(__file__)
    AUDIO_DB_PATH = os.path.join(BASE_DIR, "databases", "downloaded_audio.db")
    BUILDS_DB_PATH = os.path.join(BASE_DIR, "databases", "nmarket.db")
    VECTOR_DP_PATH = os.path.join(BASE_DIR, "vector_index")

    # files = [AUDIO_DB_PATH, BUILDS_DB_PATH]
    files = [BUILDS_DB_PATH, AUDIO_DB_PATH]
    create_index_from_file(files, str(VECTOR_DP_PATH))
    print(f"Индекс обновлён: {VECTOR_DP_PATH}")
