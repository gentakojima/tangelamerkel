#!/usr/bin/python3

import time
import sys
import argparse
import json
import os

from telethon import TelegramClient
from telethon.tl.functions.contacts import ResolveUsernameRequest
from telethon.tl.functions.channels import GetParticipantsRequest
from telethon.tl.types import ChannelParticipantsSearch
from telethon.errors.rpc_errors_400 import UsernameInvalidError
from telethon.errors.rpc_errors_420 import FloodWaitError

#
# Parse command line args
#

parser = argparse.ArgumentParser(description='Helps moderating Pokémon GO Telegram groups with an iron hammer')
parser.add_argument('--force-setup', help='Force the initial setup, automatically called first time', dest='setup', action='store_true')
parser.add_argument('--refresh-oak', help='Refresh Oak info for all users (basic info always refreshed)', dest='refreshall', action='store_true')
parser.add_argument('--group', help='Specify the group handle (use the @name)', nargs=1, dest='group')
args = parser.parse_args()

#
# Setup configuration and data directory
#

datapath = os.path.expanduser("~") + "/.local/share/tangelamerkel"
os.path.isdir(datapath) or os.mkdir(datapath)

#
# Load persistent data
#

cached_users = {}
try:
    with open(datapath + '/users.json') as f:
        cached_users = json.load(f)
except FileNotFoundError:
    pass
configuration = {}
try:
    with open(datapath + '/config.json') as f:
        configuration = json.load(f)
except FileNotFoundError:
    args.setup=True

#
# What group?
#

if args.group == None:
    group = input('Enter the group name: ')
    args.group = [group]

#
# Initial setup
#

if args.setup == True:
    print("Go to https://my.telegram.org/ and create an app. Then input the required fields.")
    configuration['api_id'] = input('API ID: ').strip()
    configuration['api_hash'] = input('API Hash: ').strip()
    configuration['phone'] = input('Phone (+34600000000): ').strip()
    with open(datapath + '/config.json', 'w') as f:
        json.dump(configuration, f)

#
# Connect
#

client = TelegramClient('session_name', configuration['api_id'], configuration['api_hash'])
client.connect()

#
# Ensure you're authorized
#

if not client.is_user_authorized():
    client.send_code_request(phone)
    client.sign_in(phone, input('Authorization required. Check Telegram and enter the code: '))

#
# Search group
#

while True:
    try:
        result = client(ResolveUsernameRequest(str(args.group[0])))
    except UsernameInvalidError:
        pass
    except FloodWaitError:
        print("API returned a FloodWaitError. Looks like you reached the API limit! Exiting...")
        exit(1)
    if 'result' in locals():
        break
    print("Group name seems to be not valid. Please enter the @name (no spaces, no special chars...)")
    group = input('Enter the group name: ')
    args.group = [group]

#
# Search participants in group
#

users = {}
r = client(GetParticipantsRequest(channel=result.chats[0],filter=ChannelParticipantsSearch(""),offset=0,limit=500))
total,messages,senders = client.get_message_history('profesoroak_bot',limit=1)

for user in r.users:
    # Output user basic info while processing
    sys.stdout.write("%s - %s %s " % (user.id,user.first_name or "",user.last_name or ""))
    if user.username != None:
        sys.stdout.write("(@%s)" % user.username)

    sys.stdout.flush()

    # Search in cache. Use cached version if already registered and validated
    # and no special "refresh all" mode is used
    if args.refreshall == False and \
    str(user.id) in cached_users.keys() and \
    cached_users[str(user.id)]["registered"] == True and \
    cached_users[str(user.id)]["validated"] == True:
        if user.username != None:
            cached_users[str(user.id)]["username"] = user.username
        newuser = cached_users[str(user.id)]
        sys.stdout.write(" (Cached!)\n")
        sys.stdout.flush()
    else:
        # Ask Profesor Oak for relevant data
        sys.stdout.write(" (Asking Profesor Oak...)")
        sys.stdout.flush()
        client.send_message('profesoroak_bot', 'Quién es %s' % user.id)
        tries = 0
        while True:
            time.sleep(10 + tries * 2)

            sys.stdout.flush()
            oldtotal = total
            total,messages,senders = client.get_message_history('profesoroak_bot',limit=1)
            tries += 1
            if total >= (oldtotal+2):
                break
        sys.stdout.write(" (done!)\n")
        sys.stdout.flush()

        # Parse Professor Oak output
        newuser = {}
        if user.username != None:
            newuser["username"] = user.username
        if messages[0].message.find(u"✅") >- 1:
            newuser["registered"] = True
            newuser["validated"] = True
        elif messages[0].message.find(u"⚠️") >- 1:
            newuser["registered"] = True
            newuser["validated"] = False
        else:
            newuser["registered"] = False
        if messages[0].message.find(u"Amarillo") >- 1:
            newuser["team"] = "instinct"
        elif messages[0].message.find(u"Rojo") >- 1:
            newuser["team"] = "valor"
        elif messages[0].message.find(u"Azul") >- 1:
            newuser["team"] = "mystic"

    users[str(user.id)] = newuser
    cached_users[str(user.id)] = newuser

    # Save cache on disk
    with open(datapath + '/users.json', 'w') as f:
        json.dump(cached_users, f)

#
# Print information
#

print("Unregistered users:")
for u in users:
    if users[u]["registered"] == False:
        sys.stdout.write("%s " % u)
sys.stdout.write("\n")
sys.stdout.flush()

print("Unvalidated users:")
for u in users:
    if users[u]["registered"] == True and users[u]["validated"] == False:
        sys.stdout.write("%s " % u)
sys.stdout.write("\n")
sys.stdout.flush()

print("Validated users:")
for u in users:
    if users[u]["registered"] == True and users[u]["validated"] == True:
        sys.stdout.write("%s " % u)
sys.stdout.write("\n")
sys.stdout.flush()

print("Users without username:")
for u in users:
    if "username" not in users[u].keys():
        sys.stdout.write("%s " % u)
sys.stdout.write("\n")
sys.stdout.flush()

print("Users from team Mystic:")
for u in users:
    if users[u]["registered"] == True and "team" in users[u].keys() and \
        users[u]["team"] == "mystic":
        sys.stdout.write("%s " % u)
sys.stdout.write("\n")
sys.stdout.flush()

print("Users from team Valor:")
for u in users:
    if users[u]["registered"] == True and "team" in users[u].keys() and \
        users[u]["team"] == "valor":
        sys.stdout.write("%s " % u)
sys.stdout.write("\n")
sys.stdout.flush()

print("Users from team Instinc:")
for u in users:
    if users[u]["registered"] == True and "team" in users[u].keys() and \
        users[u]["team"] == "instinct":
        sys.stdout.write("%s " % u)
sys.stdout.write("\n")
sys.stdout.flush()
