#!/usr/bin/env python

import os
from transer.utils import init_db, recreate_entire_database

recreate_entire_database(engine=init_db(uri=os.environ.get("DATABASE_URL")))
