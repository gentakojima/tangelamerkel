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
parser.add_argument('--human-output', help='Print the output with usernames when available', dest='humanoutput', action='store_true')

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
        if update.users[0].username == "ProfesorOak_bot":
            response = update.updates[0].message.message

            # Parse Professor Oak output
            if response.find(u"✅") >- 1:
                cached_users[askingOakUserId]["registered"] = True
                cached_users[askingOakUserId]["validated"] = True
            elif response.find(u"⚠️") >- 1:
                cached_users[askingOakUserId]["registered"] = True
                cached_users[askingOakUserId]["validated"] = False
            else:
                cached_users[askingOakUserId]["registered"] = False
            if response.find(u"Amarillo") >- 1:
                cached_users[askingOakUserId]["team"] = "instinct"
            elif response.find(u"Rojo") >- 1:
                cached_users[askingOakUserId]["team"] = "valor"
            elif response.find(u"Azul") >- 1:
                cached_users[askingOakUserId]["team"] = "mystic"

            # Add user info to global users dict
            users[askingOakUserId] = cached_users[askingOakUserId]

            # Save cache on disk
            with open(datapath + '/users.json', 'w') as f:
                json.dump(cached_users, f)
    except:
        pass

#
# Connect to Telegram
#

client = TelegramClient('session_name', configuration['api_id'], configuration['api_hash'])
client.connect()
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
    cached_users[str(user.id)]["registered"] == True and \
    cached_users[str(user.id)]["validated"] == True:
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
        # Ask Profesor Oak for relevant data
        sys.stdout.write(" (Asking Profesor Oak...")
        sys.stdout.flush()
        # Limit Oak questions to one every 20 seconds
        while lastOakQuestion != None and time.time() - lastOakQuestion < 20:
            sys.stdout.write(".")
            sys.stdout.flush()
            time.sleep(1)
        # Ok, we can continue now. Ask Oak!
        askingOakUserId = str(user.id)
        client.send_message('profesoroak_bot', 'Quién es %s' % user.id)
        lastOakQuestion = time.time()
        sys.stdout.write(")\n")
        sys.stdout.flush()

#
# Print information
#

print("Unregistered users:")
for u in users:
    if users[u]["registered"] == False:
        if args.humanoutput == True:
            sys.stdout.write(" %s - %s %s (@%s)\n" % \
                (u, \
                users[u]["first_name"] if "first_name" in users[u].keys() and users[u]["first_name"] != None else '', \
                users[u]["last_name"] if "last_name" in users[u].keys() and users[u]["last_name"] != None else '', \
                users[u]["username"] if "username" in users[u].keys() and users[u]["username"] != None else '', \
                ))
        else:
            sys.stdout.write("%s " % u)
sys.stdout.write("\n")
sys.stdout.flush()

print("Unvalidated users:")
for u in users:
    if users[u]["registered"] == True and users[u]["validated"] == False:
        if args.humanoutput == True:
            sys.stdout.write(" %s - %s %s (@%s)\n" % \
                (u, \
                users[u]["first_name"] if "first_name" in users[u].keys() and users[u]["first_name"] != None else '', \
                users[u]["last_name"] if "last_name" in users[u].keys() and users[u]["last_name"] != None else '', \
                users[u]["username"] if "username" in users[u].keys() and users[u]["username"] != None else '', \
                ))
        else:
            sys.stdout.write("%s " % u)
sys.stdout.write("\n")
sys.stdout.flush()

print("Validated users:")
for u in users:
    if users[u]["registered"] == True and users[u]["validated"] == True:
        if args.humanoutput == True:
            sys.stdout.write(" %s - %s %s (@%s)\n" % \
                (u, \
                users[u]["first_name"] if "first_name" in users[u].keys() and users[u]["first_name"] != None else '', \
                users[u]["last_name"] if "last_name" in users[u].keys() and users[u]["last_name"] != None else '', \
                users[u]["username"] if "username" in users[u].keys() and users[u]["username"] != None else '', \
                ))
        else:
            sys.stdout.write("%s " % u)
sys.stdout.write("\n")
sys.stdout.flush()

print("Users without username:")
for u in users:
    if "username" not in users[u].keys() or users[u]["username"] == None:
        if args.humanoutput == True:
            sys.stdout.write(" %s - %s %s (@%s)\n" % \
                (u, \
                users[u]["first_name"] if "first_name" in users[u].keys() and users[u]["first_name"] != None else '', \
                users[u]["last_name"] if "last_name" in users[u].keys() and users[u]["last_name"] != None else '', \
                users[u]["username"] if "username" in users[u].keys() and users[u]["username"] != None else '', \
                ))
        else:
            sys.stdout.write("%s " % u)
sys.stdout.write("\n")
sys.stdout.flush()

print("Users from team Mystic:")
for u in users:
    if users[u]["registered"] == True and "team" in users[u].keys() and \
        users[u]["team"] == "mystic":
        if args.humanoutput == True:
            sys.stdout.write(" %s - %s %s (@%s)\n" % \
                (u, \
                users[u]["first_name"] if "first_name" in users[u].keys() and users[u]["first_name"] != None else '', \
                users[u]["last_name"] if "last_name" in users[u].keys() and users[u]["last_name"] != None else '', \
                users[u]["username"] if "username" in users[u].keys() and users[u]["username"] != None else '', \
                ))
        else:
            sys.stdout.write("%s " % u)
sys.stdout.write("\n")
sys.stdout.flush()

print("Users from team Valor:")
for u in users:
    if users[u]["registered"] == True and "team" in users[u].keys() and \
        users[u]["team"] == "valor":
        if args.humanoutput == True:
            sys.stdout.write(" %s - %s %s (@%s)\n" % \
                (u, \
                users[u]["first_name"] if "first_name" in users[u].keys() and users[u]["first_name"] != None else '', \
                users[u]["last_name"] if "last_name" in users[u].keys() and users[u]["last_name"] != None else '', \
                users[u]["username"] if "username" in users[u].keys() and users[u]["username"] != None else '', \
                ))
        else:
            sys.stdout.write("%s " % u)
sys.stdout.write("\n")
sys.stdout.flush()

print("Users from team Instinc:")
for u in users:
    if users[u]["registered"] == True and "team" in users[u].keys() and \
        users[u]["team"] == "instinct":
        if args.humanoutput == True:
            sys.stdout.write(" %s - %s %s (@%s)\n" % \
                (u, \
                users[u]["first_name"] if "first_name" in users[u].keys() and users[u]["first_name"] != None else '', \
                users[u]["last_name"] if "last_name" in users[u].keys() and users[u]["last_name"] != None else '', \
                users[u]["username"] if "username" in users[u].keys() and users[u]["username"] != None else '', \
                ))
        else:
            sys.stdout.write("%s " % u)
sys.stdout.write("\n")
sys.stdout.flush()
