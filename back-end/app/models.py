import base64
from datetime import datetime, timedelta
from hashlib import md5
import json
import os
from time import time
from flask import current_app, url_for
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import redis
import rq
from app import db, login
from app.search import add_to_index, remove_from_index, query_index


class BasemodelMixin(object):
    @classmethod
    def _mapped_func(self, func):
        """
        Apply function ```func``` on all records in ```self```, and
        return the result as a list of records (if ```func``` returns
        recordsets)
        """
        if self:
            vals = [func(rec) for rec in self]
            if isinstance(vals[0], BasemodelMixin):
                return vals[0].union(*vals)
            return vals
        else:
            vals = func(self)
            return vals if isinstance(vals, BasemodelMixin) else []

    @classmethod
    def mapped(self, func):
        """
        Apply function ```func``` on all records in ```self```, and return the 
        resutl as a list or a recordset (if ```func``` returns recordsets). In 
        the latter case, the order of the returned recordset is arbitrary.

        :param func: a function or a dot-separated sequence of field names
        :type func: callable or str
        :return: self if func is falsy, result of func applied to all ```self```
         records.
        :rtype: list of recordset

        .. code-block:: python3

            # returns a list of summing two fields for each record in the set
            records.mapped(lambda rL r.field1 + r.field2)

        The provided function can be a string to get field values:

        .. code-block:: python3

            # returns a list of names
            records.mapped('name')

            # returns a recordset of partners
            records.mapped('partner_id.bank_ids')

            # returns the union of all partners banks, with duplicates removed
            records.mapped('partner_id.bank_ids')
        """
        if not func:
            return self
        if isinstance(func, str):
            recs = self
            for name in func.split('.'):
                recs = recs._fields[name].mapped(recs)
            return recs
        else:
            return self._mapped_func(func)


class SearchableMixin(object):
    @classmethod
    def search(cls, expression, page, per_page):
        ids, total = query_index(cls.__tablename__, expression, page, per_page)
        if total == 0:
            return cls.query.filter_by(id=0), 0
        when = []
        for i in range(len(ids)):
            when.append((ids[i], i))
        return cls.query.filter(cls.id.in_(ids)).order_by(
            db.case(when, value=cls.id)), total

    @classmethod
    def before_commit(cls, session):
        session._changes = {
            'add': list(session.new),
            'update': list(session.dirty),
            'delete': list(session.deleted)
        }

    @classmethod
    def after_commit(cls, session):
        for obj in session._changes['add']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['update']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['delete']:
            if isinstance(obj, SearchableMixin):
                remove_from_index(obj.__tablename__, obj)
        session._changes = None

    @classmethod
    def reindex(cls):
        for obj in cls.query:
            add_to_index(cls.__tablename__, obj)


db.event.listen(db.session, 'before_commit', SearchableMixin.before_commit)
db.event.listen(db.session, 'after_commit', SearchableMixin.after_commit)


class PaginatedAPIMixin(object):
    @staticmethod
    def to_collection_dict(query, page, per_page, endpoint, **kwargs):
        resources = query.paginate(page, per_page, False)
        data = {
            'items': [item.to_dict() for item in resources.items],
            '_meta': {
                'page': page,
                'per_page': per_page,
                'total_pages': resources.pages,
                'total_items': resources.total
            },
            '_links': {
                'self': url_for(endpoint, page=page, per_page=per_page,
                                **kwargs),
                'next': url_for(endpoint, page=page + 1, per_page=per_page,
                                **kwargs) if resources.has_next else None,
                'prev': url_for(endpoint, page=page - 1, per_page=per_page,
                                **kwargs) if resources.has_prev else None
            }
        }
        return data
