from dataclasses import dataclass
from enum import IntEnum


class AutonomyLevel(IntEnum):
    CONVERSATION = 0
    SUGGEST = 1
    READ_ONLY = 2
    EXECUTE = 3
    MULTI_STEP = 4
    LONG_RUNNING = 5


@dataclass
class AutonomyManager:
    level: AutonomyLevel = AutonomyLevel.EXECUTE

    def set_level(self, level: int) -> None:
        self.level = AutonomyLevel(max(0, min(5, int(level))))

    def allows_execution(self) -> bool:
        return self.level >= AutonomyLevel.EXECUTE

    def allows_multistep(self) -> bool:
        return self.level >= AutonomyLevel.MULTI_STEP

    def snapshot(self) -> dict:
        return {
            "level": int(self.level),
            "name": self.level.name.lower(),
            "allows_execution": self.allows_execution(),
            "allows_multistep": self.allows_multistep(),
        }


autonomy = AutonomyManager()
