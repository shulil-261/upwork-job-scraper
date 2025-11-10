from dataclasses import dataclass
from typing import Iterator

@dataclass
class PagePlan:
    total_pages: int
    per_page: int

    def iter_pages(self) -> Iterator[int]:
        for p in range(1, self.total_pages + 1):
            yield p