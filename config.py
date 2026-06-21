import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ['DATABASE_URL']
MONITOR_INTERVAL_HOURS = int(os.getenv('MONITOR_INTERVAL_HOURS', '8'))
BECKERS_PAYER_FEED_URL = 'https://www.beckerspayer.com/feed/'
BECKERS_PAYER_SITEMAP_INDEX = 'https://www.beckerspayer.com/sitemap_index.xml'
