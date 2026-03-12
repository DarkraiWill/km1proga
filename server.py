from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [SERVER]  %(levelname)s  %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Lesson:
    day: str
    time: str
    group: str
    subject: str
    teacher: str
    room: str


class IScheduleRepository(ABC):
    #Абстракция источника данных расписания.

    @abstractmethod
    def get_all(self) -> list[Lesson]:
        """Вернуть все занятия."""


class JsonScheduleRepository(IScheduleRepository):
    #Преобразует JSON-расписание в список объектов Lesson. Паттерн Repository изолирует логику доступа к данным.

    def __init__(self, raw: dict[str, Any]) -> None:
        self._lessons: list[Lesson] = self._parse(raw)

    @staticmethod
    def _parse(raw: dict[str, Any]) -> list[Lesson]:
        lessons: list[Lesson] = []
        for day, time_slots in raw.items():
            for time_str, entries in time_slots.items():
                for entry in entries:
                    lessons.append(
                        Lesson(
                            day=day,
                            time=time_str,
                            group=entry["группа"],
                            subject=entry["дисциплина"],
                            teacher=entry["преподаватель"],
                            room=entry["аудитория"],
                        )
                    )
        return lessons

    def get_all(self) -> list[Lesson]:
        return list(self._lessons)


class IScheduleFilter(ABC):

    @abstractmethod
    def apply(self, lessons: list[Lesson]) -> list[Lesson]:
        """Применить фильтр и вернуть отфильтрованный список."""


class GroupFilter(IScheduleFilter):
    #Оставляет только занятия указанной группы.

    def __init__(self, group_name: str) -> None:
        self._group = group_name

    def apply(self, lessons: list[Lesson]) -> list[Lesson]:
        return [l for l in lessons if l.group == self._group]

class ScheduleService:

    def __init__(
        self,
        repository: IScheduleRepository,
        schedule_filter: IScheduleFilter,
    ) -> None:
        self._repository = repository
        self._filter = schedule_filter

    def get_filtered_schedule(self) -> list[Lesson]:
        all_lessons = self._repository.get_all()
        return self._filter.apply(all_lessons)


class ResponseFactory:

    @staticmethod
    def success(data: Any) -> bytes:
        payload = {"status": "ok", "data": data}
        return json.dumps(payload, ensure_ascii=False).encode("utf-8")

    @staticmethod
    def error(message: str, code: int = 400) -> tuple[int, bytes]:
        payload = {"status": "error", "message": message}
        return code, json.dumps(payload, ensure_ascii=False).encode("utf-8")

class ScheduleRequestHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt: str, *args: Any) -> None:  # переопределяем, чтобы использовать наш logger
        logger.info(fmt, *args)

    def do_POST(self) -> None: 
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(self.path)

        if parsed.path != "/schedule":
            code, body = ResponseFactory.error("Маршрут не найден", 404)
            self._send(code, body)
            return

        params = parse_qs(parsed.query)
        group_list = params.get("group", [])
        if not group_list:
            code, body = ResponseFactory.error("Параметр 'group' обязателен")
            self._send(code, body)
            return

        group_name = group_list[0]
        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length)

        try:
            schedule_json: dict[str, Any] = json.loads(raw_body)
        except json.JSONDecodeError as exc:
            code, body = ResponseFactory.error(f"Некорректный JSON: {exc}")
            self._send(code, body)
            return

        repository = JsonScheduleRepository(schedule_json)
        schedule_filter = GroupFilter(group_name)
        service = ScheduleService(repository, schedule_filter)

        lessons = service.get_filtered_schedule()
        logger.info("Группа '%s': найдено %d занятий", group_name, len(lessons))

        result = [
            {
                "День": l.day,
                "Время": l.time,
                "Дисциплина": l.subject,
                "Преподаватель": l.teacher,
                "Аудитория": l.room,
            }
            for l in lessons
        ]
        self._send(200, ResponseFactory.success(result))

    def _send(self, code: int, body: bytes) -> None:
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class ScheduleServer:
    #Запускает HTTP-сервер на заданном адресе

    def __init__(self, host: str = "127.0.0.1", port: int = 8080) -> None:
        self._host = host
        self._port = port

    def start(self) -> None:
        server = HTTPServer((self._host, self._port), ScheduleRequestHandler)
        logger.info("Сервер запущен: http://%s:%d", self._host, self._port)
        logger.info("Ожидание запросов... (Ctrl+C для остановки)")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            logger.info("Сервер остановлен.")
        finally:
            server.server_close()


if __name__ == "__main__":
    ScheduleServer(host="127.0.0.1", port=8080).start()
