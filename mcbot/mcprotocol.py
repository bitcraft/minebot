from twisted.internet.protocol import Protocol
from twisted.internet import task
from twisted.internet import reactor
from twisted.python.failure import Failure

from bravo.packets import packets, packets_by_name, make_packet, parse_packets
from bravo.location import Location
from bravo.chunk import Chunk

from construct import Container

import sys, re, urllib2



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

    keep_alive_interval = 60    
    bot_tick_interval = 1000.000 / 1000.000
    #flying_interval = 500.000 / 1000.000
    flying_interval = 200.000 / 1000.000

    # regex to strip names from chat messages
    chat_regex = re.compile("<(.*?)>(.*)")

    def dummy_handler(self, header, packet):
        try:
            print packets[header]
        except KeyError:
            print "unhandled", header

    def __init__(self, bot, world, online=True):
        self.buffer = ""

        self.bot = bot
        bot.conn = self
        
        self.world = world

        # used for handling window actions
        self.action_no = 1

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
        # it might look funny abt "unused".  b/c MAD's packet use this name
        # but a client uses this space for a password
        p = make_packet("login", protocol=8, username=self.username, \
            unused=self.bot.password, seed=0, dimension=0)
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
        self.transport.write(make_packet("flying", flying=self.bot.location.midair))

    def send_keep_alive(self):
        self.transport.write(make_packet("ping"))

    def dataReceived(self, data):
        self.buffer += data
        packets, self.buffer = parse_packets(self.buffer)

        for header, payload in packets:
            if header in packet_handlers:
                packet_handlers[header](self, payload)
            else:
                self.dummy_handler(header, payload)

    @wrap_handler("ping")
    def OnPing(self, packet):
        pass

    @wrap_handler("time")
    def OnTime(self, packet):
        pass

#   C H U N K   R E L A T E D   ============================

    @wrap_handler("prechunk")
    def OnPreChunk(self, packet):
        pass

    @wrap_handler("chunk")
    def OnMapChunk(self, packet):
        return

        def add_chunk(chunk, packet):
            chunk.load_from_packet(packet)
            self.bot.world.add_chunk(chunk)

        def chunk_error(failure):
            print "couldn't parse chunk packet"

        cx, bx = divmod(packet.x, 16)
        cz, bz = divmod(packet.z, 16)

        d = self.world.request_chunk(cx, cz)
        d.addCallback(add_chunk, packet)
        d.addErrback(chunk_error)

    #@wrap_handler("block")
    def OnBlockChange(self, packet):
        self.world.change_block(packet.x, packet.y, packet.z, \
            packet.type, packet.meta)

    #@wrap_handler("batch")
    def OnMultiBlockChange(self, packet):
        for i in xrange(packet.length):
            bx = packet.coords[i] >> 12
            bz = packet.coords[i] >> 8 & 15
            y = packet.coords[i] & 255

            self.world.change_block(bx, y, bz, packet.types[i], \
                packet.metadata[i])

    @wrap_handler("digging")
    def OnPlayerDigging(self, packet):
        print packet

    @wrap_handler("animate")
    def OnAnimation(self, packet):
        pass

    @wrap_handler("health")
    def OnUpdateHealth(self, packet):
        self.bot.hp = packet.hp

    @wrap_handler("spawn")
    def OnPlayer(self, packet):
        pass

    @wrap_handler("position", "orientation", "location")
    def OnPlayerLocationUpdate(self, packet):
        self.bot.update_location_from_packet(packet)

        # part of the login/auth sequence
        if self.confirmed_spawn == False:
            location = Location()
            location.load_from_packet(packet)
            p = location.save_to_packet()
            self.transport.write(p)
            self.confirmed_spawn = True
            self.bot.OnReady()

    #@wrap_handler("destroy")
    def OnDestroy(self, packet):
        print packet

    @wrap_handler("create")
    def OnCreate(self, packet):
        #print "entity", packet
        self.world.add_entity_by_id(packet.eid)

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
        """
        Parse chat messages.

        The Notch server sends messages back that the client sends,
        so we check and skip any messages that we sent.
        Return who sent the message with the text.
        I don't know anything about the color codes, so they are
        not processed.
        """

        match = self.chat_regex.match(packet.message)
        if match == None:
            return

        self.throw()

        who, text = match.groups()
        if who != self.username:
            self.bot.OnChat(who, text)

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

    @wrap_handler("window-open")
    def OnWindowOpen(self, packet):
        print packet

    @wrap_handler("window-close")
    def OnWindowClose(self, packet):
        print packet

    @wrap_handler("window-action")
    def OnWindowAction(self, packet):
        print packet

    def get_action_no(self):
        self.action_no += 1
        return self.action_no

    def throw(self):
        """
        throws item in hand
        
        not sure if this is the correct way to do this.
        simulates a player opening the inventory, clicking an item
        then closing the window with the item in the cursor
        """

        action_no = self.get_action_no()

        slot_no, item = self.bot.inventory.get_filled_slot()
        
        clickit = make_packet("window-action", wid=0, slot=slot_no, button=0, \
            token=action_no, primary=item[0], secondary=item[1] , count=item[2])
        closeit = make_packet("window-close", wid=0)

        print "throwing", slot_no

        
        self.transport.write(clickit)
        self.transport.write(closeit)

    # also used when bot picks up items
    @wrap_handler("window-slot")
    def OnWindowSlot(self, packet):
        self.bot.inventory.update_from_packet(packet)
        print "pickup", packet.slot
        print self.bot.inventory.storage
        print self.bot.inventory.holdables

    @wrap_handler("window-progress")
    def OnWindowProgress(self, packet):
        print packet

    @wrap_handler("window-token")
    def OnWindowToken(self, packet):
        print "action results"
        print "number: %s, status: %s" % (packet.token, packet.acknowledged)

    # sent by server to init the player's inventory
    @wrap_handler("inventory")
    def OnInventory(self, packet):
        self.bot.inventory.load_from_packet(packet)

    @wrap_handler("error")
    def OnKick(self, packet):
        print "Kicked:", packet.message
