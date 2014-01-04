from google.appengine.ext import db
from oauth2client.appengine import CredentialsProperty


class Utilisateur(db.Model):
    userID = db.StringProperty(required=True)
    calendarID = db.StringProperty(required=True)
    playlistID = db.StringProperty(required=True)
    userEmail = db.StringProperty(required=True)
    credential = CredentialsProperty()
    date_register = db.DateTimeProperty(auto_now=True)


class Chaine(db.Model):
    channelID = db.StringProperty(required=True)
    nbVideos = db.IntegerProperty(required=True)


class UtilisateurEtChaine(db.Model):
    userID = db.StringProperty(required=True)
    channelID = db.StringProperty(required=True)


class OwnChannel(db.Model):
    channelID = db.StringProperty(required=True)
    userID = db.StringProperty(required=True)
    nbreSubscribers = db.IntegerProperty()
    nbreComments = db.IntegerProperty()
    nbreViews = db.IntegerProperty()


class Interets(db.Model):
    interetID = db.StringProperty(required=True)
    interet = db.StringProperty(required=True)


class UtilisateurEtInteret(db.Model):
    userID = db.StringProperty(required=True)
    interetID = db.StringProperty(required=True)