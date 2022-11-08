import sys
import os
import glob 
import urllib.parse
import subprocess
import locale
import re
from datetime import datetime

VERSION = "0.1.2-post"

allowed_video_domains = [
  "youtube.com",
  "youtu.be"
]

checkmark = u'\u2713'
crossmark = u'\u2715'
max_video_resolution_p = 720
DEBUG = True
DOWNLOAD_RETRIES = 3
last_temp_message_length = 0

def log( message ):
  if DEBUG:
    with open( re.sub(r"\.py$", ".log", sys.argv[0], 1), mode="a", encoding="utf-8" ) as f:
      f.write(f"[{datetime.now().strftime('%d.%m.%Y %H:%M:%S')}] {message}\n")

def error_out( message ):
  print(f"FEHLER: {message}")

def parse_args():
  # parse source-directory
  source_directory = "."
  if len(sys.argv) >= 2:
    # 1st arg without trailing "/"
    source_directory = sys.argv[1].rstrip("/")

  if not os.path.isdir(source_directory):
    error_out(f"konnte das Verzeichnis '{source_directory}' nicht finden")
    sys.exit(1)
  
  return {
    'source dir': source_directory
  }

def get_url( urlfile ):
  with open( urlfile, mode="r", encoding="utf-8" ) as f:
    lines = [line.strip() for line in f.readlines()]
  for line in lines:
    if line.startswith("URL"):
      return line.split("URL=")[1]
  return ''

def get_valid_song_list( source_directory ):
  songs = []

  print("prüfe gefundene Songs...")
  # iterate list of txt files in source directory, see https://stackoverflow.com/a/3215392
  for filepath in glob.glob(f"{source_directory}/*.txt"):
    song = {}
    files = {}
    files['txt'] = filepath

    # get filename and remove file extension
    song['name'] = '.'.join(filepath.split(os.sep)[-1].split(".")[0:-1])

    # check (required) existance of Video Weblink
    url_file = os.path.join(source_directory, f"{song['name']}.url")
    if not os.path.isfile(url_file):
      print(f"{crossmark} {song['name']}: Linkdatei '{url_file}' fehlt")
      continue
    files['url'] = url_file

    # check url is valid domain
    song['url'] = get_url( files['url'] )
    if song['url'] == '':
      print(f"{crossmark} {song['name']}: '{files['url']}' enthält keine URL")
      continue
    elif urllib.parse.urlparse( song['url'] ).hostname not in allowed_video_domains:
      print(f"{crossmark} {song['name']}: '{song['url']}' ist keine gültige Streaming Domain")
      continue
  
    # check (required) existance of cover file
    cover_file = os.path.join(source_directory, f"{song['name']} - Cover.jpg")
    if not os.path.isfile(cover_file):
      print(f"{crossmark} {song['name']}: Coverdatei '{cover_file}' fehlt")
      continue
    files['cover'] = cover_file

    # check (optional) existance of info file
    info_file = os.path.join(source_directory, f"{song['name']}.info")
    if os.path.isfile(info_file):
      files['info'] = info_file

    # checkmark for this song
    print(f"{checkmark} {song['name']}")
    song["files"] = files
    songs.append(song)

  return songs

def get_yt_download_files( youtube_url ):
  command = ['youtube-dl', '-F', youtube_url]
  log( ' '.join(command) )
  yt_result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  success = (yt_result.returncode == 0)
  if success:
    # Note: youtube-dl returns in locale encoding (Windows: 'cp1252')
    result = yt_result.stdout.decode(locale.getencoding())
    log( f"Ausgabe:\n{result}")
    return result
  else:
    # Note: youtube-dl returns in locale encoding (Windows: 'cp1252')
    log(f"kein Erfolg:\n{yt_result.returncode}\n{yt_result.stdout.decode(locale.getencoding())}\n{yt_result.stderr.decode(locale.getencoding())}")
    return ""

def parse_yt_file_info( yt_file_line ):
  original_line = yt_file_line.strip()
  match_result = re.search(r"^(\d+) *([0-9a-zA-Z]+) *(\d+x\d+|audio only) *(\d+p|tiny|DASH audio|DASH video) *(\d+k) , (.*)$", original_line)
  if match_result == None:
    return {}
  matches = match_result.groups()

  pixels = 0
  if (matches[3] == "tiny" or matches[3] == "DASH audio"):
    pixels = 0
  elif matches[3] == "DASH video":
    pixels = int(matches[2].split("x")[1])
  else:
    pixels = int(matches[3].rstrip("p"))

  return {
    "original": original_line,
    "format code": matches[0],
    "extension": matches[1],
    "resolution": "0x0" if matches[2] == "audio only" else matches[2],
    "p": pixels,
    "k": int(matches[4].rstrip("k")),
    "note": matches[5],
    "best": matches[5].find("(best)") >= 0,
    "video only": matches[5].find("video only") >= 0,
    "DASH": ("DASH" in matches[3]),   # see https://de.wikipedia.org/wiki/Dynamic_Adaptive_Streaming_over_HTTP
  }

def convert_yt_files_to_info_list( yt_files_result ):
  stream_files = []
  relevant = False
  for line in yt_files_result.strip().split("\n"):
    if line == '':
      # skip empty lines
      continue
    if not relevant and line.startswith("format code"):
      # indicate next line contains infos
      relevant = True
      continue
    elif relevant == False:
      # skip intro lines
      continue
    info = parse_yt_file_info(line)
    if len(info) == 0:
      log(f"ERROR: could not match line: '{line.strip()}'")
      continue
    stream_files.append(info)
  return stream_files

def select_audio_video( stream_files ):
  # filter for resolution and mp4 files
  filtered_list = [ f for f in stream_files if (f["p"] <= max_video_resolution_p and f["extension"] == "mp4" and not f["video only"]) ]

  # sort first for best, then for max resolution and finally for max bitrate (all highest value first)
  # Note: for sorting multiple values see https://stackoverflow.com/a/20145873
  filtered_list.sort(key = lambda f: (f["best"], f["p"], f["k"]), reverse=True)

  if len(filtered_list) >= 1:
    return filtered_list[0]
  else:
    return {}

def select_background_video( stream_files ):
  # filter for resolution and mp4 files
  filtered_list = [ f for f in stream_files if (f["p"] <= max_video_resolution_p and f["extension"] == "mp4") ]

  # sort first for max resolution and then for max bitrate (all highest value first)
  filtered_list.sort(key = lambda f: (f["p"], f["k"]), reverse=True)
  # Note: for sorting multiple values see https://stackoverflow.com/a/20145873

  if len(filtered_list) >= 1:
    return filtered_list[0]
  else:
    return {}

# print line on console that will be overwritten by next print
def print_temporary( message ):
  global last_temp_message_length
  # Note: any negative multiplier will result in empty string
  spaces_to_cover_last_line = " " * ( last_temp_message_length - len(message) )
  # output to be overwritten, see https://stackoverflow.com/a/51339999
  print(f". {message}{spaces_to_cover_last_line}", end='\r')
  last_temp_message_length = len(message)

def print_fail( message ):
  global last_temp_message_length
  # Note: any negative multiplier will result in empty string
  spaces_to_cover_last_line = " " * ( last_temp_message_length - len(message) )
  # output to be overwritten, see https://stackoverflow.com/a/51339999
  print(f"{crossmark} {message}{spaces_to_cover_last_line}")
  last_temp_message_length = len(message)

def print_success( message ):
  global last_temp_message_length
  # Note: any negative multiplier will result in empty string
  spaces_to_cover_last_line = " " * ( last_temp_message_length - len(message) )
  # output to be overwritten, see https://stackoverflow.com/a/51339999
  print(f"{checkmark} {message}{spaces_to_cover_last_line}")
  last_temp_message_length = len(message)

#########################################################
## MAIN
#########################################################
log( f"running {sys.argv[0]} in Version {VERSION}")
options = parse_args()
songs = get_valid_song_list( options['source dir'] )

print("\nGeneriere Songs-Verzeichnisse")

counter = 0
for song in songs:
  log( f"{song['name']}" )
  counter += 1
  # get filelist from video stream
  print_temporary(f"{counter}/{len(songs)} {song['name']}: lade Video-Dateiliste")

  yt_files_result = get_yt_download_files( song['url'] )
  stream_files = convert_yt_files_to_info_list( yt_files_result )
  if len(stream_files) == 0:
    print_fail(f"{counter}/{len(songs)} {song['name']}: keine Video-Dateien gefunden")
    continue

  # check which files to download from all file infos
  print_temporary(f"{counter}/{len(songs)} {song['name']}: suche optimale Videos")
  video_file_4_audio = select_audio_video( stream_files )
  if len(video_file_4_audio) == 0:
    print_fail(f"{counter}/{len(songs)} {song['name']}: keine Video für Audio-Extraktion geeignet")
    continue
  log( f"chosen file for audio extraction:\n{video_file_4_audio}")

  video_file_4_bg = select_background_video( stream_files )
  if len(video_file_4_bg) == 0:
    print_fail(f"{counter}/{len(songs)} {song['name']}: keine Video für den Hintergrund geeignet")
    continue
  log( f"chosen file for background video:\n{video_file_4_bg}")

  # create song directory
  song['output directory'] = os.path.join(".", song['name'])
  if os.path.isdir(song['output directory']):
    print_fail(f"{counter}/{len(songs)} {song['name']}: Ausgabe-Verzeichnis existiert bereits")
    continue
  os.mkdir(song['output directory'])

  # download videos
  outfile_video_for_audio = f"{song['name']} {video_file_4_audio['p']}p.{video_file_4_audio['extension']}"
  print_temporary(f"{counter}/{len(songs)} {song['name']}: lade '{outfile_video_for_audio}'")
  # just execute dont capture output see https://stackoverflow.com/a/12503246
  command = ['youtube-dl',
             # select file to download
             '-f', video_file_4_audio['format code'],
             # set local filename to save file to
             '-o', os.path.join(song['output directory'],outfile_video_for_audio),
             # get rid of 403 Forbidden Error, see https://stackoverflow.com/a/32105062
             '--rm-cache-dir',
             # url to download from
             song['url']]
  log( ' '.join(command) )
  #subprocess.run(command, stdout=subprocess.DEVNULL)
  retry_count = 0
  success = 0
  while retry_count < DOWNLOAD_RETRIES and not success:
    if retry_count > 0:
      print_temporary(f"{counter}/{len(songs)} {song['name']}: {retry_count+1}. Versuch: lade '{outfile_video_for_audio}'")
      log(f"retrying {retry_count}/{DOWNLOAD_RETRIES} ...")
    # catch stdout and stderr see https://csatlas.com/python-subprocess-run-stdout-stderr/
    yt_result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    success = (yt_result.returncode == 0)
    if not success:
      # Note: youtube-dl returns in locale encoding (Windows: 'cp1252')
      log(f"Error:\n{yt_result.returncode}\n{yt_result.stdout.decode(locale.getencoding())}\n{yt_result.stderr.decode(locale.getencoding())}")
      retry_count += 1
  if not success:
    print_fail(f"{counter}/{len(songs)} {song['name']}: kein Erfolg nach {retry_count} Versuchen -> überspringe Song")
    log(f"kein Erfolg nach {retry_count} Versuchen -> überspringe Song")
    # TODO: remove song['output directory']
    continue
  else:
    # Note: stdout contains overwrites of same line (= multiple lines separated by \r)
    # Note: youtube-dl returns in locale encoding (Windows: 'cp1252')
    log( yt_result.stdout.decode(locale.getencoding()).strip().split("\r")[-1].strip() )

  outfile_video_for_bg = f"{song['name']} {video_file_4_bg['p']}p.{video_file_4_bg['extension']}"
  if video_file_4_audio != video_file_4_bg:
    print_temporary(f"{counter}/{len(songs)} {song['name']}: lade '{outfile_video_for_bg}'")
    # just execute dont capture output see https://stackoverflow.com/a/12503246
    command = ['youtube-dl',
               # select file to download
               '-f', video_file_4_bg['format code'],
               # set local filename to save file to
               '-o', os.path.join(song['output directory'], outfile_video_for_bg),
               # get rid of 403 Forbidden Error, see https://stackoverflow.com/a/32105062
               '--rm-cache-dir',
               # url to download from
               song['url']]
    log( ' '.join(command) )
    #subprocess.run(command, stdout=subprocess.DEVNULL)
    retry_count = 0
    success = 0
    while retry_count < DOWNLOAD_RETRIES and not success:
      if retry_count > 0:
        print_temporary(f"{counter}/{len(songs)} {song['name']}: {retry_count+1}. Versuch: lade '{outfile_video_for_audio}'")
        log(f"retrying {retry_count}/{DOWNLOAD_RETRIES} ...")
      # catch stdout and stderr see https://csatlas.com/python-subprocess-run-stdout-stderr/
      yt_result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      success = (yt_result.returncode == 0)
      if not success:
        print_temporary(f"{counter}/{len(songs)} {song['name']}: kein Erfolg nach {retry_count} Versuchen -> überspringe Song")
        # Note: youtube-dl returns in locale encoding (Windows: 'cp1252')
        log(f"Error:\n{yt_result.returncode}\n{yt_result.stdout.decode(locale.getencoding())}\n{yt_result.stderr.decode(locale.getencoding())}")
        retry_count += 1
    if not success:
      print_fail(f"{counter}/{len(songs)} {song['name']}: kein Erfolg nach {retry_count} Versuchen -> überspringe Song")
      log(f"kein Erfolg nach {retry_count} Versuchen -> überspringe Song")
      # TODO: remove song['output directory']
      continue
    else:
      # Note: stdout contains overwrites of same line (= multiple lines separated by \r)
      # Note: youtube-dl returns in locale encoding (Windows: 'cp1252')
      log( yt_result.stdout.decode(locale.getencoding()).strip().split("\r")[-1].strip() )

  # extract mp3 file
  outfile_mp3 = f"{song['name']}.mp3"
  print_temporary(f"{counter}/{len(songs)} {song['name']}: extrahiere mp3")
  command = ['ffmpeg', '-i', os.path.join(song['output directory'], outfile_video_for_audio), '-c:v', 'copy', '-c:a', 'libmp3lame', '-q:a', '4', os.path.join(song['output directory'], outfile_mp3)]
  log( ' '.join(command) )
  # Note: ffmpeg seems to write out on stderror, so surpress stdout and stderr
  subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

  # move files from source directory to song directory
  # rename / moving files, see https://stackoverflow.com/a/8858026
  print_temporary(f"{counter}/{len(songs)} {song['name']}: kopiere Ausgangsdateien")
  
  outfile_original_txt = re.sub(r"\.txt$", ".ori", os.path.basename(song['files']['txt']), 1)
  os.rename( song['files']['txt'], os.path.join(song['output directory'], outfile_original_txt) )

  if "info" in song['files']:
    outfile_info = os.path.basename(song['files']['info'])
    os.rename( song['files']['info'], os.path.join(song['output directory'], outfile_info) )

  outfile_cover = os.path.basename(song['files']['cover'])
  os.rename( song['files']['cover'], os.path.join(song['output directory'], outfile_cover) )

  outfile_url = os.path.basename(song['files']['url'])
  os.rename( song['files']['url'], os.path.join(song['output directory'], outfile_url) )

  # re-create .txt file by updating #VIDEO, #MP3 and #COVER in .txt file
  print_temporary(f"{counter}/{len(songs)} {song['name']}: schreibe .txt Datei neu")
  ori_txt_content = []
  possible_input_encodings = ["utf-8", "cp1252", "latin1"]
  ori_text_read_success = False
  for enc in possible_input_encodings:
    log(enc)
    try:
      with open(os.path.join(song['output directory'], outfile_original_txt), mode="r", encoding=enc) as f:
        ori_txt_content = [l.rstrip() for l in f.readlines()]
      # take this result
      ori_text_read_success = True
      log( f"original txt encoding was '{enc}'")
      break
    except UnicodeDecodeError as e:
      log( e ) # and try next encoding
  if not ori_text_read_success:
    print_fail(f"{counter}/{len(songs)} {song['name']}: konnte Encoding der txt Datei nicht lesen")
    log(f"could not read encoding")
    continue

  new_txt_content = []
  for line in ori_txt_content:
    if line.startswith("#MP3"):
      new_txt_content.append(f"#MP3:{outfile_mp3}")
      new_txt_content.append(f"#COVER:{outfile_cover}")
      new_txt_content.append(f"#VIDEO:{outfile_video_for_bg}")
    # remove lines containing the following Tags
    elif line.startswith("#COVER"):
      continue
    elif line.startswith("#VIDEO"):
      continue
    elif line.startswith("#VIDEOGAP"):
      continue
    else:
      new_txt_content.append(line)

  outfile_txt = f"{song['name']}.txt"
  with open(os.path.join(song['output directory'], outfile_txt), mode="w", encoding="utf-8") as f:
    f.write("\n".join(new_txt_content)) # f.write will automatically convert "\n" to OS Line-Separator

  print_success(f"{counter}/{len(songs)} {song['name']}")

print("fertig")
log("fertig")