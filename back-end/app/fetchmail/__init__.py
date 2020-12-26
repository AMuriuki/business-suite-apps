#-*- coding:utf-8 -*-
# Part of Teleios. See LICENSE file for full copyright and licensing details.

from flask import Blueprint

bp = Blueprint('fetchmail', __name__)

from app.fetchmail import routes
 
