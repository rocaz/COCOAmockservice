# COCOAmockservice

Mock service of Verification and EN Key server for Japanese Exposure Notification Service a.k.a. "COCOA".

[![Python: 3.7+](https://img.shields.io/badge/Python-3.7+-4584b6.svg?style=popout&logo=python)](https://www.python.org/)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Requirement

- Python 3.7+
- Flask 1.1.2+
- I strongly recommend to use Pipenv

## Quick Start

1. Initiarize local SQLite db.

```
./init_db.sh
```

2. Set environment variable using example.env

```
. example.env
```

3. Install python packages required.

```
pip install -r requirements.txt
```

4. Start as Flask development server

```
flask run
```
or
```
python app.py
```

## API

- POST /diagnosis
  - Register positive's TEKs through Verification server.
- GET /list.json
  - Get TEK ZIp list json from EN Key server.
- GET /_n_.zip
  - GET TEK ZIP from EN Key server.

Plase see **examples_curl.txt**


## License

MIT

Copyright (c) 2020 rocaz.net

## See Also

https://developers.google.com/android/exposure-notifications/exposure-notifications-api

https://developer.apple.com/documentation/exposurenotification