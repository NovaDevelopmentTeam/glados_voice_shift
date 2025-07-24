# -*- coding: utf-8 -*-
import os
import sys
import subprocess
import time
import threading
import traceback
from ctypes import *
import pyautogui
from PIL import Image, ImageGrab

# === Setup ===

script_dir = os.path.dirname(os.path.abspath(__file__))

def relpath(*parts):
    return os.path.join(script_dir, *parts)

# Melodyne beenden, falls noch offen
subprocess.Popen(['taskkill', '/F', '/T', '/IM', 'Melodyne.exe']).wait()

PUL = POINTER(c_ulong)

class KeyBdInput(Structure):
    _fields_ = [
        ("wVk", c_ushort),
        ("wScan", c_ushort),
        ("dwFlags", c_ulong),
        ("time", c_ulong),
        ("dwExtraInfo", PUL)
    ]

class HardwareInput(Structure):
    _fields_ = [
        ("uMsg", c_ulong),
        ("wParamL", c_short),
        ("wParamH", c_ushort)
    ]

class MouseInput(Structure):
    _fields_ = [
        ("dx", c_long),
        ("dy", c_long),
        ("mouseData", c_ulong),
        ("dwFlags", c_ulong),
        ("time", c_ulong),
        ("dwExtraInfo", PUL)
    ]

class Input_I(Union):
    _fields_ = [
        ("ki", KeyBdInput),
        ("mi", MouseInput),
        ("hi", HardwareInput)
    ]

class Input(Structure):
    _fields_ = [
        ("type", c_ulong),
        ("ii", Input_I)
    ]

class POINT(Structure):
    _fields_ = [
        ("x", c_ulong),
        ("y", c_ulong)
    ]

streamrunners = []

def flushrunners():
    print('Flushing streamrunners.', file=sys.stderr)
    for s in streamrunners:
        print(s.content, file=sys.stderr)
        s.content = ''
    sys.stderr.flush()

def catch(t, v, trace):
    flushrunners()
    print('\n'.join(traceback.format_exception(t, v, trace)), file=sys.stderr)
    sys.stderr.flush()
    sys.exit(1)

sys.excepthook = catch

class streamrunner(threading.Thread):
    def __init__(self, stream, prefix='>'):
        super().__init__()
        self.stream = stream
        self.prefix = prefix
        self.content = 'Begin streamrun: ' + self.prefix + '\n'
        streamrunners.append(self)

    def run(self):
        try:
            for i in self.stream:
                line = i.strip()
                print(line, file=sys.stderr)
                try:
                    self.content += f'{self.prefix} [{time.strftime("%H:%M:%S")}] {line}\n'
                except Exception:
                    self.content += f'Error in streamrunner, {len(i)} bytes omitted\n'
        except Exception:
            self.content += 'Error while looping streamrunner.\n'
        self.content += 'End streamrun: ' + self.prefix + '\n'
        try:
            self.stream.close()
        except Exception:
            pass

log_path = relpath('log.txt')
logFile = open(log_path, 'w', encoding='utf-8')

def say(*args):
    global logFile
    s = ' '.join(str(i) for i in args).strip()
    print(s)
    logFile.write(s + '\r\n')
    logFile.flush()
    sys.stdout.flush()
    return s

def sleep(t, stfu=False):
    slowfactor = 3.5
    if not stfu:
        say('Sleeping for', t, 'seconds with slowness factor', slowfactor)
    time.sleep(t * slowfactor)

def ensurealt(delay=.1):
    sleep(delay)
    say('Ensuring ALT is not pressed...')
    pyautogui.keyDown('alt')
    time.sleep(1)
    pyautogui.keyUp('alt')
    sleep(delay)

def mouse(x, y):
    orig = POINT()
    windll.user32.GetCursorPos(byref(orig))
    windll.user32.SetCursorPos(x, y)
    return (orig.x, orig.y)

def click(x, y=None, delay=0.1, fixalt=True):
    if y is None and isinstance(x, (tuple, list)):
        return click(x[0], x[1], delay=delay, fixalt=fixalt)
    if fixalt:
        ensurealt()
    m = mouse(x, y)
    if delay:
        sleep(delay, stfu=True)
    FInputs = Input * 2
    extra = c_ulong(0)
    ii_ = Input_I()
    ii_.mi = MouseInput(0, 0, 0, 2, 0, pointer(extra))
    ii2_ = Input_I()
    ii2_.mi = MouseInput(0, 0, 0, 4, 0, pointer(extra))
    x = FInputs((0, ii_), (0, ii2_))
    windll.user32.SendInput(2, pointer(x), sizeof(x[0]))
    return m

def doubleclick(x, y=None, delay=.02):
    click(x, y, delay=0, fixalt=False)
    sleep(delay)
    result = click(x, y, delay=0, fixalt=False)
    sleep(delay * 2)
    return result

def find(findimg, insideimg=None, fail=False, clickpoint=False):
    r = subfind(findimg, insideimg=insideimg)
    if r is None:
        if fail:
            say('Finding fail:', fail)
            sys.exit(1)
        return None
    if clickpoint:
        click(r)
    return r

def subfind(findimg, insideimg=None):
    if isinstance(findimg, (tuple, list)):
        for i in findimg:
            r = subfind(i, insideimg=insideimg)
            if r is not None:
                return r
        return None
    if isinstance(findimg, dict):
        for k, v in findimg.items():
            r = subfind(relpath(k), insideimg=insideimg)
            if r is not None:
                return (r[0] + v[0], r[1] + v[1])
        return None
    if isinstance(findimg, str):
        findimg = Image.open(relpath(findimg)).convert('RGB')
    else:
        findimg = findimg.convert('RGB')

    if insideimg is None:
        insideimg = ImageGrab.grab().convert('RGB')
    elif isinstance(insideimg, str):
        insideimg = Image.open(relpath(insideimg)).convert('RGB')
    else:
        insideimg = insideimg.convert('RGB')

    findload = findimg.load()
    insideload = insideimg.load()
    w_limit = insideimg.size[0] - findimg.size[0]
    h_limit = insideimg.size[1] - findimg.size[1]

    for x in range(w_limit):
        for y in range(h_limit):
            match = True
            for x2 in range(findimg.size[0]):
                for y2 in range(findimg.size[1]):
                    p1 = findload[x2, y2]
                    p2 = insideload[x + x2, y + y2]
                    if abs(p1[0] - p2[0]) > 8 or abs(p1[1] - p2[1]) > 8 or abs(p1[2] - p2[2]) > 8:
                        match = False
                        break
                if not match:
                    break
            if match:
                say('Found point at', (x, y))
                return (x, y)
    return None

# Melodyne starten
p = subprocess.Popen(
    [r'C:\Program Files\Celemony\Melodyne 5\Melodyne.exe'],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

streamrunner(p.stdout, prefix='Melodyne>').start()
streamrunner(p.stderr, prefix='Melodyne>2').start()

sleep(11)
ensurealt()
pyautogui.press('esc')
find({'Cancel.png': (8, 8)}, clickpoint=True)
sleep(3)
pyautogui.hotkey('ctrl', 'o')
ensurealt()
sleep(4)

soundfile = None
sounddir = relpath('files')
for f in os.listdir(sounddir):
    if f.lower().endswith('.glados.wav'):
        soundfile = f
        break

if soundfile is None:
    say('No sound file found.')
    sys.exit(1)

say('Sound file is:', soundfile)
sleep(1)
ensurealt()
pyautogui.press('backspace')
sleep(1)
pyautogui.keyDown('shift')
pyautogui.press('z')
pyautogui.keyUp('shift')
sleep(1)
pyautogui.typewrite(f':\\files\\{soundfile}', interval=0.01)
pyautogui.press('enter')
ensurealt()
sleep(8)
pyautogui.press('s')
sleep(1)
pyautogui.press('p')
sleep(0.5)
pyautogui.press('a')
sleep(1)

pitchpoint = find({
    'PitchDialog.png': (5, 59),
    'PitchDialog2.png': (1, 36)
}, clickpoint=True, fail='Pitch point')

sleep(0.5)
click(pitchpoint[0] + 375, pitchpoint[1] + 40)
sleep(5)
ensurealt()
pyautogui.press('m')
sleep(0.5)
pyautogui.press('s')
sleep(2)
pyautogui.press('i')
sleep(4)

imgbefore = ImageGrab.grab().convert('RGB')
beforeload = imgbefore.load()
sleep(4)
pyautogui.press('s')
sleep(12)
imgafter = ImageGrab.grab().convert('RGB')
afterload = imgafter.load()
sleep(2)

notepixel = None
for x in range(imgbefore.size[0]):
    for y in range(imgbefore.size[1]):
        p = beforeload[x, y]
        p2 = afterload[x, y]
        if p2[0] > 160 and p2[0] > p[1] * 2 and p2[0] > p[2] * 2:
            if p != p2:
                notepixel = (x, y)
                say('Found note pixel:', notepixel)
                break
    if notepixel is not None:
        break

if notepixel is None:
    say('Could not find note pixel.')
    sys.exit(1)

say('Found note pixel:', notepixel)
doubleclick(notepixel[0], notepixel[1])
sleep(5)
pyautogui.press('f')
sleep(1)

formantpoint = find({
    'Formant.png': (84, 7),
    'Formant2.png': (83, 5)
}, fail='Formant point')

doubleclick(formantpoint)
sleep(0.2)
pyautogui.typewrite('100')
pyautogui.press('enter')
sleep(5)
pyautogui.hotkey('ctrl', 'e')
ensurealt()
sleep(1)

frequencypoint = find('WaveFrequency.png')
if frequencypoint is not None:
    click(frequencypoint[0], frequencypoint[1])
    time.sleep(0.5)
    mouse(frequencypoint[0] + 1, frequencypoint[1] + 1)
    mouse(frequencypoint[0] + 2, frequencypoint[1] + 2)
    freq44100 = find('44100kHz.png')
    if freq44100 is not None:
        click(freq44100[0] + 25, freq44100[1] + 6)
    else:
        say('WARNING: No 44100 kHz point found.')
        click(frequencypoint[0], frequencypoint[1])
    time.sleep(1)
else:
    say('WARNING: No frequency point found.')

saveaspoint = find('SaveAs.png')
if saveaspoint is None:
    say('Could not find "save as" point.')
    sys.exit(1)

click(saveaspoint[0] + 53, saveaspoint[1] + 12)
sleep(3)
ensurealt()
pyautogui.press('backspace')
sleep(1)
pyautogui.keyDown('shift')
pyautogui.press('z')
pyautogui.keyUp('shift')
sleep(1)
pyautogui.typewrite(f':\\files\\ok-{soundfile[:-11]}.done.wav')
pyautogui.press('enter')
sleep(17.5)
pyautogui.press('q')
sleep(3)
ensurealt()
pyautogui.press('right')
pyautogui.press('right')
pyautogui.press('enter')
sleep(5)
flushrunners()
subprocess.Popen(['taskkill', '/F', '/T', '/IM', 'Melodyne.exe']).wait()
logFile.close()
