import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = '208305ba3b742feccfa45eade7809918'
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:@localhost/kasir_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'app', 'static', 'product')
