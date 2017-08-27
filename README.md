# Tangela Merkel

A simple Python script that helps moderating Pokémon Go groups in Telegram.

Using the Telethon library for communicating with Telergam, Tangela Merkel
talks for you with @duhow's [Profesor Oak](https://github.com/duhow/ProfesorOak)
and lets you know how many people in a group is not registered, not validated or
(in the future) is flagged as spammer, fly and others.

After the run, you will receive simple listings that you can later process to
kick, ban or whatever you want to do to the undesired group users!

## Requeriments

Only runs in Python 3, no Python 2.7 support. To install dependencies just run:

```
pip3 install -r requeriments.txt
```

## Running

```
jorge@den:~/tangelamerkel$ ./tangelamerkel.py -h
usage: tangelamerkel.py [-h] [--force-setup] [--refresh-all] [--group GROUP]

Helps moderating Pokémon GO Telegram groups with an iron hammer

optional arguments:
  -h, --help     show this help message and exit
  --force-setup  Force the initial setup, automatically called first time
  --refresh-all  Refresh all users, even if known to be already validated
  --group GROUP  Specify the group handle (use the @name)
```

First time you will be asked for an [API key, API hash](https://my.telegram.org/)
and your phone number. This script will connect with the account linked to that
phone number. You can force the setup again with the argument `--force-setup`.

Tangela will cache on disk already validated users for subsequent runs. If you
want to ignore what is in cache and want to refresh all users, use the
argument `--refresh-all`.

## Bugs

Probably a bunch. The code was barely tested yet. I had a problem with the API
limit so I'm still waiting to keep the tests going. Use at your own risk!
