# osmChangeMonitorBot

this is a bot for telegram that monitors changes for a list of openstreetmap users.

you can customize your list and request stats by sending `/report`. Additionally, if a user exceeds 300 or 1000 changes in the current month, a notification message is sent.

## installation

 * create a bot token for telegram messenger: https://t.me/botfather

 * add the token to the secrets.env-File

 * use docker-compose to start: `docker-compose up`

## demo

or try it out (only working if my instance is running): https://t.me/osmChangesetBot

