#!/usr/bin/python3

import time
import sys
import argparse
import json
import os
import traceback
import re

from telethon import TelegramClient
from telethon.tl.functions.contacts import ResolveUsernameRequest
from telethon.tl.functions.channels import GetParticipantsRequest
from telethon.tl.types import ChannelParticipantsSearch
from telethon.tl.types import Updates
from telethon.tl.types import UpdateShortMessage
from telethon.errors.rpc_errors_400 import UsernameInvalidError
from telethon.errors.rpc_errors_420 import FloodWaitError

#
# Parse command line args
#

parser = argparse.ArgumentParser(description='Helps moderating Pokémon GO Telegram groups with an iron hammer')
parser.add_argument('--force-setup', help='Force the initial setup, automatically called first time', dest='setup', action='store_true')
parser.add_argument('--only-telegram', help='Show only Telegram info (ignore Profesor Oak)', dest='onlytelegram', action='store_true')
parser.add_argument('--refresh-oak', help='Refresh Oak info for all users (Telegram info always refreshed)', dest='refreshall', action='store_true')
parser.add_argument('--group', help='Specify the group handle (use the @name)', nargs=1, dest='group')
parser.add_argument('--human-output', help='Print the output with usernames when available', dest='humanoutput', action='store_true')
parser.add_argument('--limit', help='Limit run to the first N people (for large groups or testing purposes)', nargs=1, dest='limit')

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
# Method to get the responses from Profesor Oak
#

askingOakUserId = None
lastOakQuestion = None
def receiveUpdate(update):
    global askingOakUserId
    global users
    global cached_users
    if askingOakUserId == None:
        return
    try:
        if isinstance(update,UpdateShortMessage) and update.user_id == 201760961:
            # Short message
            go_on = True
            response = update.message
        elif isinstance(update,Updates):
            # Set of messages
            go_on = False
            for u in update.updates:
                if hasattr(u,"message") and u.message.from_id == 201760961 and \
                    not hasattr(u.message.to_id,"channel_id"):
                    go_on = True
                    response = u.message.message
                    break
        else:
            go_on = False
        if go_on == True:
            # Parse Professor Oak output
            if response.find(u"✅") >- 1:
                cached_users[askingOakUserId]["registered"] = "True"
                cached_users[askingOakUserId]["validated"] = "True"
            elif response.find(u"⚠️") >- 1:
                cached_users[askingOakUserId]["registered"] = "True"
                cached_users[askingOakUserId]["validated"] = "False"
            else:
                cached_users[askingOakUserId]["registered"] = "False"
                cached_users[askingOakUserId]["validated"] = "False"
            if response.find(u"Amarillo") >- 1:
                cached_users[askingOakUserId]["team"] = "instinct"
            elif response.find(u"Rojo") >- 1:
                cached_users[askingOakUserId]["team"] = "valor"
            elif response.find(u"Azul") >- 1:
                cached_users[askingOakUserId]["team"] = "mystic"
            m = re.match("^@([a-zA-Z0-9]+),.*$", response)
            if m != None and m.lastindex == 1:
                cached_users[askingOakUserId]["pokemon_username"] = m.group(1)

            # Add user info to global users dict
            users[askingOakUserId] = cached_users[askingOakUserId]
            askingOakUserId = None

            # Save cache on disk
            with open(datapath + '/users.json', 'w') as f:
                json.dump(cached_users, f)
    except:
        print("\n\nUnhandled exception:")
        print(update)
        traceback.print_last()
        print("\n")
#
# Connect to Telegram
#

client = TelegramClient('session_name', configuration['api_id'], configuration['api_hash'])
if client.connect() != True:
    print("Can't connect to Telegram. Maybe you abused API limit retries? Also check your connection!")
    exit(1)
client.add_update_handler(receiveUpdate)

#
# Ensure you're authorized
#

if not client.is_user_authorized():
    client.send_code_request(configuration['phone'])
    client.sign_in(configuration['phone'], input('Authorization required. Check Telegram and enter the code: '))

#
# Search group
#

while True:
    try:
        result = client(ResolveUsernameRequest(str(args.group[0])))
    except UsernameInvalidError:
        pass
    except FloodWaitError as err:
        err = str(err)
        m = re.search('wait of (\d+) seconds',err)
        m, s = divmod(int(m.group(1)), 60)
        h, m = divmod(m, 60)
        print("Looks like you reached the API limit! Must wait %ih%im before trying again" % (h, m))
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
offset = 0
count = 0
while True:
    r = client(GetParticipantsRequest(channel=result.chats[0],filter=ChannelParticipantsSearch(""),offset=offset,limit=50))
    for user in r.users:
        # Output user basic info while processing
        sys.stdout.write("%s - %s %s " % (user.id,user.first_name or "",user.last_name or ""))
        if user.username != None:
            sys.stdout.write("(@%s)" % user.username)
        sys.stdout.flush()

        newuser = {}
        # Always update username, first name and last name
        if user.username != None:
            newuser["username"] = user.username
        if user.first_name != None:
            newuser["first_name"] = user.first_name
        if user.first_name != None:
            newuser["last_name"] = user.last_name

        # Search in cache. Use cached version if already registered and validated
        # and no special "refresh all" mode is used
        if args.refreshall == False and \
        str(user.id) in cached_users.keys() and \
        "registered" in cached_users[str(user.id)].keys() and \
        "pokemon_username" in cached_users[str(user.id)].keys() and \
        cached_users[str(user.id)]["registered"] == "True" and \
        cached_users[str(user.id)]["validated"] == "True":
            # Cached! Update cache username, first name and last name
            cached_users[str(user.id)]["username"] = user.username
            cached_users[str(user.id)]["first_name"] = user.first_name
            cached_users[str(user.id)]["last_name"] = user.last_name
            sys.stdout.write(" (Cached!)\n")
            sys.stdout.flush()
            # Add user info to global users dict
            users[str(user.id)] = cached_users[str(user.id)]
            # Update cache on disk
            with open(datapath + '/users.json', 'w') as f:
                json.dump(cached_users, f)
        else:
            # Add new user to cached users but don't write to disk now
            newuser = {}
            newuser["username"] = user.username
            newuser["first_name"] = user.first_name
            newuser["last_name"] = user.last_name
            cached_users[str(user.id)] = newuser
            if args.onlytelegram == False:
                # Ask Profesor Oak for relevant data
                sys.stdout.write(" (Asking Profesor Oak...")
                sys.stdout.flush()
                # Limit Oak questions to one every 15 seconds
                while lastOakQuestion != None and time.time() - lastOakQuestion < 15:
                    sys.stdout.write(".")
                    sys.stdout.flush()
                    time.sleep(1)
                # Ok, we can continue now. Ask Oak!
                askingOakUserId = str(user.id)
                client.send_message('profesoroak_bot', 'Quién es %s' % user.id)
                lastOakQuestion = time.time()
                sys.stdout.write(")\n")
                sys.stdout.flush()
            else:
                sys.stdout.write(" (Ignoring Profesor Oak)\n")
                sys.stdout.flush()
                # Add user info to global users dict
                users[str(user.id)] = newuser
                # Update cache on disk
                with open(datapath + '/users.json', 'w') as f:
                    json.dump(cached_users, f)
        count = count + 1
        if args.limit != None and int(args.limit[0]) <= count:
            break
    if (args.limit != None and int(args.limit[0]) <= count) or len(r.users) < 50:
        break
    else:
        offset = offset + 50

#
# Waiting for Profesor Oak
#

sys.stdout.write("Finishing...")
sys.stdout.flush()
while lastOakQuestion != None and time.time() - lastOakQuestion < 15:
    sys.stdout.write(".")
    sys.stdout.flush()
    time.sleep(1)
sys.stdout.write("\n")
sys.stdout.flush()

#
# Print information
#

def humanprint(u):
    sys.stdout.write(" %s - %s %s %s %s\n" % \
        (u, \
        users[u]["first_name"] if "first_name" in users[u].keys() and users[u]["first_name"] != None else '', \
        users[u]["last_name"] if "last_name" in users[u].keys() and users[u]["last_name"] != None else '', \
        "@" + users[u]["username"] if "username" in users[u].keys() and users[u]["username"] != None else '', \
        users[u]["pokemon_username"] if "pokemon_username" in users[u].keys() and users[u]["pokemon_username"] != None else '', \
        ))

sys.stdout.write("\n")
sys.stdout.flush()

print("Users without username:")
for u in users:
    if "username" not in users[u].keys() or users[u]["username"] == None:
        if args.humanoutput == True:
            humanprint(u)
        else:
            sys.stdout.write("%s " % u)
sys.stdout.write("\n")
sys.stdout.flush()

if args.onlytelegram ==  True:
    # The rest of the output is Oak info
    exit(0)

print("Unregistered users:")
for u in users:
    if "registered" not in users[u].keys() or users[u]["registered"] == "False":
        if args.humanoutput == True:
            humanprint(u)
        else:
            sys.stdout.write("%s " % u)
sys.stdout.write("\n")
sys.stdout.flush()

print("Unvalidated users:")
for u in users:
    if users[u]["registered"] == "True" and \
        ("validated" not in users[u].keys() or users[u]["validated"] == "False"):
        if args.humanoutput == True:
            humanprint(u)
        else:
            sys.stdout.write("%s " % u)
sys.stdout.write("\n")
sys.stdout.flush()

print("Validated users:")
for u in users:
    if users[u]["registered"] == "True" and users[u]["validated"] == "True":
        if args.humanoutput == True:
            humanprint(u)
        else:
            sys.stdout.write("%s " % u)
sys.stdout.write("\n")
sys.stdout.flush()

print("Users from team Mystic:")
for u in users:
    if users[u]["registered"] == "True" and "team" in users[u].keys() and \
        users[u]["team"] == "mystic":
        if args.humanoutput == True:
            humanprint(u)
        else:
            sys.stdout.write("%s " % u)
sys.stdout.write("\n")
sys.stdout.flush()

print("Users from team Valor:")
for u in users:
    if users[u]["registered"] == "True" and "team" in users[u].keys() and \
        users[u]["team"] == "valor":
        if args.humanoutput == True:
            humanprint(u)
        else:
            sys.stdout.write("%s " % u)
sys.stdout.write("\n")
sys.stdout.flush()

print("Users from team Instinct:")
for u in users:
    if users[u]["registered"] == "True" and "team" in users[u].keys() and \
        users[u]["team"] == "instinct":
        if args.humanoutput == True:
            humanprint(u)
        else:
            sys.stdout.write("%s " % u)
sys.stdout.write("\n")
sys.stdout.flush()
