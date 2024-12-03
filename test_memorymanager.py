import unittest
from memorymanager import MemManager
from arena import Arena
from pool import Pool
from block import Block
from ram import RAM
import pandas as pd

class TestMemManager(unittest.TestCase):
    def setUp(self):
        # Create a RAM instance with a specific amount of memory
        self.ram = RAM(memory=1_000_000)  # 1,000,000 units of RAM
        # Create a MemManager instance
        self.mem_manager = MemManager(ram=self.ram)

    def test_add_arena(self):
        arena = Arena(0)
        self.mem_manager.add_arena(arena)
        self.assertEqual(len(self.mem_manager.memory["arenas"]), 1)
        self.assertEqual(self.mem_manager.memory["arenas"].iloc[0]["arena_name"], "Arena 1")

    def test_add_pool(self):
        arena = Arena(0)
        self.mem_manager.add_arena(arena)
        pool = Pool(0)
        self.mem_manager.add_pool("Arena 1", pool)
        self.assertEqual(len(self.mem_manager.memory["arenas"].iloc[0]["pools"]), 1)
        self.assertEqual(self.mem_manager.memory["arenas"].iloc[0]["pools"].iloc[0]["pool_name"], "pool 1")

    def test_add_block(self):
        arena = Arena(0)
        self.mem_manager.add_arena(arena)
        pool = Pool(0)
        self.mem_manager.add_pool("Arena 1", pool)
        block = Block(0)
        self.mem_manager.add_block("Arena 1", "pool 1", block)
        self.assertEqual(len(self.mem_manager.memory["arenas"].iloc[0]["pools"].iloc[0]["blocks"]), 1)

    def test_calculate_arena_memory(self):
        arena = Arena(0)
        self.mem_manager.add_arena(arena)
        pool = Pool(0)
        self.mem_manager.add_pool("Arena 1", pool)
        block = Block(0)
        self.mem_manager.add_block("Arena 1", "pool 1", block)
        self.assertEqual(self.mem_manager.calculate_arena_memory("Arena 1"), block.mem)

    def test_calculate_pool_memory(self):
        arena = Arena(0)
        self.mem_manager.add_arena(arena)
        pool = Pool(0)
        self.mem_manager.add_pool("Arena 1", pool)
        block = Block(0)
        self.mem_manager.add_block("Arena 1", "pool 1", block)
        self.assertEqual(self.mem_manager.calculate_pool_memory("Arena 1", "pool 1"), block.mem)

    def test_fill_ram(self):
        obj_mem = 50000  # 50,000 units of memory
        self.mem_manager.fill_ram(obj_mem)
        self.assertEqual(self.mem_manager.memory["used_ram_mem"], obj_mem)
        self.assertGreater(len(self.mem_manager.memory["arenas"]), 0)
        total_arena_mem = sum(arena.arena_obj.mem for arena in self.mem_manager.memory["arenas"].itertuples())
        self.assertEqual(total_arena_mem, obj_mem)
        for arena in self.mem_manager.memory["arenas"].itertuples():
            for pool in arena.pools.itertuples():
                self.assertGreater(len(pool.blocks), 0)

    def test_fill_arena(self):
        obj_mem = 50000  # 50,000 units of memory
        self.mem_manager.fill_ram(obj_mem)

        # Check that at least one arena has been created
        self.assertGreater(len(self.mem_manager.memory["arenas"]), 0)

        # Verify that the total memory in the arena matches the allocated memory
        total_arena_mem = sum(arena.arena_obj.mem for arena in self.mem_manager.memory["arenas"].itertuples())
        self.assertEqual(total_arena_mem, obj_mem)

    def test_fill_pool(self):
        obj_mem = 50000  # 50,000 units of memory
        self.mem_manager.fill_ram(obj_mem)

        # Check that at least one arena has been created
        self.assertGreater(len(self.mem_manager.memory["arenas"]), 0)

        # Check that pools have been created in the arenas
        for arena in self.mem_manager.memory["arenas"].itertuples():
            self.assertGreater(len(arena.pools), 0)

            # Verify that the total memory in the pools matches the allocated memory
            total_pool_mem = sum(pool.pool_obj.mem for pool in arena.pools.itertuples())
            self.assertEqual(total_pool_mem, arena.arena_obj.mem)


    def test_arena_has_pools_column(self):
        arena = Arena(0)
        self.mem_manager.add_arena(arena)
        self.assertIn("pools", self.mem_manager.memory["arenas"].columns)
        self.assertIsInstance(self.mem_manager.memory["arenas"].iloc[0]["pools"], pd.DataFrame)

    def test_pool_has_blocks_column(self):
        arena = Arena(0)
        self.mem_manager.add_arena(arena)
        pool = Pool(0)
        self.mem_manager.add_pool("Arena 1", pool)
        self.assertIn("blocks", self.mem_manager.memory["arenas"].iloc[0]["pools"].columns)
        self.assertIsInstance(self.mem_manager.memory["arenas"].iloc[0]["pools"].iloc[0]["blocks"], pd.DataFrame)

    def test_fill_ram_creates_pools(self):
        obj_mem = 50000  # 50,000 units of memory
        self.mem_manager.fill_ram(obj_mem)
        self.assertEqual(self.mem_manager.memory["used_ram_mem"], obj_mem)
        self.assertGreater(len(self.mem_manager.memory["arenas"]), 0)

        total_pools = 0
        for arena in self.mem_manager.memory["arenas"].itertuples():
            total_pools += len(arena.pools)

        # Assuming each pool can hold a certain amount of memory, we can calculate the expected number of pools
        pool_capacity = Pool().max_mem
        expected_pools = (obj_mem + pool_capacity - 1) // pool_capacity  # Ceiling division

        self.assertEqual(total_pools, expected_pools)
        for arena in self.mem_manager.memory["arenas"].itertuples():
            for pool in arena.pools.itertuples():
                self.assertGreater(len(pool.blocks), 0)

    def test_reuse_free_block(self):
        arena = Arena(0)
        self.mem_manager.add_arena(arena)
        arena_name = "Arena 1"
        self.mem_manager.add_pool(arena_name, Pool(0))

        # Add a block and then remove it
        block = Block(0)
        self.mem_manager.add_block(arena_name, "pool 1", block)

        # Remove the block using its unique identifier
        block_id = block.__hash__()
        self.mem_manager.remove_object(block_id)

        # Check that the block is still in the pool but marked as free
        pool_blocks = self.mem_manager.memory["arenas"].iloc[0]["pools"].iloc[0]["blocks"]
        self.assertEqual(len(pool_blocks), 1)  # Block should still exist
        self.assertTrue(pool_blocks.iloc[0]["block_obj"].is_free)  # Block should be marked as free

        # Add another block, which should reuse the free block
        new_block = Block(0)
        self.mem_manager.add_block(arena_name, "pool 1", new_block)

        # Check that we still have the same number of blocks and it's now allocated
        pool_blocks_after = self.mem_manager.memory["arenas"].iloc[0]["pools"].iloc[0]["blocks"]
        self.assertEqual(len(pool_blocks_after), 1)  # Should still have one block
        self.assertFalse(pool_blocks_after.iloc[0]["block_obj"].is_free)  # Block should be allocated

    def test_dynamic_pool_resizing(self):
        arena = Arena(0)
        self.mem_manager.add_arena(arena)
        pool = Pool(0)
        self.mem_manager.add_pool("Arena 1", pool)

        # Fill the pool to its maximum capacity
        for _ in range(pool.max_mem // 512):  # Assuming each block is 512 bytes
            block = Block(512)
            self.mem_manager.add_block("Arena 1", "pool 1", block)

        # Now add another block, which should trigger the creation of a new pool
        new_block = Block(512)
        self.mem_manager.add_block("Arena 1", "pool 1", new_block)

        # Check that a new pool has been created
        self.assertEqual(len(self.mem_manager.memory["arenas"].iloc[0]["pools"]), 2)

    def test_memory_stats(self):
        # Test initial state
        initial_stats = self.mem_manager.get_memory_stats()
        self.assertEqual(initial_stats["total_arenas"], 0)
        self.assertEqual(initial_stats["total_pools"], 0)
        self.assertEqual(initial_stats["used_memory"], 0)
        self.assertEqual(initial_stats["free_memory"], 1_000_000)  # From setUp
        self.assertEqual(initial_stats["free_blocks"], 0)

        # Add an arena and check stats
        arena = Arena(0)
        self.mem_manager.add_arena(arena)
        after_arena_stats = self.mem_manager.get_memory_stats()
        self.assertEqual(after_arena_stats["total_arenas"], 1)

        # Add a pool and check stats
        pool = Pool(0)
        self.mem_manager.add_pool("Arena 1", pool)
        after_pool_stats = self.mem_manager.get_memory_stats()
        self.assertEqual(after_pool_stats["total_pools"], 1)

        # Add some blocks with actual memory
        block1 = Block(100)  # Block with 100 bytes
        block2 = Block(200)  # Block with 200 bytes
        self.mem_manager.add_block("Arena 1", "pool 1", block1)
        self.mem_manager.add_block("Arena 1", "pool 1", block2)
        
        # Check stats after adding blocks
        after_blocks_stats = self.mem_manager.get_memory_stats()
        self.assertEqual(after_blocks_stats["used_memory"], 300)  # 100 + 200 bytes
        
        # Mark one block as free
        block_id = block1.__hash__()
        self.mem_manager.remove_object(block_id)  # This should mark the block as free

        # Check final stats
        final_stats = self.mem_manager.get_memory_stats()
        self.assertEqual(final_stats["total_arenas"], 1)
        self.assertEqual(final_stats["total_pools"], 1)
        self.assertEqual(final_stats["free_blocks"], 1)  # One block should be free
        self.assertEqual(final_stats["used_memory"], 200)  # Only block2's memory remains
        self.assertEqual(final_stats["free_memory"], 1_000_000 - 200)  # Total - used memory

if __name__ == "__main__":
        unittest.main()