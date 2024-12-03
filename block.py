from memorychunk import MemoryChunk
class Block(MemoryChunk):

    def __init__(self, mem: int = 0) -> None:
        super().__init__(max_mem=512, mem=mem)
        if mem > 512:
            raise ValueError("Memory exceeds the maximum limit")
        self.objects = []
        self.is_free = True

    def add_mem(self, amount: int):
        if self.mem + amount > self.max_mem:
            raise ValueError("Exceeds block memory limit")
        self.mem += amount

    def add_object(self, obj_id: str):
        self.objects.append(obj_id)

    def contains(self, obj_id: str) -> bool:
        return obj_id in self.objects

    def allocate(self):
        self.is_free = False

    def deallocate(self):
        self.is_free = True

    def remove_object(self, obj_id: str):
        """Remove an object from the block"""
        if obj_id in self.objects:
            self.objects.remove(obj_id)
            self.deallocate()  # Mark the block as free when object is removed

    def is_empty(self) -> bool:
        """Check if the block is empty (contains no objects)"""
        return len(self.objects) == 0