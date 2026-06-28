# Деплой живого демо на Streamlit Community Cloud

Бесплатный хостинг для Streamlit-приложений: [share.streamlit.io](https://share.streamlit.io)

## 1. Подготовка (уже в репозитории)

- `streamlit_app.py` — точка входа для облака
- `requirements.txt` — зависимости
- `.streamlit/config.toml` — тема и настройки
- `.streamlit/secrets.toml.example` — шаблон секретов

## 2. Создание приложения

1. Откройте [share.streamlit.io](https://share.streamlit.io) и войдите через **GitHub**
2. Нажмите **Create app**
3. Заполните:
   - **Repository:** `PavelKoff2025/ResumeScore`
   - **Branch:** `main`
   - **Main file path:** `streamlit_app.py`
4. **Advanced settings → Python version:** `3.11`
5. Нажмите **Deploy**

Первый деплой займёт 2–5 минут.

## 3. Secrets (обязательно для ИИ)

**App settings → Secrets** и вставьте (шаблон: `.streamlit/secrets.toml.example`):

```toml
DEEPSEEK_API_KEY = "sk-ваш-ключ"
LLM_PROVIDER = "deepseek"
APP_BASE_URL = "https://resumescore-zjgmnauufoxcdnmuqsfu4d.streamlit.app"
```

После сохранения нажмите **Reboot app**. Локальный `.env` на Streamlit Cloud **не используется** — только Secrets.

Без ключей приложение работает в **демо-режиме** с тестовыми данными.

## 4. Проверка

- Откройте [живое демо](https://resumescore-zjgmnauufoxcdnmuqsfu4d.streamlit.app/)
- В sidebar: **«Загрузить демо-данные»** → **«Анализировать»**
- Или вставьте ссылку hh.ru

## 5. Обновления

Каждый `git push` в `main` автоматически пересобирает приложение.

## Альтернативы

| Платформа | Когда использовать |
|-----------|-------------------|
| **Streamlit Cloud** | Бесплатное демо, проще всего |
| **Render / Railway** | Больше контроля, свой домен |
| **GitHub Pages** | Только документация (не Streamlit) |
