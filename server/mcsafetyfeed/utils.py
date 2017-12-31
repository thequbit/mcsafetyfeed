
from pyramid.response import Response

from pyramid.view import view_config

#from .models import (
    #Users,
    #Histories,
#)

import transaction

import time
import datetime
import json
from uuid import UUID
import copy
import email
import traceback

#import requests
#class Logger(object):
#
#    _url = None
#
#    def __init__(self, url):
#        print("[INFO] Logger.__init__()")
#        self._url = url 
#
#    def log(self, entry):
#        print("[INFO] Logger.log()")
#        payload =json.dumps(entry)
#        r = requests.post(self._url, data=payload)
#        print(r.text)
#        #resp = None
#        #try:
#        if True:
#            resp = json.loads(r.text)
#        #except:
#        #    pass
#        return resp
#
#    def get_logs(self, start, count):
#        return []

class BaseRequest(object):

    def __init__(self, request, use_req=True):

        self.request = request
        print("\n\n--------------------------------")
        print("\nrequest:")
        print("\tclient:   %s" % self.request.client_addr)
        print("\tpath:     %s" % self.request.path)
        print("\tmethod:   %s" % self.request.method)
        print("\tget:      %s" % self.request.GET)
        print("\tpost:     %s" % self.request.POST)
        print("\tfull url: %s" % self.request.url)
        
        print('\ninit:')

        self.start_time = None
        self.stop_time = None

        # allow for req override from the calling web end
        # point class.  usually cls.req is dynamicly created
        # using the __dict___ of the ORM modle.  we allow
        # the web class to override it for non MVVM scheme
        if not hasattr(self, 'req'):
            self.req = dict()
            if use_req:
                print('\tinfo: using req for class:', self.cls.__single__)
                self.req = self.cls.to_req()
            if hasattr(self, '_req') and self._req:
                # copy additional validation rules into req
                for key in self._req:
                    if not key in self.req:
                        print("ERROR: key '" + key + "' not in self.req")
                    else:
                        for sub_key in self._req[key]:
                            self.req[key][sub_key] = self._req[key][sub_key]

        # authenticate 
        #self.user = self._authenticate()
        self.user = None

        # set the 'with_auth' flag used by the users table 
        # based on the user type
        self.with_auth = False
        if self.user and self.user.user_type == 'system':
            self.with_auth = True
        
        # parse the json payload, and validate it.
        self.payload = self._get_payload()

        # gets the GET params from the url and validates 
        # them.
        self.params = self._get_params()

        # pulls out the start and count from the GET params if
        # they are specified, other wise populates them with 
        # defaults
        self.start, self.count = self._build_paging()

        print('\tinfo: done.')

    def _tick(self):
        self.start_time = time.time()

    def _tock(self):
        self.stop_time = time.time()
        return self.stop_time - self.start_time

    def _build_paging(self, start=0, count=25, count_max=2500):
        if 'start' in self.request.GET and 'count' in self.request.GET:
            try:
                start = int(float(self.request.GET['start']))
                count = int(float(self.request.GET['count']))
                if count > count_max:
                    count = count_max
            except:
                # default count after error too low?
                start = 0
                count = 25
            del self.request.GET['start']
            del self.request.GET['count']
        return start, count

    def _authenticate(self):
        token = None
        user = None
        print("\ntoken:")
        try:
            # get as token
            token = self.request.GET['token']
            print('\tGET param: ', token)
        except:
            try:
                # get as token
                token = self.request.GET['token']
                print('\tGET param: ', token)
            except:
                try:
                    # get from session
                    token = self.request.session['token']
                    print('\tsession: ', token)
                except:
                    try:
                        # get from cookie
                        token = self.request.cookies['token']
                        print('\tcookies: ', token)
                    except:
                        print('\t<none> ( no token found )')
                        pass
        if token:
            print('\tuser:   ', token)
            if BaseRequest.validate_uuid4(token):
                try:
                    #with transaction.manager:
                    user = Users.get_by_token(self.request.dbsession, token)
                    if user:
                        print('\t', user.email)
                    else:
                        print('\t<none> ( no user associated with token )')
                except Exception as ex:
                    # nothing good
                    print('\terror: an exception occured while trying to get user by token.')
                    print('\texception: ', str(ex))
            else:
                print('\terror: invalid token format. token = ', token)
                pass
        else:
            print('\tnote: no token found!')
            pass
        if user:
            print('\t', user.id)
            pass
        else:
            print('\twarning: user not found')
            pass
        return user 

    def _get_payload(self):
        payload = {}
        print("\npayload:")
        try:
            if self.request.body == '' or self.request.body == b'' or self.request.body == None:
                pass
            else:
                payload = self.request.json_body
                for key in payload:
                    if payload[key] == 'None':
                        payload[key] = None
                    if '_datetime_utc' in key:
                        try:
                            payload[key] = datetime.datetime.strptime(payload[key], '%m/%d/%Y')
                        except:
                            try:
                                #2016-07-26T04:02:15.454275
                                payload[key] = datetime.datetime.strptime(payload[key].split('.')[0], '%Y-%m-%dT%H:%M:%S')
                            except:
                                raise Exception("invalid date format")
                    #
                    # This is for the whole Boolean issue with sqlite3 and foreign key length thing ... or something like that.
                    #
                    elif key == 'enabled' or key == 'selected':
                        int(payload[key])
                        
        except Exception as ex:
            print("\terror: ", str(ex))
            payload = None
        if payload:
            print("\tkey count: ", len(payload))
        return payload

    def _get_params(self):
        print('\nparams:')
        params = {}
        for key in self.request.GET:
            if key in self.cls.__dict__:
                if key[-3:] == '_id':
                    if BaseRequest.validate_uuid4(self.request.GET[key]):
                        params[key] = self.request.GET[key]
                    else:
                        print('\twarning: invalid id in key %s = "%s" ( invalid uuid )' % (key, self.request.GET[key]))    
                else:
                    # todo: may want to revisit this check
                    if key != 'start' and key != 'count' and key != 'token':
                        params[key] = self.request.GET[key]
        print('\tparams: ', end='')
        print(params)
        return params

    @classmethod
    def validate_value(cls, _val, _item):
        valid = False
        text = ''
        if _item['type'] == 'uuid':
            if BaseRequest.validate_uuid4(_val):
                valid = True
            else:
                text = 'Invalid UUID format.  UUIDs can be presented with or without dashes.'
        elif _item['type'] == 'unicode':
            if isinstance(_val, str):
                valid = True
            else:
                text = 'Invalid string.'
        elif _item['type'] == 'unicode_list':
            if isinstance(_val, list):
                valid = True
                for _v in _val:
                    if not isinstance(_v, str):
                        valid = False
                        break
        elif _item['type'] == 'email':
            if isinstance(_val, str):
                _full_name, _email = email.utils.parseaddr(_val)
                if _full_name == '' and _email != '':
                    valid = True
                else:
                    text = 'Invalid email format.'
            else:
                text = 'Invalid email stirng.'
        elif _item['type'] == 'datetime_utc':
            if BaseRequest.validate_date(_val):
                valid = True
            else:
                text = 'Invalid date/time format.  Allowed: "%m/%d/%Y", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"'
        elif _item['type'] == 'integer':
            if isinstance(_val, int):
                if 'range' in _item:
                    if 'low' and 'high' in _item['range']:
                        if _val > _item['range']['low'] and _val < _item['range']['high']:
                            valid = True
                        else:
                            text = 'Value out of range.  %i < value < %i' %(_item['range']['low'], _item['range']['high'])
                    else:
                        # if we get there, it's a developers issue.
                        text = 'Error 500'
                else:
                    valid = True
        elif _item['type'] == 'float':
            if isinstance(_val, float):
                if 'range' in _item:
                    if 'low' and 'high' in _item['range']:
                        if _val > _item['range']['low'] and _val < _item['range']['high']:
                            valid = True
                        else:
                            text = 'Value out of range.  %i < value < %i' %(_item['range']['low'], _item['range']['high'])
                    else:
                        # if we get there, it's a developers issue.
                        text = 'Error 500'
                else:
                    valid = True
            else:
                text = 'Invalid floating point number.'
        else:
            pass
        return valid, text

    @classmethod
    def validate_uuid4(cls, uuid_string):
        try:
            val = UUID(uuid_string, version=4)
        except:
            return None
        return val.hex == uuid_string.replace('-','')

    @classmethod
    def validate_date(cls, d):
        _d = None
        try:
            #07/26/2016
            _d = datetime.datetime.strptime(payload[key], '%m/%d/%Y')
        except:
            try:
                #2016-07-26
                _d = datetime.datetime.strptime(payload[key], '%Y-%m-%d')
            except:
                try:
                    #2016-07-26T04:02:15.454275
                    _d = datetime.datetime.strptime(payload[key].split('.')[0], '%Y-%m-%dT%H:%M:%S')
                except:
                    pass
        return _d

    def auth(self):
        ret = False
        if self.user and self.user.enabled:
            print('\tauth:     ', self.user.token)
            ret = True
        else:
            print("\tauth:     false")
            self.request.response.status = 401
        return ret

    def validate(self):
        valid = False
        print('\npayload validation:')
        valid = True
        valid_fields = []
        invalid_fields = []
        missing_fields = []
        omitted_fields = []
        not_permitted_fields = []
        _req = copy.deepcopy(self.req)
        for item in self.req:
            if item in self.payload:
                _val = self.payload[item]
                if BaseRequest.validate_value(_val, _req[item]):
                    print('\t%s [ OKAY ]' % item)
                    _req[item]['status'] = 'valid'
                    valid_fields.append(item)
                else:
                    print('\t%s [ INVALID ]' % item)
                    _req[item]['status'] = 'invalid'
                    invalid_fields.append(item)
                    valid = False
            else:
                if not item in self.payload and _req[item]['required']:
                    print('\t%s [ MISSING ]' % item)
                    _req[item]['status'] = 'missing'
                    missing_fields.append(item)
                    valid = False
                elif not item in self.payload and not _req[item]['required']:
                    print('\t%s [ OMITTED ]' % item)
                    _req[item]['status'] = 'omitted'
                    omitted_fields.append(item)
        for item in self.payload:
            if not item is 'token':
                if not item in self.req:
                    print('\t%s [ NOT PERMITTED ]' % item)
                    _req[item] = {}
                    _req[item]['status'] = 'not permitted'
                    not_permitted_fields.append(item)
                    valid = False
        print("\tvalid: %s" % valid)
        if not valid:
            _req['errors'] = dict(
                error_text = 'Invalid payload.',
                valid_fields = valid_fields,
                invalid_fields = invalid_fields,
                missing_fields = missing_fields,
                omitted_fields = omitted_fields,
                not_permitted_fields = not_permitted_fields,
            )

            self.request.response.status = 400
        self.req = copy.deepcopy(_req)
        return valid

    def __get(self):
        resp = {}
        print('\nget:')
        if 'id' in self.request.matchdict and BaseRequest.validate_uuid4(self.request.matchdict['id']):
            _id = self.request.matchdict['id']
            if _id != None and _id != 'null':
                thing = self.cls.get_by_id(
                    self.request.dbsession,
                    _id,
                )
                if thing:
                    print('\t', _id)
                    resp = thing.to_dict(self.with_auth)
                else:
                    print('\t<none> ( id not found )')
                    self.request.response.status = 404
            else:
                print('\terror: invalid. id = ', _id)
                self.request.response.status = 400
        else:
            print('\terror: missing id')
            self.request.response.status = 400
        return resp

    def __get_collection(self):
        resp = []
        print('\nget collection:')
        things = self.cls.get_paged(
            self.request.dbsession,
            self.start,
            self.count,
        )
        if things:
            print('\tcount: ', len(things))
            resp = [t.to_dict(self.with_auth) for t in things]
        else:
            #print('\twarning: not found.')
            pass
        return resp    

    def __get_collection_by(self):
        resp = []
        print('\nget collection by:')
        if len(self.params):
            things = self.cls.get_by(
                self.request.dbsession,
                self.params,
                self.start,
                self.count,
            )
            if things:
                print('\tcount: ', len(things))
                resp = [t.to_dict(self.with_auth) for t in things]
            else:
                #print('\twarning: not found.')
                pass
        else:
            print('error: params is empty.')
            self.request.response.status = 400
        return resp

    def __post(self):
        resp = {}
        print('\npost:')
        if self.validate():

            # this is so we populate the author id in the payload
            # automaticly with the authenticated user.  this is so 
            # we don't have to pass in our own id from the client
            if hasattr(self.cls, 'author_id') and not 'author_id' in self.payload:
                print('\tinfo: adding author_id to payload for class:', self.cls.__single__)
                self.payload['author_id'] = str(self.user.id)

            thing = self.cls.add(self.request.dbsession, **self.payload)
            if thing:
                print('\tinfo: success')
                resp = thing.to_dict(self.with_auth)
            else:
                print('\terror: unable to add for class ', self.cls.__single__)
                self.request.response.status = 500
        else:
            _errors = self.req['errors']
            del self.req['errors']
            resp = dict(
                fields = self.req,
                errors = _errors,
            )
        return resp

    def __put(self):
        resp = {}
        print('\nput:')
        if self.validate():

            # this is so we populate the author id in the payload
            # automaticly with the authenticated user.  this is so 
            # we don't have to pass in our own id from the client
            if hasattr(self.cls, 'author_id') and not 'author_id' in self.payload:
                print('\tinfo: adding author_id to payload for class:', self.cls.__single__)
                self.payload['author_id'] = str(self.user.id)
            
            _id = self.request.matchdict['id'].replace('-','')
            #thing = self.cls.update_by_id(self.request.dbsession, _id, **self.payload)
            thing = self.cls.get_by_id(self.request.dbsession, _id)
            if thing:
                if self.user.user_type is 'user' and hasattr(self.cls, 'author_id') and thing.author_id == self.user.id:
                    _thing = self.cls.update_by_thing(self.request.dbsession, thing, **self.payload)
                    if _thing:
                        print('\tinfo: successful')
                        resp = _thing.to_dict(self.with_auth)
                    else:
                        print('\tinfo: model could not be updated')
                        self.request.response.status = 400
                else:
                    print('\tinfo: unauthorized')
                    self.request.response.status = 403
            else:
                print('\tinfo: id not found')
                self.request.response.status = 404

        else:
            resp = json.dumps(self.req)
        return resp

    def __delete(self):
        resp = {}
        print('\ndelete:')
        _id = self.request.matchdict['id']
        thing = self.cls.delete_by_id(
            self.request.dbsession,
            _id,
        )
        if thing:
            print('\tsuccess')
            resp = thing.to_dict(self.with_auth)
        else:
            print('error: id not found')
            self.request.response.status = 404
        return resp

    #[ GET ]
    def _get(self, auth_required=True):
        resp = {}
        self._tick()
        try:
            if (auth_required and self.auth()) or not auth_required:
                resp = self.__get()
        except Exception as ex:
            # this is bad, this is a server error that we, 
            # hopefully, can recover from.
            resp = dict(
                error = 500,
                error_text = "An internal server error has occured.",
                exception_text = str(ex),
                tb = traceback.format_exc()
            )
            self.request.response.status = 500
        resp.update(exec_time=self._tock())
        return resp

    #[ GET COLLECTION ]
    def _get_collection(self, auth_required=True):
        resp = {}
        self._tick()
        try:
            if (auth_required and self.auth()) or not auth_required:
                if 'token' in self.request.GET:
                    del self.request.GET['token']
                if len(self.params) == 0:
                    resp.update(collection=self.__get_collection())
                else:
                    resp.update(collection=self.__get_collection_by())
                    
        except Exception as ex:
            # this is bad, this is a server error that we, 
            # hopefully, can recover from.
            resp = dict(
                error = 500,
                error_text = "An internal server error has occured.",
                exception_text = str(ex),
                tb = traceback.format_exc()
            )
            self.request.response.status = 500
        resp.update(exec_time=self._tock())
        return resp

    #[ POST ]
    def _post(self, auth_required=True):
        resp = {}
        self._tick()
        if not 'id' in self.request.matchdict:
            try:
                if (auth_required and self.auth()) or not auth_required:
                    resp = self.__post()
            except Exception as ex:
                # this is bad, this is a server error that we, 
                # hopefully, can recover from.
                resp = dict(
                    error = 500,
                    error_text = "An internal server error has occured.",
                    exception_text = str(ex),
                    tb = traceback.format_exc(),
                )
                self.request.response.status = 500
        else:
            self.request.response.status = 501
        resp.update(exec_time=self._tock())
        return resp

    #[ PUT ]
    def _put(self, auth_required=True):
        resp = {}
        self._tick()
        try:
            if (auth_required and self.auth()) or not auth_required:
                resp = self.__put()
        except Exception as ex:
            # this is bad, this is a server error that we, 
            # hopefully, can recover from.
            resp = dict(
                error = 500,
                error_text = "An internal server error has occured.",
                exception_text = str(ex),
                tb = traceback.format_exc()
            )
            self.request.response.status = 500
        resp.update(exec_time=self._tock())
        return resp

    #[ DELETE ]
    def _delete(self, auth_required=True):
        resp = {}
        self._tick()
        try:
            if (auth_required and self.auth()) or not auth_required:
                resp = self.__delete()
        except Exception as ex:
            # this is bad, this is a server error that we, 
            # hopefully, can recover from.
            resp = dict(
                error = 500,
                error_text = "An internal server error has occured.",
                exception_text = str(ex),
                tb = traceback.format_exc()
            )
            self.request.response.status = 500
        resp.update(exec_time=self._tock())
        return resp
       
    
