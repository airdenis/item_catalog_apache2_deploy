from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
from passlib.apps import custom_app_context as pwd_context
import random
import string
from itsdangerous import \
    (
        TimedJSONWebSignatureSerializer as
        Serializer, BadSignature, SignatureExpired
)
from flask import Flask
import psycopg2


Base = declarative_base()


class Category(Base):
    __tablename__ = 'category'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    item = relationship('Item', cascade='all, delete-orphan')

    @property
    def serialize(self):
        return{
                'id': self.id,
                'name': self.name,
}

def connect():
	return psycopg2.connect("dbname=itemcatalog user=itemcatalog password=test host=localhost")

engine = create_engine('postgresql://', creator=connect)
Base.metadata.create_all(engine)

app = Flask(__name__)

@app.route("/")
def hello():
    return 'test'
if __name__ == "__main__":
    app.run()
