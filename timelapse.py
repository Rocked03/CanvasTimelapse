import json, PIL, datetime, copy, cv2, numpy
from PIL import Image, ImageDraw


x = [1, 500]
y = [1, 500]
scale = 4 # must be int >=1
fps = 60
times = [1651920900, 1652526300]
duration = None # 150 # seconds (doesn't count additional hangtime)
frequency = 150 * 1000 # milliseconds
hangtime = 5 # seconds


# x = [50, 142]
# y = [296, 349]
# scale = 10
# duration = 30
# times = [1651921200, 1652180400]

baseimage = '500x500 logo.png'
dbcoloursdefault = '2022_colours_default.json'
dbcolourspartner = '2022_colours_partner.json'
dbhistory = '2022_history_clean.json'

basetime = 1651920900
times[0] = times[0] if times[0] >= basetime else basetime
timesms = [i * 1000 for i in times]
width = x[1]-x[0]+1
height = y[1]-y[0]+1
size = ((x[1]-x[0]+1)*scale, (y[1]-y[0]+1)*scale)


print("Loading colours...")
colours = {}
with open(dbcoloursdefault) as f:
    data = json.load(f)
    for i in data:
        colours[i['code']] = tuple(i['rgb'])
with open(dbcolourspartner) as f:
    data = json.load(f)
    for i in data:
        colours[i['tag']] = tuple(i['rgb'])
print("Loaded colours.\n")


print("Processing timestamps...")
timestamps = []
if duration:
    interval = (timesms[1] - timesms[0]) / (duration * fps)
    nexttime = timesms[0]
    for i in range(duration * fps):
        nexttime += interval
        timestamps.append(int(round(nexttime, 0)))
else:
    nexttime = timesms[0] + frequency
    while nexttime < timesms[1]:
        timestamps.append(nexttime)
        nexttime += frequency
    timestamps.append(timesms[1])
print("Processed timestamps.\n")


frames = []

print("Creating base...")
base = Image.new('RGBA', size, colours['blank'])
if baseimage:
    with Image.open(baseimage) as im:
        newim = Image.new('RGBA', size)
        draw = ImageDraw.Draw(newim)
        for xi in range(width-1):
            for yi in range(height-1):
                xii = xi+x[0]-1
                yii = yi+y[0]-1
                colour = im.getpixel((xii, yii))
                if colour != (0, 0, 0, 0):
                    topleft = ((xii * scale) - 1, (yii * scale) - 1)
                    bottomright = ((xii - 1) * scale, (yii - 1) * scale)
                    draw.rectangle([topleft, bottomright], fill=colour)
        im = newim
        base.paste(im, mask=im)
frames.append(base)
print("Created base.\n")


print("Loading and saving history...")
starttime = datetime.datetime.utcnow()

history = {}
with open(dbhistory) as f:
    data = json.load(f)
    print("Loaded history.")
    for i in data:
        t = int(i['created']['$date']['$numberLong'])
        if basetime * 1000 <= t <= timesms[1]:
            coords = i['coords']
            if x[0] <= coords[0] <= x[1] and y[0] <= coords[1] <= y[1]:
                if t not in history.keys():
                    history[t] = []
                history[t].append({'coords': tuple(coords), 'colour': i['colour']})


timetaken = (datetime.datetime.utcnow() - starttime).total_seconds()
print(f"Saved history. {len(history.keys())} timestamps. {sum([len(i) for i in history.values()])} total points. ({timetaken}s)\n")

print("Generating frames...")
starttime = datetime.datetime.utcnow()

currenttime = 0
im = Image.new('RGBA', size, (0, 0, 0, 0))
draw = ImageDraw.Draw(im)
for k in sorted(history.keys()):
    while k > timestamps[currenttime]:
        frames.append(copy.copy(im))
        im = Image.new('RGBA', size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(im)
        currenttime += 1

    for p in history[k]:
        coords = p['coords']
        coords = (coords[0] - x[0] + 1, coords[1] - y[0] + 1)
        topleft = tuple((i - 1) * scale for i in coords)
        bottomright = tuple((i * scale) - 1 for i in coords)
        draw.rectangle([topleft, bottomright], fill=colours[p['colour']])
frames.append(copy.copy(im))

timetaken = (datetime.datetime.utcnow() - starttime).total_seconds()
print(f"Generated frames. {len(frames)} total. ({timetaken}s)\n")


print("Combining frames...")
starttime = datetime.datetime.utcnow()

combinedframes = []

bg = Image.new('RGBA', size, (47, 49, 54, 255))
blank = Image.new('RGBA', size, (0, 0, 0, 0))
currentframe = Image.new('RGBA', size, (0, 0, 0, 0))
for f in frames:
    mask = copy.copy(f)
    r, g, b, alpha = mask.split()
    alpha = alpha.point(lambda p: 0 if p==0 else 255)
    mask = Image.merge("RGBA", (r, g, b, alpha))

    currentframe.paste(blank, mask=mask)
    currentframe.paste(f, mask=f)

    full = copy.copy(bg)
    full.alpha_composite(currentframe)

    combinedframes.append(full)

del frames

timetaken = (datetime.datetime.utcnow() - starttime).total_seconds()
print(f"Combined frames. ({timetaken}s)\n")


print("Creating and saving video...")
starttime = datetime.datetime.utcnow()

video = cv2.VideoWriter(f"timelapse_({x[0]},{y[0]})-({x[1]},{y[1]})_x{scale}_{times[0]}-{times[1]}.mp4", cv2.VideoWriter_fourcc(*'mp4v'), fps, size)

for f in combinedframes:
    video.write(cv2.cvtColor(numpy.array(f), cv2.COLOR_RGB2BGR))

for i in range(hangtime * fps):
    video.write(cv2.cvtColor(numpy.array(combinedframes[-1]), cv2.COLOR_RGB2BGR))

timetaken = (datetime.datetime.utcnow() - starttime).total_seconds()
print(f"Created video. ({timetaken}s)")

video.release()
print("Saved video.")