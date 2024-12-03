from memorychunk import MemoryChunk

class Pool(MemoryChunk):

    def __init__(self, mem: int = 0) -> None:
        super().__init__(max_mem=2048, mem=mem)
        if mem > 2048:
            raise ValueError("Memory exceeds the maximum limit")