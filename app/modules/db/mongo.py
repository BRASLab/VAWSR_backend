from mongoengine import connect, StringField, IntField, EmailField, BooleanField, BinaryField, Document
connect('vawsr')

class Users(Document):
    name = StringField(required=True, max_length=200)
    fbid = IntField(require=True, primary_key=True, unique=True)
    email = EmailField(required=True) 
    token = StringField(required=True)
    signed = StringField(required=True)
    hasivector = BooleanField(default=False)
    processing = BooleanField(default=False)
    clf = BinaryField()
    ivectors = BinaryField()
