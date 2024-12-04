from sqlalchemy import event
from sqlalchemy.orm import Session
from sqlalchemy import func
from Schemas import Block, Pool, Arena

# Definiera en funktion som uppdaterar is_free och poolens mem
def update_block_and_pool(mapper, connection, target):
    # Uppdatera is_free baserat på blockets minnesanvändning
    target.is_free = 0 if target.mem == target.max_mem else 1

    # Skapa en ny session
    session = Session(bind=connection)
    
    try:
        # Beräkna summan av mem för alla block i samma pool
        total_mem = session.query(func.sum(Block.mem)).filter(Block.pool_id == target.pool_id).scalar() or 0
        
        # Hämta poolen och uppdatera dess mem
        pool = session.query(Pool).filter(Pool.id == target.pool_id).one()
        pool.mem = total_mem
        
        # Spara ändringarna
        session.commit()
    finally:
        session.close()

# Koppla funktionen till after_update-händelsen för Block
event.listen(Block, 'after_update', update_block_and_pool)

# Definiera en funktion som uppdaterar arenans mem
def update_arena_mem(mapper, connection, target):
    # Skapa en ny session
    session = Session(bind=connection)
    
    try:
        # Beräkna summan av mem för alla pooler i samma arena
        total_mem = session.query(func.sum(Pool.mem)).filter(Pool.arena_id == target.arena_id).scalar() or 0
        
        # Hämta arenan och uppdatera dess mem
        arena = session.query(Arena).filter(Arena.id == target.arena_id).one()
        arena.mem = total_mem
        
        # Spara ändringarna
        session.commit()
    finally:
        session.close()

# Koppla funktionen till after_update-händelsen för Pool
event.listen(Pool, 'after_update', update_arena_mem)

