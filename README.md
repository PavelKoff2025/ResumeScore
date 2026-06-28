# ResumeScore

Многоагентное веб-приложение для автоматического сопоставления резюме и вакансий с выдачей рекомендаций.

## Архитектура

```
Пользователь → Frontend-агент → Orchestrator → Backend-агент → LLM API
                    ↑                  ↓                ↓
                    └──────────────────┴────────────────┘
```

| Агент | Файл | Ответственность |
|-------|------|-----------------|
| Frontend | `agents/frontend_agent.py` | UI/UX, формы, визуализация |
| Orchestrator | `agents/orchestrator.py` | Координация workflow, история |
| Backend | `agents/backend_agent.py` | LLM, парсинг, валидация |

## Быстрый старт

```bash
cd ResumeScore
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # добавьте OPENAI_API_KEY
streamlit run app.py
```

Приложение откроется в браузере на `http://localhost:8501`.

## Демо-режим

Если `OPENAI_API_KEY` не задан, приложение работает в **демо-режиме** с тестовыми данными:
- Вакансия: «Специалист по промпт-инжинирингу и ИИ-разработке (Vibe Coding)»
- Резюме: «Резюме_PI_VC.pdf»

Нажмите **«Загрузить демо-данные»** в боковой панели.

## Возможности

- Загрузка вакансии и резюме (текст или PDF/DOCX)
- Анализ через OpenAI / YandexGPT
- Статусы агентов в реальном времени
- Прогресс-бар совпадения, таблица 🟢🟡🔴
- Топ-3 рекомендации с чекбоксами
- История последних 5 анализов
- Экспорт JSON / PDF
- Светлая и тёмная тема
- Кнопка «Отмена»

## Структура проекта

```
ResumeScore/
├── app.py
├── agents/
│   ├── orchestrator.py
│   ├── backend_agent.py
│   └── frontend_agent.py
├── core/
│   ├── config.py
│   ├── prompts.py
│   ├── schemas.py
│   └── demo_data.py
├── utils/
├── storage/
├── ui/
├── logs/
└── tests/
```

## Логи

- `logs/orchestrator.log` — оркестратор
- `logs/backend.log` — backend-агент
- `logs/frontend.log` — frontend-агент

## Тесты

```bash
pytest tests/ -v
```

## Переменные окружения

| Переменная | Описание |
|------------|----------|
| `OPENAI_API_KEY` | Ключ OpenAI API |
| `OPENAI_MODEL` | Модель (по умолчанию `gpt-4o-mini`) |
| `DEEPSEEK_API_KEY` | Ключ DeepSeek — **работает без VPN** |
| `DEEPSEEK_MODEL` | Модель DeepSeek (по умолчанию `deepseek-chat`) |
| `LLM_PROVIDER` | `openai`, `deepseek` или `yandex` |
| `YANDEX_API_KEY` | Ключ Yandex Cloud |
| `YANDEX_FOLDER_ID` | ID каталога Yandex Cloud |

### DeepSeek без VPN

Если OpenAI недоступен, достаточно добавить в `.env`:

```
DEEPSEEK_API_KEY=sk-...
```

Приложение **автоматически переключится на DeepSeek**, даже если `LLM_PROVIDER=openai`.
Явное указание: `LLM_PROVIDER=deepseek`.
