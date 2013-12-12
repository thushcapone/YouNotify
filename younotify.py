import jinja2
import os
import urllib
import webapp2
import httplib2
import pytz

from oauth2client.client import Credentials
from oauth2client.appengine import  CredentialsProperty
from oauth2client.appengine import CredentialsModel
from google.appengine.api import users
from google.appengine.ext import db
from oauth2client.appengine import StorageByKeyName
from apiclient.discovery import build
from oauth2client import appengine
from oauth2client import client
from google.appengine.api import memcache
from datetime import datetime
from datetime import timedelta
from models import Utilisateur
from models import UtilisateurEtChaine
from models import Chaine

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

# CLIENT_SECRETS, name of a file containing the OAuth 2.0 information for this
# application, including client_id and client_secret, which are found
# on the API Access tab on the Google APIs
# Console <http://code.google.com/apis/console>
CLIENT_SECRETS = os.path.join(os.path.dirname(__file__), 'client_secrets.json')

# Helpful message to display in the browser if the CLIENT_SECRETS file
# is missing.
MISSING_CLIENT_SECRETS_MESSAGE = """
<h1>Warning: Please configure OAuth 2.0</h1>
<p>
To make this sample run you will need to populate the client_secrets.json file
found at:
</p>
<p>
<code>%s</code>.
</p>
<p>with information found on the <a
href="https://code.google.com/apis/console">APIs Console</a>.
</p>
""" % CLIENT_SECRETS

http = httplib2.Http(memcache)

decorator = appengine.oauth2decorator_from_clientsecrets(
    CLIENT_SECRETS,
    scope=['https://www.googleapis.com/auth/youtube.readonly',
            'https://www.googleapis.com/auth/calendar'],
    message=MISSING_CLIENT_SECRETS_MESSAGE)



CALENDAR_API_VERSION = "v3"
CALENDAR_API_SERVICE_NAME = "calendar"
DEVELOPER_KEY = "AIzaSyA4MFLF5_V5wbu_NAM6DXZvZCsnEOk3TGE"
SERVICECALENDAR = build(serviceName=CALENDAR_API_SERVICE_NAME, version=CALENDAR_API_VERSION, developerKey=DEVELOPER_KEY)


class Register(webapp2.RequestHandler):

    @decorator.oauth_required
    def get(self):
        u = db.GqlQuery('SELECT * FROM Utilisateur where userID = :userID', userID = users.get_current_user().user_id())
        #ICI JE VEUX VERIFIER SI LE USER NEXISTE PAS DEJA DANS LA BDD ON LENREGISTRE MAIS YA UN BLEM AVEC LA VERIFICATION
        if u.get() is None: 
            userID = users.get_current_user().user_id()
            userEmail = users.get_current_user().email()
            calendar_serv = SERVICECALENDAR
            calendar = {
                'summary': 'youNotify',            
            }
            http = decorator.http()
            request = calendar_serv.calendars().insert(body=calendar).execute(http=http)
            calendarId = request['id']
            cred = decorator.get_credentials()
            utilisateur = Utilisateur(calendarID=calendarId, userID=userID, userEmail=userEmail, credential=cred)
            utilisateur.put()

        template_values = {}
        template = JINJA_ENVIRONMENT.get_template('templates/register.html')
        self.response.write(template.render(template_values))


class ComingSoon(webapp2.RequestHandler):

    def get(self):
        template_values = {}
        template = JINJA_ENVIRONMENT.get_template('templates/comingSoon/index.html')
        self.response.write(template.render(template_values))


class Index(webapp2.RequestHandler):

    def get(self):
        template_values = {}
        template = JINJA_ENVIRONMENT.get_template('templates/index.html')
        self.response.write(template.render(template_values))


# Set DEVELOPER_KEY to the "API key" value from the "Access" tab of the
# Google APIs Console http://code.google.com/apis/console#access
# Please ensure that you have enabled the YouTube Data API for your project.
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"
SERVICEYOUTUBE = build(serviceName=YOUTUBE_API_SERVICE_NAME, version=YOUTUBE_API_VERSION, developerKey=DEVELOPER_KEY)


class YoutubeHandler(webapp2.RequestHandler):

    @decorator.oauth_required
    def listSubscriptions(self):
        youtube = SERVICEYOUTUBE
        http = decorator.http()
        user_chaines = db.GqlQuery("SELECT * FROM UtilisateurEtChaine WHERE userID = :idU", idU=users.get_current_user().user_id())
        tab_abonnement = []
        for i in user_chaines:
            tab_abonnement.append(i.channelID)
        db.delete(user_chaines)
        u = db.GqlQuery("SELECT * FROM Utilisateur WHERE userID = :idU", idU=users.get_current_user().user_id())
        credentials = ''
        if u.get() is None:
            self.redirect("http://gcdc2013-younotify.appspot.com/register")
            return 0
        else:
            for i in u:
                credentials = i.credential
            http = httplib2.Http()
            http = credentials.authorize(http)            
            list_subscriptions_response = youtube.subscriptions().list(
                part="id,snippet",
                mine=True,
                maxResults=25
            ).execute(http=http)

            if not list_subscriptions_response["items"]:
                print "No subscriptions was found."

            subscriptions = []
            for result in list_subscriptions_response.get("items", []):
                if result['snippet']['resourceId']['channelId'] in tab_abonnement:
                    result['deja_abonne'] = True
                subscriptions.append(result)

            template_values = {
            'subscriptions': subscriptions
            }

            #self.response.headers['Content-type'] = 'text/plain' 
            template = JINJA_ENVIRONMENT.get_template('templates/channel.html')
            self.response.write(template.render(template_values))


    def get(self):

        self.listSubscriptions()


class TutorialHandler(webapp2.RequestHandler):

    def post(self):
        template_values = {}
        template = JINJA_ENVIRONMENT.get_template('templates/tutorial.html')
        self.response.write(template.render(template_values))


class Tutorial2Handler(webapp2.RequestHandler):

    def get(self):
        template_values = {}
        template = JINJA_ENVIRONMENT.get_template('templates/tutorial2.html')
        self.response.write(template.render(template_values))


class WhatHandler(webapp2.RequestHandler):

    def get(self):
        template_values = {}
        template = JINJA_ENVIRONMENT.get_template('templates/whatis.html')
        self.response.write(template.render(template_values))


class Register2Handler(webapp2.RequestHandler):

    @decorator.oauth_required
    def post(self):
        idChaines = self.request.get('chaines', allow_multiple=True)
        template_values = {
        'images': self.request.get('image[]', allow_multiple=True)
        }
        template = JINJA_ENVIRONMENT.get_template('templates/channel2.html')
        self.response.write(template.render(template_values))


class Register3Handler(webapp2.RequestHandler):

    @decorator.oauth_required
    def get(self):
        tab1, tab2, tab3 = [], [],[]
        req = db.GqlQuery("SELECT * FROM Utilisateur")
        for i in req:
            tab1.append(i)
        req = db.GqlQuery("SELECT * FROM Chaine")
        for i in req:
            tab2.append(i)
        req = db.GqlQuery("SELECT * FROM UtilisateurEtChaine")
        for i in req:
            tab3.append(i)        
        template_values = {
        'tab1': tab1,
        'tab2': tab2,
        'tab3': tab3
        }

        #self.response.headers['Content-type'] = 'text/plain' 
        template = JINJA_ENVIRONMENT.get_template('templates/channel3.html')
        self.response.write(template.render(template_values))


class ThanksHandler(webapp2.RequestHandler):

    @decorator.oauth_required
    def post(self):

        idChaines = self.request.get('chaines', allow_multiple=True)
        youtube = SERVICEYOUTUBE
        for idChaine in idChaines:
            c = db.GqlQuery('SELECT * FROM Chaine where channelID = :channelID', channelID = idChaine)
            if c.get() is None: 
                userID = users.get_current_user().user_id()
                http = decorator.http()
                search_response = youtube.channels().list(
                id=idChaine,
                part="id,snippet,statistics",
                ).execute(http=http)
                nbVideo  = 0
                for stat in search_response["items"]:
                    nbVideo = stat['statistics']['videoCount']
                chaine = Chaine(channelID=idChaine, nbVideos=int(nbVideo))
                chaine.put()
        
        c = db.GqlQuery('SELECT * FROM UtilisateurEtChaine where userID = :userID', userID = users.get_current_user().user_id())
        results = c.fetch(5)
        for result in results:
            result.delete()
        
        userID = users.get_current_user().user_id()
        for idChaine in idChaines:
            chaine2 = UtilisateurEtChaine(userID=userID,channelID=idChaine)
            chaine2.put()

        template_values = {
        'nom': users.get_current_user().nickname(),
        'chaines':idChaines
        }
        template = JINJA_ENVIRONMENT.get_template('templates/thanks.html')
        self.response.write(template.render(template_values))


class UpdateVideoHandler(webapp2.RequestHandler):

    @decorator.oauth_required
    def get(self):
        nbre_video = 0       
        youtube = SERVICEYOUTUBE
        http = decorator.http()        
        requete = db.GqlQuery("SELECT * FROM Chaine")
        liste = []
        cred = []
        idCal = []
        for chaine in requete:
            nbre_video = chaine.nbVideos
            new_videos = 0
            credentials = StorageByKeyName(CredentialsModel, users.get_current_user().user_id(), 'credentials').get()
            channelID = chaine.channelID
            channels_response = youtube.channels().list(
                part="id,snippet,statistics",
                id=channelID
                ).execute(http=http)
            i = 1
            for stat in channels_response["items"]:
                new_videos = stat['statistics']['videoCount']
                nomChannel = stat['snippet']['title']
            if int(nbre_video) != int(new_videos):
                chaine.nbVideos = int(new_videos)
                chaine.put()
                liste.append({'nbre_video':nbre_video, "nbVideos":new_videos})
                calendar_serv = SERVICECALENDAR
                #requete = db.GqlQuery("SELECT Utilisateur.userID, channelID , credentials  FROM UtilisateurEtChaine, Utilisateur WHERE channelID = :chaineID and Utilisateur.userID=UtilisateurEtChaine.userID", chaineID=channelID)
                for b in db.GqlQuery("SELECT * FROM UtilisateurEtChaine WHERE channelID = :channelID", channelID=channelID):
                    u = db.GqlQuery("SELECT * FROM Utilisateur WHERE userID = :userID", userID=b.userID)
                    for ligne in u:
                        cred.append(ligne.credential)
                        liste.append({'userID': ligne.userID, 'channelID': b.channelID})
                        http = httplib2.Http()
                        http = ligne.credential.authorize(http)
                        now = datetime.now(pytz.timezone('UTC'))
                        start = now + timedelta(minutes=i)
                        i = i + 1
                        end = now + timedelta(minutes=i)
                        calendar = {
                            'summary': 'A new video is posted by '+str(nomChannel),
                            'location': 'Youtube',
                            'start': {
                                'dateTime': str(start.isoformat())
                            },
                            'end': {
                                'dateTime': str(end.isoformat())
                            },
                            'reminders':{
                                'overrides':['sms', 'email', 'popup']
                            }
                        }
                        request = calendar_serv.events().insert(
                            calendarId=ligne.calendarID, 
                            body=calendar, 
                            sendNotifications=True
                            ).execute(http=http)

                        idCal.append(request['id'])

        template_values = {
            'liste': liste,
            'cred': cred,
            'events': idCal
        }
        template = JINJA_ENVIRONMENT.get_template('templates/update.html')
        self.response.write(template.render(template_values))


class DeleteToken(webapp2.RequestHandler):

    @decorator.oauth_aware
    def get(self):
        u = db.GqlQuery('SELECT * FROM UtilisateurEtChaine where userID =: userID ', userID=user.get_current_user().userID)
        db.delete(u)
        u = db.GqlQuery('SELECT * FROM Utilisateur where userID =: userID', userID=user.get_current_user().userID)
        db.delete(u)


application = webapp2.WSGIApplication([
    ('/', ComingSoon),
    ('/index.html', ComingSoon),
    ('/bbt', Index),
    ('/youtube', YoutubeHandler),
    ('/register', Register),
    ('/register2', YoutubeHandler),
    ('/channel2', Register2Handler),
    ('/thanks', ThanksHandler),
    ('/update', UpdateVideoHandler),
    ('/register3',Register3Handler),
    ('/tutorial',TutorialHandler),
    ('/tutorial2',Tutorial2Handler),
    ('/whatis.html', WhatHandler),
    ('/revoke', DeleteToken),
    (decorator.callback_path, decorator.callback_handler())
], debug=True)