
import json
import datetime
#import uuid
#import hashlib
#import os

from dateutil import parser as dateparser

from pyramid.view import (
    view_defaults,
    view_config,
)

from ..utils import (
    BaseRequest,
)

from ..geocode import (
    geocode,
)

import transaction

from ..models import (
    ScraperRuns,
    Dispatches,
    CallTypes,
    Addresses,
    Agencies,
    DailyAgencyStats,
    MonthlyAgencyStats,
    Incidents,
    Settings,
)

@view_config(route_name='/', renderer='../static/index.jinja2')
def view_index(request):
    return {}

@view_defaults(route_name='/api/v1/scraper_runs', renderer='json')
class ScraperRunsAPI(BaseRequest):
    
    cls = ScraperRuns

    def __init__(self, request):
        super(ScraperRunsAPI, self).__init__(request)
        
    @view_config(request_method='GET')
    def get(self):
        resp = []
        with transaction.manager:
            resp = self._get_collection(auth_required=False)
        return resp

    @view_config(request_method='POST')
    def post(self):
        resp = {}
        with transaction.manager:
            if 'token' in self.request.GET:
                token = self.request.GET['token']
                if self.validate_uuid4(token):
                    setting = Settings.get_by(
                        self.request.dbsession,
                        dict(
                            name='scraper_token',
                            value=token
                        ),
                    )
                    if setting:
                        if self.validate():

                            scraper_run = ScraperRuns.add(
                                self.request.dbsession,
                                xml=self.payload['xml'],
                            )

                        else:
                            self.request.response.status = 400
                            resp = self.req
                            resp.update(
                                details="failed validate"
                            )
                    else:
                        self.request.response.status = 403    
                        resp = self.req
                        resp.update(
                            details="no setting"
                        )
                else:
                    self.request.response.status = 400
                    resp = self.req
                    resp.update(
                        details="invalid token"
                    )
            else:
                self.request.response.status = 400
                resp = self.req
                resp.update(
                    details="no token in GET"
                )
        return resp

@view_defaults(route_name='/api/v1/dispatches', renderer='json')
class DispatchesAPI(BaseRequest):
    
    cls = Dispatches

    def __init__(self, request):
        super(DispatchesAPI, self).__init__(request)
        
    @view_config(request_method='GET')
    def get(self):
        resp = []
        with transaction.manager:
            resp = self._get_collection(auth_required=False)
        return resp

@view_defaults(route_name='/api/v1/dispatches/_publish', renderer='json')
class DispatchesInsertAPI(BaseRequest):
    
    cls = Dispatches

    req = dict(
        title=dict(
            type='unicode',
            required=True,
        ),
        #raw_address=dict(
        #    type='unicode',
        #    required=True,
        #),
        publish_datetime=dict(
            type='unicode',
            required=True,
        ),
        description=dict(
            type='unicode',
            required=True,
        ),
        #dispatch_unique=dict(
        #    type='unicode',
        #    required=True,
        #),
        lat=dict(
            type='float',
            required=False,
        ),
        lng=dict(
            type='float',
            required=False,
        ),
    )

    def __init__(self, request):
        super(DispatchesInsertAPI, self).__init__(request)
        
    @view_config(request_method='POST')
    def post(self):
        resp = {}
        with transaction.manager:
            if 'token' in self.request.GET:
                token = self.request.GET['token']
                if self.validate_uuid4(token):
                    setting = Settings.get_by(
                        self.request.dbsession,
                        dict(
                            name='scraper_token',
                            value=token
                        ),
                    )
                    if setting:
                        if self.validate():

                            #
                            # we get the raw data from the scraper, we need to 
                            # parse that data into it's respective parts
                            #

                            SPLIT_STR = ' at '
                            _split_index = self.payload['title'].rfind(SPLIT_STR)
                            call_type_string = self.payload['title'][:_split_index]
                            raw_address_string = self.payload['title'][_split_index+len(SPLIT_STR):] 

                            print("Call Type: %s"  % call_type_string)
                            print("Raw Address: %s" % raw_address_string)

                            _desc_parts = self.payload['description'].split(',')
                            status_string = _desc_parts[0].replace('Status:','').strip()
                            id_string = _desc_parts[1].replace('ID:','').strip()
                            agency_short_name = id_string[:4]

                            print("Status: %s"  % status_string)
                            print("ID: %s"  % id_string)
                            print("Short Name: %s"  % agency_short_name)

                            #raise Exception('debug')

                            dispatch = Dispatches.get_by(
                                self.request.dbsession,
                                dict(
                                    dispatch_unique=id_string,
                                )
                            )
                            if dispatch:

                                if isinstance(dispatch, list) and len(dispatch) > 0:
                                    dispatch = dispatch[0]

                                # does exist, may need to update.  check if the datetime
                                # for this status is null, and if it is, set it to the 
                                # current datetime.
                                key = '%s_datetime_utc' % status_string.lower()
                                if dispatch.__dict__[key] == None:
                                    payload = dict()
                                    payload[key] = datetime.datetime.utcnow()
                                    dispatch = Dispatches.update_by_id(self.request.dbsession, dispatch.id, **payload)

                            else:

                                # query for or create call type
                                call_type = CallTypes.get_by(
                                    self.request.dbsession,
                                    dict(
                                        title=call_type_string
                                    ),
                                )

                                if isinstance(call_type, list) and len(call_type) > 0:
                                    call_type = call_type[0]

                                if not call_type:
                                    call_type = CallTypes.add(
                                        self.request.dbsession,
                                        title=call_type_string,
                                    )

                                # query for or create address
                                address = Addresses.get_by(
                                    self.request.dbsession,
                                    dict(
                                        raw_address=raw_address_string,
                                    ),
                                )

                                if isinstance(address, list) and len(address) > 0:
                                    address = address[0]

                                if not address:
                                    
                                    # figure out if lat/lng have been included
                                    # in the publish ( this is different than )
                                    # what we reverse geocode
                                    pub_lat = None
                                    pub_lng = None
                                    if 'lat' in self.payload and 'lng' in self.payload:
                                        pub_lat = self.payload['lat']
                                        pub_lng = self.payload['lng']

                                    address = Addresses.add(
                                        self.request.dbsession,
                                        raw_address=raw_address_string,
                                        geocoded=0,
                                        pub_lat=pub_lat,
                                        pub_lng=pub_lng,
                                    )

                                    # try and perform a geo lookup
                                    geo_result = geocode(raw_address_string)
                                    if geo_result:
                                        address = Addresses.update_by_id(self.request.dbsession, address.id, **geo_result)

                                # query for or agency
                                if len(id_string) >= 4:
                                    agency = Agencies.get_by(
                                        self.request.dbsession,
                                        dict(
                                            short_name=agency_short_name
                                        ),
                                    )

                                    if isinstance(agency, list) and len(agency) > 0:
                                        agency = agency[0]

                                    if not agency:
                                        #
                                        # *really* shouldn't happen because we
                                        # will load in agencies by hand
                                        #
                                        agency = Agencies.add(
                                            self.request.dbsession,
                                            short_name=agency_short_name,
                                            full_name='',
                                            agency_type=agency_short_name[-1],
                                            description='',
                                            website_url='',
                                        )
                                else:
                                    
                                    #
                                    # the dispatch ID doesn't match the pattern
                                    # we exect.
                                    #

                                    #
                                    # todo:
                                    #   report this?
                                    #

                                    pass

                                def date_string_to_datetime_utc(_str):
                                    dt_str = _str.split(',')[1].strip()
                                    offset = float(dt_str.split(' -')[1].strip())
                                    dt_str = dt_str.split(' -')[0].strip()
                                    #try:
                                    if True:
                                        dt = datetime.datetime.strptime(dt_str, "%d %b %Y %H:%M:%S")
                                    #except:
                                    #    dt = None
                                    return dt

                                publish_datetime_utc = date_string_to_datetime_utc(self.payload['publish_datetime'])
                                payload = dict(
                                    call_type_id=call_type.id,
                                    address_id=address.id,
                                    publish_datetime_utc=publish_datetime_utc,
                                    current_status=status_string,
                                    dispatch_unique=id_string,
                                    pub_lat=self.payload['lat'] if 'lat' in self.payload else None,
                                    pub_lng=self.payload['lng'] if 'lng' in self.payload else None,
                                    agency_id=agency.id,
                                )
                                dispatch = Dispatches.add(self.request.dbsession, **payload)
                            resp = dispatch.to_dict()

                        else:
                            self.request.response.status = 400
                            resp = self.req
                            resp.update(
                                details="failed validate"
                            )
                    else:
                        self.request.response.status = 403    
                        resp = self.req
                        resp.update(
                            details="no setting"
                        )
                else:
                    self.request.response.status = 400
                    resp = self.req
                    resp.update(
                        details="invalid token"
                    )
            else:
                self.request.response.status = 400
                resp = self.req
                resp.update(
                    details="no token in GET"
                )

        return resp


@view_defaults(route_name='/api/v1/dispatches/_cleanup', renderer='json')
class DispatchesCleanupAPI(BaseRequest):

    cls = Dispatches

    req = dict(
        dispatch_uniques=dict(
            type='unicode_list',
            required=True,
        ),
    )

    def __init__(self, request):
        super(DispatchesCleanupAPI, self).__init__(request)

    @view_config(request_method='PUT')
    def put(self):
        resp = []
        with transaction.manager:
            if 'token' in self.request.GET:
                token = self.request.GET['token']
                if self.validate_uuid4(token):
                    setting = Settings.get_by(
                        self.request.dbsession,
                        dict(
                            name='scraper_token',
                            value=token
                        ),
                    )
                    if setting:
                        if self.validate():

                            open_dispatches = Dispatches.get_by(
                                self.request.dbsession,
                                dict(
                                    closed_datetime_utc=None,
                                )
                            )

                            dispatches = []
                            for d in open_dispatches:
                                if not d.dispatch_unique in self.payload['dispatch_uniques']:
                                    dispatch = Dispatches.update_by_id(
                                        self.request.dbsession,
                                        d.id,
                                        closed_datetime_utc=datetime.datetime.utcnow(),
                                        current_status='CLOSED',
                                    )
                                    if dispatch:
                                        dispatches.append(dispatch)

                            resp = [d.to_dict() for d in dispatches]

                        else:
                            self.request.response.status = 400
                            resp = self.req
                            resp.update(
                                details="failed validate"
                            )
                    else:
                        self.request.response.status = 403    
                        resp = self.req
                        resp.update(
                            details="no setting"
                        )
                else:
                    self.request.response.status = 400
                    resp = self.req
                    resp.update(
                        details="invalid token"
                    )
            else:
                self.request.response.status = 400
                resp = self.req
                resp.update(
                    details="no token in GET"
                )

        return resp


@view_defaults(route_name='/api/v1/dispatches/{id}', renderer='json')
class DispatchAPI(BaseRequest):

    cls = Dispatches

    def __init__(self, request):
        super(DispatchAPI, self).__init__(request)

    @view_config(request_method='GET')
    def get(self):
        with transaction.manager:
            resp = self._get(auth_required=False)
        return resp


@view_defaults(route_name='/api/v1/call_types', renderer='json')
class CallTypesAPI(BaseRequest):
    
    cls = CallTypes

    def __init__(self, request):
        super(DispatchesAPI, self).__init__(request)
        
    @view_config(request_method='GET')
    def get(self):
        resp = []
        with transaction.manager:
            resp = self._get_collection(auth_required=False)
        return resp


@view_defaults(route_name='/api/v1/call_types/{id}', renderer='json')
class CallTypeAPI(BaseRequest):

    cls = CallTypes

    def __init__(self, request):
        super(DispatchAPI, self).__init__(request)

    @view_config(request_method='GET')
    def get(self):
        with transaction.manager:
            resp = self._get(auth_required=False)
        return resp


@view_defaults(route_name='/api/v1/addresses', renderer='json')
class AddressesAPI(BaseRequest):
    
    cls = Addresses

    def __init__(self, request):
        super(AddressesAPI, self).__init__(request)
        
    @view_config(request_method='GET')
    def get(self):
        resp = []
        with transaction.manager:
            resp = self._get_collection(auth_required=False)
        return resp


@view_defaults(route_name='/api/v1/addresses/_query', renderer='json')
class AddressesQueryAPI(BaseRequest):
    
    cls = Addresses

    def __init__(self, request):
        super(AddressesQueryAPI, self).__init__(request)
        
    @view_config(request_method='GET')
    def get(self):
        resp = []
        #with transaction.manager:
            #resp = self._get_collection(auth_required=False)

            #
            # todo:
            #   implement fuzzy search for addresses
            #

        return resp


@view_defaults(route_name='/api/v1/addresses/{id}', renderer='json')
class AddressAPI(BaseRequest):

    cls = Addresses

    def __init__(self, request):
        super(AddressAPI, self).__init__(request)

    @view_config(request_method='GET')
    def get(self):
        with transaction.manager:
            resp = self._get(auth_required=False)
        return resp


@view_defaults(route_name='/api/v1/agencies', renderer='json')
class AgenciesAPI(BaseRequest):
    
    cls = Agencies

    def __init__(self, request):
        super(AgenciesAPI, self).__init__(request)
        
    @view_config(request_method='GET')
    def get(self):
        resp = []
        with transaction.manager:
            resp = self._get_collection(auth_required=False)
        return resp


@view_defaults(route_name='/api/v1/agencies/{id}', renderer='json')
class AgencyAPI(BaseRequest):

    cls = Agencies

    def __init__(self, request):
        super(AgencyAPI, self).__init__(request)

    @view_config(request_method='GET')
    def get(self):
        with transaction.manager:
            resp = self._get(auth_required=False)
        return resp


@view_defaults(route_name='/api/v1/incidents', renderer='json')
class IncidentsAPI(BaseRequest):
    
    cls = Incidents

    def __init__(self, request):
        super(IncidentsAPI, self).__init__(request)
        
    @view_config(request_method='GET')
    def get(self):
        resp = []
        with transaction.manager:
            resp = self._get_collection(auth_required=False)
        return resp


@view_defaults(route_name='/api/v1/incidents/{id}', renderer='json')
class IncidentAPI(BaseRequest):

    cls = Incidents

    def __init__(self, request):
        super(IncidentAPI, self).__init__(request)

    @view_config(request_method='GET')
    def get(self):
        with transaction.manager:
            resp = self._get(auth_required=False)
        return resp

@view_defaults(route_name='/api/v1/settings', renderer='json')
class SettingsAPI(BaseRequest):
    
    cls = Settings

    def __init__(self, request):
        super(SettingsAPI, self).__init__(request)
        
    @view_config(request_method='GET')
    def get(self):
        resp = []
        with transaction.manager:
            resp = self._get_collection()
        return resp

    @view_config(request_method='POST')
    def post(self):
        with transaction.manager:
            resp = self._post()
        return resp


@view_defaults(route_name='/api/v1/settings/{id}', renderer='json')
class SettingAPI(BaseRequest):

    cls = Settings

    def __init__(self, request):
        super(SettingAPI, self).__init__(request)

    @view_config(request_method='GET')
    def get(self):
        with transaction.manager:
            resp = self._get()
        return resp

    @view_config(request_method='PUT')
    def put(self):
        with transaction.manager:
            resp = self._put()
        return resp

    @view_config(request_method='DELETE')
    def delete(self):
        with transaction.manager:
            resp = self._delete()
        return resp
