# -*- coding: utf-8 -*-
import os
import json
import re
import io
import base64
from datetime import datetime, timedelta
import zipfile

from flask import Flask
from flask import flash
from flask import jsonify
from flask import make_response
from flask import request
from flask import send_file
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String
from flask_migrate import Migrate
from ecdsa import SigningKey, VerifyingKey, NIST256p

from TemporaryExposureKey.TemporaryExposureKey_pb2 import TemporaryExposureKeyExport, TEKSignatureList, SignatureInfo, TemporaryExposureKey, TEKSignature


__version__ = '1.20200903'

__tek_key_name = "export.bin"
__tek_sig_name = "export.sig"

# Exceptions
class Error(Exception):
      pass
class AugumentError(Error):
  def __init__(self, message):
        self.message = message
class ParamError(Error):
  def __init__(self, message):
        self.message = message
class DataError(Error):
  def __init__(self, message):
        self.message = message
class SignatureKeyError(Error):
      def __init__(self, message):
        self.message = message

# Service Settings
LISTEN_PORT = os.getenv('FLASK_RUN_PORT', '31310')
# SQLite DB Settings
DB_TYPE = 'sqlite'
DB_NAME = 'COCOAMOCK.db'
db_connect_URL = 'sqlite:///{}'.format(os.path.join(os.path.dirname(os.path.abspath(__name__)), DB_NAME))
# Set Flask SecretKey
SECRET_KEY = os.getenv('FLASK_SECRET_KEY', os.urandom(40))
# Base URL for list.json and zip. Default is localhost.
BASE_URL = os.getenv('COCOAMOCK_BASE_URL', 'http://{:}:{:}'.format('localhost', LISTEN_PORT))


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = db_connect_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = SECRET_KEY
app.config['DEBUG'] = True
db = SQLAlchemy(app)
db.init_app(app)
Migrate(app, db)

# Load signature key
signature_key = None
if os.getenv("COCOAMOCK_SIGNATURE_KEY_FILENAME", None) is None:
    raise SignatureKeyError("'COCOAMOCK_SIGNATURE_KEY_FILENAME' env is not setted.")
try:
    with open(os.getenv("COCOAMOCK_SIGNATURE_KEY_FILENAME", None)) as f:
        signature_key = SigningKey.from_pem(f.read())
except Exception as e:
    raise e

# TEK DB Model
class TEKs(db.Model):
    __tablename__ = "teks"
    id = db.Column(db.Integer, primary_key=True)
    epoch = db.Column(Integer)
    key_data = db.Column(String(100))
    rolling_start_number = db.Column(Integer)
    rolling_period = db.Column(Integer)
    transmission_risk = db.Column(Integer)
    region = db.Column(String(10))
    created = db.Column(db.DateTime, index=True, default=datetime.now())


#
# API Registration
#
@app.route('/version', methods=['GET'])
def version():
    return make_response(jsonify({"version":__version__}), 200)


@app.route('/diagnosis', methods=['PUT', 'POST'])
def diagnosis():
    positive_data = request.json
    print(positive_data)
    for item in positive_data["keys"]:
        tek = TEKs(epoch=int(item["rollingStartNumber"]) * 600, key_data=item["keyData"], rolling_start_number=int(item["rollingStartNumber"]),
                    rolling_period=int(item["rollingPeriod"]), transmission_risk=int(item["transmissionRisk"]), region=positive_data["regions"][0])
        db.session.add(tek)
        db.session.commit()
        db.session.close()
    return make_response(jsonify({"message":"Accepted."}), 200)


@app.route('/list.json', methods=['GET'])
def list_json():
    zip_list = []
    for tek in TEKs.query.order_by(TEKs.epoch).all():
        zip_entry = {}
        zip_entry["region"] = tek.region
        zip_entry["url"] = "{:}{:}{:}.zip".format(BASE_URL, "/", str(tek.id))
        zip_entry["created"] = round(tek.created.timestamp() * 1000)
        zip_list.append(zip_entry)
    return make_response(jsonify(zip_list), 200)


@app.route('/<id>.zip', methods=['GET'])
def get_zip(id):
    tek = TEKs.query.filter_by(id=id).first()
    if tek is None:
        return make_response("Not Found", 404)
    
    tek_bin = TemporaryExposureKeyExport()
    tek_bin.start_timestamp = int(datetime.strptime(datetime.fromtimestamp(int(tek.created.timestamp())).astimezone().strftime("%Y-%m-%d 00:00:00%z"), "%Y-%m-%d %H:%M:%S%z").timestamp())
    tek_bin.end_timestamp = int(datetime.strptime((datetime.fromtimestamp(int(tek.created.timestamp())) + timedelta(days=1)).astimezone().strftime("%Y-%m-%d 00:00:00%z"), "%Y-%m-%d %H:%M:%S%z").timestamp())
    tek_bin.region = tek.region
    tek_bin.batch_num = 1
    tek_bin.batch_size = 1
    signature_infos = SignatureInfo()
    signature_infos.verification_key_version = "v1"
    signature_infos.verification_key_id = "440"
    signature_infos.signature_algorithm = "1.2.840.10045.4.3.2"
    tek_bin.signature_infos.append(signature_infos)
    temporary_exposure_key = TemporaryExposureKey()
    temporary_exposure_key.key_data = base64.b64decode(tek.key_data)
    temporary_exposure_key.transmission_risk_level = tek.transmission_risk
    temporary_exposure_key.rolling_start_interval_number = tek.rolling_start_number
    temporary_exposure_key.rolling_period = tek.rolling_period
    tek_bin.keys.append(temporary_exposure_key)
    
    sig_bin = TEKSignatureList()
    tek_signature = TEKSignature()
    tek_signature.signature_info.verification_key_version = "v1"
    tek_signature.signature_info.verification_key_id = "440"
    tek_signature.signature_info.signature_algorithm = "1.2.840.10045.4.3.2"
    tek_signature.signature = signature_key.sign(tek_bin.SerializeToString())
    sig_bin.signatures.append(tek_signature)

    zipdata = io.BytesIO()
    with zipfile.ZipFile(zipdata, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr(__tek_key_name, tek_bin.SerializeToString())
        z.writestr(__tek_sig_name, sig_bin.SerializeToString())
    zipdata.seek(0)

    return send_file(zipdata, as_attachment=True, attachment_filename="{:}.zip".format(id), mimetype="application/zip")


if __name__ == '__main__':
    app.run(port=int(LISTEN_PORT, 10), debug=os.getenv("FLASK_ENV", "") == "development")

