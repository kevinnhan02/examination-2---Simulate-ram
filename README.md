# Memory Management System

## Summary

This project involves implementing a memory management system that mimics Python's memory management. The system includes classes for managing memory allocation and deallocation, tracking memory usage, and optimizing memory management.

## Tasks for Students

1. **Task 1: Create the Arena, Pool, and Block Classes**
   - Define a class Arena that holds several pools.
   - Define a class Pool that holds several blocks.
   - Define a class Block that represents a memory unit to store a value.

2. **Task 2: Implement Block Allocation and Deallocation**
   - Write methods in the MemoryManager class to allocate a block of memory (i.e., add a block to a pool).
   - Write methods to deallocate a block (i.e., remove a block from a pool).

3. **Task 3: Use Custom Data Types in Blocks**
   - Extend the block class to store different data types (e.g., integers, strings, custom objects).
   - Write a method to add an object of custom data type (like a class instance) into the block.

4. **Task 4: Automatic Pool Creation and Management**
   - When the current pool is full, automatically create a new pool in the memory manager.
   - Write logic to manage the pools within an arena and assign blocks to the appropriate pool.

5. **Task 5: Track Free Blocks**
   - Implement a method to track free blocks and reuse them instead of allocating new memory.

6. **Task 6: Implement a Memory Manager Class**
   - Create the MemoryManager class that interacts with the Arena, Pool, and Block classes.
   - This class should handle adding/deleting blocks and creating new pools or arenas as needed.

7. **Task 7: Add Performance Monitoring**
   - Add a feature that tracks memory usage and displays statistics on the number of blocks and pools in use.

8. **Task 8: Simulate Data Storage**
   - Simulate storing a variety of data types, such as integers, strings, and objects, within the allocated blocks.

9. **Task 9: Test the Memory Manager**
   - Write tests that allocate and deallocate blocks in different scenarios (e.g., filling up a pool, deleting a block, etc.).

10. **Task 10: Optimize the Memory Management System**
    - Challenge students to implement optimization techniques, such as reusing deleted blocks or balancing the number of pools in use.

## Code Explanation

### Listeners

The `listeners.py` module defines event listeners for SQLAlchemy ORM models. These listeners update memory usage statistics for blocks, pools, and arenas whenever changes occur.

- **update_block_and_pool**: Updates the `is_free` attribute based on the block's memory usage and updates the pool's memory.
- **update_arena_mem**: Updates the arena's memory based on the total memory of its pools.

### MemoryManager

The `memorymanager.py` module contains the `MemManager` class, which manages memory allocation and deallocation. It includes methods for adding arenas, pools, and blocks, allocating memory for objects, freeing memory, and performing manual garbage collection.

- **allocate_memory_for_object**: Allocates memory for an object by creating necessary arenas, pools, and blocks. It checks if the object is already stored, finds suitable blocks, and allocates memory to them. If no suitable block is found, it creates new blocks, pools, and arenas as needed.
- **free_memory_for_object**: Frees memory for an object by updating the ledger and blocks. It identifies the blocks associated with the object and marks them as free.
- **is_object_stored**: Checks if the object is already stored in the database.
- **find_suitable_block**: Finds a suitable block that has enough space for the object.
- **allocate_to_block**: Allocates part of the object to a block.
- **allocate_to_new_block**: Allocates part of the object to a new block in a new pool and arena if necessary.
- **add_arena**: Creates a new arena and adds it to the `MemRam` table.
- **add_pool**: Creates a new pool and adds it to the arena table.
- **add_block**: Creates a new block and adds it to the pool table.
- **print_memory_statistics**: Prints memory usage statistics, including the total number of arenas, pools, blocks, total allocated memory, and total free memory.
- **remove_unused_resources**: Removes all unused blocks, pools, and arenas. This method identifies and removes blocks that are not used, pools that are empty, and arenas that are empty.

### Database Models

The `database_models.py` module defines the SQLAlchemy ORM models for the memory management system. It includes classes for `MemRam`, `Arena`, `Pool`, `Block`, `StoredObject`, and `Ledger`.

- **MemRam**: Represents the main memory space, managing multiple arenas.
- **Arena**: Represents a large memory space, managing multiple pools.
- **Pool**: Represents a chunk of memory that contains blocks.
- **Block**: Represents a small portion of memory allocated to store a value.
- **StoredObject**: Represents an object stored in the memory management system.
- **Ledger**: Represents a ledger entry for tracking memory allocations.

## Installation

To install the required dependencies, run:

```bash
pip install -r [requirements.txt](http://_vscodecontentref_/2)