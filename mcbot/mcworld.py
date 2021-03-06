from bravo.entity import Entity, Player
from bravo.world import World as bravo_world
from bravo.chunk import Chunk

from twisted.internet.defer import Deferred, succeed



# wrap bravo's impl. of the World to include managment of
# entities.  kinda just putting together the "factory" and world

# lots of changes because we are now a client.

class World(bravo_world):
    def __init__(self, folder):
        super(World, self).__init__(folder)
        self.entities = {}

    def pathfind(self, start, end, waypoints=[], width=0):
        """
        Width is the amount of chunks around the current chunk to process
        A long width will yield a better path, but takes longer to process,
        will require more memory, and may be slow.

        If chunks are not available a partial path will be given based on
        what chunks are available.

        Waypoints can be added to help guide the pathfinder, or to avoid
        areas.  If waypoints are given and pathfinding fails, then the path
        will be truncated to the last waypoint.

        points to think about:
            unlike most games, the world is manipulatable.
            costs should be taken seriously
            pathfinder should also be given a budget:
                based on the bot's current inventory, what is
                an acceptable cost/time trade off?
                because we just might rather go through some stone (high cost)
                rather than try to completely avoid it, if we have the tools.
            suicide just may be the the answer.

        the z,x axis are easy to find, but acending and decending will have to
        be specifically coded because we will be fighting gravity.

        * possible mechanic is the "dig down/build up" method of tunneling

        * build stars going down if possible
        * if going up, build stairs, or spirals

        * if building tunnels, try to find a mountain to build into, rather than
          just building from current location

        * define zones that digging shouldn't happen (like around base)
        * try to avoid crossing tunnels

        * set diggable blocks to a high cost.

        * costs should be:
            time
            dig cost (per tool class)
            movement
       
        * use minecarts as transportation?
            goap can handle loading/unloading carts if need be
            (how to tie that in with pathfinding???)
 
        """

    def get_surrounding(self, x, y, z, width=0):
        """
        Get a list of blocks surrounding this block.
        There will always be 8 tuples returned.
        This is used for pathfinding with the bot.

        The format is:

        <   X   >

        0   1   2  ^

        3       4  Z

        5   6   7  v

        (...(block_type, height)...)
        """
        sx = 0; ex = 3
        sy = 0; ey = 3
        sz = 0; ez = 3

        # can't do pathfinding accross chunks, yet
        if (x + sx < 0) or (x + ex >= 64) or (z + sz < 0) or (z + ez >= 64):
            return None


    def populate_chunk(self, chunk):
        """
        Override since we don't [really] need [/want] to do this on the client side.
        """
        pass

    def save_chunk(self, chunk):
        """
        For now, its best to just keep it in memory.

        Saving chunks is too impractical/slow in a bot environment (json).
        """
        pass

    def change_block(self, x, y, z, block, meta):
        def set_block(chunk, x, y, z, block, meta):
            chunk.set_block((x, y, z), block)
            chunk.metadata[x, z, y] = meta

        cx, bx = divmod(x, 16)
        cz, bz = divmod(z, 16)

        d = self.request_chunk(cx, cz)
        d.addCallback(set_block, bx, y, bz, block, meta)

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

            # just for now, lets just return a new chunk.
            # in the future, may have have it wait until it comes
            # from the server, idk

            self.dirty_chunk_cache[x, z] = chunk

            return succeed(chunk)            

            #d = Deferred()
            #forked = Deferred()
            #forked.addCallback(lambda none: chunk)
            #d.chainDeferred(forked)
            #self._pending_chunks[x, z] = d
            #return forked    

    def load_chunk(self, x, z):
        """
        As the bot goes through the world, it would be helpful for it to keep records
        of chunks it has been to.
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

    def add_chunk(self, chunk):
        """
        Used by the protocol to add chunks coming in over the wire.
        """

        x, z = chunk.x, chunk.z

        self.dirty_chunk_cache[x, z] = chunk

        if (x, z) in self._pending_chunks:
            self._pending_chunks[x, z].callback(chunk)
            del self._pending_chunks[x, z]
        
        # if it was already in the cache, then its going to get dirty'd
        # with any update.
        if (x, z) in self.chunk_cache:
            del self.chunk_cache[x, z]

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

