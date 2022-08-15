import datetime
import struct
import logging
from MemoryHelper import ReadMemory
from Booter import OFFSETS, logger
from boto3.dynamodb.conditions import Key
from Booter import dynamodb, client, TABLE, REVTABLE, ddb_exceptions
from Crew import Crew

DEBUG = False
last_ship_count = 0
#Player_name_found = list of player addresses who's names have been found
player_name_found = []
player_addresses = []
# player_seed_searched = Dict(K = address, V = Playername)
player_seed_searched = {}

class SoTMemoryReader:
    def __init__(self):
        self.rm = ReadMemory("SoTGame.exe")
        base_address = self.rm.base_address
        logging.info(f"Process ID: {self.rm.pid}")

        u_world_offset = self.rm.read_ulong(
            base_address + self.rm.u_world_base + 3
        )
        u_world = base_address + self.rm.u_world_base + u_world_offset + 7
        self.world_address = self.rm.read_ptr(u_world)

        g_name_offset = self.rm.read_ulong(
            base_address + self.rm.g_name_base + 3
        )
        g_name = base_address + self.rm.g_name_base + g_name_offset + 7
        logging.info(f"SoT gName Address: {hex(g_name)}")
        self.g_name = self.rm.read_ptr(g_name)

        g_objects_offset = self.rm.read_ulong(
            base_address + self.rm.g_object_base + 2
        )
        g_objects = base_address + self.rm.g_object_base + g_objects_offset + 22
        logging.info(f"SoT gObject Address: {hex(g_objects)}")
        self.g_objects = self.rm.read_ptr(g_objects)

        self.u_level = self.rm.read_ptr(self.world_address +
                                        OFFSETS.get('World.PersistentLevel'))

        self.u_local_player = self._load_local_player()
        self.player_controller = self.rm.read_ptr(
            self.u_local_player + OFFSETS.get('LocalPlayer.PlayerController')
        )

        self.my_coords = self._coord_builder(self.u_local_player)
        self.my_coords['fov'] = 90
        self.actor_name_map = {}
        self.display_objects = []

        self.server_players = []
        self.total_players = 0
        self.tracked_ship_count = 0
        self.temp_player_addresses = []
        self.first_manifest = True
        self.FOTD = False
        self.FOF = False
        self.FORT = False
        self.FLEET = False
        self.ASHEN = False

    def _load_local_player(self) -> int:
        game_instance = self.rm.read_ptr(
            self.world_address + OFFSETS.get('World.OwningGameInstance')
        )
        local_player = self.rm.read_ptr(
            game_instance + OFFSETS.get('GameInstance.LocalPlayers')
        )
        return self.rm.read_ptr(local_player)


    def update_my_coords(self):
        manager = self.rm.read_ptr(
            self.player_controller + OFFSETS.get('PlayerController.CameraManager')
        )
        self.my_coords = self._coord_builder(
            manager,
            OFFSETS.get('PlayerCameraManager.CameraCache')
            + OFFSETS.get('CameraCacheEntry.FMinimalViewInfo'),
            fov=True)


    def _coord_builder(self, actor_address: int, offset=0x78, camera=True,
                       fov=False) -> dict:
        if fov:
            actor_bytes = self.rm.read_bytes(actor_address + offset, 44)
            unpacked = struct.unpack("<ffffff16pf", actor_bytes)
        else:
            actor_bytes = self.rm.read_bytes(actor_address + offset, 24)
            unpacked = struct.unpack("<ffffff", actor_bytes)

        coordinate_dict = {"x": unpacked[0]/100, "y": unpacked[1]/100,
                           "z": unpacked[2]/100}
        if camera:
            coordinate_dict["cam_x"] = unpacked[3]
            coordinate_dict["cam_y"] = unpacked[4]
            coordinate_dict["cam_z"] = unpacked[5]
        if fov:
            coordinate_dict['fov'] = unpacked[7]

        return coordinate_dict


    def _read_name(self, actor_id: int) -> str:
        name_ptr = self.rm.read_ptr(self.g_name + int(actor_id / 0x4000) * 0x8)
        name = self.rm.read_ptr(name_ptr + 0x8 * int(actor_id % 0x4000))
        return self.rm.read_string(name + 0x10, 64)


    def read_actors(self):
        global last_ship_count
        global player_addresses

        self.__init__()

        for display_ob in self.display_objects:
            try:
                display_ob.text_render.delete()
            except:
                continue
        self.display_objects = []
        self.update_my_coords()


        actor_raw = self.rm.read_bytes(self.u_level + 0xa0, 0xC)
        actor_data = struct.unpack("<Qi", actor_raw)

        for x in range(0, actor_data[1]):

            raw_name = ""
            actor_address = self.rm.read_ptr(actor_data[0] + (x * 0x8))
            actor_id = self.rm.read_int(
                actor_address + OFFSETS.get('Actor.actorId')
            )

            if actor_id not in self.actor_name_map and actor_id != 0:
                try:
                    raw_name = self._read_name(actor_id)
                    self.actor_name_map[actor_id] = raw_name
                except Exception as e:
                    logger.error(f"Unable to find actor name: {e}")
            elif actor_id in self.actor_name_map:
                raw_name = self.actor_name_map.get(actor_id)


            # Ignore anything we cannot find a name for
            if not raw_name:
                continue

            elif "CrewService" in raw_name:
                # Find the starting address for our Crews TArray
                crews_raw = self.rm.read_bytes(actor_address + OFFSETS.get('CrewService.Crews'), 12)
                # (Crews_Data<Array>, Crews length)
                crews = struct.unpack("<Qi", crews_raw)

                for y in range(0, crews[1]):
                    ship_size_raw = self.rm.read_ptr(
                        crews[0] + OFFSETS.get('Crew.CrewSessionTemplate') + (OFFSETS.get('Crew.Size') * y))
                    ship_size = self.rm.read_string(ship_size_raw)
                    players_raw = self.rm.read_bytes(
                        crews[0] + OFFSETS.get('Crew.Players') + (OFFSETS.get('Crew.Size') * y), 12
                    )
                    # Players<Array>, current length
                    crew_players = struct.unpack("<Qi", players_raw)
                    ship_occupancy = crew_players[1]
                    ThisCrew = Crew(ship_occupancy, ship_size, crew_players[0])

                    if ship_occupancy > 0:
                        self.server_players.append(ThisCrew.get_ship_size())
                        self.total_players += ship_occupancy
                        for z in range(0, crew_players[1]):
                            # 8 = size of crew address, reads the player array in each crew object
                            crew_players_raw = self.rm.read_bytes((crew_players[0] + (8 * z)), 8)
                            current_player = struct.unpack("<Q", crew_players_raw)[0]
                            self.temp_player_addresses.append(current_player)
                            self.read_world_players(current_player)

            elif "_RitualSkullCloud" in raw_name:
                self.FOTD = True

            elif "_LegendSkellyFort_SkullCloud" in raw_name:
                self.FOF = True

            elif "_SkellyFort_SkullCloud" in raw_name:
                self.FORT = True

            elif "_SkellyShip_ShipCloud" in raw_name:
                self.FLEET = True

            elif "_AshenLord_SkullCloud" in raw_name:
                self.ASHEN = True

            elif "CrewShipManifest" in raw_name and self.first_manifest:
                self.first_manifest = False
                # CSM + ShipTemplate offset
                path_address = self.rm.read_ptr(actor_address + 200)
                ship_template_id = self.rm.read_int(path_address+OFFSETS.get('Actor.actorId'))
                ship_template_name = self._read_name(ship_template_id)
                if 'BP_MediumShipTemplate_C' == ship_template_name:
                    map_offset = 6328
                elif 'BP_LargeShipTemplate_C' == ship_template_name:
                    map_offset = 6440
                elif 'BP_SmallShipTemplate_C' == ship_template_name:
                    map_offset = 6240
                else:
                    self.tracked_ship_count = last_ship_count
                    continue
                #ShipTemplate + MapTable
                path_address = self.rm.read_ptr(path_address + map_offset)
                #MapTable + Maptable_C
                path_address = self.rm.read_ptr(path_address + 744)
                #MapTable + Tracked Ships
                if path_address:
                    tracked_ships_raw = self.rm.read_bytes(path_address + 1272, 12)
                    self.tracked_ship_count = struct.unpack("<Qi", tracked_ships_raw)[1]
                    last_ship_count = self.tracked_ship_count
                else:
                    self.tracked_ship_count = last_ship_count
                #TODO differentiate reapers from marks
                # tracked_ships = struct.unpack("<Qi", tracked_ships_raw)[0]
                # print(self.rm.read_str(self.rm.read_bytes(tracked_ships,  8)))

            else:
                self.tracked_ship_count = last_ship_count


        #TODO test reset aws querys if players leave or join
        if not self.temp_player_addresses == player_addresses:
            if DEBUG:
                print(self.temp_player_addresses)
                print('Player addresses updated')
                print(player_addresses)
            self.reset_searches()
            for player in self.temp_player_addresses:
                player_addresses.append(player)


    def search_seed(self, seed):
        try:
            response = REVTABLE.query(KeyConditionExpression=Key('Seed').eq(seed))
            if response['Items']:
                return (response['Items'][0]['Gamertag'])
            else:
                return ""
        except Exception as e:
            logging.info("search issue " + e)


    def search_name(self, name, seed):
        try:
            response = TABLE.query(KeyConditionExpression=Key('Gamertag').eq(name))
            #PlayerSeed = response['Items'][0]['Seed']
            if not response['Items']:
                #AWS
                print(name + " is in the game.")  # Console output
                if DEBUG:
                    print("Logged Data: " + name, seed)  # Console output
                try:
                    client.put_item(TableName='PlayerList', Item={'Gamertag': {'S': name}, 'Seed': {'N': str(seed)}})
                    client.put_item(TableName='PlayerListSeedFirst', Item={'Seed': {'N': str(seed)}, 'Gamertag': {'S': name}})
                except ddb_exceptions as e:
                    print(e)
            # TODO: TEST update player seed if pirate changed
            # add new seed if pirate changed
            else:
                if not int(response['Items'][0]['Seed']) == int(seed):
                    print("Looks like " + name + " had some work done.")
                    if DEBUG:
                        print("Old Seed: " + str(response['Items'][0]['Seed']) +" New Seed: "+ str(seed))
                        print("Updated " + name)
                    client.delete_item(TableName='PlayerList',
                                       Key={'Gamertag': {'S': name}, 'Seed': {'N': str(response['Items'][0]['Seed'])}})
                    client.put_item(TableName='PlayerList', Item={'Gamertag': {'S': name}, 'Seed': {'N': str(seed)}})
                    client.delete_item(TableName='PlayerListSeedFirst',
                                       Key={'Seed': {'N': str(response['Items'][0]['Seed'])}, 'Gamertag': {'S': name}})
                    client.put_item(TableName='PlayerListSeedFirst', Item={'Seed': {'N': str(seed)}, 'Gamertag': {'S': name}})
        except Exception as e:
            logging.info("search name issue " + e)

    def reset_searches(self):
        global player_seed_searched
        global player_addresses
        player_seed_searched = {}
        player_addresses = []


    def read_world_players(self, actor_address):
        global player_name_found
        global player_seed_searched


        player_name_location = self.rm.read_ptr(
            actor_address + OFFSETS.get('PlayerState.PlayerName')
        )
        player_name = self.rm.read_name_string(player_name_location)
        player_seed = self.rm.read_int(
            actor_address + OFFSETS.get('PlayerState.PirateDesc.Seed')
        )

        if player_name == "":
            #self.server_players.append(str(player_seed))
            if actor_address not in player_seed_searched:
                DBPlayerName = self.search_seed(player_seed)
                if DBPlayerName == "":
                    self.server_players.append("N/A")
                    player_seed_searched[actor_address] = "N/A"
                else:
                    self.server_players.append(DBPlayerName)
                    player_seed_searched[actor_address] = DBPlayerName
            else:
                self.server_players.append(player_seed_searched[actor_address])
        else:
            #TODO Test
            #Supposed to store actor addresses and only update player list if addresses change
            if actor_address not in player_name_found:
                if DEBUG:
                    print(player_name_found)
                player_name_found.append(actor_address)
                self.search_name(player_name, player_seed)
            self.server_players.append(player_name)
