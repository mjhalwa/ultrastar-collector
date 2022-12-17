"""
Mini-Skript to shift all beats of all lines after a linebreak in a txt#
file by a number of beats upwards (+) or downwards (-)

1. filepath  path to txt file
2. shift     positive for later, negative for earlier

Outputs lines with shifted beats

Note: scans files with utf-8 encoding
"""
import sys

print(len(sys.argv))
if len(sys.argv) != 3:
  print(f"python {sys.argv[0]} FILENAME BEATS")
  print("Error: 2 Arguments required")
  sys.exit(1)

filename=sys.argv[1]
beats_later = int(sys.argv[2])

on = False
with open(filename, encoding = 'utf-8') as f:
  for line in f:
    if not on and line == "\n":
      on = True
    elif on:
      cols = line.strip().split(" ")
      cols[1] = f'{int(cols[1]) + beats_later}'
      print(" ".join(cols))
