import os
import sys
import uuid

import transaction

from pyramid.paster import (
    get_appsettings,
    setup_logging,
    )

from pyramid.scripts.common import parse_vars

from ..models.meta import Base
from ..models import (
    get_engine,
    get_session_factory,
    get_tm_session,
    Agencies,
    Settings,
)


def usage(argv):
    cmd = os.path.basename(argv[0])
    print('usage: %s <config_uri> [var=value]\n'
          '(example: "%s development.ini")' % (cmd, cmd))
    sys.exit(1)


def main(argv=sys.argv):
    if len(argv) < 2:
        usage(argv)
    config_uri = argv[1]
    options = parse_vars(argv[2:])
    setup_logging(config_uri)
    settings = get_appsettings(config_uri, options=options)

    engine = get_engine(settings)
    Base.metadata.create_all(engine)

    session_factory = get_session_factory(engine)

    with transaction.manager:
        dbsession = get_tm_session(session_factory, transaction.manager)

        #
        # import agencies
        #

        import os
        print(os.getcwd())

        with open('./mcsafetyfeed/scripts/agencies.tsv', 'r') as f:
            lines = f.read().replace('\r\n', '\n').split('\n')

        for line in lines:
            parts = line.split('\t')
            if len(parts) >= 6:
                _id = parts[0].strip()
                _shortname = parts[1].strip()
                _longname = parts[2].strip()
                _type = parts[3].strip()
                _description = parts[4].strip()
                _websiteurl = parts[5].strip()

                _agency = Agencies.get_by(
                    dbsession, 
                    dict(
                        short_name=_shortname,
                    ),
                )
                if not _agency:
                    _agency = Agencies.add(
                        dbsession,
                        short_name=_shortname,
                        full_name=_longname, 
                        agency_type=_type, 
                        description=_description,
                        website_url=_websiteurl,
                    )
                    print("Added %s as %s successfully." % (_agency.full_name, _agency.id))
                else:
                    if isinstance(_agency, list) and len(_agency) != 0:
                        _agency = _agency[0]
                    print("Ignoring %s - already exists." % _agency.full_name)
        #
        # create scraper token
        #

        scraper_token = str(uuid.uuid4())

        setting = Settings.get_by(
            dbsession,
            dict(
                name='scraper_token',
            ),
        )

        if not setting:
            setting = Settings.add(
                dbsession,
                permission_level=0,
                name='scraper_token',
                value=scraper_token,
                value_type='uuid',
            )

        if isinstance(setting, list) and len(setting) != 0:
            setting = setting[0]

        print("Scraper Token: %s" % setting.value)
