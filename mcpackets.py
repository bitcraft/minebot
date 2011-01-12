# parts from the Mineserver Project

# Client to Server Packets
KEEP_ALIVE                = 0x00
LOGIN_REQUEST             = 0x01
HANDSHAKE                 = 0x02
CHAT_MESSAGE              = 0x03
ENTITY_EQUIPMENT          = 0x05
RESPAWN                   = 0x09
PLAYER                    = 0x0a
PLAYER_POSITION           = 0x0b
PLAYER_LOOK               = 0x0c
PLAYER_POSITION_AND_LOOK  = 0x0d
PLAYER_DIGGING            = 0x0e
PLAYER_BLOCK_PLACEMENT    = 0x0f
HOLDING_CHANGE            = 0x10
ANIMATION                 = 0x12
INVENTORY_CLOSE           = 0x65
INVENTORY_CHANGE          = 0x66
SET_SLOT                  = 0x67
INVENTORY                 = 0x68
SIGN                      = 0x82
DISCONNECT                = 0xff

# Server to Client Packets
LOGIN_RESPONSE            = 0x01
TIME_UPDATE               = 0x04
SPAWN_POSITION            = 0x06
UPDATE_HEALTH             = 0x08
ADD_TO_INVENTORY          = 0x11
NAMED_ENTITY_SPAWN        = 0x14
PICKUP_SPAWN              = 0x15
COLLECT_ITEM              = 0x16
ADD_OBJECT                = 0x17
MOB_SPAWN                 = 0x18
DESTROY_ENTITY            = 0x1d
ENTITY                    = 0x1e
ENTITY_RELATIVE_MOVE      = 0x1f
ENTITY_LOOK               = 0x20
ENTITY_LOOK_RELATIVE_MOVE = 0x21
ENTITY_TELEPORT           = 0x22
DEATH_ANIMATION           = 0x26
PRE_CHUNK                 = 0x32
MAP_CHUNK                 = 0x33
MULTI_BLOCK_CHANGE        = 0x34
BLOCK_CHANGE              = 0x35
OPEN_WINDOW               = 0x64
TRANSACTION               = 0x6a
#COMPLEX_ENTITIES          = 0x3b
KICK                      = 0xff

#  v4 Packets
USE_ENTITY      = 0x07
ENTITY_VELOCITY = 0x1c
ATTACH_ENTITY   = 0x27

