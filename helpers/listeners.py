from sqlalchemy import event
from sqlalchemy.orm import Session
from sqlalchemy import func
from Schemas import Block, Pool, Arena, MemRam

# Define a function that updates is_free and the pool's memory
def update_block_and_pool(mapper, connection, target):
    # Update is_free based on the block's memory usage
    target.is_free = 0 if target.mem == target.max_mem else 1

    # Create a new session
    session = Session(bind=connection)

    try:
        # Calculate the total memory for all blocks in the same pool
        total_mem = session.query(func.sum(Block.mem)).filter(Block.pool_id == target.pool_id).scalar() or 0

        # Get the pool and update its memory
        pool = session.query(Pool).filter(Pool.id == target.pool_id).one()
        pool.mem = total_mem

        # Save the changes
        session.commit()
    finally:
        session.close()

# Attach the function to the after_update event for Block
event.listen(Block, 'after_update', update_block_and_pool)

# Define a function that updates the arena's memory
def update_arena_mem(mapper, connection, target):
    # Create a new session
    session = Session(bind=connection)

    try:
        # Calculate the total memory for all pools in the same arena
        total_mem = session.query(func.sum(Pool.mem)).filter(Pool.arena_id == target.arena_id).scalar() or 0

        # Get the arena and update its memory
        arena = session.query(Arena).filter(Arena.id == target.arena_id).one()
        arena.mem = total_mem

        # Save the changes
        session.commit()
    finally:
        session.close()

# Attach the function to the after_update event for Pool
event.listen(Pool, 'after_update', update_arena_mem)

# Define a function that updates the arena's memram
def update_arena_memram(mapper, connection, target):
    # Create a new session
    session = Session(bind=connection)

    try:
        # Calculate the total memory for all arenas in the same memram
        total_memram = session.query(func.sum(Arena.mem)).filter(Arena.memram_id == target.memram_id).scalar() or 0

        # Get the memram and update its memory
        memram = session.query(MemRam).filter(MemRam.id == target.memram_id).one()
        memram.mem = total_memram

        # Save the changes
        session.commit()
    finally:
        session.close()

# Attach the function to the after_update event for Arena
event.listen(Arena, 'after_update', update_arena_memram)