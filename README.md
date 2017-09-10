# Tangela Merkel

A simple Python script that helps moderating Pokémon Go groups in Telegram.

Using the Telethon library for communicating with Telegram, Tangela Merkel
talks for you with @duhow's [Profesor Oak](https://github.com/duhow/ProfesorOak)
and lets you know how many people in a group is not registered, not validated or
(probably in the near future) is flagged as spam, fly or others.

Please notice that questions to Profesor Oak are intentionally limited to one
every 15 seconds to avoid flooding the bot. A channel consisting of 200 users
will last about 50 minutes on the first run.

Tangela caches users information on disk and registered and validated users
are only requested once. Assuming 80% of registered users in a channel consisting
of 200 users, the script would only last about 12 minutes on the second run.

After every run, you will get simple numeric ID listings that you can
later process to kick, ban or whatever you want to do! If you want to get more
information alongside IDs, make sure to use the `--human-output` argument.

## Requeriments

Only runs in Python 3 (no Python 2.7 support!). To install dependencies just run:

```
pip3 install -r requeriments.txt
```

## Running

```
$ ./tangelamerkel.py --help
usage: tangelamerkel.py [-h] [--force-setup] [--only-telegram] [--refresh-oak]
                        [--group GROUP] [--human-output]

Helps moderating Pokémon GO Telegram groups with an iron hammer

optional arguments:
  -h, --help       show this help message and exit
  --force-setup    Force the initial setup, automatically called first time
  --only-telegram  Show only Telegram info (ignore Profesor Oak)
  --refresh-oak    Refresh Oak info for all users (Telegram info always
                   refreshed)
  --group GROUP    Specify the group handle (use the @name)
  --human-output   Print the output with usernames when available
  --limit LIMIT    Limit run to the first N people (for large groups or
                 testing purposes)
```

On first run you will be asked for an [API key, API hash](https://my.telegram.org/)
and your phone number. This script will connect with the account linked to that
phone number. If anything goes wrong, you can force the setup again with the 
argument `--force-setup`.

To ignore the disk cache and refresh all users, use the argument `--refresh-oak`.
Sorry, Oak. Make sure to [donate a pair of euros to duhow](http://donar.profoak.me).

If you are only interested in getting what users have no username assigned
you can add the argument `--only-telegram`. It won't ask Oak for any information,
so the script should last only some seconds.

## FAQ

### What do I do with that numeric ID listings?
You can use the ids to kick users using the command `/kick` in Profesor Oak. Note
that Profesor Oak must be group administrator. If you want a more human-friendly
output with more information, use the argument `--human-output`.

### Won't this spam Profesor Oak a lot?
Since most people will only be asked once, if validated, and there is some waiting
between requests... I hope not. Even so, use with caution.

### I'm getting told that I reached the API limit! Why?
Sincerely, don't know. The script tries to be gentle with the API, but seems like
large channels (>250 users) will sometimes trigger the API limit. In that case,
you might want to use the option `--limit N` to limit the script to the first 250
users, act accordingly and then wait some hours to repeat with a slightly higher
number.

## Bugs

Probably a bunch. The code was barely tested yet. I had a problem with the API
limit so I'm still waiting to keep the tests going. This could kill your Telegram
account, ba-da-boom your computer, hold your foldy flops, or even turn your Pokémon
Go account into Mystic, so use at your own risk!
