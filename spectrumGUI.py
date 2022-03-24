# import libraries
import os
import io
import math
import time
import picamera
from fractions import Fraction
from collections import OrderedDict
import PIL.Image
import PIL.ImageTk
import PIL.ImageDraw
import PIL.ImageFile
import PIL.ImageFont
from tkinter import *
import tkinter as tk
from tkinter import filedialog


# create tkinter object
root = Tk()

# get screen width and height
wid = root.winfo_screenwidth()
hgt = root.winfo_screenheight()

# set width of button window
wid_but = 140
wid_slide = 80

# root: main window displays images
root.title('Spectrometer')
root.geometry('%dx%d+%d+%d' % (wid-wid_but-wid_slide, hgt, wid_but+wid_slide+1,-30))
root.configure(bg="black")
frame = Frame(root, bg="blue")
frame.grid(row=0, column=0, sticky="nsew")

# slider window: displays slider
sliWin = tk.Toplevel(root)
sliWin.geometry('%dx%d+%d+%d' % (wid_slide, hgt+30, wid_but, -30))
sliWin.configure(bg='white')
Win2 = Frame(sliWin)
Win2.grid(row=0,column=0, sticky='nsew')

# side window: displays buttons
butWin = tk.Toplevel(root) # Tk()
butWin.geometry('%dx%d+%d+%d' % (wid_but, hgt+30, 1, -30))
butWin.configure(bg="white")
Win1 = Frame(butWin)
Win1.grid(row=0, column=0, sticky="nsew")

# exit window: displays shutdown buttons
def shutdown():
    call(['sudo', 'shutdown', '-h', 'now'])

def open_popup():
    top = Toplevel(butWin)
    top.geometry('%dx%d+%d+%d' % (wid / 2, hgt / 2, wid / 4, hgt / 4))
    Label(top, text="Shutdown Now?", font='Mistral 18 bold').pack(side=TOP, pady=10)#place(x=wid/8, y=20)

    shutdown_button_yes = Button(top, text="Yes", font='Mistral 16 bold', bg="#AAFF00", height=5, command=shutdown) #will need to change this
    shutdown_button_yes.config(width=10, height=5, activebackground="#568156", relief=RAISED, justify='left')
    shutdown_button_yes.pack(side=LEFT, padx=10)

    shutdown_button_no = Button(top, text="No",font='Mistral 16 bold', bg="#FF0000", height=5, command=top.destroy)
    shutdown_button_no.config(width=10, height=5, activebackground="#f26161", relief=RAISED, justify='center')
    shutdown_button_no.pack(side=LEFT, padx=10)



global name
global camera
global output_chart
global output_raw
global output_out
global shutter
global button1

button1 = True

camera = picamera.PiCamera()

# set default shutter value
shutter = 100000






# output filenames
name = 'test'
output_chart = name + "_chart.png"
output_raw = name + "_raw.jpg"
output_out = name + "_out.png"



########### FUNCTION DEFINTIONS #######################


#######################################################
# Analysis on Raw Image
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
    for i in range(0, len(thresholds) - 1, 1): # for 0-6 step of 1
        t1 = thresholds[i] # 380nm
        t2 = thresholds[i + 1] # cycle through remaining wavelengths
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
    fill_color = '#000' #"#888"
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


#######################################################
# Lower level functions
#######################################################


## Use old image view code:
def take_picture(imname, shutter):

    camera.vflip = True
    camera.framerate = Fraction(1, 2)
    camera.shutter_speed = shutter #tkScale.get()
    camera.iso = 100
    camera.exposure_mode = 'off'
    camera.awb_mode = 'off'
    camera.awb_gains = (1, 1)
    time.sleep(3)
    # #print("capturing image")
    camera.capture(imname, resize=(wid - wid_but, hgt))
    return
# save image with overlay
def save_image_with_overlay(im):
    PIL.ImageFile.MAXBLOCK = 2 ** 20
    overlay_filename = 'test_out.png'
    im.save(overlay_filename, "PNG", quality=80, optimize=True, progressive=True)
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
def export_diagram(normalized_results,aperture, spectrum_angle):
    antialias = 4
    w = 600 * antialias #2400
    h2 = 300 * antialias  #1200

    h = h2 - 20 * antialias  #1120
    sd = PIL.Image.new('RGB', (w, h2), (255, 255, 255)) # creates new image, 2400 width x 1200 height white rectangle
    draw = PIL.ImageDraw.Draw(sd) # allows objects to be drawn on the image in the argument

    w1 = 380.0 # leftmost wavelength
    w2 = 720 #780.0 # rightmost wavelength
    f1 = 1.0 / w1 # frequency upper bound: 1/wavelength 1
    f2 = 1.0 / w2 # frequency lower bound: 1/wavelength 2
    for x in range(0, w, 1): # for each x position in the width of the image
        # Iterate across frequencies, not wavelengths
        lambda2 = 1.0 / (f1 - (float(x) / float(w) * (f1 - f2))) #converts frequency to wavelength to x_px location
        c = wavelength_to_color(lambda2) # get rgb color associated with wavelength
        draw.line((x, 0, x, h), fill=c) # draw a vertical line at position px x with height 1120
        # this creates basically a rectangle with all of the colors at the correct location


    # create a white polygon which fills the negative space of the spectrum
    pl = [(w, 0), (w, h)] # [(2400,0), (2400,1200)]

    spectrum_line_width = 60 # set the width of the line on the spectrum

    #count = 0
    line_points = []
    for wavelength in normalized_results: # for each wavelength
        wl = float(wavelength) # create a float value
        x = int((wl - w1) / (w2 - w1) * w) # (current wavelength - 380nm)/(del wave2 - wave1) * width.
        # determine x position of current wavelength based on fraction of wavelengths to x_px width
        # print wavelength,x
        pl.append((int(x), int((1 - normalized_results[wavelength]) * h))) # ordered dictionary
        line_points.append((int(x), int((1 - normalized_results[wavelength]) * h)))


    pl.append((0, h))
    pl.append((0, 0))

    draw.polygon(pl, fill="#fff")  # background color
    draw.polygon(pl)


    draw.line(line_points, width=40, fill='#000', joint='curve')

    font = PIL.ImageFont.truetype('/usr/share/fonts/truetype/lato/Lato-Regular.ttf', 12 * antialias)
    draw.line((0, h, w, h), fill="#000", width=antialias) # bottom solid line on spectrum
    print(h) #1120
    print(x) #4
    #draw.line((0,h,w,h), width=10)

    for wl in range(400, 1001, 10):
        x = int((float(wl) - w1) / (w2 - w1) * w)
        draw.line((x, h, x, h + 3 * antialias), fill="#000", width=antialias) # bottom dotted line on spectrum

    for wl in range(400, 1001, 50):
        x = int((float(wl) - w1) / (w2 - w1) * w)
        draw.line((x, h, x, h + 5 * antialias), fill="#000", width=antialias) # line directly above wavelength num text
        wls = str(wl)
        tx = draw.textsize(wls, font=font)
        draw.text((x - tx[0] / 2, h + 5 * antialias), wls, font=font, fill="#000")

    # save chart
    sd = sd.resize((int(w / antialias), int(h / antialias)), PIL.Image.ANTIALIAS)
    sd.save(output_chart, "PNG", quality=95, optimize=True, progressive=True)



#######################################################
# High level functions
#######################################################
# Take photo
def button_start():
    button_captureVideo.config(bg="#fdad5c", relief=RAISED)
    button_viewPicture.config(bg="#fdad5c", relief=RAISED)
    button_viewSpectrum.config(bg="#fdad5c", relief=RAISED)
    button_takePicture.config(bg="#ffdbb7", relief=SUNKEN)
    return

def button_main():

    # print(shutter)
    take_picture(output_raw,shutter)
    createSpectrum()

def button_end():
    button_takePicture.config(bg="#fdad5c", relief=RAISED)


def acquire_photo():
    button_start()
    button_main()
    button_takePicture.config(bg="#fdad5c", relief=RAISED)

# buttons inside exit popup window
#def button_shutdown_yes():






def createSpectrum():
    camera.stop_preview()
    # get pictures aperature
    im = PIL.Image.open(output_raw)
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
    wavelength_factor = 1.415
    #wavelength_factor = 0.892  # 1000/mm
    #wavelength_factor=0.892*2.0*600/650 # 500/mm
    results, max_result = draw_graph(draw, pic_pixels, aperture, spectrum_angle, wavelength_factor)

    # inform user of issues with exposure
    inform_user_of_exposure(max_result)


    # save images
    save_image_with_overlay(im)
    normalized_results = normalize_results(results, max_result)

    # save csv
    export_csv(name, normalized_results)

    # display image with overlay?
    # display spectrum
    print("generating chart")
    export_diagram(normalized_results,aperture,  spectrum_angle )
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
    h = root.winfo_height()

    rimg = PIL.Image.open(output_raw) #oct change back from output_out to output_raw

    # Crop the image (width: 660, height: 480)
    rimg1 = rimg.resize((w,h))

    # # Setting the points for cropped image
    height_rimg = 480
    #width_rimg = 660

    left = 50
    top = 160
    right = 310
    bottom = 3 * height_rimg / 4


    #
    # # Cropped image of above dimension
    # # (It will not change original image)
    rimg2 = rimg1.crop((left, top, right, bottom))

    rimg3 = rimg2.resize((w, h))
    rimg4 = rimg3.transpose(PIL.Image.FLIP_LEFT_RIGHT)

    renderRaw = PIL.ImageTk.PhotoImage(rimg4, master=root)
    rawIm = Label(frame, bd=0,  image=renderRaw)
    rawIm.image = renderRaw
    rawIm.grid(row=0,column=0,columnspan=1)

    # in openImage
    # turn off capture video, viewSpectrum turn on view picture
    button_captureVideo.config(bg="#fdad5c", relief=RAISED)
    button_viewSpectrum.config(bg="#fdad5c", relief=RAISED)
    button_takePicture.config(bg="#fdad5c", relief=RAISED)

    button_viewPicture.config(bg="#ffdbb7", relief=SUNKEN)


def openSpectrum():
    camera.stop_preview()
    w = root.winfo_width()
    h = root.winfo_height()

    ## To open spectrum
    simg = PIL.Image.open(output_chart)
    renderSpec = PIL.ImageTk.PhotoImage(simg.resize((w, h)), master=root)
    specIm = Label(frame, image=renderSpec)
    specIm.image = renderSpec
    specIm.grid(row=0,column=0, columnspan=1)

    # in openSpectrum
    # turn off captureVideo, viewPicture turn on viewSpectrum
    button_captureVideo.config(bg="#fdad5c", relief=RAISED)
    button_viewPicture.config(bg="#fdad5c", relief=RAISED)
    button_takePicture.config(bg="#fdad5c", relief=RAISED)

    button_viewSpectrum.config(bg="#ffdbb7", relief=SUNKEN)



## Using original camera settings
def openVideo():
    w = root.winfo_width()
    h = root.winfo_height()
    # make background frame black
    bkimage = PIL.Image.new('RGB', (255, 255), "black")
    rendbkimage = PIL.ImageTk.PhotoImage(bkimage.resize((w,h)), master=root)
    backgnd = Label(frame, bd=0, image=rendbkimage)
    backgnd.image = rendbkimage
    backgnd.grid(row=0, column=0, columnspan=1)

    setwidth = wid_but + wid_slide + 4

    camera.start_preview(fullscreen=False,
                         window=(setwidth, -15, w, h))  # 800-setwidth (wid_but, 20, 800-wid_but-17, 500))

    camera.vflip = True
    camera.framerate = Fraction(1, 2)
    camera.shutter_speed = shutter
    camera.iso = 100
    camera.exposure_mode = 'off'
    camera.awb_mode = 'off'
    camera.awb_gains = (1, 1)

    # in openVideo
    # turn off viewPicture, viewSpectrum turn on captureVideo
    button_viewPicture.config(bg="#fdad5c", relief=RAISED)
    button_viewSpectrum.config(bg="#fdad5c", relief=RAISED)
    button_takePicture.config(bg="#fdad5c", relief=RAISED)

    button_captureVideo.config(bg="#ffdbb7", relief=SUNKEN)


def shutterp001():
    camera.shutter_speed = 1000
    global shutter
    shutter = 1000

    # Remove relief on all other buttons
    button_sp01.config(bg="#1E4D2B", relief=RAISED)
    button_sp1.config(bg="#1E4D2B", relief=RAISED)
    button_s1p.config(bg="#1E4D2B", relief=RAISED)
    button_s10p.config(bg="#1E4D2B", relief=RAISED)

    # set relief
    button_sp001.config(bg="#568156",relief=SUNKEN)


def shutterp01():
    camera.shutter_speed = 10000
    global shutter
    shutter = 10000

    # Remove relief on all other buttons
    button_sp001.config(bg="#1E4D2B", relief=RAISED)
    button_sp1.config(bg="#1E4D2B", relief=RAISED)
    button_s1p.config(bg="#1E4D2B", relief=RAISED)
    button_s10p.config(bg="#1E4D2B", relief=RAISED)

    # set relief
    button_sp01.config(bg="#568156",relief=SUNKEN)

def shutterp1():
    camera.shutter_speed = 100000
    global shutter
    shutter = 100000

    # Remove relief on all other buttons
    button_sp001.config(bg="#1E4D2B", relief=RAISED)
    button_sp01.config(bg="#1E4D2B", relief=RAISED)
    button_s1p.config(bg="#1E4D2B", relief=RAISED)
    button_s10p.config(bg="#1E4D2B", relief=RAISED)

    # set relief
    button_sp1.config(bg="#568156",relief=SUNKEN)

def shutter1p():
    camera.shutter_speed = 1000000
    global shutter
    shutter = 1000000

    # Remove relief on all other buttons
    button_sp001.config(bg="#1E4D2B", relief=RAISED)
    button_sp01.config(bg="#1E4D2B", relief=RAISED)
    button_sp1.config(bg="#1E4D2B", relief=RAISED)
    button_s10p.config(bg="#1E4D2B", relief=RAISED)

    # set relief
    button_s1p.config(bg="#568156",relief=SUNKEN)

def shutter10p():
    camera.shutter_speed = 10000000
    global shutter
    shutter = 10000000

    # Remove relief on all other buttons
    button_sp001.config(bg="#1E4D2B", relief=RAISED)
    button_sp01.config(bg="#1E4D2B",relief=RAISED)
    button_sp1.config(bg="#1E4D2B", relief=RAISED)
    button_s1p.config(bg="#1E4D2B", relief=RAISED)

    # set relief
    button_s10p.config(bg="#568156",relief=SUNKEN)

def set_relief1(button):
    global button1
    button1 = not button1 # default is FALSE

    if button1 == True:
        button.config(relief=SUNKEN)
    else:
        button.config(relief=RAISED)
###################################################
# GUI Build
###################################################



button_sp001 = Button(sliWin, text="1 ms", bg="#1E4D2B", fg='#ffffff',height=5, command=shutterp001)
button_sp001.config(activebackground="#568156", relief=RAISED)#command=set_relief1(button_sp001)
button_sp01 = Button(sliWin, text="10 ms", bg="#1E4D2B", fg='#ffffff',height=5, command=shutterp01)
button_sp01.config(activebackground="#568156", relief=RAISED)
button_sp1 = Button(sliWin, text="100 ms", bg="#1E4D2B", fg='#ffffff',height=5, command=shutterp1)
button_sp1.config(activebackground="#568156", bg="#568156",relief=SUNKEN)
button_s1p = Button(sliWin, text = "1 s", bg="#1E4D2B", fg='#ffffff',height=5, command=shutter1p)
button_s1p.config(activebackground="#568156",relief=RAISED)
button_s10p = Button(sliWin, text = "10 s", bg="#1E4D2B", fg='#ffffff',  height=5, command=shutter10p)
button_s10p.config(activebackground="#568156",relief=RAISED)


button_takePicture = Button(butWin, text="Take Picture", bg="#fdad5c", height=5, command=lambda:[button_start(),button_main(), button_end()])
button_takePicture.config(activebackground="#ffdbb7")
button_viewPicture = Button(butWin, text="View Image",  bd=0, bg="#fdad5c", height=5,  command=openImage)
button_viewPicture.config(activebackground="#ffdbb7")
#button_createSpectrum = Button(butWin, text="Create Spectrum", bg="#fdad5c", height=4, command=createSpectrum)
button_viewSpectrum = Button(butWin, text="View Spectrum", bd=0, bg="#fdad5c", height=5, command=openSpectrum)
button_viewSpectrum.config(activebackground="#ffdbb7")
#makeshift exit
#button_captureVideo = Button(butWin, text="Video Capture", bg="#fdad5c",  height=5, command=openVideo)
button_captureVideo = Button(butWin, text="Video Capture", bg="#fdad5c",  height=5, command=root.destroy)
button_captureVideo.config(activebackground="#ffdbb7")









#exit_button = Button(butWin, text="Exit", bg="#bf0000",height=5, command=root.destroy)
exit_button = Button(butWin, text="Exit", bg="#bf0000",height=5, command=open_popup)
exit_button.config(activebackground="#f26161")
exit_button.grid(row=4,column=0, sticky='nsew')



# New windows
button_captureVideo.grid(row=0, column=0, sticky="nsew")
button_takePicture.grid(row=1,column=0, sticky="nsew")
button_viewPicture.grid(row=2,column=0, sticky="nsew")
#button_createSpectrum.grid(row=3,column=0, sticky="nsew")
button_viewSpectrum.grid(row=3,column=0,sticky="nsew")

button_sp001.grid(row=0, column=0, sticky="nsew")
button_sp01.grid(row=1,column=0, sticky="nsew")
button_sp1.grid(row=2,column=0, sticky="nsew")
button_s1p.grid(row=3,column=0,sticky="nsew")
button_s10p.grid(row=4,column=0,sticky="nsew")




root.mainloop()