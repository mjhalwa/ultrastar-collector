import sys
import os
import glob 
import urllib.parse
import subprocess
import re
from datetime import datetime

VERSION = "0.1.0"

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
    with open( re.sub(r"\.py$", ".log", sys.argv[0], 1), "a" ) as f:
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
  with open( urlfile ) as f:
    lines = [line.strip() for line in f.readlines()]
  for line in lines:
    if line.startswith("URL"):
      return line.split("=")[1].strip()
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

def get_stream_files_infos():
  # # TODO: remove this contion block and keep ELSE when finishing DEBUGGING
  # if DEBUG:
  #   with open("./examples/yt-download-zoomania-files.out") as f:
  #     yt_result = ''.join(f.readlines())
  # else:
  #   # execute and get process console output see https://stackoverflow.com/a/4760517
  #   yt_result = subprocess.run(['youtube-dl', '-F', song['url']], stdout=subprocess.PIPE).stdout.decode()
  # execute and get process console output see https://stackoverflow.com/a/4760517
  command = ['youtube-dl', '-F', song['url']]
  log( ' '.join(command) )
  yt_result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  success = (yt_result.returncode == 0)
  if success:
    log( f"Ausgabe:\n{yt_result.stdout.decode()}")
  else:
    log(f"kein Erfolg:\n{yt_result.returncode}\n{yt_result.stdout.decode()}\n{yt_result.stderr.decode()}")
    return []

  stream_files = []
  relevant = False
  for line in yt_result.stdout.decode().strip().split("\n"):
    if not relevant and line.startswith("format code"):
      # indicate next line contains infos
      relevant = True
      continue
    elif relevant == False:
      # skip intro lines
      continue
    
    # skip empty lines
    if line == '':
      continue

    match_result = re.search(r"^(\d+) *([0-9a-zA-Z]+) *(\d+x\d+|audio only) *(\d+p|tiny) *(\d+k) , (.*)$", line.strip())
    if match_result == None:
      log(f"ERROR: could not match line: '{line.strip()}'")
      continue
    matches = match_result.groups()
    info = {
      "format code": matches[0],
      "extension": matches[1],
      "resolution": "0x0" if matches[2] == "audio only" else matches[2],
      "p": 0 if matches[3] == "tiny" else int(matches[3].rstrip("p")),
      "k": int(matches[4].rstrip("k")),
      "note": matches[5],
      "best": matches[5].find("(best)") >= 0,
      "video only": matches[5].find("video only") >= 0
    }
    stream_files.append(info)

  return stream_files

def get_audio_video( stream_files ):
  # filter for resolution and mp4 files
  filtered_list = [ f for f in stream_files if (f["p"] <= max_video_resolution_p and f["extension"] == "mp4" and not f["video only"]) ]

  # sort first for best, then for max resolution and finally for max bitrate (all highest value first)
  # Note: for sorting multiple values see https://stackoverflow.com/a/20145873
  filtered_list.sort(key = lambda f: (f["best"], f["p"], f["k"]), reverse=True)

  if len(filtered_list) >= 1:
    return filtered_list[0]
  else:
    return {}

def get_background_video( stream_files ):
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
  print(f"{message}{spaces_to_cover_last_line}", end='\r')
  last_temp_message_length = len(message)


#########################################################
## MAIN
#########################################################
options = parse_args()
songs = get_valid_song_list( options['source dir'] )

print("\nGeneriere Songs-Verzeichnisse")

counter = 0
for song in songs:
  log( f"{song['name']}" )
  counter += 1
  # get filelist from video stream
  print_temporary(f". {counter}/{len(songs)} {song['name']}: lade Video-Dateiliste")
  stream_files = get_stream_files_infos()
  if len(stream_files) == 0:
    print(f"{crossmark} {counter}/{len(songs)} {song['name']}: keine Video-Dateien gefunden")
    continue

  # check which files to download from all file infos
  print_temporary(f". {counter}/{len(songs)} {song['name']}: suche optimale Videos")
  video_file_4_audio = get_audio_video( stream_files )
  if len(video_file_4_audio) == 0:
    print(f"{crossmark} {counter}/{len(songs)} {song['name']}: keine Video für Audio-Extraktion geeignet")
    continue
  log( f"chosen file for audio extraction:\n{video_file_4_audio}")

  video_file_4_bg = get_background_video( stream_files )
  if len(video_file_4_bg) == 0:
    print(f"{crossmark} {counter}/{len(songs)} {song['name']}: keine Video für den Hintergrund geeignet")
    continue
  log( f"chosen file for background video:\n{video_file_4_bg}")

  # create song directory
  song['output directory'] = os.path.join(".", song['name'])
  if os.path.isdir(song['output directory']):
    print(f"{crossmark} {counter}/{len(songs)} {song['name']}: Ausgabe-Verzeichnis existiert bereits")
    continue
  os.mkdir(song['output directory'])

  # download videos
  outfile_video_for_audio = f"{song['name']} {video_file_4_audio['p']}p.{video_file_4_audio['extension']}"
  print_temporary(f". {counter}/{len(songs)} {song['name']}: lade '{outfile_video_for_audio}'")
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
      print_temporary(f". {counter}/{len(songs)} {song['name']}: {retry_count+1}. Versuch: lade '{outfile_video_for_audio}'")
      log(f"retrying {retry_count}/{DOWNLOAD_RETRIES} ...")
    # catch stdout and stderr see https://csatlas.com/python-subprocess-run-stdout-stderr/
    yt_result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    success = (yt_result.returncode == 0)
    if not success:
      log(f"Error:\n{yt_result.returncode}\n{yt_result.stdout.decode()}\n{yt_result.stderr.decode()}")
      retry_count += 1
  if not success:
    print(f"{crossmark} {counter}/{len(songs)} {song['name']}: kein Erfolg nach {retry_count} Versuchen -> überspringe Song")
    log(f"kein Erfolg nach {retry_count} Versuchen -> überspringe Song")
    # TODO: remove song['output directory']
    continue
  else:
    # Note: stdout contains overwrites of same line (= multiple lines separated by \r)
    log( yt_result.stdout.decode().strip().split("\r")[-1].strip() )

  outfile_video_for_bg = f"{song['name']} {video_file_4_bg['p']}p.{video_file_4_bg['extension']}"
  if video_file_4_audio != video_file_4_bg:
    print_temporary(f". {counter}/{len(songs)} {song['name']}: lade '{outfile_video_for_bg}'")
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
        print_temporary(f". {counter}/{len(songs)} {song['name']}: {retry_count+1}. Versuch: lade '{outfile_video_for_audio}'")
        log(f"retrying {retry_count}/{DOWNLOAD_RETRIES} ...")
      # catch stdout and stderr see https://csatlas.com/python-subprocess-run-stdout-stderr/
      yt_result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      success = (yt_result.returncode == 0)
      if not success:
        print_temporary(f". {counter}/{len(songs)} {song['name']}: kein Erfolg nach {retry_count} Versuchen -> überspringe Song")
        log(f"Error:\n{yt_result.returncode}\n{yt_result.stdout.decode()}\n{yt_result.stderr.decode()}")
        retry_count += 1
    if not success:
      print(f"{crossmark} {counter}/{len(songs)} {song['name']}: kein Erfolg nach {retry_count} Versuchen -> überspringe Song")
      log(f"kein Erfolg nach {retry_count} Versuchen -> überspringe Song")
      # TODO: remove song['output directory']
      continue
    else:
      # Note: stdout contains overwrites of same line (= multiple lines separated by \r)
      log( yt_result.stdout.decode().strip().split("\r")[-1].strip() )

  # extract mp3 file
  outfile_mp3 = f"{song['name']}.mp3"
  print_temporary(f". {counter}/{len(songs)} {song['name']}: extrahiere mp3")
  command = ['ffmpeg', '-i', os.path.join(song['output directory'], outfile_video_for_audio), '-c:v', 'copy', '-c:a', 'libmp3lame', '-q:a', '4', os.path.join(song['output directory'], outfile_mp3)]
  log( ' '.join(command) )
  # Note: ffmpeg seems to write out on stderror, so surpress stdout and stderr
  subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

  # move files from source directory to song directory
  # rename / moving files, see https://stackoverflow.com/a/8858026
  print_temporary(f". {counter}/{len(songs)} {song['name']}: kopiere Ausgangsdateien")
  
  outfile_original_txt = re.sub(r"\.txt$", ".ori", os.path.basename(song['files']['txt']), 1)
  os.rename( song['files']['txt'], os.path.join(song['output directory'], outfile_original_txt) )

  if "info" in song['files']:
    outfile_info = os.path.basename(song['files']['info'])
    os.rename( song['files']['info'], os.path.join(song['output directory'], outfile_info) )

  outfile_cover = os.path.basename(song['files']['cover'])
  os.rename( song['files']['cover'], os.path.join(song['output directory'], outfile_cover) )

  outfile_url = os.path.basename(song['files']['url'])
  os.rename( song['files']['url'], os.path.join(song['output directory'], outfile_url) )

  # TODO: re-create .txt file by updating #VIDEO, #MP3 and #COVER in .txt file
  print_temporary(f". {counter}/{len(songs)} {song['name']}: schreibe .txt Datei neu")
  ori_txt_content = []
  with open(os.path.join(song['output directory'], outfile_original_txt), "r") as f:
    ori_txt_content = [l.rstrip() for l in f.readlines()]

  new_txt_content = []
  for line in ori_txt_content:
    if line.startswith("#MP3"):
      new_txt_content.append(f"#MP3:{outfile_mp3}")
      new_txt_content.append(f"#COVER:{outfile_cover}")
      new_txt_content.append(f"#VIDEO:{outfile_video_for_bg}")
    elif line.startswith("#COVER"):
      continue
    elif line.startswith("#VIDEO"):
      continue
    else:
      new_txt_content.append(line)

  outfile_txt = f"{song['name']}.txt"
  with open(os.path.join(song['output directory'], outfile_txt), "w") as f:
    f.write("\n".join(new_txt_content)) # f.write will automatically convert "\n" to OS Line-Separator

  print(f"{checkmark} {counter}/{len(songs)} {song['name']}")

print("fertig")
log("fertig")