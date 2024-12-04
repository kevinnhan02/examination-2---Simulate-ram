import unittest
from memorymanager import MemManager
from Schemas import Arena, Pool, Block

class TestMemoryManager(unittest.TestCase):

    def setUp(self):
        self.memory_manager = MemManager("sqlite:///databasetest.sqlite")
        

    def test_create_arena(self):
        arena = Arena()
        self.assertIsInstance(arena, Arena)

    def test_create_pool(self):
        pool = Pool()
        self.assertIsInstance(pool, Pool)

    def test_create_block(self):
        block = Block()
        self.assertIsInstance(block, Block)

    def test_allocate_block(self):
        obj = "Test Object"
        self.memory_manager.allocate_memory_for_object(obj)
        # Kontrollera att blocket har allokerats
        self.assertTrue(any(block for block in self.memory_manager.blocks if block.contains(obj)))

    def test_deallocate_block(self):
        obj = "Test Object"
        self.memory_manager.allocate_memory_for_object(obj)
        self.memory_manager.free_memory_for_object(obj)
        # Kontrollera att blocket har deallokerats
        self.assertFalse(any(block for block in self.memory_manager.blocks if block.contains(obj)))

    def test_automatic_pool_creation(self):
        # Allokera tillräckligt med objekt för att fylla en pool och skapa en ny
        for i in range(100):  # Anta att 100 objekt fyller en pool
            self.memory_manager.allocate_memory_for_object(f"Object {i}")
        # Kontrollera att en ny pool har skapats
        self.assertGreater(len(self.memory_manager.pools), 1)

    def test_reuse_free_blocks(self):
        obj1 = "Object 1"
        obj2 = "Object 2"
        self.memory_manager.allocate_memory_for_object(obj1)
        self.memory_manager.free_memory_for_object(obj1)
        self.memory_manager.allocate_memory_for_object(obj2)
        # Kontrollera att det fria blocket återanvänds
        self.assertTrue(any(block for block in self.memory_manager.blocks if block.contains(obj2)))

    def test_memory_usage_statistics(self):
        # Kontrollera att statistik över minnesanvändning rapporteras korrekt
        stats = self.memory_manager.get_memory_stats()
        self.assertIn("total_blocks", stats)
        self.assertIn("used_memory", stats)

if __name__ == '__main__':
    unittest.main()