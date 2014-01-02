from google.appengine.ext import db
from oauth2client.appengine import CredentialsProperty


class Utilisateur(db.Model):
    userID = db.StringProperty(required=True)
    calendarID = db.StringProperty(required=True)
    userEmail = db.StringProperty(required=True)
    credential = CredentialsProperty()


class Chaine(db.Model):
    channelID = db.StringProperty(required=True)
    nbVideos = db.IntegerProperty(required=True)


class UtilisateurEtChaine(db.Model):
    userID = db.StringProperty(required=True)
    channelID = db.StringProperty(required=True)


class OwnChannel(db.Model):
    channelID = db.StringProperty(required=True)
    userID = db.StringProperty(required=True)
    nbreLikes = db.IntegerProperty()
    nbreSubscribers = db.IntegerProperty()
    nbreHiddenSubscribers = db.IntegerProperty()
    nbreFavorites = db.IntegerProperty()
    nbreViews = db.IntegerProperty()
