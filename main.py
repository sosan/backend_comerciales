# -*- coding:utf-8 -*-
"""
APLICACION BACKEND COMERCIALES

"""

import os

# configuracion de puertos, path, etc...
import settings

from datetime import datetime

from flask import Flask, jsonify
from flask import render_template
from flask import redirect
from flask import url_for
from flask import session
from flask import request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from flask_bootstrap import Bootstrap
from werkzeug.utils import secure_filename
from flask import send_from_directory

from ModuloMongodb.ManagerMongodb import managermongo
# from ModuloLogica.ManagerLogica import ManagerLogica
from ModuloLogica.ManagerLogicaUsuarios import ManagerLogicaUsuarios
from ModuloLogica.ManagerLogicaComerciales import ManagerLogicaComerciales
from ModuloHelper.ManagerHelper import Errores
from ModuloWeb.ManagerWeb import ManagerWeb
from flask_socketio import SocketIO, emit

import sys

# instanciaciones e inicializaciones
app = Flask(__name__)

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# instanciacion de variables
managerweb = ManagerWeb()
socketio = SocketIO(app)
bootstrap = Bootstrap(app)
errores = Errores()
# managerlogica = ManagerLogica()
managerlogica_usuarios = ManagerLogicaUsuarios()
managerlogica_comerciales = ManagerLogicaComerciales()

# configuracion
app.secret_key = "holaa"
# CARPETAS_SUBIDAS obtenie una ruta absoluta desde "static/images/archivos_subidos"
CARPETA_SUBIDAS = os.path.abspath("static/images/archivos_subidos")
# mostramos la ruta absolta, pos si hay algun error
# TODO: implementar un logerror
print("carpeta subida archivos:" + CARPETA_SUBIDAS)

# configuracion de APP.CONFIG
app.config["CARPETA_SUBIDAS"] = CARPETA_SUBIDAS

# establecemos un limite 16 megas por archivo subido
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024


@app.route("/logout", methods=["GET"])
def logout_admin():
    session.clear()
    return redirect(url_for("comerciales_login"))


########################################
# BACKEND COMERCIALES
########################################

# TODO: controlarlo mejor
# @limiter.limit("1/second")
@app.route("/comerciales", methods=["GET"])
def comerciales_login():
    resultado_ok = comprobar_existencia_datos_session()
    if resultado_ok == True:
        # TODO: para no saturar la base de datos podriamos consultar con una base de datos mongo
        ok = managerlogica_comerciales.comprobar_existencia_comercial(session["usuario"], session["password"])

        # en caso de que no exista borramos las variables de sesion.
        # TODO: ...
        # ..controlar mejor el acceso, si no coincide con las ultimas ips,
        # reconocimiento de usuariosa traves de escritura..
        if ok == False:
            session.clear()
            return redirect(url_for("comerciales_login"))
        else:
            return redirect(url_for("menu_dashboard_comerciales"))

    # renderizamos el login_comerciales.html
    return render_template("login_comerciales.html")


# TODO: controlarlo mejor
# @limiter.limit("1/second")
@app.route("/comerciales", methods=["POST"])
def recibir_comerciales_login():
    if "usuario" and "password" in request.form:
        # deberiamos hacer esta comprobacion con un base de datos mucho mas rapida que mysql
        # por ejemplo: mongodb o redis.
        # en este caso para no complicarlo demasiado hacemos la comprobacion contra mysql
        ok, datos = managerlogica_comerciales.comprobar_existencia_comercial(usuario=request.form["usuario"],
                                                                             password=request.form["password"])
        # nos han devuelto: ok => si no ha habido algun erro y el nombre del usuario
        if ok == True:
            # el usuario y password los guardamos en una sesion para consultarlo
            # mas adelante y en proximas conexiones que haga el usuario.
            # ademas tambien guardamos el nombre de usuario y asi nos ahorramos
            # tener que volver a consultar a la base de datos
            session["usuario"] = request.form["usuario"]
            session["password"] = request.form["password"]
            session["nombre"] = datos["nombre"]
            session["imagen_perfil"] = datos["imagen_perfil"]
            # redirigimos al menu de administradores para que haga un render del html
            # podriamos hacer un render desde aqui
            # pero en caso de que el usuario actulice el navegador, saltaria un error
            return redirect(url_for("menu_dashboard_comerciales"))
        else:
            # TODO: faltaria controlar los errores de login
            # con base de datos, recogiendo la ip, etc...
            # tambien controlamos redirigirlo a la pagina principal, etc...
            return redirect(url_for("comerciales_login"))

    # directamente si nos hacen una peticion donde no haya un usuaro y password,
    # redigimos a "comerciales_login"
    # actualmente controlamos el limite de peticiones rate-limiter de flask, pero podriamos
    # controlar mucho mejor el tiempo de peticiones, ips, ataques, etc...
    # TODO: mejorar el control de peticiones
    return redirect(url_for("comerciales_login"))


@app.route("/profile_comercial", methods=["GET"])
def menu_dashboard_comerciales():
    resultado_ok = comprobar_existencia_datos_session()
    if resultado_ok == False:
        return redirect(url_for("comerciales_login"))

    if "usuario" and "password" in session:
        # comprobar el usuario y password en la session
        # TODO: para no saturar la base de datos podriamos consultar con una base de datos mongo
        ok = managerlogica_comerciales.comprobar_existencia_comercial(session["usuario"], session["password"])
        if ok == False:
            session.clear()
            return redirect(url_for("comerciales_login"))

        # ok = managermongo.comprobar_existencia_usuario(session["usuario"], session["password"])
        # if ok == True:

        listado = managermongo.get_sin_mediciones()
        if len(listado) > 0:
            fechadelta = datetime.utcnow()
            return render_template("menu_admin.html", datos=listado, fechaahora=fechadelta,
                                   totalelementos=len(listado))
        else:
            return render_template("menu_admin.html", datos=None)

    return redirect(url_for("comerciales_login"))


@app.route("/profile_comercial", methods=["POST"])
def menu_admin_post():
    return redirect(url_for("menu_dashboard_comerciales"))

@app.route("/alta_vivienda", methods=["GET"])
def alta_piso():
    if "usuario" not in session or "password" not in session:
        return redirect(url_for("comerciales_login"))
    else:
        posibleexistencia = managerlogica_comerciales.comprobar_solo_usuario(session["usuario"], session["password"])
        if posibleexistencia == False:
            return redirect(url_for("comerciales_login"))

    if "anterior_calle" in session:
        anterior_calle = session.pop("anterior_calle")
        anterior_numero = session.pop("anterior_numero")

        outputhtml = managerlogica_comerciales.generarmensajeerror(session["mensajeerror"], anterior_calle,
                                                                   anterior_numero)
        errores = session.pop("mensajeerror")

        return jsonify({"data": outputhtml, "errores": errores})

    if "calle" and "numero" and "cp" and "habitaciones" and "localidad" and "numerobanos" \
            and "tipocasa" and "dueno" and "totalmetros" \
            in session:
        variables = managerlogica_comerciales.mostrarvivienda()
        return render_template("alta_piso_admin.html", **variables)

    if "mensajeerror" in session:
        session.pop("mensajeerror")

    return render_template("alta_piso_admin.html")


@socketio.on('obtenercalle')
def obtenercalle(latitude, longitude):
    print("lat {0} long; {1} tipo:{2}".format(latitude, longitude, type(longitude)))
    calle, numero, cp, localidad = managerweb.getstreet(latitude, longitude)
    emit("r_obtenercalle",
         {
             "calle": calle,
             "numero": numero,
             "cp": cp,
             "localidad": localidad
         })


@app.route("/profile/alta", methods=["POST"])
def recibir_alta_piso():
    if "usuario" not in session or "password" not in session:
        return redirect(url_for("comerciales_login"))

    if "calle" and "cp" and "habitaciones" and "localidad" \
            and "banos" and "tipocasa" and "numero" and "dueno" and "telefonodueno" in request.form:

        # comprobacion de si ya existe el piso en la db
        posible_insercion = managerlogica_comerciales.comprobarexisteinmueble(request.form["calle"],
                                                                              request.form["numero"])
        if posible_insercion == True:
            managerlogica_comerciales.alta_vivienda(request.form, app.config["MAX_CONTENT_LENGTH"],
                                                    app.config["CARPETA_SUBIDAS"])
        else:
            # ya existe
            managerlogica_comerciales.procesar_formulario_noposibleinsercion(request.form)

    return redirect(url_for("alta_piso"))


@app.route("/profile/ver", methods=["GET"])
def ver_piso():
    return render_template("ver_piso.html")


@app.route("/profile/ver", methods=["GET"])
def buscar_piso():
    return render_template("buscar_piso.html")


@app.route("/profile/item", methods=["get"])
def ver_piso_para_modificar_get():
    if "usuario" not in session or "password" not in session:
        return redirect(url_for("comerciales_login"))
    else:
        ok = managerlogica_comerciales.comprobar_solo_usuario(session["usuario"], session["password"])
        # ok = managermongo.comprobar_existencia_usuario(session["usuario"], session["password"])
        if ok == False:
            return redirect(url_for("comerciales_login"))

    if "mensajeerror" in session:
        outputhtml = managerlogica_comerciales.generarmensajeerror(session["mensajeerror"])
        session.pop("mensajeerror")

        return jsonify({"data": outputhtml})

    if "datos_vivienda" in session:
        datos_vivienda = session.pop("datos_vivienda")
        return render_template("modificar_piso_admin.html", datos_vivienda=datos_vivienda)

    return redirect(url_for("menu_dashboard_comerciales"))


@app.route("/profile/item", methods=["post"])
def ver_piso_para_modificar():
    if "usuario" not in session or "password" not in session:
        return redirect(url_for("comerciales_login"))
    else:
        ok = managerlogica_comerciales.comprobar_solo_usuario(session["usuario"], session["password"])
        # ok = managermongo.comprobar_existencia_usuario(session["usuario"], session["password"])
        if ok == False:
            return redirect(url_for("comerciales_login"))

    if "iditem" in request.form:
        datos = managermongo.get_vivienda_porid(request.form["iditem"])
        session["datos_vivienda"] = datos

    return redirect(url_for("ver_piso_para_modificar_get"))


# quizas hacer con websockets?
@app.route("/profile/item_modificado", methods=["post"])
def modificar_vivienda():
    if "usuario" not in session or "password" not in session:
        return redirect(url_for("comerciales_login"))
    else:
        ok = managerlogica_comerciales.comprobar_solo_usuario(session["usuario"], session["password"])
        # ok = managermongo.comprobar_existencia_usuario(session["usuario"], session["password"])
        if ok == False:
            return redirect(url_for("comerciales_login"))

    if "iditem" and "calle" and "cp" and "habitaciones" and "localidad" \
            and "banos" and "tipocasa" and "numero" and "dueno" and "telefonodueno" in request.form:

        # comprobacion de si el iditem existe en la db
        ok, datosmongo = managerlogica_comerciales.comprobarexiste_iditem(request.form["iditem"])
        if ok == errores.existe:
            formulario = request.form.to_dict()
            actualizado = managerlogica_comerciales.actualizar_vivienda(formulario, app.config["CARPETA_SUBIDAS"],
                                                                        app.config["MAX_CONTENT_LENGTH"],
                                                                        datosmongo["nombrefile"])
            session["mensajeerror"] = actualizado
        else:
            # alerta
            # todo: mostrar mensaje de error
            session["mensajeerror"] = ok
        return redirect(url_for("ver_piso_para_modificar_get"))

    return redirect(url_for("menu_dashboard_comerciales"))


@app.route("/profile/tomar_medidas_pago", methods=["GET"])
def tomar_medidas_pago():
    return render_template("tomar_medidas_pago.html")


@app.route("/profile/tomar_medidas", methods=["GET"])
def tomar_medidas_light():
    return render_template("tomar_medidas_light.html")


@app.route("/profile/recibir_menu_medicion", methods=["POST"])
def recibir_menu_medicion():
    if "sin" in request.form:
        listado = managermongo.get_sin_mediciones()
        session["listado_viviendas"] = listado
        return redirect(url_for("menu_dashboard_comerciales"))
    elif "con" in request.form:
        listado = managermongo.get_con_mediciones()
        session["listado_viviendas"] = listado
        return redirect(url_for("menu_dashboard_comerciales"))

    return render_template("listado_sin_mediciones.html")


##################################

def comprobar_existencia_datos_session():
    # comprobar el usuario y password en la session
    if not ("usuario" in session) or not ("password" in session):
        return False

    # comprobamos que no esten vacios
    if not session["usuario"] or not session["password"]:
        return False

    return True


@app.route("/")
def home():
    return render_template("index.html")


if __name__ == "__main__":
    settings.readconfig()
    # env_port = int(os.environ.get("PORT", 5000))
    # env_debug = os.environ.get("FLASK_DEBUG", 1)

    env_port = int(os.getenv("PORT", 5000))
    env_debug = os.getenv("FLASK_DEBUG", True)
    # produccion = os.getenv("FLASK_ENV", "production")
    # app.config("ENV", produccion)

    socketio.run(host="0.0.0.0", port=env_port, app=app, debug=env_debug)
