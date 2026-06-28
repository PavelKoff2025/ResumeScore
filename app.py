"""Точка входа ResumeScore — запуск Frontend-агента."""

from agents.frontend_agent import FrontendAgent


def main() -> None:
    """Запускает Streamlit-приложение."""
    FrontendAgent().render()


if __name__ == "__main__":
    main()
