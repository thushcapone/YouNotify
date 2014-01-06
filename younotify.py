import jinja2
import os
import webapp2
import httplib2
import urllib
import json
import pytz

from datetime import datetime
from datetime import timedelta


from google.appengine.api import users
from google.appengine.ext import db
from apiclient.discovery import build
from oauth2client import appengine
from google.appengine.api import memcache
from oauth2client.appengine import StorageByKeyName, CredentialsModel
from google.appengine.api import urlfetch

from models import Utilisateur
from models import UtilisateurEtChaine
from models import Chaine
from models import OwnChannel
from models import UtilisateurEtInteret
from models import Interets



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
FREEBASE_SEARCH_URL = "https://www.googleapis.com/freebase/v1/search?%s"

decorator = appengine.OAuth2Decorator(
    client_id="873080943535-r530olahgmoggead5efgbekk7ecu1oro.apps.googleusercontent.com",
    client_secret="IurBjo_aR-1NzW7NHZw-1xms",
    scope=['https://www.googleapis.com/auth/youtube',
           "https://www.googleapis.com/auth/youtubepartner",
           'https://www.googleapis.com/auth/calendar'],
    message=MISSING_CLIENT_SECRETS_MESSAGE,
    access_type="offline",
    approval_prompt="force"
)


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
            youtube = SERVICEYOUTUBE
            calendar = {
                'summary': 'youNotify'
            }
            if decorator.has_credentials():
                http = decorator.http()
                request = calendar_serv.calendars().insert(body=calendar).execute(http=http)
                calendar_list = {
                    'id': request['id'],
                    "defaultReminders": [
                        {
                            "method": "sms",
                            "minutes": 0
                        },
                        {
                            "method": "popup",
                            "minutes": 0
                        }
                    ]
                }
                request = calendar_serv.calendarList().insert(body=calendar_list).execute(http=http)
                watch_later = youtube.channels().list(
                    part="id,contentDetails",
                    mine=True
                ).execute(http=http)
                watch_later = watch_later.get("items", [])
                playlist_id = watch_later[0]['contentDetails']['relatedPlaylists']['watchLater']
                calendarId = request['id']
                cred = decorator.get_credentials()
                utilisateur = Utilisateur(calendarID=calendarId, userID=userID, userEmail=userEmail, credential=cred,
                                          playlistID=playlist_id)
                utilisateur.put()
                now = datetime.now(pytz.timezone('UTC'))
                i = 1
                start = now + timedelta(minutes=i)
                i += 2
                end = now + timedelta(minutes=i)
                calendar = {
                    'summary': "Thanks for registering to YouNotify!",
                    'start': {
                        'dateTime': str(start.isoformat())
                    },
                    'end': {
                        'dateTime': str(end.isoformat())
                    }
                }
                calendar_serv.events().insert(
                    calendarId=calendarId,
                    body=calendar,
                    sendNotifications=True
                ).execute(http=http)
            else:
                self.redirect(decorator.authorize_url())
        else:
            self.redirect('/youtube')
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
        u = db.GqlQuery('SELECT * FROM Utilisateur WHERE userID=:id_u', id_u=users.get_current_user().user_id())
        has_credentials = False
        if u.get() is not None:
            has_credentials = True
        template_values = {
            'user': users.get_current_user().nickname(),
            'has_credentials':  has_credentials
        }
        template = JINJA_ENVIRONMENT.get_template('templates/index.html')
        self.response.write(template.render(template_values))


class YoutubeHandler(webapp2.RequestHandler):

    @decorator.oauth_required
    def get(self):
        youtube = SERVICEYOUTUBE
        http = decorator.http()
        userID = users.get_current_user().user_id()
        user_chaines = db.GqlQuery("SELECT * FROM UtilisateurEtChaine WHERE userID = :idU", idU=userID)
        tab_abonnement = []
        for i in user_chaines:
            tab_abonnement.append(i.channelID)
        u = db.GqlQuery("SELECT * FROM Utilisateur WHERE userID = :idU", idU=userID)
        credentials = ''
        if u.get() is None:
            self.redirect("http://gcdc2013-younotify.appspot.com/register")
        else:
            list_subscriptions_response = youtube.subscriptions().list(
                part="id,snippet",
                mine=True,
                maxResults=50
            ).execute(http=http)

            if not list_subscriptions_response["items"]:
                print "No subscriptions was found."

            subscriptions = []
            for result in list_subscriptions_response.get("items", []):
                if result['snippet']['resourceId']['channelId'] in tab_abonnement:
                    result['deja_abonne'] = True
                subscriptions.append(result)

            interets = db.GqlQuery("SELECT * FROM UtilisateurEtInteret Where userID = :userID", userID=userID)
            topics = []
            index = [0,1,2,3,4]
            for interet in interets:
                topics.append(interet.interetID)

            template_values = {
            'subscriptions': subscriptions,
            'topic': topics,
            'index':index
            }

            template = JINJA_ENVIRONMENT.get_template('templates/channel.html')
            self.response.write(template.render(template_values))

class TutorialHandler(webapp2.RequestHandler):

    def get(self):
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

class ThanksHandler(webapp2.RequestHandler):

    @decorator.oauth_required
    def post(self):
        user_chaines = db.GqlQuery("SELECT * FROM UtilisateurEtChaine WHERE userID = :idU", idU=users.get_current_user().user_id())
        db.delete(user_chaines)
        idChaines = self.request.get('chaines', allow_multiple=True)
        userID = users.get_current_user().user_id()
        topics = []
        topics.append(self.request.get('topic1'))
        topics.append(self.request.get('topic2'))
        topics.append(self.request.get('topic3'))
        topics.append(self.request.get('topic4'))
        topics.append(self.request.get('topic5'))

        youtube = SERVICEYOUTUBE

        error = ""

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

        c = db.GqlQuery('SELECT * FROM UtilisateurEtChaine where userID = :userID', userID=userID)
        db.delete(c)

        for idChaine in idChaines:
            chaine2 = UtilisateurEtChaine(userID=userID, channelID=idChaine)
            chaine2.put()

        c = db.GqlQuery('SELECT * FROM UtilisateurEtInteret where userID = :userID', userID=userID)
        db.delete(c)

        for topic in topics:
            # Retrieve a list of Freebase topics associated with the provided query term.
            if topic != "":
                freebase_params = dict(query=topic, key=DEVELOPER_KEY, maxResults=5)
                freebase_url = FREEBASE_SEARCH_URL % urllib.urlencode(freebase_params)
                freebase_response = json.loads(urllib.urlopen(freebase_url).read())

                if len(freebase_response["result"]) == 0:
                    error = "Sorry but for now "+topic+" is not a topic!!"

                else:
                    c = db.GqlQuery('SELECT * FROM Interets where interetID = :interetID', interetID=topic)
                    if c.get() is None:
                        http = decorator.http()
                        mid = freebase_response["result"][0]["mid"]
                        interet = Interets(interetID=topic, interet=mid)
                        interet.put()
                    interet = UtilisateurEtInteret(userID=userID, interetID=topic)
                    interet.put()

        template_values = {
            'nom': users.get_current_user().nickname(),
            'chaines': idChaines
        }
        template = JINJA_ENVIRONMENT.get_template('templates/thanks.html')
        self.response.write(template.render(template_values))


class UpdateInteret(webapp2.RequestHandler):

    def get(self):
        youtube = SERVICEYOUTUBE
        calendar_serv = SERVICECALENDAR

        requete = db.GqlQuery('SELECT * FROM Interets')
        for topic in requete:
            one_week_ago = datetime.now(pytz.timezone('UTC')) - timedelta(days=7)
            one_week_ago = one_week_ago.isoformat()
            list_video = youtube.search().list(
                topicId=topic.interet.strip(),
                part="id,snippet",
                order="viewCount",
                publishedAfter=one_week_ago,
                type="video",
                maxResults=1
            ).execute()
            videos = list_video.get('items', [])
            message_calendar = videos[0]['snippet']['title']+" is treading!!!"
            users = db.GqlQuery('SELECT * FROM UtilisateurEtInteret Where interetID = :interetID', interetID=topic.interetID)
            for user in users:
                users2 = db.GqlQuery('SELECT * FROM Utilisateur Where userID = :userID', userID=user.userID)
                for u in users2:
                    credentials = u.credential
                    http = httplib2.Http()
                    http = credentials.authorize(http)
                    now = datetime.now(pytz.timezone('UTC'))
                    i = 2
                    start = now + timedelta(minutes=i)
                    i += 5
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

                    request = calendar_serv.events().insert(
                        calendarId=u.calendarID,
                        body=calendar,
                        sendNotifications=True
                    ).execute(http=http)


class UpdateVideoHandler(webapp2.RequestHandler):

    def get(self):
        nbre_video = 0
        youtube = SERVICEYOUTUBE
        calendar_service = SERVICECALENDAR
        requete = db.GqlQuery("SELECT * FROM Chaine")
        liste = []
        cred = []
        idCal = []
        search_response = []
        channels_with_new_videos = {}
        channels_video = {}
        for chaine in requete:
            videos = []
            nbre_video = chaine.nbVideos
            new_videos = 0
            channelID = chaine.channelID
            try:
                channels_response = youtube.channels().list(
                    part="id,snippet,statistics",
                    id=channelID
                ).execute()
            except Exception:
                pass
            nom_channel = ''
            for stat in channels_response["items"]:
                new_videos = stat['statistics']['videoCount']
                nom_channel = stat['snippet']['title']
                cred.append({'1 NEW_video': new_videos})
            if int(new_videos) != nbre_video:
                nbreSearch = int(new_videos) - nbre_video
                chaine.nbVideos = int(new_videos)
                chaine.put()
                liste.append({'nbre_video': nbre_video, "nbVideos": new_videos})
                channels_with_new_videos[channelID] = nom_channel
                search_response = ''
                if nbreSearch != 0:
                    if nbreSearch > 50 or nbreSearch < 0:
                        nbreSearch = 5
                    search_response = youtube.search().list(
                        part="id,snippet",
                        channelId=chaine.channelID,
                        maxResults=nbreSearch,
                        order="date",
                        type="video"
                    ).execute()
                    for i in search_response.get('items', []):
                        videos.append([i['id']['videoId'], i['snippet']['title'], nom_channel])
                    channels_video[chaine.channelID] = videos
        playlists_insert = ''
        error = []
        for b in db.GqlQuery("SELECT * FROM Utilisateur"):
            u = db.GqlQuery("SELECT * FROM UtilisateurEtChaine WHERE userID = :userID",
                            userID=b.userID)
            credentials = b.credential
            cred.append(credentials)
            http = httplib2.Http()
            http = credentials.authorize(http)
            for ligne in u:
                if ligne.channelID in channels_with_new_videos:
                    for liste in channels_video[ligne.channelID]:
                        try:
                            playlists_insert = youtube.playlistItems().insert(
                                part="snippet",
                                body=dict(
                                    snippet=dict(
                                        playlistId=b.playlistID,
                                        resourceId=dict(
                                            kind="youtube#video",
                                            videoId=liste[0]
                                        )
                                    )
                                )
                            ).execute(http=http)
                        except Exception:
                            pass
                        now = datetime.now(pytz.timezone('UTC'))
                        i = 2
                        start = now + timedelta(minutes=i)
                        i += 5
                        end = now + timedelta(minutes=i)
                        calendar = {
                            'summary': liste[1] + " have been posted by " + liste[2],
                            'location': 'Youtube',
                            'start': {
                                'dateTime': str(start.isoformat())
                            },
                            'end': {
                                'dateTime': str(end.isoformat())
                            }
                        }
                        cred.append({"calendar": calendar})
                        request = calendar_service.events().insert(
                            calendarId=b.calendarID,
                            body=calendar,
                            sendNotifications=True
                        ).execute(http=http)
                        idCal.append(request['id'])
            template_values = {
                'cred': cred,
                'channel': channels_video
            }
            template = JINJA_ENVIRONMENT.get_template('templates/update.html')
            self.response.write(template.render(template_values))


class RevokeHandler(webapp2.RequestHandler):

    @decorator.oauth_aware
    def get(self):
        http = httplib2.Http()
        service = SERVICECALENDAR
        youtube = SERVICEYOUTUBE
        userID = users.get_current_user().user_id()
        cred = ''
        token = ''
        calendar_id = ''
        playlist_id = ''
        u = db.GqlQuery('SELECT * FROM Utilisateur where userID = :userID', userID=userID)
        for ligne in u:
            token = ligne.credential.refresh_token
            cred = ligne.credential
            calendar_id = ligne.calendarID
            playlist_id = ligne.playlistID
        #http = cred.authorize(http)
        http = decorator.http()
        result = urlfetch.fetch(url="https://accounts.google.com/o/oauth2/revoke?token="+token)
        if result.status_code == 200:
            uc = db.GqlQuery('SELECT * FROM UtilisateurEtChaine where userID = :userID ', userID=userID)
            ui = db.GqlQuery('SELECT * FROM UtilisateurEtInteret where userID = :userID', userID=userID)
            a = db.GqlQuery('SELECT * FROM CredentialsModel where id=:id_user', id_user=userID)
            db.delete(a)
            db.delete(uc)
            db.delete(u)
            db.delete(ui)
            #service.calendars().delete(calendarId=calendar_id).execute(http=http)
            self.redirect("http://gcdc2013-younotify.appspot.com/")
        else:
            self.response.out.write("There was a problem. Please try again later. "+str(result.status_code))
            #self.redirect("http://gcdc2013-younotify.appspot.com/bbt")

class ClearHandler(webapp2.RequestHandler):

    def get(self):
        service = SERVICECALENDAR
        http = httplib2.Http()
        cred = ''
        u = db.GqlQuery('SELECT * FROM Utilisateur')
        for ligne in u:
            cred = ligne.credential
            calendar_id = ligne.calendarID
            http = cred.authorize(http)
            service.calendars().clear(
                calendarId=calendar_id
            ).execute(http=http)



application = webapp2.WSGIApplication([
    ('/', Index),
    ('/index.html', Index),
    ('/youtube', YoutubeHandler),
    ('/register', Register),
    ('/register2', YoutubeHandler),
    ('/thanks', ThanksHandler),
    ('/update', UpdateVideoHandler),
    ('/tutorial', TutorialHandler),
    ('/tutorial2', Tutorial2Handler),
    ('/whatis', WhatHandler),
    ('/update_interet', UpdateInteret),
    ('/revoke', RevokeHandler),
    ('/clear', ClearHandler),
    (decorator.callback_path, decorator.callback_handler())
], debug=True)
