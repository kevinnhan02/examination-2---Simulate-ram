class MemoryChunk():
    def __init__(self, max_mem: int, mem:int = 0):
        self.max_mem = max_mem
        self.mem = mem

    def add_mem(self, amount: int) -> None:
        if self.mem + amount <= self.max_mem:
            self.mem += amount
        else:
            self.mem = self.max_mem

    def subtract_mem(self, amount: int) -> None:
        if self.mem - amount >= 0:
            self.mem -= amount
        else:
            self.mem = 0

    def get_remaining_unused_mem(self) -> int:
        return self.max_mem - self.mem
