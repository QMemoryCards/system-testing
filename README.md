Для запуска тестов
1. Установить зависимости `pip install -r requirements.txt`
2. Прописать команду `playwright install`
3. Запустить тесты `pytest test_e2e.py`


Для запуска отдельного теста можно использовать одну из следующих команд:
По имени теста:

`pytest test_e2e.py -k "test_scenario_1"`

Указывайте точное имя теста, иначе могут запуститься все тесты, содержащие указанную строку в названии.

По точному пути (класс + тест):

`pytest test_e2e.py::TestMemoryCardsE2E::test_scenario_1_register_login_create_deck`

Для визуальных (headed) тестов:

`pytest test_e2e.py -k "test_scenario_1" --headed --slowmo 500`


Также можно запускать тесты с различными параметрами:
* Для запуска с открытым браузером (чтобы видеть, как робот "кликает"): `pytest test_e2e.py --headed --slowmo 500`

## CI/CD

Workflow `.github/workflows/main.yaml` запускается:

* на `push` и `pull_request` в `main` — E2E против текущих образов `latest`;
* по `repository_dispatch` с типом `images-published` — после публикации нового
  образа backend или frontend в GHCR;
* по расписанию (ночью) — smoke-проверка без деплоя;
* вручную через `workflow_dispatch` (можно включить деплой).

После успешных E2E образы, зафиксированные по digest, деплоятся в `dev` на
self-hosted runner с меткой `dev`, затем в `prod` на runner с меткой `prod`.
Деплой в `prod` требует ручного подтверждения через GitHub Environment `prod`.

Секреты окружений (`POSTGRES_*`, `CORS_ORIGIN_PATTERNS`) задаются в
GitHub Environments, а не в репозитории. Полная инструкция по настройке —
в `DEVOPS_SETUP.md`.
