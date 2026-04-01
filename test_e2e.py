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
    # Сценарий 1. Регистрация нового пользователя, вход и создание первой колоды
    # -------------------------------------------------------------------------
    def test_scenario_1_register_login_create_deck(self, page: Page):
        uid = get_uid()
        email = f"e2e_user1_{uid}@mail.com"
        login = f"e2e_user1_{uid}"

        # 1-2. Переход на главную и открытие формы регистрации
        page.goto(FRONTEND_URL)
        page.get_by_role("button", name="Зарегистрироваться").click()

        # 3. Ввод валидных данных
        page.get_by_placeholder("example@mail.com").fill(email)
        page.get_by_placeholder("username").fill(login)
        page.get_by_placeholder("Введите пароль").fill("StrongPass123!")

        # 4-6. Кнопка активна, нажимаем, ждем редиректа на логин
        submit_btn = page.get_by_role("button", name="Зарегистрироваться")
        expect(submit_btn).to_be_enabled()
        submit_btn.click()
        expect(page).to_have_url(f"{FRONTEND_URL}/login")

        # 7-9. Вход в систему
        page.get_by_placeholder("Введите логин").fill(login)
        page.get_by_placeholder("Введите пароль").fill("StrongPass123!")
        page.get_by_role("button", name="Войти").click()
        expect(page).to_have_url(f"{FRONTEND_URL}/decks")

        # 10-14. Создание колоды
        page.get_by_role("button", name="Создать первую колоду").click()
        page.get_by_placeholder("Введите название колоды").fill("Английские слова")
        page.get_by_placeholder("Добавьте описание колоды").fill("Базовая лексика")

        modal = page.get_by_role("dialog")
        modal.get_by_role("button", name="Создать").click()
        expect(modal).not_to_be_visible()

        # 15. Проверка колоды в списке
        expect(page.get_by_text("Английские слова")).to_be_visible()
        expect(page.get_by_text("Базовая лексика")).to_be_visible()
        expect(page.locator("text=Карточек").locator("..").get_by_text("0", exact=True)).to_be_visible()

    # -------------------------------------------------------------------------
    # Сценарий 2. Регистрация: невалидные поля, исправление, успешный вход/выход
    # -------------------------------------------------------------------------
    def test_scenario_2_invalid_registration_and_logout(self, page: Page):
        uid = get_uid()
        valid_email = f"good_user_{uid}@mail.com"
        valid_login = f"good_user_{uid}"

        page.goto(f"{FRONTEND_URL}/register")

        # Ввод невалидных данных
        page.get_by_placeholder("example@mail.com").fill("badmail")
        page.get_by_placeholder("username").fill("русский_логин")
        page.get_by_placeholder("Введите пароль").fill("123")
        page.keyboard.press("Tab")  # Чтобы сработал onBlur

        # Проверка ошибок и неактивной кнопки
        expect(page.get_by_text("Введите корректный email адрес")).to_be_visible()
        expect(page.get_by_role("button", name="Зарегистрироваться")).to_be_disabled()

        # Исправление
        page.get_by_placeholder("example@mail.com").fill(valid_email)
        page.get_by_placeholder("username").fill(valid_login)
        page.get_by_placeholder("Введите пароль").fill("GoodPass123!")

        # Регистрация и вход
        page.get_by_role("button", name="Зарегистрироваться").click()
        page.get_by_placeholder("Введите логин").fill(valid_login)
        page.get_by_placeholder("Введите пароль").fill("GoodPass123!")
        page.get_by_role("button", name="Войти").click()
        expect(page).to_have_url(f"{FRONTEND_URL}/decks")

        # Выход
        page.get_by_label("Профиль").click()
        page.get_by_role("button", name="Выйти из аккаунта").click()
        page.get_by_role("button", name="Выйти", exact=True).click()

        # Проверка защиты роута
        expect(page).to_have_url(f"{FRONTEND_URL}/")
        page.goto(f"{FRONTEND_URL}/decks")
        expect(page).to_have_url(f"{FRONTEND_URL}/login")  # Редирект для неавторизованных

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
    # Сценарий 4. Полный цикл обучения
    # -------------------------------------------------------------------------
    def test_scenario_4_full_study_cycle(self, page: Page):
            self._register_and_login(page, "cycle_user")
            self._create_deck_with_cards(page, "Биология", [("Вопрос 1", "Ответ 1"), ("Вопрос 2", "Ответ 2")])

            page.get_by_role("button", name="Изучить").click()

            # Карточка 1
            page.get_by_role("button", name="Показать ответ").click()
            page.get_by_role("button", name="Помню").first.click()

            # Карточка 2
            page.get_by_role("button", name="Показать ответ").click()
            page.get_by_role("button", name="Не помню").click()

            # Экран статистики
            expect(page.get_by_text("Отличная работа!")).to_be_visible()
            page.get_by_role("button", name="Вернуться к колодам").click()
            page.reload()

            # Проверяем, что сессия завершена и колода отмечена как изученная сегодня.
            expect(page.get_by_text("Биология")).to_be_visible()
            expect(page.get_by_text("Сегодня")).to_be_visible()

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

    # -------------------------------------------------------------------------
    # Сценарий 6. Негативный: создание дубликата
    # -------------------------------------------------------------------------
    def test_scenario_6_duplicate_deck_name(self, page: Page):
        self._register_and_login(page, "dup_user")

        # Создаем первую колоду
        page.get_by_role("button", name="Создать первую колоду").click()
        page.get_by_placeholder("Введите название колоды").fill("История")
        page.get_by_role("dialog").get_by_role("button", name="Создать").click()

        # Пытаемся создать вторую с таким же именем
        page.get_by_role("button", name="Создать колоду").click()
        page.get_by_placeholder("Введите название колоды").fill("История")
        modal = page.get_by_role("dialog")
        modal.get_by_role("button", name="Создать").click()

        # Проверка ошибки с бэкенда (Toast или текст в UI)
        expect(page.get_by_text("Колода с таким названием уже существует")).to_be_visible()

        # Исправляем и сохраняем
        page.get_by_placeholder("Введите название колоды").fill("История России")
        modal.get_by_role("button", name="Создать").click()
        expect(page.get_by_text("История России")).to_be_visible()

    # -------------------------------------------------------------------------
    # Сценарий 7. Редактирование колоды, удаление карточки (отмена и подтверждение)
    # -------------------------------------------------------------------------
    def test_scenario_7_edit_and_delete_card(self, page: Page):
        self._register_and_login(page, "edit_user")

        # Создаем колоду
        page.get_by_role("button", name=re.compile("Создать (первую )?колоду")).first.click()
        page.get_by_placeholder("Введите название колоды").fill("QA Basics")
        page.get_by_role("dialog").get_by_role("button", name="Создать").click()

        # Переходим в редактирование колоды
        page.get_by_role("button", name="Редактировать").first.click()
        expect(page).to_have_url(re.compile(r".*/decks/.*/edit"))

        # Добавляем 2 карточки
        for q, a in [("Smoke", "Быстрая проверка"), ("Regression", "Повторная проверка")]:
            page.get_by_role("button", name="Добавить карточку").click()
            page.get_by_placeholder("Введите вопрос").fill(q)
            page.get_by_placeholder("Введите ответ").fill(a)
            page.get_by_role("dialog").get_by_role("button", name="Создать").click()
            expect(page.get_by_text(q)).to_be_visible()

        smoke_row = page.locator("div").filter(has_text="Smoke").filter(has_text="Быстрая проверка").first

        # Удаление карточки с отменой
        smoke_row.get_by_label("Удалить").first.click()
        page.get_by_role("button", name="Отмена").click()
        expect(page.get_by_text("Smoke", exact=True)).to_be_visible()

        # Удаление карточки с подтверждением
        smoke_row.get_by_label("Удалить").first.click()
        page.get_by_role("dialog").last.get_by_role("button", name="Удалить", exact=True).click()
        expect(page.get_by_text("Smoke", exact=True)).not_to_be_visible()

        page.get_by_role("button", name="Сохранить").click()
        expect(page.get_by_text("Колода успешно обновлена")).to_be_visible()

    # -------------------------------------------------------------------------
    # Сценарий 8. Поделиться колодой и импортировать (Мульти-браузер)
    # -------------------------------------------------------------------------
    def test_scenario_8_share_and_import(self, browser: Browser):
            # Пользователь А
            context_a = browser.new_context()
            page_a = context_a.new_page()
            self._register_and_login(page_a, "user_a")
            self._create_deck_with_cards(page_a, "Shared English", [("Apple", "Яблоко")])

            page_a.get_by_label("Редактировать").click()
            page_a.get_by_role("button", name="Поделиться").click()
            share_url = page_a.locator("input[readonly]").input_value()

            # Пользователь B
            context_b = browser.new_context()
            page_b = context_b.new_page()
            self._register_and_login(page_b, "user_b")

            # Переход по ссылке
            page_b.goto(share_url)
            expect(page_b.get_by_text("Shared English")).to_be_visible()

            page_b.get_by_role("button", name="Импортировать колоду").click()
            page_b.get_by_placeholder("Введите название колоды").fill("Shared English Copy")
            page_b.get_by_role("dialog").get_by_role("button", name="Импортировать").click()

            expect(page_b).to_have_url(re.compile(r".*/decks/.*/edit"))
            expect(page_b.get_by_placeholder("Введите название колоды")).to_have_value("Shared English Copy")

    def _create_deck_with_cards(self, page: Page, name: str, cards: list):
        page.get_by_role("button", name=re.compile("Создать (первую )?колоду")).first.click()
        page.get_by_placeholder("Введите название колоды").fill(name)
        page.get_by_role("dialog").get_by_role("button", name="Создать").click()

        page.get_by_label("Редактировать").click()
        for q, a in cards:
            page.get_by_role("button", name="Добавить карточку").click()
            page.get_by_placeholder("Введите вопрос").fill(q)
            page.get_by_placeholder("Введите ответ").fill(a)
            page.get_by_role("dialog").get_by_role("button", name="Создать").click()
        page.get_by_role("button", name="Сохранить").click()
