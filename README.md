Для запуска тестов
1. Установить зависимости `pip install -r requirements.txt`
2. Прописать команду `playwrithg install`
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
