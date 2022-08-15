class Crew:

    def __init__(self, current_occupancy, ship_size, player_list_address):

        self.current_occupancy = current_occupancy
        self.ship_size = ship_size
        self.player_list_address = player_list_address

    def get_ship_size(self):
        if self.ship_size == 'S':
            return '=====Sloop====='
        elif self.ship_size == 'M':
            return '===Brigantine==='
        elif self.ship_size == 'L':
            return '====Galleon===='


