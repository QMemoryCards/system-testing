import pytest
from playwright.sync_api import Page, expect, Browser
import uuid
import re

FRONTEND_URL = "http://localhost:5173"
BACKEND_URL = "http://localhost:8080/api/v1"


def get_uid():
    return str(uuid.uuid4())[:8]


class TestMemoryCardsE2E:
    # -------------------------------------------------------------------------
    # Сценарий 3. Создание колоды, добавление карточек и старт обучения
    # -------------------------------------------------------------------------
    def test_scenario_3_create_deck_add_cards_start_study(self, page: Page):
        self._register_and_login(page, "study_user")

        page.get_by_role("button", name="Создать первую колоду").click()
        page.get_by_placeholder("Введите название колоды").fill("Java Core")
        page.get_by_role("dialog").get_by_role("button", name="Создать").click()

        page.get_by_label("Редактировать").click()
        expect(page).to_have_url(re.compile(r".*/decks/.*/edit"))

        for q, a in [("JVM", "Java Virtual Machine"), ("JDK", "Java Development Kit")]:
            page.get_by_role("button", name="Добавить карточку").click()
            page.get_by_placeholder("Введите вопрос").fill(q)
            page.get_by_placeholder("Введите ответ").fill(a)
            page.get_by_role("dialog").get_by_role("button", name="Создать").click()
            expect(page.get_by_text(q)).to_be_visible()

        page.get_by_role("button", name="Сохранить").click()
        expect(page.get_by_text("Колода успешно обновлена")).to_be_visible()

        page.get_by_role("button", name="Изучить").click()
        expect(page).to_have_url(re.compile(r".*/decks/.*/study"))
        expect(page.get_by_text("JVM")).to_be_visible()


    # -------------------------------------------------------------------------
    # Сценарий 5. Негативный: старт обучения пустой колоды
    # -------------------------------------------------------------------------
    def test_scenario_5_empty_deck_study(self, page: Page):
        self._register_and_login(page, "empty_deck_user")

        page.get_by_role("button", name="Создать первую колоду").click()
        page.get_by_placeholder("Введите название колоды").fill("Пустая колода")
        page.get_by_role("dialog").get_by_role("button", name="Создать").click()

        study_btn = page.get_by_role("button", name="Нет карточек")
        expect(study_btn).to_be_disabled()


    def _register_and_login(self, page: Page, prefix: str):
        uid = get_uid()
        login = f"{prefix}_{uid}"
        page.goto(f"{FRONTEND_URL}/register")
        page.get_by_placeholder("example@mail.com").fill(f"{login}@mail.com")
        page.get_by_placeholder("username").fill(login)
        page.get_by_placeholder("Введите пароль").fill("StrongPass123!")
        page.get_by_role("button", name="Зарегистрироваться").click()

        page.get_by_placeholder("Введите логин").fill(login)
        page.get_by_placeholder("Введите пароль").fill("StrongPass123!")
        page.get_by_role("button", name="Войти").click()
        expect(page).to_have_url(f"{FRONTEND_URL}/decks")
        return login
