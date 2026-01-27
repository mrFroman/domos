#!/bin/bash
# Скрипт для слияния ветки main из origin в upstream с учетом изменений в upstream

cd /home/mrfroman/Development/domos || exit 1

echo "=== Проверка текущей ветки ==="
current_branch=$(git branch --show-current)
echo "Текущая ветка: $current_branch"

if [ "$current_branch" != "main" ]; then
    echo "Переключение на ветку main..."
    git checkout main || exit 1
fi

echo ""
echo "=== Получение последних изменений из origin (ваш форк) ==="
git fetch origin || exit 1

echo ""
echo "=== Получение последних изменений из upstream (оригинальный репозиторий) ==="
git fetch upstream || exit 1

echo ""
echo "=== Проверка различий между ветками ==="
echo "Коммиты в origin/main, которых нет в upstream/main:"
git log upstream/main..origin/main --oneline || echo "Нет новых коммитов в origin/main"

echo ""
echo "Коммиты в upstream/main, которых нет в origin/main:"
git log origin/main..upstream/main --oneline || echo "Нет новых коммитов в upstream/main"

echo ""
echo "=== Слияние изменений из origin/main в текущую ветку ==="
git merge origin/main || {
    echo "Ошибка при слиянии origin/main. Возможно, есть конфликты."
    echo "Разрешите конфликты вручную и затем выполните:"
    echo "  git add ."
    echo "  git commit -m 'Merge origin/main'"
    echo "  git pull upstream main --rebase  # или git merge upstream/main"
    echo "  git push upstream main"
    exit 1
}

echo ""
echo "=== Интеграция изменений из upstream/main ==="
echo "Вариант 1: Merge (сохраняет историю коммитов)"
echo "Вариант 2: Rebase (более чистая история)"
read -p "Выберите вариант (1/2, по умолчанию 1): " merge_type
merge_type=${merge_type:-1}

if [ "$merge_type" = "2" ]; then
    echo "Используется rebase..."
    git pull upstream main --rebase || {
        echo "Ошибка при rebase. Возможно, есть конфликты."
        echo "Разрешите конфликты и выполните:"
        echo "  git rebase --continue"
        echo "  git push upstream main"
        exit 1
    }
else
    echo "Используется merge..."
    git pull upstream main --no-rebase || {
        echo "Ошибка при merge. Возможно, есть конфликты."
        echo "Разрешите конфликты вручную и затем выполните:"
        echo "  git add ."
        echo "  git commit -m 'Merge upstream/main'"
        echo "  git push upstream main"
        exit 1
    }
fi

echo ""
echo "=== Отправка изменений в upstream ==="
echo "ВНИМАНИЕ: Это отправит изменения в оригинальный репозиторий."
read -p "Продолжить отправку в upstream? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    git push upstream main || {
        echo ""
        echo "Ошибка при отправке. Возможно:"
        echo "1. У вас нет прав на запись в upstream"
        echo "2. Есть конфликты, которые нужно разрешить"
        echo ""
        echo "Если нет прав, создайте Pull Request через GitHub:"
        echo "https://github.com/VoronchenkoNikolay/domos/compare/main...mrFroman:domos:main"
        exit 1
    }
    echo ""
    echo "✅ Изменения успешно отправлены в upstream!"
else
    echo "Отправка отменена."
fi

