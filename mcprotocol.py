from twisted.internet.protocol import Protocol
from twisted.internet import task
from twisted.internet import reactor

from bravo.packets import packets_by_name, make_packet, parse_packets
from bravo.alpha import Location
from bravo.chunk import Chunk
import urllib2

import sys



packet_handlers = {}



# make the handlers a little more obvious by using decorators.
# functions warapped will automatically be added the the handlers
# dictionary of the protocol.
# look at bravo.packets for the name dict used
def wrap_handler(*types):
    def wrap_it(func):
        for t in types:
            packet_handlers[packets_by_name[t]] = func
        def wrapped(self, *args, **kwargs):
            func(*args, **kwargs)
        return wrapped
    return wrap_it



class MinecraftClientProtocol(Protocol):
    """
    Impliment v.8 of the Minecraft Protocol for clients

    """

    server_version = 12

    login_url = "http://www.minecraft.net/game/getversion.jsp"
    vfy_url   = "http://www.minecraft.net/game/checkserver.jsp"
    join_url  = "http://www.minecraft.net/game/joinserver.jsp"

    keep_alive_interval = 30    # seconds between each keep-alive packet
    bot_tick_interval = 0.125
    flying_interval = 3


    def __init__(self, bot, world, online=True):
        self.buffer = ""

        self.bot = bot
        bot.conn = self
        
        self.world = world

        online = False

        # after client is ready, sends this back to the server
        self.confirmed_spawn = False

        if online:
            self.username = self.main_login(bot.username, bot.password)
        else:
            self.username = bot.username

        if self.username == None:
            reactor.stop()

    def connectionMade(self):
        self.transport.write(make_packet("handshake", username=self.username))

    def connectionLost(self, reason):
        print "Lost connection:", reason
        try:
            self.keep_alive.cancel()
            self.bot_tick.cancel()
        except:
            pass

    # this is the login for minecraft.net
    def main_login(self, user, passwd, server_ver=None):
        if server_ver == None:
            server_ver = self.server_version

        o = "?user=%s&password=%s&version=%s" % (user, passwd, server_ver)
        c = urllib2.urlopen(self.login_url + o).read()
        try:
            ver, ticket, user, sid = c.split(":")[:4]
        except:
            return None

        self.sid = sid
        return user

    # this is the login for the server
    def server_login(self):
        p = make_packet("login", protocol=8, username=self.username, \
            password=self.bot.password, seed=0, dimension=0)
        self.transport.write(p)

    # ask the server what kind of authentication to use
    def check_auth(self, hash):
        o = "?user=%s&sessionId=%s&serverID=%s" % (self.username, self.sid, hash)
        c = urllib2.urlopen(self.join_url + o).read()
        return c.lower() == "ok"

    # serverID aka "server hash"
    def verify_name(self, serverID):
        o = "?user=%s&serverID=%s" % (self.username, serverID)
        c = urllib2.urlopen(self.vfy_url + o).read()
        return c.lower() == "yes"

    def send_flying(self):
        self.transport.write(make_packet("flying", flying=False))

    def send_keep_alive(self):
        self.transport.write(make_packet("ping"))

    def dataReceived(self, data):
        self.buffer += data
        packets, self.buffer = parse_packets(self.buffer)

        for header, payload in packets:
            if header in packet_handlers:
                packet_handlers[header](self, payload)
            else:
                pass

#   C H U N K   R E L A T E D   ============================

    @wrap_handler("prechunk")
    def OnPreChunk(self, packet):
        pass

    @wrap_handler("chunk")
    def OnMapChunk(self, packet):
        cx = (packet.x / 16)
        cz = (packet.z / 16)

        chunk = Chunk(cx, cz)

        try:
            chunk.load_from_packet(packet)
        except ValueError:
            print "ValueError!  Cannot load from packet.  (seems to be a bug)" 
            raise
        else:
            self.bot.world.add_chunk(cx, cz, chunk)

    @wrap_handler("block")
    def OnBlockChange(self, packet):
        print int(self.bot.location.x)
        print int(self.bot.location.z)
        print int(self.bot.location.y)
        print "BLOCK CHANGE"
        print packet

        if not self.bot.is_walking():
            self.bot.move_to(packet.x, packet.z)

    @wrap_handler("batch")
    def OnMultiBlockChange(self, packet):
        print "MULTI BLOCK CHANGE"

    @wrap_handler("digging")
    def OnPlayerDigging(self, packet):
        print packet

    @wrap_handler("animate")
    def OnAnimation(self, packet):
        print packet

    @wrap_handler("health")
    def OnUpdateHealth(self, packet):
        self.bot.hp = packet.hp

    @wrap_handler("spawn")
    def OnPlayer(self, packet):
        pass

    @wrap_handler("position", "orientation", "location")
    def OnPlayerLocationUpdate(self, packet):
        self.bot.update_location_from_packet(packet)

        if self.confirmed_spawn == False:
            location = Location()
            location.load_from_packet(packet)
            p = location.save_to_packet()
            self.transport.write(p)
            self.confirmed_spawn = True
            self.bot.OnReady()

    @wrap_handler("entity-position", "entity-orientation", "entity-location")
    def OnEntityLocationUpdate(self, packet):
        #print packet
        pass
 
    @wrap_handler("teleport")
    def OnEntityTeleport(self, packet):
        #print packet
        pass

    @wrap_handler("chat")
    def OnChat(self, packet):
        pass

    @wrap_handler("handshake")
    def OnHandshake(self, packet):
        username = packet.username
        if username == "ok":
            self.auth = True
        elif username == "-":
            self.auth = True
        elif username == "+":
            print "joining password protected servers is not implemented [yet]"
            sys.exit()
        else:
            self.auth = self.check_auth(username)

        self.server_login()

    @wrap_handler("login")
    def OnLoginResponse(self, packet):
        # hack, b/c not implimenting the client protocol
        self.bot.eid = packet.protocol

        self.keep_alive = task.LoopingCall(self.send_keep_alive)
        self.keep_alive.start(self.keep_alive_interval)

        self.flying_tick = task.LoopingCall(self.send_flying)
        self.flying_tick.start(self.flying_interval)
        
        self.bot_tick = task.LoopingCall(self.bot.tick)
        self.bot_tick.start(self.bot_tick_interval)

    @wrap_handler("create")
    def OnEntity(self, packet):
        self.world.add_entity_by_id(packet.eid)

    @wrap_handler("error")
    def OnKick(self, packet):
        print "Kicked:", packet.message
