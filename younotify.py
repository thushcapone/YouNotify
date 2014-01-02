import jinja2
import os
import webapp2
import httplib2
import pytz
from datetime import datetime
from datetime import timedelta


from google.appengine.api import users
from google.appengine.ext import db
from apiclient.discovery import build
from oauth2client import appengine
from google.appengine.api import memcache
from oauth2client.appengine import StorageByKeyName, CredentialsModel

from models import Utilisateur
from models import UtilisateurEtChaine
from models import Chaine
from models import OwnChannel



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

#decorator = appengine.oauth2decorator_from_clientsecrets(
#    CLIENT_SECRETS,
#    scope=['https://www.googleapis.com/auth/youtube.readonly',
#           'https://www.googleapis.com/auth/calendar'],
#    message=MISSING_CLIENT_SECRETS_MESSAGE
#)

decorator = appengine.OAuth2Decorator(
    client_id="873080943535-r530olahgmoggead5efgbekk7ecu1oro.apps.googleusercontent.com",
    client_secret="IurBjo_aR-1NzW7NHZw-1xms",
    scope=['https://www.googleapis.com/auth/youtube.readonly',
           'https://www.googleapis.com/auth/calendar'],
    message=MISSING_CLIENT_SECRETS_MESSAGE,
    access_type="offline",
    approval_prompt="force"
)
#decorator.flow.params.update({'access_type': 'offline'})



CALENDAR_API_VERSION = "v3"
CALENDAR_API_SERVICE_NAME = "calendar"
DEVELOPER_KEY = "AIzaSyA4MFLF5_V5wbu_NAM6DXZvZCsnEOk3TGE"
SERVICECALENDAR = build(serviceName=CALENDAR_API_SERVICE_NAME, version=CALENDAR_API_VERSION, developerKey=DEVELOPER_KEY)

YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"
SERVICEYOUTUBE = build(serviceName=YOUTUBE_API_SERVICE_NAME, version=YOUTUBE_API_VERSION, developerKey=DEVELOPER_KEY)


class Register(webapp2.RequestHandler):

    @decorator.oauth_required
    def get(self):
        u = db.GqlQuery('SELECT * FROM Utilisateur where userID = :userID', userID=users.get_current_user().user_id())
        if u.get() is None:
            userID = users.get_current_user().user_id()
            userEmail = users.get_current_user().email()
            calendar_serv = SERVICECALENDAR
            calendar = {
                'summary': 'youNotify',            
            }
            #decorator.flow.params.update({'approval_prompt': 'force'})
            if decorator.has_credentials():
                http = decorator.http()
                request = calendar_serv.calendars().insert(body=calendar).execute(http=http)
                calendarId = request['id']
                cred = decorator.get_credentials()
                utilisateur = Utilisateur(calendarID=calendarId, userID=userID, userEmail=userEmail, credential=cred)
                utilisateur.put()
            else:
                self.redirect(decorator.authorize_url())

        template_values = {}
        template = JINJA_ENVIRONMENT.get_template('templates/register.html')
        self.response.write(template.render(template_values))


class ComingSoon(webapp2.RequestHandler):

    def get(self):
        template_values = {}
        template = JINJA_ENVIRONMENT.get_template('templates/comingSoon/index.html')
        self.response.write(template.render(template_values))


class Index(webapp2.RequestHandler):

    @decorator.oauth_aware
    def get(self):
        template_values = {
            'user':users.get_current_user(),
            'has_credentials':  decorator.has_credentials()
        }
        template = JINJA_ENVIRONMENT.get_template('templates/index.html')
        self.response.write(template.render(template_values))


class YoutubeHandler(webapp2.RequestHandler):

    @decorator.oauth_required
    def get(self):
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
        else:
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

            template = JINJA_ENVIRONMENT.get_template('templates/channel.html')
            self.response.write(template.render(template_values))


class GetUsersChannelHandler(webapp2.RequestHandler):

    @decorator.oauth_required
    def get(self):
        youtube = SERVICEYOUTUBE
        http = decorator.http()
        user_id = users.get_current_user().user_id()
        user_chaines = db.GqlQuery("SELECT * FROM OwnChannel WHERE userID = :idU", idU=user_id)
        tab_abonnement = []
        for i in user_chaines:
            tab_abonnement.append(i.channelID)
        db.delete(user_chaines)
        u = db.GqlQuery("SELECT * FROM Utilisateur WHERE userID = :idU", idU=user_id)
        if u.get() is None:
            self.redirect("http://gcdc2013-younotify.appspot.com/register")
        else:
            list_subscriptions_response = youtube.channels().list(
                part="id,snippet,contentDetails",
                mine=True,
                maxResults=25
            ).execute(http=http)

            my_channels = []
            if len(list_subscriptions_response) != 0:
                message = ''
                for result in list_subscriptions_response.get("items", []):
                    if result['id'] in tab_abonnement:
                        result['deja_abonne'] = True
                    my_channels.append(result)
            else:
                message = "No subscriptions was found."
                my_channels = []
            template_values = {
                'my_channels': my_channels,
                'message': message
            }

            template = JINJA_ENVIRONMENT.get_template('templates/channel.html')
            self.response.write(template.render(template_values))


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
        tab1, tab2, tab3 = [], [], []
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

        template = JINJA_ENVIRONMENT.get_template('templates/channel3.html')
        self.response.write(template.render(template_values))


class ThanksHandler(webapp2.RequestHandler):

    @decorator.oauth_required
    def post(self):
        idChaines = self.request.get('chaines', allow_multiple=True)
        youtube = SERVICEYOUTUBE
        for idChaine in idChaines:
            c = db.GqlQuery('SELECT * FROM Chaine where channelID = :channelID', channelID=idChaine)
            if c.get() is None:
                http = decorator.http()
                search_response = youtube.channels().list(
                    id=idChaine,
                    part="id,snippet,statistics").execute(http=http)
                nbVideo = 0
                for stat in search_response["items"]:
                    nbVideo = stat['statistics']['videoCount']
                chaine = Chaine(channelID=idChaine, nbVideos=int(nbVideo))
                chaine.put()
        
        c = db.GqlQuery('SELECT * FROM UtilisateurEtChaine where userID = :userID', userID=users.get_current_user().user_id())
        db.delete(c)
        userID = users.get_current_user().user_id()
        for idChaine in idChaines:
            chaine2 = UtilisateurEtChaine(userID=userID, channelID=idChaine)
            chaine2.put()
        template_values = {
        'nom': users.get_current_user().nickname(),
        'chaines':idChaines
        }
        template = JINJA_ENVIRONMENT.get_template('templates/thanks.html')
        self.response.write(template.render(template_values))


class SaveOwnedChannelHandler(webapp2.RequestHandler):

    @decorator.oauth_required
    def post(self):
        chaines = self.request.get('chaines', allow_multiple=True)
        likes = self.request.get('likesCount', allow_multiple=True)
        favorites = self.request.get('FavCount', allow_multiple=True)
        subs = self.request.get('SubsCount', allow_multiple=True)
        view_count = self.request.get('viewCount', allow_multiple=True)
        hidden_subs = self.request.get('hiddenSubsCount', allow_multiple=True)
        user_id = users.get_current_user().user_id()
        for i in range(0, len(chaines)):
            chaine = OwnChannel(channelID=chaines[i], nbreLike=int(likes[i]), nbreViews=int(view_count[i]),
                                nbreFavorites=int(favorites[i]), nbreSubscribers=int(subs[i]),
                                nbreHiddenSubscribers=int(hidden_subs[i]), userID=user_id)
            chaine.put()
        template_values = {
            'nom': users.get_current_user().nickname(),
        }
        template = JINJA_ENVIRONMENT.get_template('templates/thanks.html')
        self.response.write(template.render(template_values))


class UpdateVideoHandler(webapp2.RequestHandler):

    def get(self):
        nbre_video = 0
        youtube = SERVICEYOUTUBE
        calendar_serv = SERVICECALENDAR
        http = httplib2.Http()
        requete = db.GqlQuery("SELECT * FROM Chaine")
        liste = []
        cred = []
        idCal = []
        channels_with_new_videos = {}
        for chaine in requete:
            nbre_video = chaine.nbVideos
            new_videos = 0
            cred.append({'1 nbre_video': nbre_video})
            channelID = chaine.channelID
            channels_response = youtube.channels().list(
                part="id,snippet,statistics",
                id=channelID
                ).execute()
            nom_channel = ''
            for stat in channels_response["items"]:
                new_videos = stat['statistics']['videoCount']
                nom_channel = stat['snippet']['title']
                cred.append({'1 NEW_video': new_videos})
            if int(new_videos) != 0:
                chaine.nbVideos = int(new_videos)
                chaine.put()
                liste.append({'nbre_video': nbre_video, "nbVideos": new_videos})
                channels_with_new_videos[channelID] = nom_channel
        # chaineID=channelID)
        message_calendar = ''
        for b in db.GqlQuery("SELECT * FROM Utilisateur"):
            u = db.GqlQuery("SELECT * FROM UtilisateurEtChaine WHERE userID = :userID",
                            userID=b.userID)
            message_calendar = 'New video(s) is(are) posted on these channel(s) '
            for ligne in u:
                if ligne.channelID in channels_with_new_videos:
                    message_calendar += channels_with_new_videos[ligne.channelID] + ',\n'
            #credentials = StorageByKeyName(CredentialsModel, b.userID, 'credentials').get()
            credentials = b.credential
            cred.append(credentials)
            http = credentials.authorize(http)
            #http = decorator.http()
            now = datetime.now(pytz.timezone('UTC'))
            i = 5
            start = now + timedelta(minutes=i)
            i += 10
            end = now + timedelta(minutes=i)
            calendar = {
                'summary': message_calendar,
                'location': 'Youtube',
                'start': {
                    'dateTime': str(start.isoformat())
                },
                'end': {
                    'dateTime': str(end.isoformat())
                }
            }
            cred.append({"calendar": calendar})
            request = calendar_serv.events().insert(
                calendarId=b.calendarID,
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


class UpdateChannelOwnerHandler(webapp2.RequestHandler):

    def get(self):
        youtube = SERVICEYOUTUBE
        calendar_serv = SERVICECALENDAR
        requete = db.GqlQuery("SELECT * FROM OwnChannel")
        liste = []
        cred = []
        idCal = []
        for chaine in requete:
            credentials = StorageByKeyName(CredentialsModel, chaine.userID, 'credentials').get()
            http = httplib2.Http()
            http = credentials.authorize(http)
            nbre_like = chaine.nbreLike
            nbreSubs = chaine.nbreSubscribers
            nbreHiddenSubs = chaine.nbreHiddenSubscribers
            nbreFav = chaine.nbreFavorites
            nbreViews = chaine.nbreViews
            new_like = 0
            new_subs = 0
            new_hidden_subs = 0
            new_favs = 0
            new_views = 0
            channels_response = youtube.channels().list(
                part="id,snippet,statistics,contentDetails",
                mine=True,
                id=chaine.channelID
                ).execute(http=http)
            for stat in channels_response["items"]:
                new_views = stat['statistics']['viewCount']
                new_subs = stat['statistics']['subscriberCount']
                new_hidden_subs = stat['statistics']['hiddenSubscriberCount']
                new_favs = stat['contentDetails']['relatedPlaylists']['favorites']
                new_like = stat['contentDetails']['relatedPlaylists']['likes']
            if int(new_like) != nbre_like or int(new_favs) != nbreFav or int(new_subs) != nbreSubs or \
                    int(new_views) != nbreViews or int(new_hidden_subs) != nbreHiddenSubs:
                chaine.nbreViews = int(new_views)
                chaine.nbreLike = int(new_like)
                chaine.nbreFavorites = int(new_favs)
                chaine.nbreHiddenSubscribers = int(new_hidden_subs)
                chaine.nbreSubscribers = int(new_subs)
                chaine.put()

                message_calendar = 'New video(s) is(are) posted on these channel(s) '
                cred.append(credentials)
                now = datetime.now(pytz.timezone('UTC'))
                i = 5
                start = now + timedelta(minutes=i)
                i += 10
                end = now + timedelta(minutes=i)
                calendar = {
                    'summary': message_calendar,
                    'location': 'Youtube',
                    'start': {
                        'dateTime': str(start.isoformat())
                    },
                    'end': {
                        'dateTime': str(end.isoformat())
                    },
                    'reminders': {
                        'overrides': ['sms', 'email', 'popup']
                    }
                }
                cred.append({"calendar": calendar})
                req = db.GqlQuery("SELECT * FROM Utilisateur where userID=:id_u", id_u=chaine.userID)
                calendar_id = 0
                for i in req:
                    calendar_id = i.calendarID
                request = calendar_serv.events().insert(
                    calendarId=calendar_id,
                    body=calendar,
                    sendNotifications=True
                    ).execute(http=http)
                idCal.append(request['id'])
            else:
                pass
        template_values = {
            'liste': liste,
            'cred': cred,
            'events': idCal
        }
        template = JINJA_ENVIRONMENT.get_template('templates/update.html')
        self.response.write(template.render(template_values))


class RevokeHandler(webapp2.RequestHandler):

    @decorator.oauth_aware
    def get(self):
        http = httplib2.Http()
        userID = users.get_current_user().user_id()
        uc = db.GqlQuery('SELECT * FROM UtilisateurEtChaine where userID = :userID ', userID=userID)
        db.delete(uc)
        u = db.GqlQuery('SELECT * FROM Utilisateur where userID = :userID', userID=userID)
        cred = ""
        for ligne in u:
            cred = ligne.credential
            http = cred.authorize(http)
            cred._revoke(http)
        db.delete(u)
        #self.redirect("https://accounts.google.com/o/oauth2/revoke?token="+)"""
        self.redirect("https://accounts.google.com/IssuedAuthSubTokens")



#class RevokeHandler(webapp2.RequestHandler):
#
#    #def __init__(self):
#    #    self.user = users.get_current_user()
#
#    def get(self):
#        u = db.GqlQuery("SELECT * FROM Utilisateur WHERE userID = :idU", idU=users.get_current_user().user_id())
#        credentials = ''
#        token = ''
#        if u.get() is None:
#            self.redirect("http://gcdc2013-younotify.appspot.com/register")
#            return 0
#        else:
#            for i in u:
#                token = i.credential['access_token']
#
#        result = urlfetch.fetch(url="https://www.google.com/accounts/AuthSubRevokeToken",
#                                method="GET",
#                                headers={'Authorization': token},
#                                deadline=5)
#        if result.status_code == 200:
#            self.response.out.write("Its ok!")
#            #self.redirect("/settings")
#        else:
#            self.response.out.write("There was a problem. Please try again later.")



application = webapp2.WSGIApplication([
    ('/', ComingSoon),
    ('/index.html', ComingSoon),
    ('/bbt', Index),
    ('/youtube', YoutubeHandler),
    ('/my_channels', GetUsersChannelHandler),
    ('/register', Register),
    ('/register2', YoutubeHandler),
    ('/channel2', Register2Handler),
    ('/thanks', ThanksHandler),
    ('/save_own_channel', SaveOwnedChannelHandler),
    ('/update', UpdateVideoHandler),
    ('/update_my_channels', UpdateChannelOwnerHandler),
    ('/register3',Register3Handler),
    ('/tutorial',TutorialHandler),
    ('/tutorial2',Tutorial2Handler),
    ('/whatis.html', WhatHandler),
    ('/revoke', RevokeHandler),
    (decorator.callback_path, decorator.callback_handler())
], debug=True)