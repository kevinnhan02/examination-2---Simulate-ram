from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from Schemas import Base, MemRam, Arena, Pool, Block
from sqlalchemy.sql import func
import helpers.listeners 


class MemManager:
    def __init__(self, db_url: str) -> None:
        # Skapa en databasanslutning
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)  # Skapa tabellerna
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

        # Skapa en ny MemRam-post
        self.memram = MemRam()
        self.session.add(self.memram)
        self.session.commit()

    def add_arena(self) -> Arena:
        """Skapa och lägg till en ny arena i databasen."""
        new_arena = Arena()
        new_arena.memram = self.memram
        self.session.add(new_arena)
        self.session.commit()
        return new_arena

    def add_pool(self, arena: Arena) -> Pool:
        """Skapa och lägg till en ny pool till en specifik arena."""
        new_pool = Pool()
        new_pool.arena = arena
        self.session.add(new_pool)
        self.session.commit()
        return new_pool

    def add_block(self, pool: Pool) -> Block:
        """Skapa och lägg till ett nytt block till en specifik pool."""
        new_block = Block()
        new_block.pool = pool
        self.session.add(new_block)
        self.session.commit()
        return new_block

    def allocate_memory_for_object(self, obj_instance) -> None:
        """Allokera minne för ett objekt genom att skapa nödvändiga arenor, pooler och block."""
        obj_size = obj_instance.__sizeof__()

        # Kontrollera om det finns tillräckligt med minne i MemRam
        if self.memram.max_mem < obj_size:
            raise MemoryError("Inte tillräckligt med minne för att allokera objektet.")
        
        remaining_size = obj_size
        blocks_to_update = []

        # Hämta block som har tillräckligt med utrymme för objektet
        while remaining_size > 0:
            suitable_block = self.session.query(Block).filter(
                Block.is_free == 1,
                Block.max_mem - Block.mem > 0
            ).first()

            if suitable_block:
                # Beräkna hur mycket utrymme som finns kvar i blocket
                available_space = suitable_block.max_mem - suitable_block.mem
                to_allocate = min(remaining_size, available_space)

                # Lägg till del av objektet i blocket
                suitable_block.mem += to_allocate
                suitable_block.is_free = 0 if suitable_block.mem == suitable_block.max_mem else 1
                remaining_size -= to_allocate
                blocks_to_update.append(suitable_block)
            else:
                # Hitta en arena med tillräckligt med utrymme för en ny pool
                arena = self.session.query(Arena).filter(Arena.max_mem - Arena.mem > 0).first()
                if not arena:
                    arena = self.add_arena()
                
                # Kontrollera om det finns tillräckligt med pooler i arenan
                pool = self.session.query(Pool).filter(Pool.arena_id == arena.id, Pool.max_mem - Pool.mem > 0).first()
                if not pool:
                    pool = self.add_pool(arena)
                
                # Skapa ett nytt block i poolen
                block = self.add_block(pool)

                # Beräkna hur mycket utrymme som finns kvar i blocket
                available_space = block.max_mem - block.mem
                to_allocate = min(remaining_size, available_space)

                # Lägg till del av objektet i blocket
                block.mem += to_allocate
                block.is_free = 0 if block.mem == block.max_mem else 1
                remaining_size -= to_allocate
                blocks_to_update.append(block)

        # Batch commit
        self.session.bulk_save_objects(blocks_to_update)
        self.session.commit()

        print(f"Allocated {obj_size} bytes for object across multiple blocks.")

