# Blue key discord bot
###### Blue locksmith

### Requirements
* python 3.12>
* pip
* poetry

Install dependencies with:
`poetry install --no-root` 

Add .env file witrh filled values:
```
DISCORD_TOKEN=token
LOG_SOURCE_CHANNEL_ID = id
SYNC_SOURCE_CHANNEL_ID = id
SYNC_TARGET_THREAD_ID = id
MAPPING_FILE = 'message_mappings.json'
MESSAGE_REQUIRED_CONTENT = 'some required message'
ALLOWED_ROLES = comma,separated,roles
```
Run script with:
`poetry run python app.py`
