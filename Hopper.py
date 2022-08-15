import asyncio
import logging
import pyglet
from pyglet.text import Label
from Booter import SOT_WINDOW, SOT_WINDOW_H, SOT_WINDOW_W, main_batch, \
    version, logger, menu_screen_time, finding_server_time, ssd_time, \
    web_hook_URL, namers, manual_mode, ship_type, discord_name, steam_version, \
    namer_hop, reaper_hop, fotd_hop, fof_hop, fort_hop, fleet_hop, ashen_hop
from discord import Webhook, AsyncWebhookAdapter
from aiohttp import ClientSession
from pynput.keyboard import Key, Controller
from time import sleep
from win32gui import FindWindow, SetForegroundWindow
from random import randint
from MemoryReader import SoTMemoryReader

# from pyautogui import keyDown, keyUp, moveTo, easeInOutQuad

smr = SoTMemoryReader()

# Displays hop countdown on the server
hopsin = Label("Hops in: 0",
               bold=True,
               font_size=10,
               color=(0, 255, 0, 255),
               x=SOT_WINDOW_W * 0.01,
               y=SOT_WINDOW_H * 0.92, batch=main_batch)

# Displays times hopped on the server
hopCount = Label("Hop count: 0",
                 bold=True,
                 font_size=10,
                 color=(0, 255, 0, 255),
                 x=SOT_WINDOW_W * 0.01,
                 y=SOT_WINDOW_H * 0.90, batch=main_batch)
# hopCount.text = ("Hop count: {}".format(times_hopped))

# Displays the amount of namers on the server
namer_count = Label("Namer count: 0",
                    bold=True,
                    font_size=10,
                    color=(0, 255, 0, 255),
                    x=SOT_WINDOW_W * 0.01,
                    y=SOT_WINDOW_H * 0.88, batch=main_batch)

# Count of total server players updated in OnDraw
player_count = Label("Player count: {}",
                     bold=True,
                     font_size=10,
                     color=(0, 255, 0, 255),
                     x=SOT_WINDOW_W * 0.01,
                     y=SOT_WINDOW_H * 0.86, batch=main_batch)

reaper_count = Label("Reaper count: {}",
                     bold=True,
                     font_size=10,
                     color=(0, 255, 0, 255),
                     x=SOT_WINDOW_W * 0.01,
                     y=SOT_WINDOW_H * 0.84, batch=main_batch)

FOTD_Active = Label("FOTD Active: {}",
                    bold=True,
                    font_size=10,
                    color=(0, 255, 0, 255),
                    x=SOT_WINDOW_W * 0.01,
                    y=SOT_WINDOW_H * 0.82, batch=main_batch)

WorldEvent_Active = Label("World Event: ",
                          bold=True,
                          font_size=10,
                          color=(0, 255, 0, 255),
                          x=SOT_WINDOW_W * 0.01,
                          y=SOT_WINDOW_H * 0.8, batch=main_batch)

# The label for showing all players on the server under the count
player_list = Label("\n".join(smr.server_players),
                    bold=True,
                    font_size=10,
                    color=(0, 220, 220, 220),
                    x=SOT_WINDOW_W * 0.01,
                    y=(SOT_WINDOW_H - 25) * 0.78,
                    batch=main_batch, width=300,
                    multiline=True)

brand_label = Label("InfamyModBeta",
                    x=SOT_WINDOW_W - 285, y=10, font_size=20, bold=True,
                    color=(127, 127, 127, 65), batch=main_batch)

# variables
beard_error = False
beard_error_countdown = 120
first_namer_found = False
namer_list_found = []
namers_found = 0
times_hopped = 0
namer_check_countdown = 500
beard_error_count = 0
rand_list = []
rand_list_pointer = 0
hop_countdown = ssd_time

# Build list of random integers to decide what activity to do in server
for i in range(42):
    rand_list.append(randint(1, 7))


# Switches focus to Sea of Thieves
def focus():
    window_name = "Sea of Thieves"
    hwnd = FindWindow(None, window_name)
    SetForegroundWindow(hwnd)


# Countdown until hop
def countdown(_):
    global namer_list_found
    global beard_error
    global beard_error_countdown
    global hop_countdown
    global first_namer_found
    global beard_error_count
    if len(smr.server_players) == 0 and beard_error_countdown > 0:
        hopsin.text = ("Hops in: {}".format('Waiting For Server'))
        WorldEvent_Active.text = ("World Event: ")
        hop_countdown = ssd_time
        beard_error_countdown -= 1
    # Beard Error if server players are 0 for duration of beardErrorCountdown
    elif beard_error_countdown <= 0:
        hopsin.text = ("Hops in: {}".format('hopping'))
        beard_error = True
        print("Beard Error Detected")
        beard_error_count += 1
        hop()
    else:
        hop_countdown -= 1
        hopsin.text = ("Hops in: {}".format(hop_countdown))
        if hop_countdown <= 1:
            hopsin.text = ("Hops in: {}".format('hopping'))
            if hop_countdown <= -1:
                update_namer_counter
                # TODO
                smr.read_actors()
                if not first_namer_found and not (smr.FOTD and fotd_hop) and not (smr.FOF and fof_hop) and not (smr.FORT and fort_hop) and not (smr.FLEET and fleet_hop) and not (smr.ASHEN and ashen_hop) and not (smr.tracked_ship_count > 0 and reaper_hop):
                    hop()
                elif smr.FOTD and fotd_hop:
                    hopsin.text = ("Hops in: {}".format('FOTD Found'))
                elif smr.FOF and fof_hop:
                    hopsin.text = ("Hops in: {}".format('FOF Found'))
                elif smr.FORT and fort_hop:
                    hopsin.text = ("Hops in: {}".format('FORT Found'))
                elif smr.FLEET and fleet_hop:
                    hopsin.text = ("Hops in: {}".format('FLEET Found'))
                elif smr.ASHEN and ashen_hop:
                    hopsin.text = ("Hops in: {}".format('Ashen Lord Found'))
                elif smr.tracked_ship_count > 0 and reaper_hop:
                    hopsin.text = ("Hops in: {}".format('Reaper Found'))


def update_namer_counter(_):
    global namer_list_found
    global first_namer_found
    if not first_namer_found:
        # constantly check namer list against server players
        for player in smr.server_players:
            if player.lower() in namers and player.lower() not in namer_list_found:
                namer_check(player.lower())
                namer_list_found.append(player.lower())
                first_namer_found = True
    else:
        counterHelper()


def counterHelper():
    global hop_countdown
    global namer_list_found
    global first_namer_found
    global namer_check_countdown
    global beard_error
    i = 0
    namer_check_countdown -= 1
    # Check the list every 5 seconds
    if (namer_check_countdown % 5) == 0:
        for player in smr.server_players:
            if player.lower() in namers and player.lower() not in namer_list_found:
                namer_check(player.lower())
                namer_list_found.append(player.lower())
    else:
        # update count every second
        for name in namer_list_found:
            for player in smr.server_players:
                if name.lower() == player.lower():
                    i += 1
        if i == 0 and manual_mode:
            hopsin.text = ("Hops in: {}".format('ManualMode'))
        namer_count.text = ("Namer count: {}".format(i))
        # checks if namers leaves the server and holds the spot for 2 min
        if i == 0 and first_namer_found and len(smr.server_players) != 0:
            asyncio.get_event_loop().run_until_complete(discord_ping("!@Dodger!@"))
            print("Namer Dodged")
            hop_countdown = 120
            namer_check_countdown = 500
            namer_list_found = []
            first_namer_found = False
            if not manual_mode:
                pyglet.clock.schedule_interval(countdown, 1)
        elif first_namer_found and len(smr.server_players) == 0:
            print("Lazybearded from namer server")
            asyncio.get_event_loop().run_until_complete(discord_ping("!@LazyBeardError!@"))
            namer_list_found = []
            first_namer_found = False
            beard_error = True
            hop_countdown = ssd_time
            namer_check_countdown = 500
            if not manual_mode:
                pyglet.clock.schedule_interval(countdown, 1)


def namer_check(player):
    logger.info("Namer Found: " + player)
    Namer_Found()
    print(player + " Found")
    asyncio.get_event_loop().run_until_complete(discord_ping(player))


def Namer_Found():
    pyglet.clock.unschedule(countdown)
    sleep(1)
    hopsin.text = ("Hops in: {}".format('Namer found'))


def world_event_scan(_):
    if not smr.FOTD and not smr.FOF and not smr.FORT and not smr.FLEET and not smr.ASHEN:
        WorldEvent_Active.text = ("World Event: ")
    elif smr.FOF:
        WorldEvent_Active.text = ("World Event: Fort of Fortune")
    elif smr.FORT:
        WorldEvent_Active.text = ("World Event: Skeleton Fort")
    elif smr.FLEET:
        WorldEvent_Active.text = ("World Event: Skeleton Fleet")
    elif smr.ASHEN:
        WorldEvent_Active.text = ("World Event: Ashen Lord")


# scuttleship leave game then enter new lobby
def hop():
    global rand_list
    global rand_list_pointer
    global menu_screen_time
    global finding_server_time
    global beard_error_count
    global beard_error
    global Namer_check_countdown
    global steam_version
    global times_hopped
    global ship_type
    # hop_seed = rand_list[rand_list_pointer]
    rand_list_pointer += 1
    if rand_list_pointer > 41:
        randListPointer = 0
    if beard_error_count / (times_hopped + 1) > .05:
        print("Increasing main menu time")
        finding_server_time += 2
        beard_error_count = 0
    keyboard = Controller()
    if not beard_error:
        focus()
        keyboard.press(Key.esc)
        keyboard.release(Key.esc)
        sleep(0.2)
        keyboard.press(Key.down)
        keyboard.release(Key.down)
        sleep(0.3)
        keyboard.press(Key.down)
        keyboard.release(Key.down)
        sleep(0.3)
        keyboard.press(Key.down)
        keyboard.release(Key.down)
        sleep(0.3)
        # Add two down presses for steam version of game
        if steam_version:
            keyboard.press(Key.down)
            keyboard.release(Key.down)
            sleep(0.3)
            keyboard.press(Key.down)
            keyboard.release(Key.down)
            sleep(0.3)
        keyboard.press(Key.enter)
        keyboard.release(Key.enter)
        sleep(0.2)
        keyboard.press(Key.enter)
        keyboard.release(Key.enter)
        sleep(menu_screen_time)
    else:
        focus()
        keyboard.press(Key.enter)
        keyboard.release(Key.enter)
        sleep(7)
    focus()
    keyboard.press(Key.enter)
    keyboard.release(Key.enter)
    sleep(finding_server_time)
    keyboard.press(Key.enter)
    keyboard.release(Key.enter)
    sleep(0.05)
    keyboard.press(Key.enter)
    keyboard.release(Key.enter)
    sleep(0.05)
    if ship_type.lower() == "brigantine" or ship_type.lower() == "brig":
        keyboard.press(Key.down)
        keyboard.release(Key.down)
        sleep(0.05)
    if ship_type.lower() == "sloop":
        keyboard.press(Key.down)
        keyboard.release(Key.down)
        sleep(0.05)
        keyboard.press(Key.down)
        keyboard.release(Key.down)
        sleep(0.05)
    keyboard.press(Key.enter)
    keyboard.release(Key.enter)
    sleep(0.05)
    keyboard.press(Key.enter)
    keyboard.release(Key.enter)
    sleep(3)
    keyboard.press(Key.enter)
    keyboard.release(Key.enter)
    sleep(3)
    keyboard.press(Key.enter)
    keyboard.release(Key.enter)
    sleep(3)
    keyboard.press(Key.enter)
    keyboard.release(Key.enter)
    global hop_countdown
    hop_countdown = ssd_time
    beard_error = False
    global beard_error_countdown
    beard_error_countdown = 120
    namer_check_countdown = 500
    times_hopped += 1
    hopCount.text = ("Hop count: {}".format(times_hopped))


# TODO add param to replace LazyBeard Error
async def discord_ping(namer):
    async with ClientSession() as session:
        # NBB
        try:
            webhook = Webhook.from_url(
                '',
                adapter=AsyncWebhookAdapter(session))
            if namer == "!@LazyBeardError!@":
                await webhook.send("User Dodged", username=discord_name)
            elif namer == "!@Dodger!@":
                await webhook.send("Namer Dodged", username=discord_name)
            else:
                await webhook.send(namer + ' Found', username=discord_name)
        except Exception as e:
            logging.info("Invalid webHookURL or discordName (most likely webURL)")

        try:
            configWebHook = Webhook.from_url(
                web_hook_URL,
                adapter=AsyncWebhookAdapter(session))
            if namer == "!@LazyBeardError!@":
                await configWebHook.send("User Dodged", username=discord_name)
            elif namer == "!@Dodger!@":
                await configWebHook.send("Namer Dodged", username=discord_name)
            else:
                await configWebHook.send(namer + ' Found', username=discord_name)
        except Exception as e:
            logging.info("Invalid webHookURL or discordName (most likely webURL)")
