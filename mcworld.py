from bravo.entity import Entity



class World:
    def __init__(self):
        self.entities = {}

    def add_entity(self, eid):
        e = Entity()
        self.entities[eid] = e
        return e

    def update_entity(self, eid, x, y, z, relative=False):
        pass