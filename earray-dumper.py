#!/usr/bin/env python
import freenect, sys, signal, time
import matplotlib.pyplot as mp
import frame_convert
from tables import *

dump_file = openFile(sys.argv[1], "w")
keep_running = True

frame_number = 1

dep_data = dump_file.createEArray("/", "dep", UInt8Atom(), (480, 640, 0) )
rgb_data = dump_file.createEArray("/", "rgb", UInt8Atom(), (480, 640, 3, 0) )

rgb_temp = None
rgb_time = time.time()

def log_dep(dev, data, timestamp):
    global rgb_data, dep_data, frame_number, rgb_time

    data = frame_convert.pretty_depth(data)[:,:,None]
    dep_data.append( data )
    rgb_data.append( rgb_temp )
    frame_number += 1
    print "Writing frame", frame_number, 
    print "\tColor data is %ims stale" % ((time.time() - rgb_time)*1000)
    

def log_rgb(dev, data, timestamp):
    global rgb_temp, time, rgb_time
    rgb_temp = data[:,:,:,None]
    rgb_time = time.time()

def body(*args):
    if not keep_running:
        raise freenect.Kill

def handler(signum, frame):
    global keep_running
    keep_running = False


print('Press Ctrl-C in terminal to stop')
signal.signal(signal.SIGINT, handler)
freenect.runloop(depth=log_dep, video=log_rgb, body=body)
