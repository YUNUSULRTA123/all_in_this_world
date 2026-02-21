# all_in_this_world

## Что умеет бот
- Отвечает на частые вопросы через `/faq` и поиск по тексту сообщения.
- Принимает обращения к специалистам через `/specialist` (текст и голос).
- Сохраняет обращения в отдельную таблицу `specialist_requests`.

## Команды пользователя
- `/start` - приветствие и меню.
- `/help` - список команд.
- `/faq` - список вопросов FAQ.
- `/faq <вопрос>` - поиск ответа в FAQ.
- `/specialist` - создание обращения к специалисту.

## База данных
Файл базы: `data.db`.

### Таблица FAQ
Таблица: `faq`
- `question` (TEXT)
- `answer` (TEXT)
- `keywords` (TEXT, ключевые слова через запятую)

### Таблица обращений к специалистам
Таблица: `specialist_requests`
- `id` (INTEGER, PK, AUTOINCREMENT)
- `user_id` (INTEGER, Telegram ID пользователя)
- `username` (TEXT)
- `full_name` (TEXT)
- `message_type` (TEXT: `text` или `voice`)
- `message_text` (TEXT, текст обращения)
- `voice_file_id` (TEXT, ID голосового файла Telegram)
- `status` (TEXT, по умолчанию `new`)
- `created_at` (TEXT, дата/время создания, UTC SQLite)

## Операции администратора
Примеры запросов к SQLite:

```sql
-- Все новые обращения
SELECT id, user_id, username, full_name, message_type, message_text, voice_file_id, created_at
FROM specialist_requests
WHERE status = 'new'
ORDER BY created_at DESC;

-- Изменить статус обращения на "in_progress"
UPDATE specialist_requests
SET status = 'in_progress'
WHERE id = 1;

-- Закрыть обращение
UPDATE specialist_requests
SET status = 'closed'
WHERE id = 1;
```

## Запуск
1. Убедиться, что в `config.py` указан корректный `TOKEN`.
2. Запустить бота:

```bash
python main.py
```

При старте бот автоматически:
- создаёт таблицы `faq` и `specialist_requests`, если их нет;
- заполняет `faq`, если он пуст.
