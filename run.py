#!/usr/bin/python2.5

# a very special minecraft beta bot
# leif.theden@gmail.com

# special thanks to the bravo project!

from twisted.internet.protocol import ClientFactory
from twisted.internet import reactor

from mcworld import World
from mcbot import MinecraftBot
from mcprotocol import MinecraftClientProtocol



server = "127.0.0.1"
port   = 25565

# for authentication on minecraft.net
# lets keep it legit here
username = "b2"
password = "password"



class MineBotClientFactory(ClientFactory):
    def __init__(self, bot):
        self.bot = bot
        
    def buildProtocol(self, addr):
        p = MinecraftClientProtocol(self.bot)
        return p

    def clientConnectionLost(self, conn, reason):
        print "Lost connection:", reason
        reactor.stop()

    def clientConnectionFailed(self, conn, reason): 
        print "Connection failed:", reason
        reactor.stop()

class Server:
    def __init__(self, name, address):
        self.name = name
        self.address = address    

if __name__ == "__main__":
    bot = MinecraftBot(username, password)

    # hand control over to twisted
    reactor.connectTCP(server, port, MineBotClientFactory(bot))

    reactor.run()