# tg_schedule_woodpecker

Simple Bot to sending media files to Telegram channel according to a interval
schedule.

This Bot uses the Updater class to handle the bot and the JobQueue to send
messages in linear defined time intervals.

Press `Ctrl-C` on the command line or send a signal to the process to stop the
bot.

## Build Windows Application 

To create runnable execute application use next:
```bash
pyinstaller --onefile --console main.py
```
[More info about PyInstaller](https://www.pyinstaller.org/)

## BOT /start command example
```
tg_schedule_woodpecker v1.0.1
Hello! I am sending media files to Telegram channel according to selected interval schedule.

You can control me by sending these commands:

Commands
/start - Initial point (now you here)
/help - List of available commands (same as /start)
/send - Post next media to channel now
/set [interval] - Create schedule job for publishing a limited set of media
/clear - Clear the current job queue
/uinfo - You personal Telegram account information
```

## Requirements

* Python 3.4 or later
* python-telegram-bot
* pyinstaller (only for Windows builds)

## Support & Contributing
Anyone is welcome to contribute. If you decide to get involved, please take a moment and check out the following:

* [Bug reports](.github/ISSUE_TEMPLATE/bug_report.md)
* [Feature requests](.github/ISSUE_TEMPLATE/feature_request.md)

## License

The code is available under the [MIT license](LICENSE).
