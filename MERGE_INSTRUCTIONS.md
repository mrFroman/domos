# Инструкция по слиянию ветки main из вашего форка в оригинальный репозиторий

## Текущая конфигурация
- **origin**: https://github.com/mrFroman/domos.git (ваш форк)
- **upstream**: https://github.com/VoronchenkoNikolay/domos.git (оригинальный репозиторий)

## Шаги для слияния

### Вариант 1: Через командную строку (рекомендуется)

Выполните следующие команды в терминале из корня репозитория:

```bash
# 1. Убедитесь, что вы на ветке main
git checkout main

# 2. Получите последние изменения из вашего форка
git fetch origin

# 3. Получите последние изменения из оригинального репозитория
git fetch upstream

# 4. Слейте изменения из вашего origin/main в текущую ветку
git merge origin/main

# 5. Отправьте изменения в upstream
# ВНИМАНИЕ: Это сработает только если у вас есть права на запись в upstream
git push upstream main
```

### Вариант 2: Если нет прав на запись в upstream

Если команда `git push upstream main` не работает (ошибка доступа), вам нужно создать Pull Request:

1. Убедитесь, что ваши изменения запушены в ваш форк:
   ```bash
   git push origin main
   ```

2. Перейдите на GitHub: https://github.com/VoronchenkoNikolay/domos
3. Нажмите "New Pull Request"
4. Выберите base repository: `VoronchenkoNikolay/domos` (base: `main`)
5. Выберите head repository: `mrFroman/domos` (compare: `main`)
6. Создайте Pull Request

### Вариант 3: Использование скриптов

Я создал два скрипта для автоматизации:

**Для Linux/WSL:**
```bash
chmod +x merge_to_upstream.sh
./merge_to_upstream.sh
```

**Для Windows PowerShell:**
```powershell
.\merge_to_upstream.ps1
```

## Решение ошибки "non-fast-forward"

Если вы получили ошибку:
```
! [rejected]        main -> main (non-fast-forward)
error: failed to push some refs to 'https://github.com/VoronchenkoNikolay/domos.git'
hint: Updates were rejected because the tip of your current branch is behind
```

Это означает, что в `upstream/main` есть новые коммиты, которых нет в вашей локальной ветке. Нужно сначала интегрировать изменения из upstream:

```bash
# 1. Получить последние изменения из upstream
git fetch upstream

# 2. Слить изменения из upstream/main в вашу локальную ветку
# Вариант A: Merge (рекомендуется, сохраняет всю историю)
git pull upstream main --no-rebase

# ИЛИ Вариант B: Rebase (более чистая история)
git pull upstream main --rebase

# 3. Теперь можно пушить
git push upstream main
```

## Разрешение конфликтов

Если при слиянии возникнут конфликты:

1. Git покажет файлы с конфликтами
2. Откройте каждый файл и найдите маркеры конфликтов:
   ```
   <<<<<<< HEAD
   код из upstream
   =======
   код из origin/main
   >>>>>>> origin/main
   ```
3. Разрешите конфликты вручную
4. После разрешения всех конфликтов:
   ```bash
   git add .
   git commit -m "Merge upstream/main with origin/main"
   git push upstream main
   ```

Если использовали rebase и возникли конфликты:
```bash
# Разрешите конфликты в файлах
git add .
git rebase --continue
git push upstream main
```

## Проверка результата

После успешного слияния проверьте:
- https://github.com/VoronchenkoNikolay/domos - должны появиться ваши изменения
- Все коммиты из вашего форка должны быть в истории upstream

