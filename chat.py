# -*- encoding: utf-8 -*-

from chat_downloader import ChatDownloader
from chat_downloader.errors import (
    ChatDisabled,
    NoChatReplay,
    LoginRequired,
    VideoUnplayable,
    VideoUnavailable,
    VideoNotFound,
    ChatDownloaderError
)
import scrapetube
import sys, os, re, time
import requests, json
from urllib3.util.retry import Retry
from http.cookiejar import MozillaCookieJar
from datetime import datetime
import dateutil.parser
from zoneinfo import ZoneInfo

class Program():
    def __init__(self, idchannel, urlchannel, youtubeKey, session_params, tz, output_dirs, dateFormats):
        self.idchannel = idchannel
        self.urlchannel = urlchannel
        self.youtubeKey = youtubeKey
        self.session_params = session_params
        self.tzinfo = ZoneInfo(tz)
        self.output_dirs = output_dirs
        self.dateFormats = dateFormats
        self.loggingfile = None
        self.resultfile = None
        self.sessionYoutube = None
        self.sessionGoogleApis = None
                       
        self.start()
        
    def start(self):
        self.initLoggingFile()
        print("Starting program")
        self.writelog("Starting program")
        self.initCookies()
        self.initSessionYoutube()
        self.initSessionGoogleApis()
        self.initChannel()
        self.initResultFile()
       
    def initLoggingFile(self):
        loggingfilename = self.output_dirs['log_file'] + "chat_" + self.idchannel + ".log"
        try:
            self.loggingfile = open(loggingfilename, "a", encoding="utf-8")
        except Exception as e:
            print(e)
            self.exitProgram()
    
    def initResultFile(self):
        dateNow = self.getDateNow()
        resultfilename = self.output_dirs['result_file'] + "chat_" + self.idchannel + "_" + dateNow['dateFileString'] +  ".txt"
        try:
            self.resultfile = open(resultfilename, "w", encoding="utf-8")
        except Exception as e:
            print(e)
            self.exitProgram()
    
    def getDateNow(self):
        timestamp_now = datetime.now().timestamp()
        date = datetime.fromtimestamp(timestamp_now, self.tzinfo)
        dateString = date.strftime(self.dateFormats['dateString'])
        dateDBString = date.strftime(self.dateFormats['dateDBString'])
        dateFileString = date.strftime(self.dateFormats['dateFileString'])
        
        dateNow = {"dateString": dateString, "dateDBString": dateDBString, "dateFileString": dateFileString}
        
        return dateNow

    def writelog(self, message):
        dateNow = self.getDateNow()
        self.loggingfile.write(dateNow["dateString"] + " : " + message + "\n")
        # Write in real time
        self.loggingfile.flush()
            
    def writeresult(self, message):
        self.resultfile.write(message)
        # Write in real time
        #self.resultfile.flush()

    def initCookies(self):
        self.set_user_cookies()
        self.setCookies()

    def set_user_cookies(self):
        self.user_cookies = False
        if self.session_params['cookies']:
            if os.path.isfile(self.session_params['cookies']):
                self.user_cookies = True
                   
    def setCookies(self):
        if self.user_cookies is False:
            # To avoid consent popup showing off when calling response = requests.get(url), we set a cookie to "Accept all"
            cookie_jar = requests.cookies.RequestsCookieJar()
            cookie_jar.set('SOCS', 'CAI', domain='.youtube.com', secure=True) # CAI means "accept all"          
        else:
            cookie_jar = MozillaCookieJar(self.session_params['cookies'])
            cookie_jar.load(ignore_discard=True)
            
        self.cookie_jar = cookie_jar

    def initSessionYoutube(self):
        self.sessionYoutube = self.create_session(cookies=self.cookie_jar)

    def initSessionGoogleApis(self):
        # Youtube Data API V3 can sometimes return HTTP status 400 and 403 whereas request is valid, and sending this same request succeeds.
        self.sessionGoogleApis = self.create_session(status_forcelist=(400, 403, 408, 425, 429, 500, 502, 503, 504))

    def create_session(
        self,
        cookies=None,
        retries=3,
        backoff_factor=1,
        backoff_jitter=0.5,
        allowed_methods=frozenset(["GET", "POST", "HEAD", "OPTIONS"]),
        status_forcelist=(408, 425, 429, 500, 502, 503, 504),
    ):

        session = requests.Session()
        
        if cookies is not None:
            session.cookies = cookies        

        retry = Retry(
            total=retries,
            backoff_factor=backoff_factor,
            backoff_jitter=backoff_jitter,
            allowed_methods=allowed_methods,
            status_forcelist=status_forcelist,
            raise_on_status=False
        )

        adapter = requests.adapters.HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def initChannel(self):
        # Get handle from idchannel
        channelInfosURL = "https://www.googleapis.com/youtube/v3/channels?key=" + self.youtubeKey + "&id=" + self.idchannel + "&part=snippet"
        print(channelInfosURL)
        try:
            response = self.sessionGoogleApis.get(channelInfosURL, timeout=(3.05, 20))
            channelInfosResponse = response.text
            if response.status_code == 200:
                channel_json = json.loads(channelInfosResponse)

                if channel_json.get('pageInfo').get('totalResults') == 0:
                    print(f"[×] channel={self.idchannel} Error channelInfosURL {channelInfosURL} : channel not found")
                    self.writelog(f"[×] channel={self.idchannel} Error channelInfosURL {channelInfosURL} : channel not found")
                    self.exitProgram()
                
                item = channel_json.get('items')[0]
                snippet = item.get('snippet')
                handle = snippet.get('customUrl')[1:len(snippet.get('customUrl'))]
                self.urlchannel = "https://www.youtube.com/@" + handle
            else:
                print(f"[×] channel={self.idchannel} Response of channelInfosURL {channelInfosURL} isn't OK : {response.status_code} {response.text}")
                self.writelog(f"[×] channel={self.idchannel} Response of channelInfosURL {channelInfosURL} isn't OK : {response.status_code} {response.text}")
                self.exitProgram()
        except Exception as e:
            print(f"[×] channel={self.idchannel} Error channelInfosURL {channelInfosURL} : {e}")
            self.writelog(f"[×] channel={self.idchannel} Error channelInfosURL {channelInfosURL} : {e}")
            self.exitProgram()

    def safely_get_value_from_key(self, *args, default=None):
        obj = args[0]
        keys = args[1:]

        for key in keys:
            try:
                obj = obj[key]
            except Exception:
                return default

        return obj        

    # Used when errors/exceptions occured and when we want to exit right now
    def exitProgram(self):
        try:
            self.writelog("Execution had errors")
            self.writelog("Ending program")
        except Exception as e:
            print(e)

        self.clean()
        sys.exit(1)
    
    # Used at the end of program without errors/exceptions and when errors/exception occured
    def clean(self):
        try:
            # Close Files
            if self.loggingfile is not None:
                self.loggingfile.close()
            if self.resultfile is not None:    
                self.resultfile.close()
        except Exception as e:
            print("Error cleaning up : " + str(e))
    
    def getVideoInfos(self, url):
        infosVideo = {"ytInitialPlayerResponse": None, "videoDetails": None}

        try:
            response = self.sessionYoutube.get(url, timeout=(3.05, 20))
            
            if response.status_code == 200:
                ytInitialPlayerResponse = re.findall('ytInitialPlayerResponse\\s*=\\s*({.+?})\\s*;', response.text)
                if len(ytInitialPlayerResponse) == 1:
                    data = json.loads(ytInitialPlayerResponse[0])
                    infosVideo["ytInitialPlayerResponse"] = data
                    
                    videoDetails = data.get('videoDetails')
                    playabilityStatus = data.get('playabilityStatus')
                    liveBroadcastDetails = self.safely_get_value_from_key(data, "microformat", "playerMicroformatRenderer", "liveBroadcastDetails")
                    has_chat = True if liveBroadcastDetails is not None else False
                    scheduledStartTime = self.safely_get_value_from_key(playabilityStatus, "liveStreamability", "liveStreamabilityRenderer", "offlineSlate",
                                                                        "liveStreamOfflineSlateRenderer", "scheduledStartTime")
                    if videoDetails is not None:
                        video = {"videoId": videoDetails.get('videoId'), "title": videoDetails.get('title'),
                        "is_live": videoDetails.get("isLive"), "has_chat": has_chat, "playabilityStatus": playabilityStatus,
                        "scheduledStartTime": scheduledStartTime}
                        infosVideo["videoDetails"] = video
                    else:
                        print(f"{url} ytInitialPlayerResponse : videoDetails not found, status={playabilityStatus.get('status')} reason={playabilityStatus.get('reason')}")
                        self.writelog(f"{url} ytInitialPlayerResponse : videoDetails not found, status={playabilityStatus.get('status')} reason={playabilityStatus.get('reason')}")
                else:
                    print(f"{url} ytInitialPlayerResponse not found")
                    self.writelog(f"{url} ytInitialPlayerResponse not found")
            else:
                print(f"[×] Response of url {url} isn't OK : {response.status_code} {response.text}")
                self.writelog(f"[×] Response of url {url} isn't OK : {response.status_code} {response.text}")
        except Exception as e:
            print(f"[×] Error url {url} : {e}")
            self.writelog(f"[×] Error url {url} : {e}")
            
        return infosVideo
    
    def main(self):
        self.writelog("Channel " + self.urlchannel + " id : " + self.idchannel)
        self.writeresult("Channel " + self.urlchannel + " id : " + self.idchannel)
        self.writeresult("\n\n")

        # Get all url streams and Premiere videos
        videotypes = ["streams", "videos"]
        for videotype in videotypes:
            num_videos_processed = 0
            try:
                videos = scrapetube.get_channel(channel_id=self.idchannel, content_type=videotype, cookies=self.session_params["cookies"], sort_by="newest")
                videosList = list(videos)
            except Exception as e:
                print(f"[×] Error scrapetube getting {videotype} : {e}")
                self.writelog(f"[×] Error scrapetube getting {videotype} : {e}")
                self.exitProgram()
            
            num_videosList = len(videosList)
            print(f"Type : {videotype} (total : {num_videosList})")
            self.writelog(f"Type : {videotype} (total : {num_videosList})")
            self.writeresult(f"Type : {videotype} (total : {num_videosList})")
            self.writeresult("\n\n")
            
            for video in videosList:
                time.sleep(2)
                url = "https://www.youtube.com/watch?v="+str(video['videoId'])
               
                if videotype == "videos":
                    # Impossible to determine with scrapetube.get_channel() if a video is a Premiere
                    # and I don't want to hit YTB API V3 /videos for each video and consume a lot of quota.
                    # So I can determine wether a video has/had a chat by hitting Youtube video page source checking in var ytInitialPlayerResponse = {}
                    
                    videoInfo = self.getVideoInfos(url)
                    # Pass if ytInitialPlayerResponse is None or videoDetails is None
                    if videoInfo['ytInitialPlayerResponse'] is None:
                        continue
                    else:
                        if videoInfo['videoDetails'] is None:
                            continue
                        else:
                            # Ditch video if : no chat, still on live, or is scheduled
                            if (videoInfo['videoDetails']['has_chat'] is False
                            or videoInfo['videoDetails']['is_live'] is True
                            or videoInfo['videoDetails']['scheduledStartTime'] is not None):
                                continue

                # Here, we only have streams and videos that have/had a chat
                # If you don't want to use YTB API V3, use data in getVideoInfos function to get title, dates, description, duration, liveBroadcastDetails
                additionnalInfosURL = "https://www.googleapis.com/youtube/v3/videos?key=" + self.youtubeKey + "&id=" + video['videoId'] + "&part=snippet,contentDetails,liveStreamingDetails,statistics"
                print(additionnalInfosURL)
                try:
                    response = self.sessionGoogleApis.get(additionnalInfosURL, timeout=(3.05, 20))
                    additionnalInfosResponse = response.text
                    if response.status_code == 200:
                        video_json = json.loads(additionnalInfosResponse)
                        if video_json.get('pageInfo').get('totalResults') == 0:                        
                            print(f"[×] idVideo={video['videoId']} video not found")
                            self.writelog(f"[×] idVideo={video['videoId']} video not found")
                            continue
                    else:
                        print(f"[×] idVideo={video['videoId']} Response of additionnalInfosURL {additionnalInfosURL} isn't OK : {response.status_code} {response.text}")
                        self.writelog(f"[×] idVideo={video['videoId']} Response of additionnalInfosURL {additionnalInfosURL} isn't OK : {response.status_code} {response.text}")
                        self.exitProgram()
                except Exception as e:
                    print(f"[×] idVideo={video['videoId']} Error additionnalInfosURL {additionnalInfosURL} : {e}")
                    self.writelog(f"[×] idVideo={video['videoId']} Error additionnalInfosURL {additionnalInfosURL} : {e}")
                    self.exitProgram()
                        
                item = video_json.get('items')[0]
                snippet = item.get('snippet')
                dateVideo = snippet.get('publishedAt')
                dateVideo_object = dateutil.parser.isoparse(dateVideo)
                dateVideo_text = dateVideo_object.astimezone(self.tzinfo).strftime(self.dateFormats['dateString'])
                title = snippet.get('title')
                description = snippet.get('description')

                contentDetails = item.get('contentDetails')
                duration = contentDetails.get('duration', '')
                durationString = duration[2:len(duration)]

                # Check if video is ended. Because some videos can be scheduled and chat is on with messages, for this case video don't have start and endtime.
                # liveBroadcastContent is "upcoming" if scheduled and will be "live" when on and none I guess when done. So we check "none"
                if "liveStreamingDetails" in item and snippet.get("liveBroadcastContent") == "none":
                    print(url)
                    self.writeresult(url)
                    self.writeresult("\n")
                    print("Title : " + title)
                    self.writeresult("Title : " + title)
                    self.writeresult("\n")
                    print("Date : " + dateVideo_text)
                    self.writeresult("Date : " + dateVideo_text)
                    
                    actualStartTime_object = dateutil.parser.isoparse(item.get("liveStreamingDetails").get("actualStartTime", ""))
                    actualStartTime_text = actualStartTime_object.astimezone(self.tzinfo).strftime(self.dateFormats['dateString'])
                    actualEndTime_object = dateutil.parser.isoparse(item.get("liveStreamingDetails").get("actualEndTime", ""))
                    actualEndTime_text = actualEndTime_object.astimezone(self.tzinfo).strftime(self.dateFormats['dateString'])                                  
                    print("start : " + actualStartTime_text)
                    self.writeresult(" (start : " + actualStartTime_text)
                    print("end : " + actualEndTime_text)
                    self.writeresult(" end : " + actualEndTime_text + ")")
                    
                    self.writeresult("\n")
                    print("Duration : " + durationString)
                    self.writeresult("Duration : " + durationString)
                    self.writeresult("\n")
                    #print(str(description))
                    #self.writeresult(str(description))
                    #self.writeresult("\n")
                    
                    print("Chat :")
                    self.writeresult("Chat :")
                    self.writeresult("\n")

                    try:
                        chat = ChatDownloader(cookies=self.session_params['cookies']).get_chat(url)       # create a generator
                        for message in chat:                        # iterate over messages
                            print(chat.format(message))
                            self.writeresult(chat.format(message))
                            self.writeresult("\n")
                    # List of exceptions : https://deepwiki.com/xenova/chat-downloader/6-error-handling
                    # These exceptions are not really errors
                    # If you prefer not display any error in result file, comment this except block
                    except (NoChatReplay, ChatDisabled, LoginRequired, VideoUnplayable, VideoUnavailable, VideoNotFound) as ex:
                        print(f"{ex}")
                        self.writeresult(f"{ex}")
                        self.writeresult("\n")
                    # These are errors
                    except Exception as ex:
                        print(f"[×] idVideo={video['videoId']} Error writing chat : {ex}")
                        self.writelog(f"[×] idVideo={video['videoId']} Error writing chat : {ex}")
                        self.exitProgram()

                    self.writeresult("\n")
                    num_videos_processed = num_videos_processed + 1

            print(f"Processed : {num_videos_processed}")
            self.writelog(f"Processed : {num_videos_processed}")
            
        print("Execution was OK")
        self.writelog("Execution was OK")
        print("Ending program")
        self.writelog("Ending program")
        self.clean()

if __name__ == "__main__":
    # Paths
    output_dirs = {'log_file': "",
                'result_file': ""
    }
    # Youtube
    urlchannel = "https://www.youtube.com/@your_channel"
    idchannel = '' # Found channel id on Youtube by clicking "Share channel" then "Copy channel ID"
    youtubeKey = '' # YouTube API Key from Google Cloud, see https://helano.github.io/help.html
    session_params = {"cookies": ""}
    # Format
    tz = "Europe/Paris" # Set tz also in chat_downloader/formatting/custom_formats.json to apply tz to chat messages date
    dateFormats = {"dateString": "%d/%m/%Y %H:%M:%S", "dateDBString": "%Y-%m-%d %H:%M:%S", "dateFileString": "%d%m%Y%H%M%S"}

    # Launch
    program = Program(idchannel, urlchannel, youtubeKey, session_params, tz, output_dirs, dateFormats)
    program.main()
    
