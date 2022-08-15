import subprocess
import requests as requests
import boto3
from aiohttp import ClientSession
from discord import AsyncWebhookAdapter, Webhook
import json
import logging
import win32gui
from pyglet.graphics import Batch
from boto3.dynamodb.conditions import Key



#variables
version = "0.2"
menu_screen_time = 10
finding_server_time = 14
namers = set()


# Config specification for logging file
logging.basicConfig(filename='Infamy.log', level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s', filemode="w")
logger = logging.getLogger()

# Disables AWS, TableNames and Table information from appearing in .log file
logging.getLogger('boto3').setLevel(logging.CRITICAL)
logging.getLogger('botocore').setLevel(logging.CRITICAL)
logging.getLogger('s3transfer').setLevel(logging.CRITICAL)
logging.getLogger('urllib3').setLevel(logging.CRITICAL)


#build namer set
name_list = open("namers.txt", "r")
for line in name_list:
    tempName = line.lower().rstrip()
    if tempName != 'sourscar':
        namers.add(tempName)
name_list.close()


#Set config from config.txt
config = open("config.txt", "r")
configs = []
for data in config:
    configs.append(data.replace("\n",""))
config.close()
try:
    manual_mode = configs[1].lower() == 'n'
    ship_type = configs[4]
    web_hook_URL = configs[25]
    discord_name = configs[13]
    steam_version = configs[16].lower() == 'y'
    try:
        ssd_time = int(configs[19])
        finding_server_time += int(configs[22])
        reaper_hop = 'reaper' in configs[7].lower()
        fotd_hop = 'fotd' in configs[7].lower()
        fof_hop = 'fof' in configs[7].lower()
        fort_hop = 'fort' in configs[7].lower()
        fleet_hop = 'fleet' in configs[7].lower()
        ashen_hop = 'ashen' in configs[7].lower()
        namer_hop = 'namer' in configs[7].lower()
    except Exception as e:
        ssd_time = 30
        logging.info("u fucked up the ssdtime or main menu time, default value will be used")
except Exception as e:
    logging.info("u fucked up the config file")


#AWS
client = boto3.client('dynamodb',
                          aws_access_key_id='',
                          aws_secret_access_key='',
                          region_name='')

dynamodb = boto3.resource('dynamodb',
                          aws_access_key_id='',
                          aws_secret_access_key='',
                          region_name='')

TABLE = dynamodb.Table('PlayerList')
REVTABLE = dynamodb.Table('PlayerListSeedFirst')
HWIDTABLE = dynamodb.Table('HWIDs')
PRODUCTKEYTABLE = dynamodb.Table('ProductKeys')
ddb_exceptions = client.exceptions



TEXT_OFFSET_X = 13
TEXT_OFFSET_Y = -5

try:
    window = win32gui.FindWindow(None, "Sea of Thieves")
    SOT_WINDOW = win32gui.GetWindowRect(window)  # (x1, y1, x2, y2)
    SOT_WINDOW_H = SOT_WINDOW[3] - SOT_WINDOW[1]
    SOT_WINDOW_W = SOT_WINDOW[2] - SOT_WINDOW[0]
except Exception as e:
    logger.error("Unable to find Sea of Thieves window; exiting.")
    exit(-1)

main_batch = Batch()

OFFSETS = {
  "Actor.actorId": 24,
  "Actor.rootComponent": 360,
  "PlayerState.PlayerName": 976,
  "PlayerState.PirateDesc.Seed": 1672,
  "GameInstance.LocalPlayers": 56,
  "LocalPlayer.PlayerController": 48,
  "PlayerCameraManager.CameraCache": 1088,
  "PlayerController.CameraManager": 1112,
  "CameraCacheEntry.FMinimalViewInfo": 16,
  "World.OwningGameInstance": 448,
  "World.PersistentLevel": 48,
  "CrewService.Crews": 1184,
  "Crew.Players": 32,
  "Crew.Size": 152,
  "Crew.CrewSessionTemplate": 48,
  "CrewSessionTemplate.ShipSize": 40,
  "CrewSessionTemplate.MatchmakingHopper": 24,
  "PlayerState.PlayerActivity": 1824,
  "PlayerState.BodyShapeCoordinate.NormalizedAngle": 1628,
  "PlayerState.BodyShapeCoordinate.RadialDistance": 1632
}



async def hwid():
    async with ClientSession() as session:
        hardwareID = str(subprocess.check_output('wmic csproduct get uuid'), 'utf-8').split('\n')[1].strip()

        response = HWIDTABLE.query(KeyConditionExpression=Key('HWID').eq(hardwareID))
        if not response['Items']:
            # AWS
            product_key = input("Enter Product Key:")
            key_response = PRODUCTKEYTABLE.query(KeyConditionExpression=Key('ProductKey').eq(product_key))
            if not key_response['Items']:
                print("Key Invalid")
                exit()
            elif not key_response['Items'][0]['HWID'] == '0':
                print("Key has been used")
                exit()
            else:
                print("Key Activated, Starting...")
                client.put_item(TableName='HWIDs', Item={'HWID': {'S': hardwareID}, 'ProductKey': {'S': product_key}})
                client.delete_item(TableName='ProductKeys',
                                   Key={'ProductKey': {'S': product_key}, 'HWID': {'S': '0'}})
                client.put_item(TableName='ProductKeys', Item={'ProductKey': {'S': product_key}, 'HWID': {'S': hardwareID}})
        else:
            print("Starting...")
            hwidActive = Webhook.from_url(
                '',
                adapter=AsyncWebhookAdapter(session))
            await hwidActive.send("HWID - " + hardwareID + ' launched the Mod', username="HWID - " + discord_name)
       
        # site = requests.get("https://pastebin.com/RWWUawHD")  #simple UUID HWID lock. Convert to AWS next
        #
        # if hardwareID in site.text:
        #     print("[HWID]", hardwareID, "- Access Granted")
        #     hwidActive = Webhook.from_url(
        #         '', adapter=AsyncWebhookAdapter(session))
        #     await hwidActive.send("HWID - " + hardwareID + ' launched the cheat', username="HWID - " + discord_name)
        #     pass
        # elif hardwareID not in site.text:
        #     hwidGrab = Webhook.from_url(
        #         '', adapter=AsyncWebhookAdapter(session))
        #     await hwidGrab.send("HWID - " + hardwareID + ' grabbed', username="HWID - " + discord_name)
        #     logging.info("Access Denied")
        #     exit()