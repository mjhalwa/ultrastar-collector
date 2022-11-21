import os
import subprocess
import locale
import json


if not os.path.isdir('simple_norm'):
  os.mkdir('simple_norm')
if not os.path.isdir('dual_norm'):
  os.mkdir('dual_norm')


for file in os.listdir('input'):
  print(f'{file}: simple...')

  #simple
  #> ffmpeg -i input.wav -filter:a loudnorm output.wav
  command = ['ffmpeg', '-i', f'input/{file}', '-filter:a', 'loudnorm', f'simple_norm/{file}']
  result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


  print(f'{file}: dual...')
  #dual
  #> ffmpeg -i input.mp4 -af loudnorm=I=-23:LRA=7:tp=-2:print_format=json -f null -
  #> ffmpeg -i input.mp4 -af loudnorm=I=-23:LRA=7:tp=-2:measured_I=-30:measured_LRA=1.1:measured_tp=-11 04:measured_thresh=-40.21:offset=-0.47 -ar 48k -y output.mp4
  command = ['ffmpeg', '-i', f'input/{file}', '-af', 'loudnorm=I=-23:LRA=7:tp=-2:print_format=json', '-f', 'null', '-']
  result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

  analysis = result.stderr.decode(locale.getencoding()).split('\r\n')[-13:]
  print('\r\n'.join(analysis))

  analysis_json = json.loads('\r\n'.join(analysis))

  measured_I = analysis_json['output_i']
  measured_LRA = analysis_json['output_lra']
  measured_tp = analysis_json['output_tp']
  measured_thresh = analysis_json['output_thresh']
  offset = analysis_json['target_offset']

  command = ['ffmpeg', '-i', f'input/{file}', '-af', f'loudnorm=I=-23:LRA=7:tp=-2:measured_I={measured_I}:measured_LRA={measured_LRA}:measured_tp={measured_tp}:measured_thresh={measured_thresh}:offset={offset}', '-ar', '48k', '-y', f'dual_norm/{file}']
  result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

  print(f'{file} done')

print('done')
