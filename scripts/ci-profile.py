"""Write the explicitly configured CI OAuth profile without printing credentials."""
import configparser
import os
from pathlib import Path

profile = configparser.ConfigParser(interpolation=None)
profile['ci'] = {key: os.environ[env] for key, env in (
    ('host', 'DATABRICKS_HOST'), ('client_id', 'DATABRICKS_CLIENT_ID'),
    ('client_secret', 'DATABRICKS_CLIENT_SECRET'))}
if not all(profile['ci'].values()):
    raise ValueError('Configure all CI OAuth secrets in the selected GitHub environment')
path = Path.home() / '.databrickscfg'
fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, 'w') as stream:
    profile.write(stream)
