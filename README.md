# 🎓 University Schedule — Клиент-серверное приложение

> Учебный проект по дисциплине «Программирование» · Вариант №4

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![No Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen?style=for-the-badge)
![SOLID](https://img.shields.io/badge/SOLID-principles-orange?style=for-the-badge)
![Design Patterns](https://img.shields.io/badge/patterns-Repository%20·%20Strategy%20·%20Builder%20·%20Factory-purple?style=for-the-badge)

---

## 🤔 Что это такое?

Приложение моделирует реальную систему управления расписанием университета в формате «клиент — сервер».

**Сервер** получает общее расписание всех групп, фильтрует его по нужной группе и возвращает только нужные данные.  
**Клиент** загружает JSON с расписанием, отправляет его на сервер и сохраняет ответ в CSV-файл.

Весь код написан с соблюдением принципов **SOLID** и использованием паттернов проектирования.

---

## 🚀 Запуск за 2 команды

```bash
# Терминал 1 — запустить сервер
python server.py

# Терминал 2 — запустить клиент (группа, входной JSON, выходной CSV)
python client.py schedule.json "ФП-14" schedule_FP14.csv
```

Готово — в папке появится `schedule_FP14.csv` с расписанием группы ФП-14.

---

## 📂 Файлы проекта

```
.
├── server.py        # HTTP-сервер на порту 8080
├── client.py        # Клиент: читает JSON → шлёт запрос → сохраняет CSV
└── schedule.json    # Расписание групп ФП-02, ФП-13, ФП-14, ФП-15, ФП-17
```

Внешних библиотек нет — только стандартная библиотека Python.

---

## ⚙️ Как это работает

```
client.py                               server.py
─────────────────                       ──────────────────────────
1. Читает schedule.json    ──POST──►    2. Получает JSON
                                        3. Фильтрует по группе
4. Получает ответ          ◄──JSON──    4. Возвращает занятия
5. Сохраняет в .csv
```

**Результирующий CSV выглядит так:**

| День | Время | Дисциплина | Преподаватель | Аудитория |
|------|-------|------------|---------------|-----------|
| Понедельник | 09:00–10:30 (1 пара) | Иностранный язык | Ст. преп. Иванова Е.С. | Ш-107 |
| Понедельник | 10:40–12:10 (2 пара) | Программирование | Доц. Морозов К.С. | Ш-106 |
| Вторник | 09:00–10:30 (1 пара) | Математический анализ | Проф. Смирнов В.И. | Ш-204 |

---

## 🏗️ Архитектура

### Паттерны

| Паттерн | Где | Зачем |
|---------|-----|-------|
| **Repository** | `JsonScheduleRepository` | Отделяет источник данных от бизнес-логики |
| **Strategy** | `IScheduleFilter` / `GroupFilter` | Алгоритм фильтрации легко заменяется |
| **Factory Method** | `ResponseFactory` | Единый способ создавать HTTP-ответы |
| **Builder** | `ScheduleClientBuilder` | Удобная сборка клиента по шагам |

### Принципы SOLID

| | Принцип | Как реализован |
|-|---------|----------------|
| **S** | Single Responsibility | Каждый класс делает одно: `JsonFileLoader` — читает файл, `CsvResponseSaver` — пишет CSV, `HttpScheduleSender` — HTTP |
| **O** | Open / Closed | Новый фильтр = новый класс. Существующий код не трогается |
| **L** | Liskov Substitution | Любой `IDataLoader`, `IScheduleSender`, `IResponseSaver` взаимозаменяем |
| **I** | Interface Segregation | Три узких интерфейса вместо одного большого |
| **D** | Dependency Inversion | `ScheduleClient` зависит от интерфейсов, а не от конкретных классов |

---

## 🧩 Как расширить

Хочешь фильтровать по преподавателю — просто создай новый класс:

```python
class TeacherFilter(IScheduleFilter):
    def __init__(self, name: str) -> None:
        self._name = name

    def apply(self, lessons: list[Lesson]) -> list[Lesson]:
        return [l for l in lessons if self._name in l.teacher]
```

Хочешь сохранять в Excel вместо CSV — реализуй `IResponseSaver`.  
Хочешь читать данные из базы данных — реализуй `IDataLoader`.  
Существующий код при этом **не меняется**.

---

## 📋 Требования

- Python **3.9** и выше
- Сторонние библиотеки: **не нужны**
