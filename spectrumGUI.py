# import libraries
import os
import io
import math
import time
import picamera
from fractions import Fraction
from collections import OrderedDict
#import PIL.Image
import PIL.Image
import PIL.ImageTk
import PIL.ImageDraw
import PIL.ImageFile
import PIL.ImageFont
from tkinter import * 
import tkinter as tk
import cv2
from tkinter import filedialog


# create tkinter object
root = Tk()
# globals
# global wid
# global hgt
# global wid_but

# get screen width and height
wid = root.winfo_screenwidth()
hgt = root.winfo_screenheight()

# set width of button window
wid_but = 140

# root: main window displays images
root.title('Spectrometer')
root.geometry('%dx%d+%d+%d' % (wid-wid_but, hgt, wid_but, 0))
root.configure(bg="black")
frame = Frame(root, bg="blue")
frame.grid(row=0, column=0, sticky="nsew")

# side window: displays buttons
butWin = tk.Toplevel(root) # Tk()
butWin.geometry('%dx%d+%d+%d' % (wid_but, hgt, 1, 0))
butWin.configure(bg="white")
Win1 = Frame(butWin)
Win1.grid(row=0, column=0,sticky="nsew")

global name
global camera
global output_filename
camera = picamera.PiCamera()
name = 'test'
output_filename = name + "_chart.png"


# Notes (11/16/20): 

# Fix gui font size (later)
# Add in displayed images (3 images)
# Want to still save csv file? 
# Allow ability for user to define filesave name
# Change colors? 
# How to navigate multiple windows on RPi display? (Back buttons?)

# Notes (2/3/21)
# Need to run with python3


########### FUNCTION DEFINTIONS #######################


#######################################################
# Sub-functions
#######################################################

def get_spectrum_y_bound(pix, x, middle_y, spectrum_threshold, spectrum_threshold_duration):
    c = 0
    spectrum_top = middle_y
    for y in range(middle_y, 0, -1):
        r, g, b = pix[x, y]
        brightness = r + g + b
        if brightness < spectrum_threshold:
            c = c + 1
            if c > spectrum_threshold_duration:
                break
        else:
            spectrum_top = y
            c = 0

    c = 0
    spectrum_bottom = middle_y
    for y in range(middle_y, middle_y * 2, 1):
        r, g, b = pix[x, y]
        brightness = r + g + b
        if brightness < spectrum_threshold:
            c = c + 1
            if c > spectrum_threshold_duration:
                break
        else:
            spectrum_bottom = y
            c = 0

    return spectrum_top, spectrum_bottom

def draw_ticks_and_frequencies(draw, aperture, spectrum_angle, wavelength_factor):
    aperture_height = aperture['h'] / 2
    for wl in range(400, 1001, 50):
        x = aperture['x'] - (wl / wavelength_factor)
        y0 = math.tan(spectrum_angle) * (aperture['x'] - x) + aperture['y']
        draw.line((x, y0 + aperture_height + 5, x, y0 + aperture_height - 5), fill="#fff")
        font = PIL.ImageFont.truetype('/usr/share/fonts/truetype/lato/Lato-Regular.ttf', 12)
        draw.text((x, y0 + aperture_height + 15), str(wl), font=font, fill="#fff")

def wavelength_to_color(lambda2):
    factor = 0.0
    color = [0, 0, 0]
    thresholds = [380, 400, 450, 465, 520, 565, 780]
    for i in range(0, len(thresholds) - 1, 1):
        t1 = thresholds[i]
        t2 = thresholds[i + 1]
        if lambda2 < t1 or lambda2 >= t2:
            continue
        if i % 2 != 0:
            tmp = t1
            t1 = t2
            t2 = tmp
        if i < 5:
            color[i % 3] = (lambda2 - t2) / (t1 - t2)
        color[2 - int(i / 2)] = 1.0
        factor = 1.0
        break

    # Let the intensity fall off near the vision limits
    if 380 <= lambda2 < 420:
        factor = 0.2 + 0.8 * (lambda2 - 380) / (420 - 380)
    elif 600 <= lambda2 < 780:
        factor = 0.2 + 0.8 * (780 - lambda2) / (780 - 600)
    return int(255 * color[0] * factor), int(255 * color[1] * factor), int(255 * color[2] * factor)



#######################################################
# Lower level functions
#######################################################
#
# camera = picamera.PiCamera()
# ON = True
#
# zoom = 1.0
# previewTime = 3
# awbcount = 0
# effectno = 0
# delay = 5
# threshPercent = 1.8
# step = 1
# numImages = 1
# captureCount = 0
# numSav = 0
#
# def prevTime():
# 	global previewTime
# 	previewTime += 1
#         print("Preview time", previewTime, "s")
# 	return previewTime
# 	preview()
#
# def preview():
# 	camera.preview_fullscreen = False
# 	camera.preview_window = (170, -120, 860, 950)
# 	camera.video_stabilization = True
# 	#camera.brightness=w.get()
# 	camera.start_preview()
# 	print "Brightness",camera.brightness
#         camera.contrast=y.get()
#         print "Contrast",camera.contrast
#         #camera.saturation=xy.get()
#         #print "Saturation",camera.saturation
# 	for t in range (previewTime, 0, -1):
# 		camera.brightness = w.get()
#        		time.sleep(1)
#

# def contrast():
# 	camera.contrast = y.get()
#         if camera.contrast < -99:
#                 camera.contrast += 5
#         elif camera.contrast > 99:
#                 camera.contrast -= 5
#         else:
# 		camera.contrast += 5
#         print "Contrast", camera.contrast
#         y.set(camera.contrast)
#
#
#
# contrastButton = Button(root, text="  Contrast   ", command=contrast)
# contrastButton.grid(row=4, column=1)
#
# y = Scale(frame, from_=-50, to=50, resolution=1, orient=HORIZONTAL)
# y.grid(row=10, column=1)
# y.set(camera.contrast)
# print "Contrast", camera.contrast
#
# z = Label(frame, text="Contrast")
# z.grid(row=10, column=0)
#
# previewButton = Button(frame, text="    Preview    ", command=preview)
# previewButton.grid(row=1, column=1)

# Take picture
def take_picture(name, shutter):
    camera.stop_preview()
    print("initialising camera")
    #camera = picamera.PiCamera()
    #camera.preview_fullscreen = False
    #camera.preview_window = (170, -120, 860, 950)
    try:
      #  camera.start_preview()
        print("allowing camera to warmup")
        camera.vflip = True
        #camera.framerate = Fraction(1, 3)
        camera.shutter_speed = shutter
        camera.iso = 1000
        camera.exposure_mode = 'off'
        camera.awb_mode = 'off'
        camera.awb_gains = (1, 1)
        #time.sleep(3)
        time.sleep(3)
        print("capturing image")
        camera.capture(name, resize=(wid - wid_but, hgt))#(wid - wid_but, hgt) (1296, 972)
        #camera.stop_preview()
    finally:
        h = 5
    return name

# def take_video():
#     camera = picamera.PiCamera()
#     try:
#         camera.capture(name, resize=(1296, 972))
#     finally:
#         camera.close()
#     return name
#
# Find aperture
 
def find_aperture(pic_pixels, pic_width: int, pic_height: int)-> object:
    middle_x = int(pic_width / 2)
    middle_y = int(pic_height / 2)
    aperture_brightest = 0
    aperture_x = 0
    for x in range(middle_x, pic_width, 1):
        r, g, b = pic_pixels[x, middle_y]
        brightness = r + g + b
        if brightness > aperture_brightest:
            aperture_brightest = brightness
            aperture_x = x

    aperture_threshold = aperture_brightest * 0.9
    aperture_x1 = aperture_x
    for x in range(aperture_x, middle_x, -1):
        r, g, b = pic_pixels[x, middle_y]
        brightness = r + g + b
        if brightness < aperture_threshold:
            aperture_x1 = x
            break

    aperture_x2 = aperture_x
    for x in range(aperture_x, pic_width, 1):
        r, g, b = pic_pixels[x, middle_y]
        brightness = r + g + b
        if brightness < aperture_threshold:
            aperture_x2 = x
            break

    aperture_x = (aperture_x1 + aperture_x2) / 2

    spectrum_threshold_duration = 64
    aperture_y_bounds = get_spectrum_y_bound(pic_pixels, aperture_x, middle_y, aperture_threshold, spectrum_threshold_duration)
    aperture_y = (aperture_y_bounds[0] + aperture_y_bounds[1]) / 2
    aperture_height = (aperture_y_bounds[1] - aperture_y_bounds[0]) * 1.0

    return {'x': aperture_x, 'y': aperture_y, 'h': aperture_height, 'b': aperture_brightest}

# draw aperture
def draw_aperture(aperture, draw):
    fill_color = "#000"
    draw.line((aperture['x'], aperture['y'] - aperture['h'] / 2, aperture['x'], aperture['y'] + aperture['h'] / 2),
              fill=fill_color)

# draw scan line
def draw_scan_line(aperture, draw, spectrum_angle):
    fill_color = "#888"
    xd = aperture['x']
    h = aperture['h'] / 2
    y0 = math.tan(spectrum_angle) * xd + aperture['y']
    draw.line((0, y0 - h, aperture['x'], aperture['y'] - h), fill=fill_color)
    draw.line((0, y0 + h, aperture['x'], aperture['y'] + h), fill=fill_color)

# draw graph
def draw_graph(draw, pic_pixels, aperture: object, spectrum_angle, wavelength_factor):
    aperture_height = aperture['h'] / 2
    step = 1
    last_graph_y = 0
    max_result = 0
    results = OrderedDict()
    for x in range(0, int(aperture['x'] * 7 / 8), step):
        wavelength = (aperture['x'] - x) * wavelength_factor
        if 1000 < wavelength or wavelength < 380:
            continue

        # general efficiency curve of 1000/mm grating
        eff = (800 - (wavelength - 250)) / 800
        if eff < 0.3:
            eff = 0.3

        # notch near yellow maybe caused by camera sensitivity
        mid = 571
        width = 14
        if (mid - width) < wavelength < (mid + width):
            d = (width - abs(wavelength - mid)) / width
            eff = eff * (1 - d * 0.12)

        # up notch near 590
        #mid = 588
        #width = 10
        #if (mid - width) < wavelength < (mid + width):
        #    d = (width - abs(wavelength - mid)) / width
        #    eff = eff * (1 + d * 0.1)

        y0 = math.tan(spectrum_angle) * (aperture['x'] - x) + aperture['y']
        amplitude = 0
        ac = 0.0
        for y in range(int(y0 - aperture_height), int(y0 + aperture_height), 1):
            r, g, b = pic_pixels[x, y]
            q = r + b + g * 2
            if y < (y0 - aperture_height + 2) or y > (y0 + aperture_height - 3):
                q = q * 0.5
            amplitude = amplitude + q
            ac = ac + 1.0
        amplitude = amplitude / ac / eff
        # amplitude=1/eff
        results[str(wavelength)] = amplitude
        if amplitude > max_result:
            max_result = amplitude
        graph_y = amplitude / 50 * aperture_height
        draw.line((x - step, y0 + aperture_height - last_graph_y, x, y0 + aperture_height - graph_y), fill="#fff")
        last_graph_y = graph_y
    draw_ticks_and_frequencies(draw, aperture, spectrum_angle, wavelength_factor)
    return results, max_result

# inform user of exposure
def inform_user_of_exposure(max_result):
    exposure = max_result / (255 + 255 + 255)
    print("ideal exposure between 0.15 and 0.30")
    print("exposure=", exposure)
    if exposure < 0.15:
        print("consider increasing shutter time")
    elif exposure > 0.3:
        print("consider reducing shutter time")

# save image with overlay
def save_image_with_overlay(im, name):
    PIL.ImageFile.MAXBLOCK = 2 ** 20
    im.save(output_filename, "JPEG", quality=80, optimize=True, progressive=True)

# normalize results
def normalize_results(results, max_result):
    for wavelength in results:
        results[wavelength] = results[wavelength] / max_result
    return results

# export csv
def export_csv(name, normalized_results):
    csv_filename = name + ".csv"
    csv = open(csv_filename, 'w')
    csv.write("wavelength,amplitude\n")
    for wavelength in normalized_results:
        csv.write(wavelength)
        csv.write(",")
        csv.write("{:0.3f}".format(normalized_results[wavelength]))
        csv.write("\n")
    csv.close()

# export diagram
def export_diagram(name, normalized_results):
    # global output_filename
    antialias = 4
    w = 600 * antialias
    h2 = 300 * antialias

    h = h2 - 20 * antialias
    sd = PIL.Image.new('RGB', (w, h2), (255, 255, 255))
    draw = PIL.ImageDraw.Draw(sd)

    w1 = 380.0
    w2 = 780.0
    f1 = 1.0 / w1
    f2 = 1.0 / w2
    for x in range(0, w, 1):
        # Iterate across frequencies, not wavelengths
        lambda2 = 1.0 / (f1 - (float(x) / float(w) * (f1 - f2)))
        c = wavelength_to_color(lambda2)
        draw.line((x, 0, x, h), fill=c)

    pl = [(w, 0), (w, h)]
    for wavelength in normalized_results:
        wl = float(wavelength)
        x = int((wl - w1) / (w2 - w1) * w)
        # print wavelength,x
        pl.append((int(x), int((1 - normalized_results[wavelength]) * h)))
    pl.append((0, h))
    pl.append((0, 0))
    draw.polygon(pl, fill="#FFF")
    draw.polygon(pl)

    font = PIL.ImageFont.truetype('/usr/share/fonts/truetype/lato/Lato-Regular.ttf', 12 * antialias)
    draw.line((0, h, w, h), fill="#000", width=antialias)

    for wl in range(400, 1001, 10):
        x = int((float(wl) - w1) / (w2 - w1) * w)
        draw.line((x, h, x, h + 3 * antialias), fill="#000", width=antialias)

    for wl in range(400, 1001, 50):
        x = int((float(wl) - w1) / (w2 - w1) * w)
        draw.line((x, h, x, h + 5 * antialias), fill="#000", width=antialias)
        wls = str(wl)
        tx = draw.textsize(wls, font=font)
        draw.text((x - tx[0] / 2, h + 5 * antialias), wls, font=font, fill="#000")

    # save chart
    sd = sd.resize((int(w / antialias), int(h / antialias)), PIL.Image.ANTIALIAS)
    output_filename = name + "_chart.png"
    sd.save(output_filename, "PNG", quality=95, optimize=True, progressive=True)





#######################################################
# High level functions
#######################################################
# Take photo
def acquire_photo():
    # global variables
    global raw_filename
    global shutter
    # Need to add in button for this later! sys.argv[1]
    shutter = int(5) # Need to add in button for this later! int(sys.argv[2])
    # save filename as a global variable
    raw_filename = name + "_raw.jpg"
    # run take picture function
    take_picture(raw_filename,shutter)

    return




def createSpectrum():
    camera.stop_preview()
    # get pictures aperature
    im = PIL.Image.open(raw_filename)
    print("locating aperture")
    pic_pixels = im.load()
    aperture = find_aperture(pic_pixels, im.size[0], im.size[1])

    # 3. Draw aperture and scan line
    spectrum_angle = -0.01
    draw = PIL.ImageDraw.Draw(im)
    draw_aperture(aperture, draw)
    draw_scan_line(aperture, draw, spectrum_angle)

    # 4. Draw graph on picture
    print("analysing image")
    wavelength_factor = 0.95
    #wavelength_factor = 0.892  # 1000/mm
    #wavelength_factor=0.892*2.0*600/650 # 500/mm
    results, max_result = draw_graph(draw, pic_pixels, aperture, spectrum_angle, wavelength_factor)

    # inform user of issues with exposure
    inform_user_of_exposure(max_result)

    # save images
    save_image_with_overlay(im, name)
    normalized_results = normalize_results(results, max_result)

    # save csv
    export_csv(name, normalized_results)

    # display image with overlay? 
    # display spectrum 
    print("generating chart")
    export_diagram(name, normalized_results)
    return

def killWindow(event, x, y, flags, param):
    if event == cv2.EVENT_FLAG_ALTKEY:
        #cap.release()
        cv2.destroyAllWindows()




#######################################################
# File Viewing functions
#######################################################
def openImage():
    camera.stop_preview()
    # get size of frame
    w = root.winfo_width()
    h = 470


    rimg = PIL.Image.open(raw_filename)
    renderRaw = PIL.ImageTk.PhotoImage(rimg.resize((w,h)), master=root)
    rawIm = Label(frame, image=renderRaw)
    rawIm.image = renderRaw
    rawIm.grid(row=0,column=0, columnspan=1)


def openSpectrum():
    camera.stop_preview()
    w = root.winfo_width()
    h = root.winfo_height()
   ## To open spectrum

    simg = PIL.Image.open(output_filename)
    renderSpec = PIL.ImageTk.PhotoImage(simg.resize((w, h)), master=root)
    specIm = Label(frame, image=renderSpec)
    specIm.image = renderSpec
    specIm.grid(row=0,column=0, columnspan=1)


#class picamera.PiRenderer(parent, layer=0, alpha=255, fullscreen=True, window=None, crop=None, rotation=0, vflip=False, hflip=False)


def setBrightness(ev=None):
    global tkScale
    camera.brightness = tkScale.get()



# testing openVideo function
def openVideo():
    # set width of button window
    wid_but = 140 + 5

    shutter = int(5)
    #camera = picamera.PiCamera()
    camera.start_preview(fullscreen=False, window=(wid_but, 20, 800-wid_but-17, 500))
    camera.resolution = (2592,1944)
    camera.brightness = 50
    camera.sensor_mode = 3
    camera.iso = 0  # Auto.This will yield less noise during day exposures and keep the iso down in low light for less noise.
    camera.framerate_range = (0.167, 6)  # this should match the values available in sensor mode, allowing upto a 6 second exposure
    camera.exposure_mode = 'nightpreview'
    # raises the gains, and lowers the iso
    #sleep = (10)

    tkScale = tk.Scale(root,from_=0, to=100,length=300,orient=tk.HORIZONTAL,command=setBrightness)
    tkScale
    tkScale.set(50)
    tkScale.grid(row=0, column=0)
    # camera.vflip = True
    # #camera.framerate = Fraction(1, 3)
    # camera.shutter_speed = shutter
    # #camera.iso = 1000
    # camera.exposure_mode = 'off'
    # camera.exposure_compensation = 25
    # camera.awb_mode = 'auto'
    # #camera.awb_gains = ()


# openVideo Function that Works
# def openVideo():
#     global cap
#     cap = cv2.VideoCapture(0)
#     #cap.set(cv2.CAP_PROP_EXPOSURE, -4)
#
#     if not cap.isOpened():
#         print("Cannot open camera")
#         exit()
#     while True:
#         # Capture frame-by-frame
#         ret, frame = cap.read()
#         # if frame is read correctly ret is True
#         if not ret:
#             print("Can't receive frame (stream end?). Exiting ...")
#             break
#         # Our operations on the frame come here
#         #img1 = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
#         img2 = cv2.resize(frame, (wid - wid_but, hgt))
#
#         # Display the resulting frame
#         windowName = 'Video Capture'
#
#         cv2.imshow(windowName, img2)
#         #cv2.createTrackbar('slider', windowName, 0, 100, on_change)
#         cv2.moveWindow(windowName, wid_but, -10)
#         cv2.setMouseCallback(windowName, killWindow)
#
#         if cv2.waitKey(1) & 0xFF == ord('q'):
#             break
#     # When everything done, release the capture
#     cap.release()
#     cv2.destroyAllWindows()



###################################################
# GUI Build 
###################################################
button_takePicture = Button(butWin, text="Take Picture", bg="#fdad5c", height=4, command=acquire_photo)#, command=lambda: take_picture(raw_filename))
button_viewPicture = Button(butWin, text="View Image", bg="#fdad5c", height=4,  command=openImage)
button_createSpectrum = Button(butWin, text="Create Spectrum", bg="#fdad5c", height=4, command=createSpectrum) #, command=createSpectrum)
button_viewSpectrum = Button(butWin, text="View Spectrum", bg="#fdad5c", height=4, command=openSpectrum)
button_captureVideo = Button(butWin, text="Video Capture", bg="#fdad5c",  height=4, command=openVideo)


exit_button = Button(butWin, text="Exit",height=1, command=root.destroy)
exit_button.grid(row=5,column=0)

# New windows
button_captureVideo.grid(row=0, column=0, sticky="nsew")
button_takePicture.grid(row=1,column=0, sticky="nsew") #pack(side=LEFT, padx=5, pady=5)
button_viewPicture.grid(row=2,column=0, sticky="nsew") #pack(side=LEFT, padx=5, pady=5)#fill=tk.X, side=tk.LEFT, anchor=SW, expand=True)
button_createSpectrum.grid(row=3,column=0, sticky="nsew") #pack(side=LEFT, padx=5, pady=5)
button_viewSpectrum.grid(row=4,column=0,sticky="nsew") #pack(side=LEFT, padx=5, pady=5)




root.mainloop()















###################################################
# MISC Code
###################################################


# Create file save entry button 
#  e = Entry(root, width=35, borderwidth=5)
#e.grid(row=0, column=0, columnspan=3, padx=10, pady=10)
#  e.pack(side=tk.BOTTOM, anchor=S)
#  e.insert(0, "Enter file save name here")
#  raw_filename = e.get()

	# add functionality: if empty, use auto name
#	if (blank): 
#		name = sys.argv[1]
#    	shutter = int(sys.argv[2])
#    	raw_filename = name + "_raw.jpg"



# Create Buttons
#button_takePicture = Button(root, text="Take Picture", padx=40, pady = 20)#, command=lambda: take_picture(raw_filename))
#button_createSpectrum = Button(root, text="Create Spectrum", padx=40, pady=20) #, command=createSpectrum)
#b1 = Frame(root, bg="black", bd=3)
#b2 = Frame(root, bg='black', bd=3)



#button_takePicture['font'] = myFont
#button_createSpectrum['font'] = myFont
# button frames


# Pack 

# Button Locations
#button_takePicture.grid(row=0, column=0, columnspan = 2)
#button_createSpectrum.grid(row=0, column=2, columnspan=2)

# Auto column adjustments
#h = button_takePicture.winfo_height()
#w = button_takePicture.winfo_width()

#button_takePicture.columnconfigure(0, weight=2)
#button_createSpectrum.columnconfigure(2, weight=2)



# Display images: 
# initial picture
# image with overlay
# final spectrum 
















