#-*- coding:utf-8 -*-
# Part of Teleios. See LICENSE file for full copyright and licensing details.

from flask import Blueprint

bp = Blueprint('mail', __name__)

from app.mail import routes
