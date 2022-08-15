import asyncio
import pyglet
import logging
from pyglet.gl import Config
from Booter import SOT_WINDOW, SOT_WINDOW_H, SOT_WINDOW_W, main_batch, \
    version, logger, hwid, manual_mode
from Hopper import update_namer_counter, countdown, times_hopped, smr, \
    hopsin, hopCount, namer_count, player_count, player_list, brand_label, \
    reaper_count, FOTD_Active, world_event_scan

#TODO
#TODO: Fix reaper/event detection in hopper
#TODO: Detect different types of reapers
#TODO: Add gui config/ All/None/Playerlist Only
#TODO: When Namer is found Namer should be colored or have a TAG applied
#TODO: Multithreading
#TODO: Update the Height/width of the overlay in realtime, so that it always matches the window size of Sea of Thieves
#TODO: Only show overlay when Sea of Thieves is in focus
#TODO: Detect when Player has loaded onto an outpost
#TODO: Duplicate Warning or clear DB for non namers?


try:
    asyncio.get_event_loop().run_until_complete(hwid())
except RuntimeError as e:
    logging.info(e)


print("Time to raise your Notoriety!")
# Pyglet clock used to track time via FPS
clock = pyglet.clock.Clock()

def update_all(_):
    smr.read_actors()

def load_graphics(_):

    smr.update_my_coords()
    to_remove = []
    for actor in smr.display_objects:
        actor.update(smr.my_coords)
        if actor.to_delete:
            to_remove.append(actor)
    for removable in to_remove:
        smr.display_objects.remove(removable)


if __name__ == '__main__':
    logger.info("InfamyHopper Starting")
    logger.info(f"InfamyHopper Version: {version}")

    smr.read_actors()
    config = Config(double_buffer=True, depth_size=24, alpha_size=8)
    window = pyglet.window.Window(SOT_WINDOW_W, SOT_WINDOW_H,
                                  vsync=False, style='overlay', config=config,
                                  caption="Infamy Mod Beta")
    hwnd = window._hwnd  # pylint: disable=protected-access
    window.set_location(SOT_WINDOW[0], SOT_WINDOW[1])


    @window.event
    def on_draw():
        """
        The event which our window uses to determine what to draw on the
        screen. First clears the screen, then updates our player count, then
        draws both our batch (think of a canvas) & fps display
        """

        window.clear()
        # Update our player count Label, player list & namer count
        # namer_count.text = ("Namer Count: ")
        player_count.text = f"Player count: {smr.total_players}"
        FOTD_Active.text = f"FOTD Active: {smr.FOTD}"
        reaper_count.text = f"Reaper count: {smr.tracked_ship_count}"
        player_list.text = "\n".join(smr.server_players)
        # Draw our main batch & FPS counter at the bottom left
        main_batch.draw()
        # fps_display.draw()





################################################################### Timers

    if not manual_mode:
        pyglet.clock.schedule_interval(countdown, 1)
        pyglet.clock.schedule_interval(update_namer_counter, 5)
    else:
        pyglet.clock.schedule_interval(update_namer_counter, 15)
        hopsin.text = ("Hops in: {}".format('ManualMode'))
        hopsin.color = (0, 255, 0, 255)
        hopsin.bold = True

    #reset aws pings
    #####

    pyglet.clock.schedule_interval(world_event_scan, 1)

    pyglet.clock.schedule_interval(update_all, 5)

    pyglet.clock.schedule_interval(smr.rm.check_process_is_active, 5)

    pyglet.clock.schedule_interval(load_graphics, 1 / 24)

    fps_display = pyglet.window.FPSDisplay(window)

    pyglet.app.run()