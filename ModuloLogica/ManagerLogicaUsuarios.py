import base64
import os
import sys
from datetime import datetime
from werkzeug.utils import secure_filename
import math
from flask import session

from ModuloMongodb.ManagerMongodb import managermongo
from ModuloHelper.ManagerHelper import Errores
from ModuloRedis.ManagerRedis import ManagerRedis
from ModuloConstantes.Constantes import *
from ModuloSQL.ManagersqlAdministradores import Managersql


class ManagerLogicaUsuarios:
    def __init__(self):
        self.errores = Errores()

