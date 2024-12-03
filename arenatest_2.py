from memorychunk import MemoryChunk
import pandas as pd

class Arena(MemoryChunk):
    def __init__(self, mem: int = 0) -> None:
        super().__init__(max_mem=262_144, mem=mem)
        if mem > 262_144:
            raise ValueError("Memory exceeds the maximum limit")
        self.pools = pd.DataFrame(columns=["pool_obj", "pool_name", "blocks"])