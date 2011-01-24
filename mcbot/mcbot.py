from bravo.entity import Entity, Player
from bravo.location import Location
from bravo.blocks import block_names
from bravo.packets import make_packet
from mcworld import World

import random

from math import ceil

"""
notes

ragnorok engine's maths would be helpful here.
some actions wait for a response from the server --
    it would be helpful to make all actions call a defered
    we can use twisted defered framework to leverage scripts

    actions that we would want to use in a scripting environment 
    should have flags that control how they are scheduled
    for example...we can start moving to a place, then swtich item in hand
        * send command to move (marked as not blocking)
        * send command to change item in hand
    and so on.

    this could be handled by twisted's defered, or by the GOAP scheduler

bot needs a backend control.
could just use cmd.py (again)
"""


def split_coords(z, x):
    cx, bx = divmod(int(x), 16)
    cz, bz = divmod(int(z), 16)
    return cx, bx, cz, bz


class MinecraftBot(Player):
    def __init__(self, username="", password="", eid=0, *args, **kwargs):
        super(MinecraftBot, self).__init__(eid, username, *args, **kwargs)
        self.password = password
        self.conn = None

        self.hp = 20
        self.world = None

        # what chunk we are currently on
        self.chunk = None

        self.is_ready = False
        self.need_to_respawn = False
        self.tried_animation = False
        self.last_sent_chat = ""
        
        self.stance_mod = .1

        self.cmd_queue = []

    def OnReady(self):
        """
        Called by the protocol when the player/bot is ready to move around.
        """

        print "READY"
        self.is_ready = True

    def OnChatIn(self, who, text):
        """
        Handle chat messages

        Don't know if the color control codes go here or not.
        So, they are not checked for/stripped yet.
        """

        # be annoying
        #self.send_chat(text + "?")

    def OnChangeLocation(self):
        """
        Called when our location changes
        """

        cx, bx, cz, bz = split_coords(self.location.x, self.location.z)

        if self.chunk == None:
            d = self.world.request_chunk(cx, cz)
            d.addCallback(self.set_chunk)

        elif (cz != self.chunk.x) or (cz != self.chunk.z):
            d = self.world.request_chunk(cx, cz)
            d.addCallback(self.set_chunk)
    
    def set_chunk(self, chunk):
        self.chunk = chunk

    def set_location(self, location):
        """
        Call to set the location.

        Please don't call the location directly, we have hooks on the bot to manage here.
        """
        
        self.location = location
        self.OnChangeLocation()

    def gravity(self):
        """
        Does not model physics.
        Only falls through air (not water, sand, etc)
        """

        # our world/chunk may not be ready
        if self.chunk == None:
            return

        cx, bx = divmod(int(self.location.x), 16)
        cz, bz = divmod(int(self.location.z), 16)

        # somehow these are not really aligned properly
        bx -= 1
        bz -= 1
   
        # we need to look for the next block that we can fall onto 
        by = int(self.location.y -0.1)

        if self.chunk.blocks[bx, bz, by] == 0:
            print "falling!"
            self.location.midair = True
            self.location.y -= .1
            self.send_position_update()
        else:
            self.midair = False

        return

    def look_at_nearest_entity(self):
        l = self.world.get_surrounding_entities(self, 10)
        if len(l) > 0:
            # sort
            # find direction in 3d
            # point head in direction
            self.send_orientation_update()

    def nearest_player(self):
        self.world.get_surrounding(self) 

    def spin_head(self):
        # just a way to visually see a bot tick
        self.location.yaw += 1
        self.send_orientation_update()

    def is_walking(self):
        """
        Is the bot walking?

        Look through the command que and return True if there are
        any pending operations that will make it move.
        """
        
        # NOTE:  this is obviously a hack
        return len(self.cmd_queue) != 0

    def move_to(self, x, z):
        """
        Move to the place.  Don't do pathfinding.

        """

        l = Location()
        l.x = x
        l.z = z

        g = self.change_movement(l, None, 3)
        self.cmd_queue.append(g)

    def move_random(self):
        """
        Just move the bot around...

        There are no tests about the world geometry, etc
        """

        l = Location()
        
        l.x = self.location.x + 2 - random.random() * 4
        l.z = self.location.z + 2 - random.random() * 4
        
        g = self.change_movement(l, None, 5)

        self.cmd_queue.append(g)

    def hp_getter(self):
        return self._health

    def hp_setter(self, hp):
        print "hp is", hp
        self._hp = hp
        # sometimes the hp gets set super high when player is killed
        if (hp > 20) or (hp <= 0):
            self.need_to_respawn = True
    hp = property(hp_getter, hp_setter)

    def handle_queue(self):
        try:
            if self.is_ready:
                p = self.cmd_queue[0].next()
                self.wire_out(p)
        except StopIteration:
            self.cmd_queue.pop()
        except IndexError:
            pass
        except:
            pass

    def tick(self):
        if self.need_to_respawn == True:
            self.send_respawn()
            self.need_to_respawn = False

        self.gravity()

        #self.spin_head()

        # handle commands in the que.  yep. 
        #self.handle_queue()
    
    def change_movement(self, location, position, t):
        """
        give a request to the bot to move somewhere or position itself
        return a generator that will return packets so that the movement
        is smooth.  the packets will be written to the wire at regular
        intervals.  
        NOTE: wouldn't it be real nice if we implimented position as a vector?
        Would look a lot better if plugging in some real math.  splines, anyone?
        """

        this_loc = Location()

        this_loc.x = self.location.x
        this_loc.z = self.location.z

        steps = float(t) / float(self.conn.bot_tick_interval)
   
        x_origin = self.location.x
        x_offset = 0
        x_dist = location.x - self.location.x
        x_step = x_dist / steps
        
        z_origin = self.location.z
        z_offset = 0
        z_dist = location.z - self.location.z
        z_step = z_dist / steps

        arrived = False

        while arrived == False:
            if abs(x_offset) < abs(x_dist):
                x_offset += x_step
                this_loc.x = x_origin + x_offset
            else:
                arrived = True
            
            if abs(z_offset) < abs(z_dist):
                z_offset += z_step
                this_loc.z = z_origin + z_offset
                arrived = False

            self.location.x = this_loc.x
            self.location.z = this_loc.z
            
            p, l, f = self.location.build_containers()

            yield make_packet("position", position=p, flying=f)

    # the following methods rely on the bravo impl. of the protocol    

    # laziness
    def wire_out(self, data):
        self.conn.transport.write(data)
        print "out >>", data.__repr__()

    def send_respawn(self):
        self.wire_out(make_packet("respawn"))
        self.conn.confirmed_spawn = False    

    def send_orientation_update(self):
        p, l, f = self.location.build_containers()
        self.wire_out(make_packet("orientation", look=l, flying=f))
 
    def send_position_update(self):
        p, l, f = self.location.build_containers()
        self.wire_out(make_packet("position", position=p, flying=f))
        
    def update_location_from_packet(self, packet):
        # the server will occasionally send packets the client
        # correcting position.
        self.location.load_from_packet(packet)

