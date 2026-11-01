"""Catálogo local de cursos (`CourseCatalog`) cargado desde JSON."""

import copy
import json
from pathlib import Path

from app.domain.grounding import normalize
from app.domain.ports import JsonDict

DEFAULT_COURSES_PATH = Path(__file__).resolve().parent.parent / "data" / "courses.json"


class JsonCourseCatalog:
    def __init__(self, path: Path = DEFAULT_COURSES_PATH) -> None:
        raw = json.loads(path.read_text(encoding="utf-8"))
        self._courses: list[JsonDict] = [dict(item) for item in raw]

    def search(self, skills: list[str], limit: int) -> list[JsonDict]:
        wanted = [normalize(s) for s in skills if s.strip()]
        if not wanted:
            return copy.deepcopy(self._courses[:limit])

        scored: list[tuple[int, JsonDict]] = []
        for course in self._courses:
            course_skill = normalize(str(course.get("skill", "")))
            tags = {normalize(str(t)) for t in course.get("tags", [])}
            score = 0
            for term in wanted:
                if term == course_skill:
                    score += 3
                elif term in tags or term in course_skill:
                    score += 1
            if score > 0:
                scored.append((score, course))

        scored.sort(key=lambda pair: -pair[0])
        return [copy.deepcopy(c) for _, c in scored[:limit]]
