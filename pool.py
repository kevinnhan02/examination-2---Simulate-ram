from memorychunk import MemoryChunk
import pandas as pd
class Pool(MemoryChunk):

    def __init__(self, mem: int = 0) -> None:
        super().__init__(max_mem=4096, mem=mem)
        if mem > 4096:
            raise ValueError("Memory exceeds the maximum limit")
        self.blocks = pd.DataFrame(columns=["block_obj", "block_name"])
