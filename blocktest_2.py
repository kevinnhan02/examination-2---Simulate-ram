from memorychunk import MemoryChunk
class Block(MemoryChunk):

    def __init__(self, mem: int = 0) -> None:
        super().__init__(max_mem=512, mem=mem)
        if mem > 512:
            raise ValueError("Memory exceeds the maximum limit")