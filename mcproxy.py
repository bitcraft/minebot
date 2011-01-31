#!/usr/bin/python2.5

# [part of] a very special minecraft beta bot
# leif.theden@gmail.com

# special thanks to the bravo project!

from twisted.internet.protocol import Protocol, Factory, ClientFactory
from twisted.internet import reactor

from bravo.packets import packets, packets_by_name, make_packet, parse_packets

from mcshell import ProxyShell

"""
this proxy works with an existing python/twisted setup.

put in information here, and connect to localhost on smp
just as you would another server.  data will be filtered
here and forwarded to the remote host defined here.

* if testing locally, do not forget that you cannot use
  the default port for your local server.  you should change
  the listening port on your minecraft server.
"""


# information on what server to connect to
remote_host = "127.0.0.1"
remote_port = 24565

# information on what to listen on
listen_port = 25565

def info(text):
    print text

def error(text):
    print text

# use name from bravo's "packets_by_name"
ignore = ["chunk", "ping", "flying", "create", "entity-position", "time"]

# reverse the packets by name dict
packets_by_id = dict([(v, k) for (k, v) in packets_by_name.iteritems()])

# set our ignored packets
ignore = [ packets_by_name[x] for x in ignore ]


class ProxyPlugin(object):
    """
    Plugins have a super simple interface and are designed to be used
    in an interactive shell from within the game.
    """

    def __init__(self, c):
        self._enabled = False
        self.connection = c
        try:
            [ setattr(self, v, None) for v in self.variables ]
        except:
            pass

    def set(self, name, value):
        name = name.strip("-")
        try:
            getattr(self, name)
        except AttributeError:
            return "Cannot set %s.  Variable doesn't exist.\n"
        else:
            setattr(self, name, value)

    def get(self, name):
        name = name.strip("-")
        try:
            return str(getattr(self, name))
        except AttributeError:
            return "Cannot get %s.  Variable doesn't exist.\n"

    def enable(self):
        self._enabled = True

    def disable(self):
        self._endabled = False

    def write(self, data):
        if self._enabled:
            return self.filter(data)

    def packet(self, header, payload):
        """
        Expects a header and payload from a packet.
        Do not send raw data.
        Return the packet the packet you want to be sent.

        Make SURE to return the payload even if you dont actually change it.
        """
        raise NotImplementedError

    def filter(self, data):
        """
        Data is direct from the socket if the plugin is enabled.
        Return the data you want to be sent instead.

        Make SURE to return data even if you dont actually change it.
        """
        raise NotImplementedError

class ShellPlugin(ProxyPlugin):
    """
    Default plugin to allow use of a shell
    """
    variables = ['escape_key']

    def __init__(self, c, stdout, key):
        super(ShellPlugin, self).__init__(c)
        self.chat_header = packets_by_name["chat"]
        self.escape_key = key
        self.shell = ProxyShell(self, stdout)

    def packet(self, header, payload):
        if self._enabled:
            if header == self.chat_header:
                if payload.message[0] == self.escape_key:
                    # our shell cannot handle unicode...just convert it to plain ascii
                    msg = str(payload.message[1:])
                    self.shell.onecmd(msg)

class PacketParser(ProxyPlugin):
    """
    Filters packets based on the bravo library's definations.
    Plugins can be added to this plugin.

    Plugins added must have a "packet" function

    Does not filter packets, yet.
    """

    def __init__(self, c):
        super(PacketParser, self).__init__(c)
        self.plugins = []
        self.buffer = ""
        self.ignore = []

    def add_plugin(self, plugin):
        self.plugins.append(plugin)

    def remove_plugin(self, plugin):
        try:
            self.plugins.remove(plugin)
        except ValueError:
            pass

    def filter(self, data):
        if self._enabled:
            self.buffer += data
            packets, self.buffer = parse_packets(self.buffer)

            for header, payload in packets:
                [ p.packet(header, payload) for p in self.plugins ]

        return data

class PacketInspect(ProxyPlugin):
    def __init__(self, c, h):
        super(PacketInspect, self).__init__(c)
        self.stdout = sys.stdout
        self.header = h
        self.buffer = ""
        self.ignore = []

    def cmd_ignore(self, name):
        try:
            h = packets_by_name[name]
        except KeyError:
            return "packet %s is not recongized" % name
        else:
            self.ignore.append(h)
            return "ok."

    def cmd_unignore(self, name):
        try:
            h = packets_by_name[name]
        except KeyError:
            return "packet %s is not recongized" % name
        else:
            self.ignore.remove(h)
            return "ok."

    # this expects to use minecraft packets, not raw data
    def packet(self, header, payload):
        if self._enabled:
            if header not in self.ignore:
                write = self.stdout.write
                write("%s\n" % self.header)
                write("========== %s ===========\n" % packets_by_id[header])
                write(payload)

# this handle traffic from the client
class MCClientProtocol(Protocol):
    def dataReceived(self, data):
        if self.remote:
            for p in self.plugins:
                p.filter(data)
            self.remote.transport.write(data)

    def add_plugin(self, plugin):
        self.plugins.append(plugin)

    def remove_plugin(self, plugin):
        try:
            self.plugins.remove(plugin)
        except ValueError:
            pass

    def connectionMade(self):
        self.plugins = []
        self.buffer = ""
        self.remote = None

        # setup our packet parser plugin
        parser = PacketParser(self)
        parser.enable()
        self.add_plugin(parser)

        # set up the shell plugin (goes the the packet parser)
        s = ShellPlugin(self, self.transport, "#")
        s.enable()
        parser.add_plugin(s)

        reactor.connectTCP(remote_host, remote_port, RemoteClientProxyFactory(self))

# this handles traffic to the client
class MCRemoteProtocol(Protocol):
    def __init__(self, remote):
        self.remote = remote
        self.plugins = []
        self.buffer = ""

    def dataReceived(self, data):
        self.remote.transport.write(data)
        #for p in self.plugins:
        #    data = p.filter(data)

class RemoteClientProxyFactory(ClientFactory):
    def __init__(self, caller):
        self.caller = caller

    def buildProtocol(self, addr):
        conn = MCRemoteProtocol(self.caller)
        self.caller.remote = conn
        info("Connected.\n")
        return conn

    def clientConnectionLost(self, connector, reason):
        #self.caller.loseConnection()
        error("Remote connection lost.\n")

    def clientConnectionFailed(self, connector, reason):
        # bug: reason is a bit too detailed to send back to the client...
        error("Connection failed. Reason %s\n:" % reason)

class ClientProxyFactory(Factory):
    protocol = MCClientProtocol

if __name__ == "__main__":
    reactor.listenTCP(listen_port, ClientProxyFactory())
    reactor.run()
