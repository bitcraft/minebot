#!/usr/bin/python2.5

# special thanks to the bravo project!

from twisted.internet.protocol import Protocol, ClientFactory
from twisted.internet import reactor, task

import urllib2
import sys

from packets import make_packet, parse_packets
from packet_names import *

from bravo.entity import Entity, Player
from bravo.alpha import Location

server = "127.0.0.1"
port   = 25565

# wrap up functions to add themselves to the packet handler
def handler(func, packet_type):
    return func

class World:
    def __init__(self):
        self.entities = {}

    def add_entity(self, eid):
        e = Entity()
        self.entities[eid] = e
        return e

    def update_entity(self, eid, x, y, z, relative=False):
        pass

class MinecraftBot(Player):
    def __init__(self, eid=0, username="", conn=None, *args, **kwargs):
        super(MinecraftBot, self).__init__(eid, username, *args, **kwargs)
        self.conn = conn
        self.hp = 20

        self.need_to_respawn = False

        self.tried_animation = False
        self.stance_mod = .1

    def update_location_from_packet(self, packet):
        print "new location!"
        self.location.load_from_packet(packet)
        print self.location

    def spin_head(self):
        self.location.yaw += 1
        p, l, f = self.location.build_containers()
        return make_packet("orientation", look=l, flying=f)

    def move_random(self):
        print self.location
        self.location.x = self.location.x + 0.0005
        #self.location.z = int(self.location.z /32)
        #self.stance_mod += .0005
        #self.location.stance = self.location.y - self.stance_mod
        p, l, f = self.location.build_containers()
        return make_packet("position", position=p, flying=f)

    def set_health(self, hp):
        self.hp = hp
        if self.hp == 0:
            self.need_to_respawn = True

    def tick(self):
        if self.need_to_respawn == True:
            print "trying to respawn"
            self.conn.transport.write(make_packet("respawn"))
            self.need_to_respawn = False

        if not self.tried_animation:
            #p= make_packet("animate", eid=self.eid, animation="uncrouch")
            #self.conn.transport.write(p)
            self.tried_animation = False

        #p = self.move_random()
        p = self.spin_head()
        self.conn.transport.write(p)

class MinecraftProtocol(Protocol):
    login_url = "http://www.minecraft.net/game/getversion.jsp"
    vfy_url  = "http://www.minecraft.net/game/checkserver.jsp"
    join_url = "http://www.minecraft.net/game/joinserver.jsp"

    keep_alive_interval = 30    # seconds between each keep-alive packet
    bot_tick_interval = .05
    flying_interval = 3

    def do_nothing(self, *arg, **kwarg):
        pass

    def __init__(self, user, passwd, online=True):
        self.buffer = ""

        self.bot = MinecraftBot(username=user, conn=self)
        self.world = World()

        online = False

        self.passwd = passwd

        # after client is ready, sends this back to the server
        self.confirmed_spawn = False

        self.handlers = {
            KEEP_ALIVE:                self.OnKeepAlive,
            HANDSHAKE:                 self.OnHandshake,
            LOGIN_RESPONSE:            self.OnLoginResponse,
            TIME_UPDATE:               self.do_nothing,
            SPAWN_POSITION:            self.do_nothing,
            UPDATE_HEALTH:             self.OnUpdateHealth,
            ADD_TO_INVENTORY:          self.do_nothing,
            NAMED_ENTITY_SPAWN:        self.OnPlayer,
            PICKUP_SPAWN:              self.do_nothing,
            COLLECT_ITEM:              self.do_nothing,
            ADD_OBJECT:                self.do_nothing,
            MOB_SPAWN:                 self.do_nothing,

            ENTITY:                    self.OnEntity,
            DESTROY_ENTITY:            self.do_nothing,
            ENTITY_RELATIVE_MOVE:      self.OnEntityRelativeMove,
            ENTITY_LOOK:               self.OnEntityLook,
            ENTITY_LOOK_RELATIVE_MOVE: self.OnEntityLookRelativeMove,
            ENTITY_TELEPORT:           self.OnEntityTeleport,
            ENTITY_VELOCITY:           self.do_nothing,
            
            PLAYER:                    self.do_nothing,
            PLAYER_LOOK:               self.OnPlayerLocationUpdate,
            PLAYER_POSITION_AND_LOOK:  self.OnPlayerLocationUpdate,
            PLAYER_DIGGING:            self.do_nothing,

            DEATH_ANIMATION:           self.do_nothing,
            PRE_CHUNK:                 self.do_nothing,
            MAP_CHUNK:                 self.do_nothing,
            MULTI_BLOCK_CHANGE:        self.do_nothing,
            BLOCK_CHANGE:              self.OnBlockChange, 
            OPEN_WINDOW:               self.do_nothing,
            TRANSACTION:               self.do_nothing,

            ANIMATION:                 self.OnAnimation,
            HOLDING_CHANGE:            self.do_nothing,

            INVENTORY_CLOSE:           self.do_nothing,
            INVENTORY_CHANGE:          self.do_nothing,
            SET_SLOT:                  self.do_nothing,
            INVENTORY:                 self.do_nothing,
            SIGN:                      self.do_nothing,

            KICK:                      self.OnKick            
        }

        if online:
            self.user = self.main_login(user, passwd)
        else:
            self.user = user

        if self.user == None:
            reactor.stop()


    # this is the login for minecraft.net
    def main_login(self, user, passwd, server_ver=12):
        o = "?user=%s&password=%s&version=%s" % (user, passwd, server_ver)
        c = urllib2.urlopen(self.login_url + o).read()
        print "main login:", c
        try:
            ver, ticket, user, sid = c.split(":")[:4]
        except:
            return None

        self.sid = sid

        return user

    # this is the login for the server
    def server_login(self):
        p = make_packet("login", protocol=8, username=self.user, password=self.passwd, seed=0, dimension=0)
        self.transport.write(p)

    def check_auth(self, hash):
        o = "?user=%s&sessionId=%s&serverID=%s" % (self.user, self.sid, hash)
        c = urllib2.urlopen(self.join_url + o).read()
        print "check auth", c
        if c.lower() == "ok":
            return True
        else:
            return False

    # serverID aka "server hash"
    def verify_name(self, serverID):
        o = "?user=%s&serverID=%s" % (self.user, serverID)
        c = urllib2.urlopen(self.vfy_url + o).read()
        print "verify name", c
        if c.lower() == "yes":
            return True
        else:
            return False

    def dataReceived(self, data):
        self.buffer += data
        packets, self.buffer = parse_packets(self.buffer)

        for header, payload in packets:
            if header in self.handlers:
                self.handlers[header](payload)
            else:
                print "cannot process packed %d" % header
                print payload

    def OnAnimation(self, packet):
        print "ani"
        print packet

    def OnUpdateHealth(self, packet):
        self.bot.set_health(packet.hp)

    def send_flying(self):
        self.transport.write(make_packet("flying", flying=False))

    def send_keep_alive(self):
        self.transport.write(make_packet("ping"))

    def OnPlayer(self, packet):
        pass

    def OnPlayerLocationUpdate(self, packet):
        self.bot.update_location_from_packet(packet)

        if self.confirmed_spawn == False:
            location = Location()
            location.load_from_packet(packet)
            p = location.save_to_packet()
            self.transport.write(p)
            self.confirmed_spawn = True

    # keep the connection alive
    def OnKeepAlive(self, packet):
        pass

    #@handler(HANDSHAKE)
    def OnHandshake(self, packet):
        username = packet.username
        if username == "ok":
            self.auth = True
        elif username == "-":
            self.auth = True
        elif username == "+":
            print "cannot join password protected server"
            sys.exit()
        else:
            self.auth = self.check_auth(username)

        self.server_login()

    def OnLoginResponse(self, packet):
        # hack, b/c not implimenting the client protocol
        self.bot.eid = packet.protocol

        self.keep_alive = task.LoopingCall(self.send_keep_alive)
        self.keep_alive.start(self.keep_alive_interval)

        self.flying_tick = task.LoopingCall(self.send_flying)
        self.flying_tick.start(self.flying_interval)
        
        self.bot_tick = task.LoopingCall(self.bot.tick)
        self.bot_tick.start(self.bot_tick_interval)

    def OnEntity(self, packet):
        self.world.add_entity(packet.eid)

    def OnEntityRelativeMove(self, packet):
        eid, x, y, z = packet.eid, packet.x, packet.y, packet.z
        self.world.update_entity(eid, x, y, z)

    def OnEntityLook(self, packet):
        pass

    def OnEntityLookRelativeMove(self, packet):
        pass

    def OnEntityTeleport(self, packet):
        eid, x, y, z = packet.eid, packet.x, packet.y, packet.z
        self.world.update_entity(eid, x, y, z)

    def OnBlockChange(self, packet):
        pass

    def OnKick(self, packet):
        print "Kicked:", packet.message

    def connectionMade(self):
        print "Handshaking..."
        self.transport.write(make_packet("handshake", username=self.user))

    def connectionLost(self, reason):
        print "Lost connection:", reason
        try:
            self.keep_alive.cancel()
            self.bot_tick.cancel()
        except:
            pass

class MineBotClientFactory(ClientFactory):
    def __init__(self, user, passwd):
        self.user = user
        self.passwd = passwd

    def buildProtocol(self, addr):
        p = MinecraftProtocol(self.user, self.passwd)
        return p

    def clientConnectionLost(self, conn, reason):
        print "Lost connection:", reason
        reactor.stop()

    def clientConnectionFailed(self, conn, reason): 
        print "Connection failed:", reason
        reactor.stop()

if __name__ == "__main__":
    #sys.exit()

    user = "b2"
    passwd = "akujin123"

    # hand control over to twisted
    reactor.connectTCP(server, port, MineBotClientFactory(user, passwd))

    reactor.run()



