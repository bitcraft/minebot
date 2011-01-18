from bravo.entity import Entity, Player
from bravo.alpha import Location
from bravo.blocks import block_names
from bravo.utilities import split_coords
from bravo.packets import make_packet
from mcworld import World

import random


class MinecraftBot(Player):
    def __init__(self, username="", password="", eid=0, *args, **kwargs):
        super(MinecraftBot, self).__init__(eid, username, *args, **kwargs)
        self.password = password
        self.conn = None

        self.hp = 20
        self.world = None

        self.is_ready = False
        self.need_to_respawn = False
        self.tried_animation = False
        
        self.stance_mod = .1

        self.cmd_queue = []

    # should be called by the protocol to signal the bot that it is ready
    # to move around and do stuff.
    def OnReady(self):
        print "READY"
       
        self.gravity()
 
        self.is_ready = True

        l = Location()
        
        l.x = self.location.x - 5
        l.z = self.location.z - 5
       
        g = self.change_movement(l, None, 5)

        self.cmd_queue.append(g)

    def OnChat(self, message):
        """
        Handle chat messages

        """
        print "in>", message
        self.wire_out(make_packet("chat", message="i hear something!")) 

    def print_block(self, chunk, callbackArgs=None):
        x, z, y = callbackArgs

        print x, z, int(y)
        print block_names[chunk.blocks[x, z, int(y) - 5]]

    def gravity(self):
        """
        my small brain cant really figure out gravity, so, here is a stab at it

        probably not fast, so to be used sparingly
        """

        print "flying", self.location.midair

        if self.location.midair:
            cx, bx, cz, bz = split_coords(self.location.x, self.location.z)

            d = self.world.request_chunk(cx, cz)
            d.addCallback(self.print_block, \
                callbackArgs=(bx, bz, self.location.y))

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
        self._hp = hp
        if self._hp == 0:
            self.need_to_respawn = True
    health = property(hp_getter, hp_setter)

    def handle_queue(self):
        try:
            if self.is_ready:
                p = self.cmd_queue[0].next()
                #self.wire_out(p)
        except StopIteration:
            print "stop"
            self.cmd_queue.pop()
        except IndexError:
            pass
        except:
            pass

    def tick(self):
        if self.need_to_respawn == True:
            self.send_respawn()
            self.need_to_respawn = False

        if not self.tried_animation:
            #p= make_packet("animate", eid=self.eid, animation="uncrouch")
            #self.wire_out(p)
            self.tried_animation = False

        #if self.is_ready:
        #    if not self.is_walking():
        #        self.move_random()

        # just spam packets to the bot.  looks funny, too.
        # self.spin_head()

        # handle commands in the que.  yep. 
        self.handle_queue()
    
    # give a request to the bot to move somewhere or position itself
    # return a generator that will return packets so that the movement
    # is smooth.  the packets will be written to the wire at regular
    # intervals.  
    # NOTE: wouldn't it be real nice if we implimented position as a vector?
    # Would look a lot better if plugging in some real math.  splines, anyone?
    def change_movement(self, location, position, t):
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
            
            #p, l, f = this_loc.build_containers()

            self.send_position_update()

            yield None

            #yield make_packet("position", position=p, flying=f)

    # protocol dependent.  abstraction, plz?
    # the following methods rely on the bravo impl. of the protocol    

    # laziness
    def wire_out(self, data):
        self.conn.transport.write(data)

    def send_respawn(self):
        self.wire_out(make_packet("respawn"))
    
    def send_orientation_update(self):
        p, l, f = self.location.build_containers()
        self.wire_out(make_packet("orientation", look=l, flying=f))
 
    def send_position_update(self):
        p, l, f = self.location.build_containers()
        print p.x, p.z 
        self.wire_out(make_packet("position", position=p, flying=f))
        
    def update_location_from_packet(self, packet):
        self.location.load_from_packet(packet)

        

