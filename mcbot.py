from bravo.entity import Entity, Player
from bravo.alpha import Location
from mcworld import World

# would be nice to remove this dep sometime
from bravo.packets import make_packet



class MinecraftBot(Player):
    def __init__(self, username="", password="", eid=0, *args, **kwargs):
        super(MinecraftBot, self).__init__(eid, username, *args, **kwargs)
        self.password = password
        self.conn = None

        self.hp = 20
        self.world = World()

        self.need_to_respawn = False
        self.tried_animation = False
        
        self.stance_mod = .1

    # laziness
    def wire_out(self, data):
        self.conn.transport.write(data)

    def nearest_player(self):
        pass

    def spin_head(self):
        self.location.yaw += 1
        self.send_orientation_update()

    def move_random(self):
        self.location.x = self.location.x + .5
        #self.stance_mod += .0005
        #self.location.stance = self.location.y - self.stance_mod
        self.send_location_update()

    def set_health(self, hp):
        self.hp = hp
        if self.hp == 0:
            self.need_to_respawn = True

    def tick(self):
        if self.need_to_respawn == True:
            self.conn.transport.write(make_packet("respawn"))
            self.need_to_respawn = False

        if not self.tried_animation:
            #p= make_packet("animate", eid=self.eid, animation="uncrouch")
            #self.conn.transport.write(p)
            self.tried_animation = False

        #p = self.move_random()
        self.spin_head()

    # protocol dependent.  abstraction, plz?
    # the following methods rely on the bravo impl. of the protocol
    def send_orientation_update(self):
        p, l, f = self.location.build_containers()
        self.wire_out(make_packet("orientation", look=l, flying=f))
        
    def send_position_update(self):
        p, l, f = self.location.build_containers()
        self.wire_out(make_packet("position", position=p, flying=f))
        
    def update_location_from_packet(self, packet):
        self.location.load_from_packet(packet)

        

