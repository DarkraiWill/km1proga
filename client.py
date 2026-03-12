
from __future__ import annotations

import csv
import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [CLIENT]  %(levelname)s  %(message)s",
)
logger = logging.getLogger(__name__)

class IDataLoader(ABC):
    """Абстракция загрузчика исходных данных."""

    @abstractmethod
    def load(self) -> dict[str, Any]:
        """Вернуть словарь с расписанием."""


class JsonFileLoader(IDataLoader):
    #Читает JSON из файла. Single Responsibility: только чтение файла.

    def __init__(self, filepath: str | Path) -> None:
        self._path = Path(filepath)

    def load(self) -> dict[str, Any]:
        logger.info("Загрузка JSON-файла: %s", self._path)
        with self._path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        logger.info("JSON загружен (%d дней)", len(data))
        return data


class IScheduleSender(ABC):
    #Абстракция транспортного уровня.

    @abstractmethod
    def send(self, payload: dict[str, Any], group: str) -> list[dict[str, str]]:
        """Отправить расписание, получить отфильтрованный список занятий."""


class HttpScheduleSender(IScheduleSender):
    """
    Отправляет POST-запрос на сервер и разбирает ответ.
    Single Responsibility только HTTP-транспорт.
    """

    def __init__(self, base_url: str = "http://127.0.0.1:8080") -> None:
        self._base_url = base_url.rstrip("/")

    def send(self, payload: dict[str, Any], group: str) -> list[dict[str, str]]:
        params = urllib.parse.urlencode({"group": group})
        url = f"{self._base_url}/schedule?{params}"
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        request = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )

        logger.info("Отправка запроса → %s (группа: %s)", url, group)
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.URLError as exc:
            raise ConnectionError(
                f"Не удалось подключиться к серверу: {exc.reason}"
            ) from exc

        result = json.loads(raw)
        if result.get("status") != "ok":
            raise ValueError(f"Сервер вернул ошибку: {result.get('message')}")

        lessons: list[dict[str, str]] = result["data"]
        logger.info("Получено занятий: %d", len(lessons))
        return lessons


class IResponseSaver(ABC):
    """Абстракция записи результата."""

    @abstractmethod
    def save(self, lessons: list[dict[str, str]], destination: str | Path) -> None:
        """Сохранить список занятий."""


class CsvResponseSaver(IResponseSaver):
    """
    Записывает полученное расписание в CSV-файл.
    Single Responsibility: только запись в CSV.
    """

    COLUMNS = ["День", "Время", "Дисциплина", "Преподаватель", "Аудитория"]

    def save(self, lessons: list[dict[str, str]], destination: str | Path) -> None:
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.DictWriter(
                fh,
                fieldnames=self.COLUMNS,
                extrasaction="ignore",
            )
            writer.writeheader()
            writer.writerows(lessons)

        logger.info("Расписание сохранено в CSV: %s", path.resolve())



class ScheduleClientBuilder:
    """
    Паттерн Builder: пошаговая сборка ScheduleClient.
    Open/Closed новые компоненты добавляются без изменения Client.
    """

    def __init__(self) -> None:
        self._loader: IDataLoader | None = None
        self._sender: IScheduleSender | None = None
        self._saver: IResponseSaver | None = None

    def with_loader(self, loader: IDataLoader) -> "ScheduleClientBuilder":
        self._loader = loader
        return self

    def with_sender(self, sender: IScheduleSender) -> "ScheduleClientBuilder":
        self._sender = sender
        return self

    def with_saver(self, saver: IResponseSaver) -> "ScheduleClientBuilder":
        self._saver = saver
        return self

    def build(self) -> "ScheduleClient":
        if not all([self._loader, self._sender, self._saver]):
            raise ValueError("Необходимо задать loader, sender и saver.")
        return ScheduleClient(self._loader, self._sender, self._saver)  # type: ignore[arg-type]

class ScheduleClient:
    """
    Оркестрирует загрузку - отправку - сохранение.
    Dependency Inversion: зависит только от абстракций.
    """

    def __init__(
        self,
        loader: IDataLoader,
        sender: IScheduleSender,
        saver: IResponseSaver,
    ) -> None:
        self._loader = loader
        self._sender = sender
        self._saver = saver

    def run(self, group: str, output_path: str | Path) -> None:
        """Выполнить полный цикл: загрузить - отправить - сохранить."""
        data = self._loader.load()
        lessons = self._sender.send(data, group)
        self._saver.save(lessons, output_path)
        logger.info("✓ Готово! Расписание группы %s → %s", group, output_path)



if __name__ == "__main__":
    import sys

    # Параметры (можно переопределить через аргументы командной строки)
    JSON_FILE   = sys.argv[1] if len(sys.argv) > 1 else "schedule.json"
    GROUP_NAME  = sys.argv[2] if len(sys.argv) > 2 else "ФП-14"
    OUTPUT_CSV  = sys.argv[3] if len(sys.argv) > 3 else f"schedule_{GROUP_NAME.replace('-', '_')}.csv"
    SERVER_URL  = sys.argv[4] if len(sys.argv) > 4 else "http://127.0.0.1:8080"

    client = (
        ScheduleClientBuilder()
        .with_loader(JsonFileLoader(JSON_FILE))
        .with_sender(HttpScheduleSender(SERVER_URL))
        .with_saver(CsvResponseSaver())
        .build()
    )

    try:
        client.run(group=GROUP_NAME, output_path=OUTPUT_CSV)
    except (ConnectionError, ValueError) as exc:
        logger.error("Ошибка: %s", exc)
        sys.exit(1)
