from bravo.entity import Entity, Player
from bravo.world import World as bravo_world
from bravo.chunk import Chunk

from twisted.internet.defer import Deferred



# wrap bravo's impl. of the World to include managment of
# entities.  kinda just putting together the "factory" and world

# lots of changes because we are now a client.

class World(bravo_world):
    def __init__(self, folder):
        super(World, self).__init__(folder)
        self.entities = {}

    def populate_chunk(self, chunk):
        """
        Override since we don't [really] need [/want] to do this on the client side.
        """
        pass

    def request_chunk(self, x, z):
        """
        Request a ``Chunk`` to be delivered later.

        :returns: Deferred that will be called with the Chunk
        """

        if (x, z) in self.chunk_cache:
            return succeed(self.chunk_cache[x, z])
        elif (x, z) in self.dirty_chunk_cache:
            return succeed(self.dirty_chunk_cache[x, z])
        elif (x, z) in self._pending_chunks:
            # Rig up another Deferred and wrap it up in a to-go box.
            d = Deferred()
            self._pending_chunks[x, z].chainDeferred(d)
            return d
        else:
            # chunk hasn't been recieved from the server yet
            chunk = Chunk(x, z)

            d = Deferred()
            forked = Deferred()
            forked.addCallback(lambda none: chunk)
            d.chainDeferred(forked)
            self._pending_chunks[x, z] = d
            return forked    

    def load_chunk(self, x, z):
        """
        Actually not needed for the client.
        """

        if (x, z) in self.chunk_cache:
            return self.chunk_cache[x, z]
        elif (x, z) in self.dirty_chunk_cache:
            return self.dirty_chunk_cache[x, z]

        # chuck is not in memory, check if it is on the disk
        chunk = Chunk(x, z)

        first, second, filename = names_for_chunk(x, z)
        f = self.folder.child(first).child(second)
        if not f.exists():
            f.makedirs()
        f = f.child(filename)
        if f.exists() and f.getsize():
            chunk.load_from_tag(read_from_file(f.open("r")))
            self.chunk_cache[x, z] = chunk
            return chunk

        print "attempting to load a chunk that is not available"
        raise Exception

    def add_chunk(self, x, z, chunk):
        """
        Used by the protocol to add chunks coming in over the wire.
        """

        self.dirty_chunk_cache[x, z] = chunk

        if (x, z) in self._pending_chunks:
            self._pending_chunks[x, z].callback(chunk)
            del self._pending_chunks[x, z]

    def add_entity(self, e):
        """
        Add and existing entity to the world.
        
        The entity must already have a eid.
        """
    
        if isinstance(e, Player):
            e.world = self
            
        self.entities[e.eid] = e

    def add_entity_by_id(self, eid):
        """
        Add an entity.
        
        A new entity will be created with the eid supplied.
        """

        e = Entity()
        self.entities[eid] = e
        return e

    def remove_entity_by_id(self, eid):
        """
        Remove an entity from the world.
        """
        
        try:
            del self.entities[eid]
        except:
            pass

    def entities_near(self, x, y, z, radius):
        """
        Given a coordinate and a radius, return all entities within that
        radius of those coordinates.

        All arguments should be in pixels, not blocks.
        """

        return [entity for entity in self.entities
            if sqrt(
                (entity.location.x - x)**2 +
                (entity.location.y - y)**2 +
                (entity.location.z - z)**2
            ) < radius]

    def update_entity(self, eid, x, y, z, relative=False):
        pass

