"""Описание шагов квиза как данных — чтобы Назад/Пропустить/К мастеру
работали одинаково на любом шаге без дублирования хендлеров."""

from dataclasses import dataclass
from typing import List, Optional, Tuple

from bot.pricing import (
    DEMONTAGE_OPTIONS,
    DISTRICT_OPTIONS,
    HARDWARE_OPTIONS,
    SERVICE_OPTIONS,
    TIMING_OPTIONS,
    VOLUME_OPTIONS,
)


@dataclass
class Step:
    key: str
    kind: str  # "choice" | "text" | "phone" | "photo"
    question: str
    options: Optional[List[Tuple[str, str]]] = None
    required: bool = False
    columns: int = 2


FULL_STEPS: List[Step] = [
    Step("service", "choice", "Что собираем?", SERVICE_OPTIONS, required=True),
    Step("volume", "choice", "Какой объём работ?", VOLUME_OPTIONS, columns=1),
    Step("demontage", "choice", "Нужно демонтировать старую мебель?", DEMONTAGE_OPTIONS, columns=1),
    Step("hardware", "choice", "Инструкция и вся фурнитура на месте?", HARDWARE_OPTIONS, columns=1),
    Step("district", "choice", "В каком районе собираем?", DISTRICT_OPTIONS, required=True),
    Step("timing", "choice", "Когда удобно собрать?", TIMING_OPTIONS, columns=1),
    Step("photo", "photo", "Прикрепите фото мебели или объекта — мастер посчитает точнее.\nНе обязательно."),
    Step("name", "text", "Как вас зовут?", required=True),
    Step("phone", "phone", "Поделитесь номером — мастер свяжется и назовёт точную цену.", required=True),
]

FAST_STEPS: List[Step] = [
    Step("name", "text", "Как вас зовут?", required=True),
    Step("phone", "phone", "Оставьте номер — мастер позвонит в течение 15 минут и всё обсудит.", required=True),
]


def get_steps(flow: str) -> List[Step]:
    return FAST_STEPS if flow == "fast" else FULL_STEPS
