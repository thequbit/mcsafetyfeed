import json
from uuid import uuid4
import hashlib

from time import sleep
from random import randint
import datetime

import transaction

from sqlalchemy_utils import UUIDType
from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    Float,
    UnicodeText,
    DateTime,
    distinct,
    func,
    desc,
    or_,
)
from sqlalchemy.orm import (
    relationship
)

from .meta import Base

class CreationMixin():

    id = Column(UUIDType(binary=False), primary_key=True, unique=True)

    creation_datetime_utc = Column(DateTime, default=datetime.datetime.utcnow(), nullable=False)
    modified_datetime_utc = Column(DateTime, default=datetime.datetime.utcnow(), nullable=False)

    has_been_modified = Column(Integer, default=0, nullable=False)
    deleted = Column(Integer, default=0, nullable=False)

    @classmethod
    def add(cls, dbsession, **kwargs):
        thing = cls(**kwargs)
        if thing.id is None:
            thing.id = str(uuid4())
        thing.creation_datetime_utc = datetime.datetime.utcnow()
        thing.modified_datetime_utc = datetime.datetime.utcnow()
        dbsession.add(thing)
        #_thing = cls.get_by_id(dbsession, thing.id)
        return thing

    @classmethod
    def get_all(cls, dbsession):
        things = dbsession.query(
            cls,
        ).order_by(
            desc(cls.creation_datetime_utc),
        ).all()
        if things:
            if not isinstance(things, list):
                things = [things]
        return things

    @classmethod
    def get_paged(cls, dbsession, start=0, count=25):
        things = dbsession.query(
            cls,
        ).order_by(
            desc(cls.creation_datetime_utc),
        ).slice(start, start+count).all()
        if things:
            if not isinstance(things, list):
                things = [things]
        return things

    @classmethod
    def get_by_id(cls, dbsession, id):
        thing = dbsession.query(
            cls,
        ).filter(
            cls.id == id,
        ).first()
        return thing

    @classmethod
    def delete_by_id(cls, dbsession, _id):
        thing = cls.get_by_id(dbsession, _id)
        if thing is not None:
            thing.deleted = 1
            dbsession.add(thing)
            #dbsession.delete(thing)
        return thing

    @classmethod
    def update_by_id(cls, dbsession, _id, **kwargs):
        keys = set(cls.__dict__)
        _thing = None
        thing = dbsession.query(cls).filter(cls.id==_id).first()
        if thing is not None:
            for k in kwargs:
                if k in keys:
                    setattr(thing, k, kwargs[k])
            thing.modified_datetime_utc = datetime.datetime.utcnow()
            thing.has_been_modified = 1
            dbsession.add(thing)
            #_thing = cls.get_by_id(dbsession, thing.id)
            _thing = thing
        return _thing

    @classmethod
    def update_by_thing(cls, dbsession, thing, **kwargs):
        keys = set(cls.__dict__)
        _thing = None
        if thing is not None:
            for k in kwargs:
                if k in keys:
                    setattr(thing, k, kwargs[k])
            thing.modified_datetime_utc = datetime.datetime.utcnow()
            thing.has_been_modified = 1
            dbsession.add(thing)
            #_thing = cls.get_by_id(dbsession, thing.id)
            _thing = thing
        return _thing

    @classmethod
    def to_req(cls):
        _ignore = (
            '_sa_instance_state',
            'id',
            'creation_datetime_utc',
            'modified_datetime_utc',
            'has_been_modified',
            'deleted',
            'author_id',
            'token',
        )
        req = {}
        for col in cls.__table__.c:
            if not col.name in _ignore:
                #print( cls.__table__.c[col.name].__dict__ )
                req[col.name] = dict()
                for key in cls.__table__.c[col.name].__dict__:
                    #print( "    ", key, " = ", cls.__table__.c[col.name].__dict__[key], type(cls.__table__.c[col.name].type) )
                    #print( "    ", key, " = ", cls.__table__.c[col.name].__dict__[key] )
                    _type = None
                    if isinstance(cls.__table__.c[col.name].type, UUIDType):
                        _type = 'uuid'
                    elif isinstance(cls.__table__.c[col.name].type, DateTime):
                        _type = 'datetime_utc'
                    elif isinstance(cls.__table__.c[col.name].type, UnicodeText):
                        _type = 'unicode'
                    elif isinstance(cls.__table__.c[col.name].type, Integer):
                        _type = 'integer'
                    elif isinstance(cls.__table__.c[col.name].type, Float):
                        _type = 'float'
                    _required = True
                    if cls.__table__.c[col.name].__dict__['nullable']:
                        _required = False
                    req[col.name].update(
                        type = _type,
                        required = _required,
                    )
                #print("")
        return req

    def to_dict(self):
        _ignore = (
            '_sa_instance_state',
            'deleted',
            'has_been_modified',
            'pass_hash',
            'pass_salt',
            'token',
            'token_expire_datetime_utc',
            'must_change_password',
            'registration_token',
            'has_completed_registration',
        )
        resp = dict(
            id=str(self.id),
            creation_datetime_utc=str(self.creation_datetime_utc),
            modified_datetime_utc=str(self.modified_datetime_utc),
            #has_been_modified=self.has_been_modified,
            #deleted=self.deleted,
        )
        keys = self.__dict__
        for key in keys:
            if not key in _ignore:
                if key[-3:] == '_id' or key == 'id':
                    if keys[key] == None:
                        resp[key] = None
                    else:
                        resp[key] = str(keys[key])
                elif key[-13:] == '_datetime_utc':
                    if keys[key] is None:
                        resp[key] = None
                    else:
                        resp[key] = str(keys[key]).split('.')[0]
                elif key[0:2] != '__' and key[-2:] != '__':
                    resp[key] = keys[key]
                else:
                    pass
        return resp

class GetByMixin():

    @classmethod
    def get_by(cls, dbsession, params, start=0, count=25):
        _things = dbsession.query(
            cls,
        ).order_by(
            desc(cls.creation_datetime_utc),
        )
        for param in params:
            _val = params[param]
            if params[param] is not None and len(params[param]) >= 2:
                if params[param][0] is '>':
                    #print("GREATER THAN OR EQUAL")
                    _val = params[param][1:]
                    _things = _things.filter(
                        cls.__dict__[param] >= _val,
                    )
                elif params[param][0] is '<':
                    #print("LESS THAN OR EQUAL")
                    _val = params[param][1:]
                    _things = _things.filter(
                        cls.__dict__[param] <= _val,
                    )
                elif params[param][0] is '!':
                    #print("NOT EQUAL")
                    _val = params[param][1:]
                    _things = _things.filter(
                        cls.__dict__[param] != _val,
                    )
                else:
                    #print("EQUAL (inside)")
                    _things = _things.filter(
                        cls.__dict__[param] == _val,
                    )
            else:
                print("EQUAL (outside)")
                _things = _things.filter(
                    cls.__dict__[param] == _val,
                )
        _things = _things.slice(start, start+count).all()
        return _things

#
# scraper runs records each time the scraper runs
#
class ScraperRuns(Base, CreationMixin, GetByMixin):

    __tablename__ = 'scraper_runs'
    __single__ = 'Scraper Run'
    xml = Column(UnicodeText, nullable=False)

    def to_dict(self, with_auth=False):
        resp = super(ScraperRuns, self).to_dict()
        resp.update(
        )
        return resp

#
# these are the action items that come from the rss feed
#
class Dispatches(Base, CreationMixin, GetByMixin):

    __tablename__ = 'dispatches'
    __single__ = 'Dispatch'
    #raw_xml = Column(UnicodeText, nullable=False)
    call_type_id = Column(ForeignKey('call_types.id'), nullable=False)
    address_id = Column(ForeignKey('addresses.id'), nullable=False)
    publish_datetime_utc = Column(DateTime, nullable=False)
    current_status = Column(UnicodeText, nullable=False)
    dispatch_unique = Column(UnicodeText, nullable=False)
    agency_id = Column(ForeignKey('agencies.id'), nullable=False)
    pub_lat = Column(Float, nullable=True)
    pub_lng = Column(Float, nullable=True)

    # datetime when each status is seen
    waiting_datetime_utc = Column(DateTime, nullable=True)
    dispatched_datetime_utc = Column(DateTime, nullable=True)
    enroute_datetime_utc = Column(DateTime, nullable=True)
    onscene_datetime_utc = Column(DateTime, nullable=True)
    closed_datetime_utc = Column(DateTime, nullable=True)

    #incident_id = Column(ForeignKey('incidents.id'), nullable=False)

    call_type = relationship('CallTypes', primaryjoin='Dispatches.call_type_id == CallTypes.id')
    address = relationship('Addresses', primaryjoin='Dispatches.address_id == Addresses.id')
    agency = relationship('Agencies', primaryjoin='Dispatches.agency_id == Agencies.id')

    def to_dict(self, with_auth=False):
        resp = super(Dispatches, self).to_dict()
        resp.update(
            call_type=self.call_type.to_dict() if self.call_type != None else None,
            address=self.address.to_dict() if self.address != None else None,
            agency=self.agency.to_dict() if self.agency != None else None,
        )
        return resp

#
# unique call types based on text seen from the rss feed
#
class CallTypes(Base, CreationMixin, GetByMixin):

    __tablename__ = 'call_types'
    __single__ = 'Call Type'
    title = Column(UnicodeText, nullable=False)

    def to_dict(self, with_auth=False):
        resp = super(CallTypes, self).to_dict()
        resp.update(
        )
        return resp

#
# addresses seen in dispatches
#
class Addresses(Base, CreationMixin, GetByMixin):

    __tablename__ = 'addresses'
    __single__ = 'Address'
    raw_address = Column(UnicodeText, nullable=False)
    pub_lat = Column(Float, nullable=True)
    pub_lng = Column(Float, nullable=True)

    geocoded = Column(Integer, nullable=False) # 0 - false, 1 - true
    raw_json = Column(UnicodeText, nullable=True)
    street = Column(UnicodeText, nullable=True)
    neighborhood = Column(UnicodeText, nullable=True)
    city = Column(UnicodeText, nullable=True)
    county = Column(UnicodeText, nullable=True)
    state = Column(UnicodeText, nullable=True)
    zipcode = Column(UnicodeText, nullable=True)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)

    def to_dict(self, with_auth=False):
        resp = super(Addresses, self).to_dict()
        if not with_auth:
            del resp['raw_json']
        return resp

#
# list of responding agencies
#
class Agencies(Base, CreationMixin, GetByMixin):

    __tablename__ = 'agencies'
    __single__ = 'Agency'
    short_name = Column(UnicodeText, nullable=False)
    full_name = Column(UnicodeText, nullable=False)
    agency_type = Column(UnicodeText, nullable=False) # Fire, Ems, Police, B_countyfile, C_traffic 
    description = Column(UnicodeText, nullable=False)
    website_url = Column(UnicodeText, nullable=False)

    def to_dict(self, with_auth=False):
        resp = super(Agencies, self).to_dict()
        resp.update(
        )
        return resp

#
# daily stats for agencies
#
class DailyAgencyStats(Base, CreationMixin, GetByMixin):

    __tablename__ = 'daily_agency_stats'
    __single__ = 'Daily Agency Stat'
    one_based_day_index = Column(Integer, nullable=False)
    agency_id = Column(ForeignKey('agencies.id'), nullable=False)
    dispatch_count = Column(Integer, nullable=False)
    average_dispatched_seconds = Column(Integer, nullable=False)
    average_waiting_seconds = Column(Integer, nullable=False)
    average_enroute_seconds = Column(Integer, nullable=False)
    average_onscene_seconds = Column(Integer, nullable=False)
    average_call_length_seconds = Column(Integer, nullable=False)
    average_dispatched_to_onscene_seconds = Column(Integer, nullable=False)

    agency = relationship('Agencies', primaryjoin='DailyAgencyStats.agency_id == Agencies.id')

    def to_dict(self, with_auth=False):
        resp = super(DailyAgencyStats, self).to_dict()
        resp.update(
            agency=self.agency.to_dict() if self.agency != None else None,
        )
        return resp

#
# monthly stats for agencies
#
class MonthlyAgencyStats(Base, CreationMixin, GetByMixin):

    __tablename__ = 'monthly_agency_stats'
    __single__ = 'Daily Agency Stat'
    one_based_month_index = Column(Integer, nullable=False)
    agency_id = Column(ForeignKey('agencies.id'), nullable=False)
    dispatch_count = Column(Integer, nullable=False)
    average_dispatched_seconds = Column(Integer, nullable=False)
    average_waiting_seconds = Column(Integer, nullable=False)
    average_enroute_seconds = Column(Integer, nullable=False)
    average_onscene_seconds = Column(Integer, nullable=False)
    average_call_length_seconds = Column(Integer, nullable=False)
    average_dispatched_to_onscene_seconds = Column(Integer, nullable=False)

    agency = relationship('Agencies', primaryjoin='MonthlyAgencyStats.agency_id == Agencies.id')

    def to_dict(self, with_auth=False):
        resp = super(MonthlyAgencyStats, self).to_dict()
        resp.update(
            agency=self.agency.to_dict() if self.agency != None else None,
        )
        return resp

#
# these are collated dispatches that represent a single incident
#
class Incidents(Base, CreationMixin, GetByMixin):

    __tablename__ = 'incidents'
    __single__ = 'Incidents'

    call_type_id = Column(ForeignKey('call_types.id'), nullable=False)
    #incident_id = Column(UnicodeText, nullable=False)
    published_datetime_utc = Column(DateTime, nullable=False)

    closed = Column(Integer, nullable=False)

    def to_dict(self, with_auth=False):
        resp = super(Incidents, self).to_dict()
        resp.update(
        )
        return resp

#
# system settings
#
class Settings(Base, CreationMixin, GetByMixin):

    __tablename__ = 'settings'
    __single__ = 'Setting'
    permission_level = Column(Integer, nullable=False)
    name = Column(UnicodeText, nullable=False)
    value = Column(UnicodeText, nullable=False)
    value_type = Column(UnicodeText, nullable=False)

    def to_dict(self, with_auth=False):
        resp = super(Groups, self).to_dict()
        resp.update(
        )
        return resp