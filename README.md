# 🎯 ResumeScore

**Умное сопоставление резюме и вакансий на базе LLM — за минуту вместо часов ручной проверки.**

ResumeScore — это портфолио-проект и рабочий инструмент для соискателей: загрузите резюме и вакансию (текст, PDF, DOCX или **ссылку с hh.ru**) и получите процент совпадения, разбор по требованиям, рекомендации и готовые материалы для отклика.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Live Demo](https://img.shields.io/badge/🚀_Live_Demo-Streamlit-FF4B4B)](https://resumescore-zjgmnauufoxcdnmuqsfu4d.streamlit.app/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-36%20passed-brightgreen)](#тесты)

**▶️ [Открыть живое демо](https://resumescore-zjgmnauufoxcdnmuqsfu4d.streamlit.app/)** — без установки, прямо в браузере.

---

## ✨ Зачем это нужно

| Боль | Решение ResumeScore |
|------|---------------------|
| «Подхожу ли я на вакансию?» | **Match %** и цветовая матрица 🟢🟡🔴 |
| «Что дописать в резюме?» | Топ-3 действия + **чек-лист** «сделано / не сделано» |
| «Куда откликаться в первую очередь?» | **Сравнение нескольких вакансий** |
| «Сколько платят на рынке?» | Медиана зарплаты с **hh.ru** |
| «Нужно письмо и PDF» | **ИИ-письмо**, экспорт PDF, **QR-код** для телефона |

---

## 🚀 Быстрый старт

```bash
git clone https://github.com/PavelKoff2025/ResumeScore.git
cd ResumeScore
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # добавьте DEEPSEEK_API_KEY или OPENAI_API_KEY
streamlit run app.py
```

Откройте **http://localhost:8501** → в боковой панели **«Загрузить демо-данные»** или вставьте ссылку `https://hh.ru/vacancy/…`.

### 🌐 Живое демо (Streamlit Cloud)

**https://resumescore-zjgmnauufoxcdnmuqsfu4d.streamlit.app/**

Инструкция по деплою: **[DEPLOY.md](DEPLOY.md)**

### DeepSeek без VPN (рекомендуется для РФ)

```env
DEEPSEEK_API_KEY=sk-...
```

Приложение автоматически выберет DeepSeek, если OpenAI недоступен.

---

## 🧠 Архитектура: 3 агента

```
Пользователь → Frontend-агент → Orchestrator → Backend-агент → LLM API
                    ↑                  ↓                ↓
                    └──────────────────┴────────────────┘
```

| Агент | Файл | Роль |
|-------|------|------|
| **Frontend** | `agents/frontend_agent.py` | UI, формы, WOW-визуализации |
| **Orchestrator** | `agents/orchestrator.py` | Pipeline, история, шаринг |
| **Backend** | `agents/backend_agent.py` | LLM, парсинг, валидация |

Поддерживаемые провайдеры: **OpenAI**, **DeepSeek**, **YandexGPT**, **демо-режим**.

---

## 📦 Возможности

### Основное
- Загрузка **PDF / DOCX / TXT** (вакансия и резюме)
- Импорт вакансии по **ссылке hh.ru** (API + парсинг страницы)
- Анализ с live-статусом агентов и прогресс-баром
- Разбор по каждому требованию: доказательство из резюме + рекомендация
- **Улучшение резюме** и **сопроводительное письмо** через ИИ
- Экспорт **PDF / JSON**, копирование отчёта в буфер

### Портфолио
- Сравнение **нескольких вакансий** с одним резюме
- Чек-лист рекомендаций с прогрессом
- **История анализов** с датами и графиком прогресса
- **Поделиться ссылкой** на результат (`?share=…`)

### WOW-панель (для демо)
- 🗺 **Карта навыков** — интерактивный граф «есть / частично / нет»
- 💰 **Рынок** — медиана зарплаты по данным hh.ru
- 🎮 **Геймификация** — «Вы на 73% готовы, осталось 27%»
- 📱 **QR-код** — открыть результат на телефоне

---

## 🖼 Скриншоты

> Добавьте скриншоты в `docs/screenshots/` и раскройте ссылку здесь для README на GitHub.

---

## 📁 Структура

```
ResumeScore/
├── app.py                 # Точка входа Streamlit
├── agents/                # Frontend, Orchestrator, Backend
├── core/                  # Конфиг, промпты, схемы, демо-данные
├── utils/                 # Парсеры, hh.ru, валидация
├── storage/               # История, чек-лист, шаринг
├── ui/                    # Компоненты и стили
├── tests/                 # 36 unit-тестов
└── logs/                  # Логи агентов
```

---

## ⚙️ Переменные окружения

| Переменная | Описание |
|------------|----------|
| `OPENAI_API_KEY` | Ключ OpenAI |
| `DEEPSEEK_API_KEY` | DeepSeek (без VPN) |
| `LLM_PROVIDER` | `openai` · `deepseek` · `yandex` · `auto` |
| `APP_BASE_URL` | URL для share-ссылок (по умолчанию `http://localhost:8501`) |
| `MAX_HISTORY_ITEMS` | Размер истории (по умолчанию `20`) |

Полный список — в [`.env.example`](.env.example).

---

## 🧪 Тесты

```bash
pytest tests/ -v
```

---

## 🛣 Roadmap

- [x] Деплой на Streamlit Cloud — см. [DEPLOY.md](DEPLOY.md)
- [ ] Поддержка LinkedIn / Habr Career
- [ ] Английский интерфейс

---

## 📄 Лицензия

[MIT](LICENSE) © 2026 Pavel Koff

---

## ⭐ Если проект полезен

Поставьте **Star** на GitHub — так его проще показать рекрутеру или ментору как кейс в портфолио.
