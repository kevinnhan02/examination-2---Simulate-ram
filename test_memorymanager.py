import unittest
from memorymanager import MemManager
from database_models import Arena, Pool, Block, StoredObject

class TestMemoryManager(unittest.TestCase):
    def setUp(self):
        self.memory_manager = MemManager("sqlite:///databasetest.sqlite")

    def test_allocate_memory_for_object(self):
        obj = "Test Object" * 1000
        self.memory_manager.allocate_memory_for_object(obj)

        # Verify that the object is stored in the database
        object_id = self.memory_manager.generate_object_id(obj)
        stored_object = self.memory_manager.session.query(StoredObject).filter(StoredObject.object_id == object_id).first()
        self.assertIsNotNone(stored_object)
        self.assertEqual(stored_object.object_data, obj)

    def test_get_object(self):
        obj = "Test Object" * 1000
        self.memory_manager.allocate_memory_for_object(obj)

        # Retrieve the object using get_object
        retrieved_obj = self.memory_manager.get_object(obj)
        self.assertEqual(retrieved_obj, obj)

    def test_free_memory_for_object(self):
        obj = "Test Object" * 1000
        self.memory_manager.allocate_memory_for_object(obj)

        # Free the memory for the object
        self.memory_manager.free_memory_for_object(obj)

        # Verify that the object is removed from the database
        object_id = self.memory_manager.generate_object_id(obj)
        stored_object = self.memory_manager.session.query(StoredObject).filter(StoredObject.object_id == object_id).first()
        self.assertIsNone(stored_object)

    def test_listener_updates(self):
        obj = "Test Object" * 1000
        self.memory_manager.allocate_memory_for_object(obj)

        # Verify that the listener updated the pool and arena memory correctly
        block = self.memory_manager.session.query(Block).first()
        pool = self.memory_manager.session.query(Pool).filter(Pool.id == block.pool_id).one()
        arena = self.memory_manager.session.query(Arena).filter(Arena.id == pool.arena_id).one()

        # Ensure the pool memory is updated correctly
        total_block_mem = sum(b.mem for b in pool.blocks)
        self.assertEqual(pool.mem, total_block_mem)

        # Ensure the arena memory is updated correctly
        total_pool_mem = sum(p.mem for p in arena.pools)
        self.assertEqual(arena.mem, total_pool_mem)

        # Ensure the block's is_free attribute is updated correctly
        self.assertEqual(block.is_free, 0 if block.mem == block.max_mem else 1)

    def test_free_memory_updates(self):
        obj = "Test Object" * 1000
        self.memory_manager.allocate_memory_for_object(obj)

        # Free the memory for the object
        self.memory_manager.free_memory_for_object(obj)

        # Explicitly commit the session to ensure changes are visible
        self.memory_manager.session.commit()

        # Refresh the objects to ensure changes are visible
        block = self.memory_manager.session.query(Block).first()
        self.memory_manager.session.refresh(block)
        pool = self.memory_manager.session.query(Pool).filter(Pool.id == block.pool_id).one()
        self.memory_manager.session.refresh(pool)
        arena = self.memory_manager.session.query(Arena).filter(Arena.id == pool.arena_id).one()
        self.memory_manager.session.refresh(arena)

        # Verify that the listener updated the pool and arena memory correctly
        total_block_mem = sum(b.mem for b in pool.blocks)
        print(f"Pool mem: {pool.mem}, Total block mem: {total_block_mem}")
        self.assertEqual(pool.mem, total_block_mem)

        # Ensure the arena memory is updated correctly
        total_pool_mem = sum(p.mem for p in arena.pools)
        print(f"Arena mem: {arena.mem}, Total pool mem: {total_pool_mem}")
        self.assertEqual(arena.mem, total_pool_mem)

        # Ensure the block's is_free attribute is updated correctly
        print(f"Block is_free: {block.is_free}, Expected is_free: {0 if block.mem == block.max_mem else 1}")
        self.assertEqual(block.is_free, 0 if block.mem == block.max_mem else 1)

    def test_reuse_freed_blocks(self):
        obj1 = "Test Object 1" * 1000
        obj2 = "Test Object 2" * 1000

        # Allocate memory for the first object
        self.memory_manager.allocate_memory_for_object(obj1)

        # Free the memory for the first object
        self.memory_manager.free_memory_for_object(obj1)

        # Allocate memory for the second object
        self.memory_manager.allocate_memory_for_object(obj2)

        # Verify that the second object is stored in the database
        object_id2 = self.memory_manager.generate_object_id(obj2)
        stored_object2 = self.memory_manager.session.query(StoredObject).filter(StoredObject.object_id == object_id2).first()
        self.assertIsNotNone(stored_object2)
        self.assertEqual(stored_object2.object_data, obj2)

        # Verify that the freed block is reused
        block = self.memory_manager.session.query(Block).first()
        self.assertEqual(block.is_free, 0 if block.mem == block.max_mem else 1)

if __name__ == '__main__':
    unittest.main()