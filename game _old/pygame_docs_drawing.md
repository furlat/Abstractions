pygame.display
pygame module to control the display window and screen
pygame.display.init
Initialize the display module
pygame.display.quit
Uninitialize the display module
pygame.display.get_init
Returns True if the display module has been initialized
pygame.display.set_mode
Initialize a window or screen for display
pygame.display.get_surface
Get a reference to the currently set display surface
pygame.display.flip
Update the full display Surface to the screen
pygame.display.update
Update all, or a portion, of the display. For non-OpenGL displays.
pygame.display.get_driver
Get the name of the pygame display backend
pygame.display.Info
Create a video display information object
pygame.display.get_wm_info
Get information about the current windowing system
pygame.display.get_desktop_sizes
Get sizes of active desktops
pygame.display.list_modes
Get list of available fullscreen modes
pygame.display.mode_ok
Pick the best color depth for a display mode
pygame.display.gl_get_attribute
Get the value for an OpenGL flag for the current display
pygame.display.gl_set_attribute
Request an OpenGL display attribute for the display mode
pygame.display.get_active
Returns True when the display is active on the screen
pygame.display.iconify
Iconify the display surface
pygame.display.toggle_fullscreen
Switch between fullscreen and windowed displays
pygame.display.set_gamma
Change the hardware gamma ramps
pygame.display.set_gamma_ramp
Change the hardware gamma ramps with a custom lookup
pygame.display.set_icon
Change the system image for the display window
pygame.display.set_caption
Set the current window caption
pygame.display.get_caption
Get the current window caption
pygame.display.set_palette
Set the display color palette for indexed displays
pygame.display.get_num_displays
Return the number of displays
pygame.display.get_window_size
Return the size of the window or screen
pygame.display.get_allow_screensaver
Return whether the screensaver is allowed to run.
pygame.display.set_allow_screensaver
Set whether the screensaver may run
pygame.display.is_fullscreen
Returns True if the pygame window created by pygame.display.set_mode() is in full-screen mode
pygame.display.is_vsync
Returns True if vertical synchronisation for pygame.display.flip() and pygame.display.update() is enabled
pygame.display.get_current_refresh_rate
Returns the screen refresh rate or 0 if unknown
pygame.display.get_desktop_refresh_rates
Returns the screen refresh rates for all displays (in windowed mode).
pygame.display.message_box
Create a native GUI message box
This module offers control over the pygame display. Pygame has a single display Surface that is either contained in a window or runs full screen. Once you create the display you treat it as a regular Surface. Changes are not immediately visible onscreen; you must choose one of the two flipping functions to update the actual display.

The origin of the display, where x = 0 and y = 0, is the top left of the screen. Both axes increase positively towards the bottom right of the screen.

The pygame display can actually be initialized in one of several modes. By default, the display is a basic software driven framebuffer. You can request special modules like automatic scaling or OpenGL support. These are controlled by flags passed to pygame.display.set_mode().

Pygame can only have a single display active at any time. Creating a new one with pygame.display.set_mode() will close the previous display. To detect the number and size of attached screens, you can use pygame.display.get_desktop_sizes and then select appropriate window size and display index to pass to pygame.display.set_mode().

For backward compatibility pygame.display allows precise control over the pixel format or display resolutions. This used to be necessary with old graphics cards and CRT screens, but is usually not needed any more. Use the functions pygame.display.mode_ok(), pygame.display.list_modes(), and pygame.display.Info() to query detailed information about the display.

Once the display Surface is created, the functions from this module affect the single existing display. The Surface becomes invalid if the module is uninitialized. If a new display mode is set, the existing Surface will automatically switch to operate on the new display.

When the display mode is set, several events are placed on the pygame event queue. pygame.QUIT is sent when the user has requested the program to shut down. The window will receive pygame.ACTIVEEVENT events as the display gains and loses input focus. If the display is set with the pygame.RESIZABLE flag, pygame.VIDEORESIZE events will be sent when the user adjusts the window dimensions. Hardware displays that draw direct to the screen will get pygame.VIDEOEXPOSE events when portions of the window must be redrawn.

A new windowevent API was introduced in pygame 2.0.1. Check event module docs for more information on that

Some display environments have an option for automatically stretching all windows. When this option is enabled, this automatic stretching distorts the appearance of the pygame window. In the pygame examples directory, there is example code (prevent_display_stretching.py) which shows how to disable this automatic stretching of the pygame display on Microsoft Windows (Vista or newer required).

pygame.display.init()
Initialize the display module
init() -> None
Initializes the pygame display module. The display module cannot do anything until it is initialized. This is usually handled for you automatically when you call the higher level pygame.init().

Pygame will select from one of several internal display backends when it is initialized. The display mode will be chosen depending on the platform and permissions of current user. Before the display module is initialized the environment variable SDL_VIDEODRIVER can be set to control which backend is used. The systems with multiple choices are listed here.

Windows : windib, directx
Unix    : x11, dga, fbcon, directfb, ggi, vgl, svgalib, aalib
On some platforms it is possible to embed the pygame display into an already existing window. To do this, the environment variable SDL_WINDOWID must be set to a string containing the window id or handle. The environment variable is checked when the pygame display is initialized. Be aware that there can be many strange side effects when running in an embedded display.

It is harmless to call this more than once, repeated calls have no effect.

pygame.display.quit()
Uninitialize the display module
quit() -> None
This will shut down the entire display module. This means any active displays will be closed. This will also be handled automatically when the program exits.

It is harmless to call this more than once, repeated calls have no effect.

pygame.display.get_init()
Returns True if the display module has been initialized
get_init() -> bool
Returns True if the pygame.displaypygame module to control the display window and screen module is currently initialized.

pygame.display.set_mode()
Initialize a window or screen for display
set_mode(size=(0, 0), flags=0, depth=0, display=0, vsync=0) -> Surface
This will create a window or display output and return a display Surface. The arguments passed in are requests for a display type. The actual created display will be the best possible match supported by the system.

Note that calling this function implicitly initializes pygame.display, if it was not initialized before.

The size argument is a pair of numbers representing the width and height. The flags argument is a collection of additional options. The depth argument represents the number of bits to use for color.

The Surface that gets returned can be drawn to like a regular Surface but changes will eventually be seen on the monitor.

If no size is passed or is set to (0, 0), the created Surface will have the same size as the current screen resolution. If only the width or height are set to 0, the Surface will have the same width or height as the screen resolution.

Since pygame 2, the depth argument is ignored, in favour of the best and fastest one. It also raises a deprecation warning since pygame-ce 2.4.0 if the passed in depth is not 0 or the one pygame selects.

When requesting fullscreen display modes, sometimes an exact match for the requested size cannot be made. In these situations pygame will select the closest compatible match. The returned surface will still always match the requested size.

On high resolution displays(4k, 1080p) and tiny graphics games (640x480) show up very small so that they are unplayable. SCALED scales up the window for you. The game thinks it's a 640x480 window, but really it can be bigger. Mouse events are scaled for you, so your game doesn't need to do it. Note that SCALED is considered an experimental API and may change in future releases.

The flags argument controls which type of display you want. There are several to choose from, and you can even combine multiple types using the bitwise or operator, (the pipe "|" character). Here are the display flags you will want to choose from:

pygame.FULLSCREEN    create a fullscreen display
pygame.DOUBLEBUF     only applicable with OPENGL
pygame.HWSURFACE     (obsolete in pygame 2) hardware accelerated, only in FULLSCREEN
pygame.OPENGL        create an OpenGL-renderable display
pygame.RESIZABLE     display window should be sizeable
pygame.NOFRAME       display window will have no border or controls
pygame.SCALED        resolution depends on desktop size and scale graphics
pygame.SHOWN         window is opened in visible mode (default)
pygame.HIDDEN        window is opened in hidden mode
New in pygame-ce 2.0.0: SCALED, SHOWN and HIDDEN

New in pygame-ce 2.0.0: vsync parameter

By setting the vsync parameter to 1, it is possible to get a display with vertical sync at a constant frame rate determined by the monitor and graphics drivers. Subsequent calls to pygame.display.flip()Update the full display Surface to the screen or pygame.display.update()Update all, or a portion, of the display. For non-OpenGL displays. will block (i.e. wait) until the screen has refreshed, in order to prevent "screen tearing" <https://en.wikipedia.org/wiki/Screen_tearing>.

Be careful when using this feature together with pygame.time.Clock or pygame.time.delay()pause the program for an amount of time, as multiple forms of waiting and frame rate limiting may interact to cause skipped frames.

The request only works when graphics acceleration is available on the system. The exact behaviour depends on the hardware and driver configuration. When vsync is requested, but unavailable, set_mode() may raise an exception.

Setting the vsync parameter to -1 in conjunction with OPENGL will request the OpenGL-specific feature "adaptive vsync" <https://www.khronos.org/opengl/wiki/Swap_Interval#Adaptive_Vsync>.

Here is an example usage of a call to set_mode() that may give you a display with vsync:

flags = pygame.OPENGL | pygame.FULLSCREEN
try:
   window_surface = pygame.display.set_mode((1920, 1080), flags, vsync=1)
   vsync_success=True
except pygame.error:
   window_surface = pygame.display.set_mode((1920, 1080), flags)
   vsync_success=False
New in pygame 2.0.0: vsync parameter

Changed in pygame-ce 2.2.0: passing vsync can raise an exception

Changed in pygame-ce 2.2.0: explicit request for "adaptive vsync"

Changed in pygame-ce 2.2.0: vsync=1 does not require SCALED or OPENGL

Deprecated since pygame-ce 2.4.0: The depth argument is ignored, and will be set to the optimal value

Basic example:

# Open a window on the screen
screen_width=700
screen_height=400
screen=pygame.display.set_mode([screen_width, screen_height])
The display index 0 means the default display is used. If no display index argument is provided, the default display can be overridden with an environment variable.

Changed in pygame 1.9.5: display argument added

Changed in pygame-ce 2.1.3: pygame now ensures that subsequent calls to this function clears the window to black. On older versions, this was an implementation detail on the major platforms this function was tested with.

pygame.display.get_surface()
Get a reference to the currently set display surface
get_surface() -> Surface
Return a reference to the currently set display Surface. If no display mode has been set this will return None.

pygame.display.flip()
Update the full display Surface to the screen
flip() -> None
This will update the contents of the entire display.

When using an pygame.OPENGL display mode this will perform a gl buffer swap.

pygame.display.update()
Update all, or a portion, of the display. For non-OpenGL displays.
update(rectangle=None, /) -> None
update(rectangle_list, /) -> None
For non OpenGL display Surfaces, this function is very similar to pygame.display.flip() with an optional parameter that allows only portions of the display surface to be updated, instead of the entire area. If no argument is passed it updates the entire Surface area like pygame.display.flip().

Note calling display.update(None) means no part of the window is updated. Whereas display.update() means the whole window is updated.
You can pass the function a single rectangle, or a sequence of rectangles. Generally you do not want to pass a sequence of rectangles as there is a performance cost per rectangle passed to the function. On modern hardware, after a very small number of rectangles passed in, the per-rectangle cost will exceed the saving of updating less pixels. In most applications it is simply more efficient to update the entire display surface at once, it also means you do not need to keep track of a list of rectangles for each call to update.

If passing a sequence of rectangles it is safe to include None values in the list, which will be skipped.

This call cannot be used on pygame.OPENGL displays and will generate an exception.

pygame.display.get_driver()
Get the name of the pygame display backend
get_driver() -> name
Pygame chooses one of many available display backends when it is initialized. This returns the internal name used for the display backend. This can be used to provide limited information about what display capabilities might be accelerated. See the SDL_VIDEODRIVER flags in pygame.display.set_mode() to see some of the common options.

pygame.display.Info()
Create a video display information object
Info() -> VideoInfo
Creates a simple object containing several attributes to describe the current graphics environment. If this is called before pygame.display.set_mode() some platforms can provide information about the default display mode. This can also be called after setting the display mode to verify specific display options were satisfied. The VidInfo object has several attributes:

hw:         1 if the display is hardware accelerated
wm:         1 if windowed display modes can be used
video_mem:  The megabytes of video memory on the display.
            This is 0 if unknown
bitsize:    Number of bits used to store each pixel
bytesize:   Number of bytes used to store each pixel
masks:      Four values used to pack RGBA values into pixels
shifts:     Four values used to pack RGBA values into pixels
losses:     Four values used to pack RGBA values into pixels
blit_hw:    1 if hardware Surface blitting is accelerated
blit_hw_CC: 1 if hardware Surface colorkey blitting is accelerated
blit_hw_A:  1 if hardware Surface pixel alpha blitting is
            accelerated
blit_sw:    1 if software Surface blitting is accelerated
blit_sw_CC: 1 if software Surface colorkey blitting is
            accelerated
blit_sw_A:  1 if software Surface pixel alpha blitting is
            accelerated
current_h, current_w:  Height and width of the current video
            mode, or of the desktop mode if called before
            the display.set_mode is called. They are -1 on error.
pixel_format: The pixel format of the display Surface as a string.
            E.g PIXELFORMAT_RGB888.
Changed in pygame-ce 2.4.0: pixel_format attribute added.

pygame.display.get_wm_info()
Get information about the current windowing system
get_wm_info() -> dict
Creates a dictionary filled with string keys. The strings and values are arbitrarily created by the system. Some systems may have no information and an empty dictionary will be returned. Most platforms will return a "window" key with the value set to the system id for the current display.

New in pygame 1.7.1.

pygame.display.get_desktop_sizes()
Get sizes of active desktops
get_desktop_sizes() -> list
This function returns the sizes of the currently configured virtual desktops as a list of (x, y) tuples of integers.

The length of the list is not the same as the number of attached monitors, as a desktop can be mirrored across multiple monitors. The desktop sizes do not indicate the maximum monitor resolutions supported by the hardware, but the desktop size configured in the operating system.

In order to fit windows into the desktop as it is currently configured, and to respect the resolution configured by the operating system in fullscreen mode, this function should be used to replace many use cases of pygame.display.list_modes() whenever applicable.

New in pygame 2.0.0.

pygame.display.list_modes()
Get list of available fullscreen modes
list_modes(depth=0, flags=pygame.FULLSCREEN, display=0) -> list
This function returns a list of possible sizes for a specified color depth. The return value will be an empty list if no display modes are available with the given arguments. A return value of -1 means that any requested size should work (this is likely the case for windowed modes). Mode sizes are sorted from biggest to smallest.

If depth is 0, the current/best color depth for the display is used. The flags defaults to pygame.FULLSCREEN, but you may need to add additional flags for specific fullscreen modes.

The display index 0 means the default display is used.

Since pygame 2.0, pygame.display.get_desktop_sizes() has taken over some use cases from pygame.display.list_modes():

To find a suitable size for non-fullscreen windows, it is preferable to use pygame.display.get_desktop_sizes() to get the size of the current desktop, and to then choose a smaller window size. This way, the window is guaranteed to fit, even when the monitor is configured to a lower resolution than the maximum supported by the hardware.

To avoid changing the physical monitor resolution, it is also preferable to use pygame.display.get_desktop_sizes() to determine the fullscreen resolution. Developers are strongly advised to default to the current physical monitor resolution unless the user explicitly requests a different one (e.g. in an options menu or configuration file).

Changed in pygame 1.9.5: display argument added

pygame.display.mode_ok()
Pick the best color depth for a display mode
mode_ok(size, flags=0, depth=0, display=0) -> depth
This function uses the same arguments as pygame.display.set_mode(). It is used to determine if a requested display mode is available. It will return 0 if the display mode cannot be set. Otherwise it will return a pixel depth that best matches the display asked for.

Usually the depth argument is not passed, but some platforms can support multiple display depths. If passed it will hint to which depth is a better match.

The function will return 0 if the passed display flags cannot be set.

The display index 0 means the default display is used.

Changed in pygame 1.9.5: display argument added

pygame.display.gl_get_attribute()
Get the value for an OpenGL flag for the current display
gl_get_attribute(flag, /) -> value
After calling pygame.display.set_mode() with the pygame.OPENGL flag, it is a good idea to check the value of any requested OpenGL attributes. See pygame.display.gl_set_attribute() for a list of valid flags.

pygame.display.gl_set_attribute()
Request an OpenGL display attribute for the display mode
gl_set_attribute(flag, value, /) -> None
When calling pygame.display.set_mode() with the pygame.OPENGL flag, Pygame automatically handles setting the OpenGL attributes like color and double-buffering. OpenGL offers several other attributes you may want control over. Pass one of these attributes as the flag, and its appropriate value. This must be called before pygame.display.set_mode().

Many settings are the requested minimum. Creating a window with an OpenGL context will fail if OpenGL cannot provide the requested attribute, but it may for example give you a stencil buffer even if you request none, or it may give you a larger one than requested.

The OPENGL flags are:

GL_ALPHA_SIZE, GL_DEPTH_SIZE, GL_STENCIL_SIZE, GL_ACCUM_RED_SIZE,
GL_ACCUM_GREEN_SIZE,  GL_ACCUM_BLUE_SIZE, GL_ACCUM_ALPHA_SIZE,
GL_MULTISAMPLEBUFFERS, GL_MULTISAMPLESAMPLES, GL_STEREO
GL_MULTISAMPLEBUFFERS

Whether to enable multisampling anti-aliasing. Defaults to 0 (disabled).

Set GL_MULTISAMPLESAMPLES to a value above 0 to control the amount of anti-aliasing. A typical value is 2 or 3.

GL_STENCIL_SIZE

Minimum bit size of the stencil buffer. Defaults to 0.

GL_DEPTH_SIZE

Minimum bit size of the depth buffer. Defaults to 16.

GL_STEREO

1 enables stereo 3D. Defaults to 0.

GL_BUFFER_SIZE

Minimum bit size of the frame buffer. Defaults to 0.

New in pygame 2.0.0: Additional attributes:

GL_ACCELERATED_VISUAL,
GL_CONTEXT_MAJOR_VERSION, GL_CONTEXT_MINOR_VERSION,
GL_CONTEXT_FLAGS, GL_CONTEXT_PROFILE_MASK,
GL_SHARE_WITH_CURRENT_CONTEXT,
GL_CONTEXT_RELEASE_BEHAVIOR,
GL_FRAMEBUFFER_SRGB_CAPABLE
GL_CONTEXT_PROFILE_MASK

Sets the OpenGL profile to one of these values:

GL_CONTEXT_PROFILE_CORE             disable deprecated features
GL_CONTEXT_PROFILE_COMPATIBILITY    allow deprecated features
GL_CONTEXT_PROFILE_ES               allow only the ES feature
                                    subset of OpenGL
GL_ACCELERATED_VISUAL

Set to 1 to require hardware acceleration, or 0 to force software render. By default, both are allowed.

pygame.display.get_active()
Returns True when the display is active on the screen
get_active() -> bool
Returns True when the display Surface is considered actively renderable on the screen and may be visible to the user. This is the default state immediately after pygame.display.set_mode(). This method may return True even if the application is fully hidden behind another application window.

This will return False if the display Surface has been iconified or minimized (either via pygame.display.iconify() or via an OS specific method such as the minimize-icon available on most desktops).

The method can also return False for other reasons without the application being explicitly iconified or minimized by the user. A notable example being if the user has multiple virtual desktops and the display Surface is not on the active virtual desktop.

Note This function returning True is unrelated to whether the application has input focus. Please see pygame.key.get_focused() and pygame.mouse.get_focused() for APIs related to input focus.
pygame.display.iconify()
Iconify the display surface
iconify() -> bool
Request the window for the display surface be iconified or hidden. Not all systems and displays support an iconified display. The function will return True if successful.

When the display is iconified pygame.display.get_active() will return False. The event queue should receive an ACTIVEEVENT event when the window has been iconified. Additionally, the event queue also receives a WINDOWEVENT_MINIMIZED event when the window has been iconified on pygame 2.

pygame.display.toggle_fullscreen()
Switch between fullscreen and windowed displays
toggle_fullscreen() -> int
Switches the display window between windowed and fullscreen modes. Display driver support is not great when using pygame 1, but with pygame 2 it is the most reliable method to switch to and from fullscreen.

Supported display drivers in pygame 1:

x11 (Linux/Unix)

wayland (Linux/Unix)

Supported display drivers in pygame 2:

windows (Windows)

x11 (Linux/Unix)

wayland (Linux/Unix)

cocoa (OSX/Mac)

Note toggle_fullscreen() doesn't work on Windows unless the window size is in pygame.display.list_modes()Get list of available fullscreen modes or the window is created with the flag pygame.SCALED. See issue #1221.
pygame.display.set_gamma()
Change the hardware gamma ramps
set_gamma(red, green=None, blue=None, /) -> bool
DEPRECATED: This functionality will go away in SDL3.

Set the red, green, and blue gamma values on the display hardware. If the green and blue arguments are not passed, they will both be the same as red. Not all systems and hardware support gamma ramps, if the function succeeds it will return True.

A gamma value of 1.0 creates a linear color table. Lower values will darken the display and higher values will brighten.

Deprecated since pygame-ce 2.1.4.

pygame.display.set_gamma_ramp()
Change the hardware gamma ramps with a custom lookup
set_gamma_ramp(red, green, blue, /) -> bool
DEPRECATED: This functionality will go away in SDL3.

Set the red, green, and blue gamma ramps with an explicit lookup table. Each argument should be sequence of 256 integers. The integers should range between 0 and 0xffff. Not all systems and hardware support gamma ramps, if the function succeeds it will return True.

Deprecated since pygame-ce 2.1.4.

pygame.display.set_icon()
Change the system image for the display window
set_icon(surface, /) -> None
Sets the runtime icon the system will use to represent the display window. All windows default to a simple pygame logo for the window icon.

Note that calling this function implicitly initializes pygame.display, if it was not initialized before.

You can pass any surface, but most systems want a smaller image around 32x32. The image can have colorkey transparency which will be passed to the system.

Some systems do not allow the window icon to change after it has been shown. This function can be called before pygame.display.set_mode() to create the icon before the display mode is set.

pygame.display.set_caption()
Set the current window caption
set_caption(title, icontitle=None, /) -> None
If the display has a window title, this function will change the name on the window. In pygame 1.x, some systems supported an alternate shorter title to be used for minimized displays, but in pygame 2 icontitle does nothing.

pygame.display.get_caption()
Get the current window caption
get_caption() -> (title, icontitle)
Returns the title and icontitle of the display window. In pygame 2.x these will always be the same value.

pygame.display.set_palette()
Set the display color palette for indexed displays
set_palette(palette=None, /) -> None
This will change the video display color palette for 8-bit displays. This does not change the palette for the actual display Surface, only the palette that is used to display the Surface. If no palette argument is passed, the system default palette will be restored. The palette is a sequence of RGB triplets.

pygame.display.get_num_displays()
Return the number of displays
get_num_displays() -> int
Returns the number of available displays. This is always 1 if pygame.get_sdl_version()get the version number of SDL returns a major version number below 2.

New in pygame 1.9.5.

pygame.display.get_window_size()
Return the size of the window or screen
get_window_size() -> tuple
Returns the size of the window initialized with pygame.display.set_mode()Initialize a window or screen for display. This may differ from the size of the display surface if SCALED is used.

New in pygame 2.0.0.

pygame.display.get_allow_screensaver()
Return whether the screensaver is allowed to run.
get_allow_screensaver() -> bool
Return whether screensaver is allowed to run whilst the app is running. Default is False. By default pygame does not allow the screensaver during game play.

Note Some platforms do not have a screensaver or support disabling the screensaver. Please see pygame.display.set_allow_screensaver()Set whether the screensaver may run for caveats with screensaver support.
New in pygame 2.0.0.

pygame.display.set_allow_screensaver()
Set whether the screensaver may run
set_allow_screensaver(bool) -> None
Change whether screensavers should be allowed whilst the app is running. The default value of the argument to the function is True. By default pygame does not allow the screensaver during game play.

If the screensaver has been disallowed due to this function, it will automatically be allowed to run when pygame.quit()uninitialize all pygame modules is called.

It is possible to influence the default value via the environment variable SDL_HINT_VIDEO_ALLOW_SCREENSAVER, which can be set to either 0 (disable) or 1 (enable).

Note Disabling screensaver is subject to platform support. When platform support is absent, this function will silently appear to work even though the screensaver state is unchanged. The lack of feedback is due to SDL not providing any supported method for determining whether it supports changing the screensaver state.
New in pygame 2.0.0.

pygame.display.is_fullscreen()
Returns True if the pygame window created by pygame.display.set_mode() is in full-screen mode
is_fullscreen() -> bool
Edge cases: If the window is in windowed mode, but maximized, this will return False. If the window is in "borderless fullscreen" mode, this will return True.

New in pygame-ce 2.2.0.

pygame.display.is_vsync()
Returns True if vertical synchronisation for pygame.display.flip() and pygame.display.update() is enabled
is_vsync() -> bool
New in pygame-ce 2.2.0.

pygame.display.get_current_refresh_rate() → int
Returns the screen refresh rate or 0 if unknown
get_current_refresh_rate() -> int
The screen refresh rate for the current window. In windowed mode, this should be equal to the refresh rate of the desktop the window is on.

If no window is open, an exception is raised.

When a constant refresh rate cannot be determined, 0 is returned.

New in pygame-ce 2.2.0.

pygame.display.get_desktop_refresh_rates() → list
Returns the screen refresh rates for all displays (in windowed mode).
get_desktop_refresh_rates() -> list
If the current window is in full-screen mode, the actual refresh rate for that window can differ.

This is safe to call when no window is open (i.e. before any calls to pygame.display.set_mode()Initialize a window or screen for display

When a constant refresh rate cannot be determined, 0 is returned for that desktop.

New in pygame-ce 2.2.0.

pygame.display.message_box()
Create a native GUI message box
message_box(title, message=None, message_type='info', parent_window=None, buttons=('OK',), return_button=0, escape_button=None) -> int
Parameters:
title (str) -- A title string.

message (str) -- A message string. If this parameter is set to None, the message will be the title.

message_type (str) -- Set the type of message_box, could be "info", "warn" or "error".

buttons (tuple) -- An optional sequence of button name strings to show to the user.

return_button (int) -- Button index to use if the return key is hit, 0 by default.

escape_button (int) -- Button index to use if the escape key is hit, None for no button linked by default.

return:
The index of the button that was pushed.

This function should be called on the thread that set_mode() is called. It will block execution of that thread until the user clicks a button or closes the message_box.

This function may be called at any time, even before pygame.init().

Negative values of return_button and escape_button are allowed just like standard Python list indexing.

New in pygame-ce 2.4.0.


pygame.image
pygame module for image transfer
pygame.image.load
load new image from a file (or file-like object)
pygame.image.load_sized_svg
load an SVG image from a file (or file-like object) with the given size
pygame.image.save
save an image to file (or file-like object)
pygame.image.get_sdl_image_version
get version number of the SDL_Image library being used
pygame.image.get_extended
test if extended image formats can be loaded
pygame.image.tostring
transfer image to byte buffer
pygame.image.tobytes
transfer image to byte buffer
pygame.image.fromstring
create new Surface from a byte buffer
pygame.image.frombytes
create new Surface from a byte buffer
pygame.image.frombuffer
create a new Surface that shares data inside a bytes buffer
pygame.image.load_basic
load new BMP image from a file (or file-like object)
pygame.image.load_extended
load an image from a file (or file-like object)
pygame.image.save_extended
save a png/jpg image to file (or file-like object)
The image module contains functions for loading and saving pictures, as well as transferring Surfaces to formats usable by other packages.

Note that there is no Image class; an image is loaded as a Surface object. The Surface class allows manipulation (drawing lines, setting pixels, capturing regions, etc.).

In the vast majority of installations, pygame is built to support extended formats, using the SDL_Image library behind the scenes. However, some installations may only support uncompressed BMP images. With full image support, the pygame.image.load()load new image from a file (or file-like object) function can load the following formats.

BMP

GIF (non-animated)

JPEG

LBM

PCX

PNG

PNM (PBM, PGM, PPM)

QOI

SVG (limited support, using Nano SVG)

TGA (uncompressed)

TIFF

WEBP

XPM

XCF

New in pygame 2.0: Loading SVG, WebP, PNM

New in pygame-ce 2.4.0: Loading QOI (Relies on SDL_Image 2.6.0+)

Saving images only supports a limited set of formats. You can save to the following formats.

BMP

JPEG

PNG

TGA

JPEG and JPG, as well as TIF and TIFF refer to the same file format

New in pygame 1.8: Saving PNG and JPEG files.

pygame.image.load()
load new image from a file (or file-like object)
load(file) -> Surface
load(file, namehint="") -> Surface
Load an image from a file source. You can pass either a filename, a Python file-like object, or a pathlib.Path.

Pygame will automatically determine the image type (e.g., GIF or bitmap) and create a new Surface object from the data. In some cases it will need to know the file extension (e.g., GIF images should end in ".gif"). If you pass a raw file-like object, you may also want to pass the original filename as the namehint argument.

The returned Surface will contain the same color format, colorkey and alpha transparency as the file it came from. You will often want to call pygame.Surface.convert()change the pixel format of an image with no arguments, to create a copy that will draw more quickly on the screen.

For alpha transparency, like in .png images, use the pygame.Surface.convert_alpha()change the pixel format of an image including per pixel alphas method after loading so that the image has per pixel transparency.

Pygame may not always be built to support all image formats. At minimum it will support uncompressed BMP. If pygame.image.get_extended()test if extended image formats can be loaded returns True, you should be able to load most images (including PNG, JPG and GIF).

You should use os.path.join() for compatibility.

eg. asurf = pygame.image.load(os.path.join('data', 'bla.png'))
Changed in pygame-ce 2.2.0: Now supports keyword arguments.

pygame.image.load_sized_svg()
load an SVG image from a file (or file-like object) with the given size
load_sized_svg(file, size) -> Surface
This function rasterizes the input SVG at the size specified by the size argument. The file argument can be either a filename, a Python file-like object, or a pathlib.Path.

The usage of this function for handling SVGs is recommended, as calling the regular load function and then scaling the returned surface would not preserve the quality that an SVG can provide.

It is to be noted that this function does not return a surface whose dimensions exactly match the size argument. This function preserves aspect ratio, so the returned surface could be smaller along at most one dimension.

This function requires SDL_image 2.6.0 or above. If pygame was compiled with an older version, pygame.error will be raised when this function is called.

New in pygame-ce 2.4.0.

pygame.image.save()
save an image to file (or file-like object)
save(Surface, file) -> None
save(Surface, file, namehint="") -> None
This will save your Surface as either a BMP, TGA, PNG, or JPEG image. If the filename extension is unrecognized it will default to TGA. Both TGA, and BMP file formats create uncompressed files. You can pass a filename, a pathlib.Path or a Python file-like object. For file-like object, the image is saved to TGA format unless a namehint with a recognizable extension is passed in.

Note When saving to a file-like object, it seems that for most formats, the object needs to be flushed after saving to it to make loading from it possible.
Changed in pygame 1.8: Saving PNG and JPEG files.

Changed in pygame 2.0.0: The namehint parameter was added to make it possible to save other formats than TGA to a file-like object. Saving to a file-like object with JPEG is possible.

Changed in pygame-ce 2.2.0: Now supports keyword arguments.

pygame.image.get_sdl_image_version()
get version number of the SDL_Image library being used
get_sdl_image_version(linked=True) -> None
get_sdl_image_version(linked=True) -> (major, minor, patch)
If pygame is built with extended image formats, then this function will return the SDL_Image library's version number as a tuple of 3 integers (major, minor, patch). If not, then it will return None.

linked=True is the default behavior and the function will return the version of the library that Pygame is linked against, while linked=False will return the version of the library that Pygame is compiled against.

New in pygame 2.0.0.

Changed in pygame-ce 2.1.4: linked keyword argument added and default behavior changed from returning compiled version to returning linked version

pygame.image.get_extended()
test if extended image formats can be loaded
get_extended() -> bool
If pygame is built with extended image formats this function will return True. It is still not possible to determine which formats will be available, but generally you will be able to load them all.

pygame.image.tostring()
transfer image to byte buffer
tostring(Surface, format, flipped=False, pitch=-1) -> bytes
DEPRECATED: This function has the same functionality as tobytes(), which is preferred and should be used.

Deprecated since pygame-ce 2.3.0.

pygame.image.tobytes()
transfer image to byte buffer
tobytes(Surface, format, flipped=False, pitch=-1) -> bytes
Creates a string of bytes that can be transferred with the fromstring or frombytes methods in other Python imaging packages. Some Python image packages prefer their images in bottom-to-top format (PyOpenGL for example). If you pass True for the flipped argument, the byte buffer will be vertically flipped.

The format argument is a string of one of the following values. Note that only 8-bit Surfaces can use the "P" format. The other formats will work for any Surface. Also note that other Python image packages support more formats than pygame.

P, 8-bit palettized Surfaces

RGB, 24-bit image

RGBX, 32-bit image with unused space

RGBA, 32-bit image with an alpha channel

ARGB, 32-bit image with alpha channel first

BGRA, 32-bit image with alpha channel, red and blue channels swapped

RGBA_PREMULT, 32-bit image with colors scaled by alpha channel

ARGB_PREMULT, 32-bit image with colors scaled by alpha channel, alpha channel first

The 'pitch' argument can be used to specify the pitch/stride per horizontal line of the image in bytes. It must be equal to or greater than how many bytes the pixel data of each horizontal line in the image bytes occupies without any extra padding. By default, it is -1, which means that the pitch/stride is the same size as how many bytes the pure pixel data of each horizontal line takes.

Note The use of this function is recommended over tostring() as of pygame 2.1.3. This function was introduced so it matches nicely with other libraries (PIL, numpy, etc), and with people's expectations.
New in pygame-ce 2.1.3.

Changed in pygame-ce 2.2.0: Now supports keyword arguments.

Changed in pygame-ce 2.5.0: Added a 'pitch' argument.

pygame.image.fromstring()
create new Surface from a byte buffer
fromstring(bytes, size, format, flipped=False, pitch=-1) -> Surface
DEPRECATED: This function has the same functionality as frombytes(), which is preferred and should be used.

Deprecated since pygame-ce 2.3.0.

pygame.image.frombytes()
create new Surface from a byte buffer
frombytes(bytes, size, format, flipped=False, pitch=-1) -> Surface
This function takes arguments similar to pygame.image.tobytes()transfer image to byte buffer. The size argument is a pair of numbers representing the width and height. Once the new Surface is created it is independent from the memory of the bytes passed in.

The bytes and format passed must compute to the exact size of image specified. Otherwise a ValueError will be raised.

The 'pitch' argument can be used specify the pitch/stride per horizontal line of the image bytes in bytes. It must be equal to or greater than how many bytes the pixel data of each horizontal line in the image bytes occupies without any extra padding. By default, it is -1, which means that the pitch/stride is the same size as how many bytes the pure pixel data of each horizontal line takes.

See the pygame.image.frombuffer()create a new Surface that shares data inside a bytes buffer method for a potentially faster way to transfer images into pygame.

Note The use of this function is recommended over fromstring() as of pygame 2.1.3. This function was introduced so it matches nicely with other libraries (PIL, numpy, etc), and with people's expectations.
New in pygame-ce 2.1.3.

New in pygame-ce 2.1.4: Added a 'pitch' argument and support for keyword arguments.

pygame.image.frombuffer()
create a new Surface that shares data inside a bytes buffer
frombuffer(buffer, size, format, pitch=-1) -> Surface
Create a new Surface that shares pixel data directly from a buffer. This buffer can be bytes, a bytearray, a memoryview, a pygame.BufferProxypygame object to export a surface buffer through an array protocol, or any object that supports the buffer protocol. This method takes similar arguments to pygame.image.fromstring()create new Surface from a byte buffer, but is unable to vertically flip the source data.

This will run much faster than pygame.image.fromstring()create new Surface from a byte buffer, since no pixel data must be allocated and copied.

It accepts the following 'format' arguments:

P, 8-bit palettized Surfaces

RGB, 24-bit image

BGR, 24-bit image, red and blue channels swapped.

RGBX, 32-bit image with unused space

RGBA, 32-bit image with an alpha channel

ARGB, 32-bit image with alpha channel first

BGRA, 32-bit image with alpha channel, red and blue channels swapped

The 'pitch' argument can be used specify the pitch/stride per horizontal line of the image buffer in bytes. It must be equal to or greater than how many bytes the pixel data of each horizontal line in the image buffer occupies without any extra padding. By default, it is -1, which means that the pitch/stride is the same size as how many bytes the pure pixel data of each horizontal line takes.

New in pygame-ce 2.1.3: BGRA format

New in pygame-ce 2.1.4: Added a 'pitch' argument and support for keyword arguments.

pygame.image.load_basic()
load new BMP image from a file (or file-like object)
load_basic(file, /) -> Surface
Load an image from a file source. You can pass either a filename or a Python file-like object, or a pathlib.Path.

This function only supports loading "basic" image format, ie BMP format. This function is always available, no matter how pygame was built.

pygame.image.load_extended()
load an image from a file (or file-like object)
load_extended(file) -> Surface
load_extended(file, namehint="") -> Surface
This function is similar to pygame.image.load()load new image from a file (or file-like object), except that this function can only be used if pygame was built with extended image format support.

Changed in pygame 2.0.1: This function is always available, but raises an NotImplementedError if extended image formats are not supported. Previously, this function may or may not be available, depending on the state of extended image format support.

Changed in pygame-ce 2.2.0: Now supports keyword arguments.

pygame.image.save_extended()
save a png/jpg image to file (or file-like object)
save_extended(Surface, file) -> None
save_extended(Surface, file, namehint="") -> None
This will save your Surface as either a PNG or JPEG image.

In case the image is being saved to a file-like object, this function uses the namehint argument to determine the format of the file being saved. Saves to JPEG in case the namehint was not specified while saving to a file-like object.

Changed in pygame 2.0.1: This function is always available, but raises an NotImplementedError if extended image formats are not supported. Previously, this function may or may not be available, depending on the state of extended image format support.

Changed in pygame-ce 2.2.0: Now supports keyword arguments.

pygame.Surface
pygame object for representing images
Surface((width, height), flags=0, depth=0, masks=None) -> Surface
Surface((width, height), flags=0, Surface) -> Surface
pygame.Surface.blit
draw another surface onto this one
pygame.Surface.blits
draw many images onto another
pygame.Surface.fblits
draw many surfaces onto the calling surface at their corresponding location and the same special_flags
pygame.Surface.convert
change the pixel format of an image
pygame.Surface.convert_alpha
change the pixel format of an image including per pixel alphas
pygame.Surface.copy
create a new copy of a Surface
pygame.Surface.fill
fill Surface with a solid color
pygame.Surface.scroll
Shift the surface image in place
pygame.Surface.set_colorkey
Set the transparent colorkey
pygame.Surface.get_colorkey
Get the current transparent colorkey
pygame.Surface.set_alpha
set the alpha value for the full Surface image
pygame.Surface.get_alpha
get the current Surface transparency value
pygame.Surface.lock
lock the Surface memory for pixel access
pygame.Surface.unlock
unlock the Surface memory from pixel access
pygame.Surface.mustlock
test if the Surface requires locking
pygame.Surface.get_locked
test if the Surface is current locked
pygame.Surface.get_locks
Gets the locks for the Surface
pygame.Surface.get_at
get the color value at a single pixel
pygame.Surface.set_at
set the color value for a single pixel
pygame.Surface.get_at_mapped
get the mapped color value at a single pixel
pygame.Surface.get_palette
get the color index palette for an 8-bit Surface
pygame.Surface.get_palette_at
get the color for a single entry in a palette
pygame.Surface.set_palette
set the color palette for an 8-bit Surface
pygame.Surface.set_palette_at
set the color for a single index in an 8-bit Surface palette
pygame.Surface.map_rgb
convert a color into a mapped color value
pygame.Surface.unmap_rgb
convert a mapped integer color value into a Color
pygame.Surface.set_clip
set the current clipping area of the Surface
pygame.Surface.get_clip
get the current clipping area of the Surface
pygame.Surface.subsurface
create a new surface that references its parent
pygame.Surface.get_parent
find the parent of a subsurface
pygame.Surface.get_abs_parent
find the top level parent of a subsurface
pygame.Surface.get_offset
find the position of a child subsurface inside a parent
pygame.Surface.get_abs_offset
find the absolute position of a child subsurface inside its top level parent
pygame.Surface.get_size
get the dimensions of the Surface
pygame.Surface.get_width
get the width of the Surface
pygame.Surface.get_height
get the height of the Surface
pygame.Surface.get_rect
get the rectangular area of the Surface
pygame.Surface.get_frect
get the rectangular area of the Surface
pygame.Surface.get_bitsize
get the bit depth of the Surface pixel format
pygame.Surface.get_bytesize
get the bytes used per Surface pixel
pygame.Surface.get_flags
get the additional flags used for the Surface
pygame.Surface.get_pitch
get the number of bytes used per Surface row
pygame.Surface.get_masks
the bitmasks needed to convert between a color and a mapped integer
pygame.Surface.set_masks
set the bitmasks needed to convert between a color and a mapped integer
pygame.Surface.get_shifts
the bit shifts needed to convert between a color and a mapped integer
pygame.Surface.set_shifts
sets the bit shifts needed to convert between a color and a mapped integer
pygame.Surface.get_losses
the significant bits used to convert between a color and a mapped integer
pygame.Surface.get_bounding_rect
find the smallest rect containing data
pygame.Surface.get_view
return a buffer view of the Surface's pixels.
pygame.Surface.get_buffer
acquires a buffer object for the pixels of the Surface.
pygame.Surface._pixels_address
pixel buffer address
pygame.Surface.premul_alpha
returns a copy of the surface with the RGB channels pre-multiplied by the alpha channel.
A pygame Surface is used to represent any image. The Surface has a fixed resolution and pixel format. Surfaces with 8-bit pixels use a color palette to map to 24-bit color.

Call pygame.Surface()pygame object for representing images to create a new image object. The Surface will be cleared to all black. The only required arguments are the sizes. With no additional arguments, the Surface will be created in a format that best matches the display Surface.

The pixel format can be controlled by passing the bit depth or an existing Surface. The flags argument is a bitmask of additional features for the surface. You can pass any combination of these flags:

HWSURFACE    (obsolete in pygame 2) creates the image in video memory
SRCALPHA     the pixel format will include a per-pixel alpha
Both flags are only a request, and may not be possible for all displays and formats.

Advance users can combine a set of bitmasks with a depth value. The masks are a set of 4 integers representing which bits in a pixel will represent each color. Normal Surfaces should not require the masks argument.

Surfaces can have many extra attributes like alpha planes, colorkeys, source rectangle clipping. These functions mainly effect how the Surface is blitted to other Surfaces. The blit routines will attempt to use hardware acceleration when possible, otherwise they will use highly optimized software blitting methods.

There are three types of transparency supported in pygame: colorkeys, surface alphas, and pixel alphas. Surface alphas can be mixed with colorkeys, but an image with per pixel alphas cannot use the other modes. Colorkey transparency makes a single color value transparent. Any pixels matching the colorkey will not be drawn. The surface alpha value is a single value that changes the transparency for the entire image. A surface alpha of 255 is opaque, and a value of 0 is completely transparent.

Per pixel alphas are different because they store a transparency value for every pixel. This allows for the most precise transparency effects, but it also the slowest. Per pixel alphas cannot be mixed with surface alpha and colorkeys.

There is support for pixel access for the Surfaces. Pixel access on hardware surfaces is slow and not recommended. Pixels can be accessed using the get_at() and set_at() functions. These methods are fine for simple access, but will be considerably slow when doing of pixel work with them. If you plan on doing a lot of pixel level work, it is recommended to use a pygame.PixelArraypygame object for direct pixel access of surfaces, which gives an array like view of the surface. For involved mathematical manipulations try the pygame.surfarraypygame module for accessing surface pixel data using array interfaces module (It's quite quick, but requires NumPy.)

Any functions that directly access a surface's pixel data will need that surface to be lock()'ed. These functions can lock() and unlock() the surfaces themselves without assistance. But, if a function will be called many times, there will be a lot of overhead for multiple locking and unlocking of the surface. It is best to lock the surface manually before making the function call many times, and then unlocking when you are finished. All functions that need a locked surface will say so in their docs. Remember to leave the Surface locked only while necessary.

Surface pixels are stored internally as a single number that has all the colors encoded into it. Use the map_rgb() and unmap_rgb() to convert between individual red, green, and blue values into a packed integer for that Surface.

Surfaces can also reference sections of other Surfaces. These are created with the subsurface() method. Any change to either Surface will effect the other.

Each Surface contains a clipping area. By default the clip area covers the entire Surface. If it is changed, all drawing operations will only effect the smaller area.

blit()
draw another surface onto this one
blit(source, dest, area=None, special_flags=0) -> Rect
Draws another Surface onto this Surface.

Parameters
source
The Surface object to draw onto this Surface. If it has transparency, transparent pixels will be ignored when blittting to an 8-bit Surface.

dest
The source draw position onto this Surface. It can be a coordinate (x, y) or a Rect (using its top-left corner). If a Rect is passed, its size will not affect the blit.

area (optional)
The rectangular portion of the source to draw. It can be a Rect object representing that section. If None or not provided, the entire source surface will be drawn. If the Rect has negative position, the final blit position will be dest - Rect.topleft.

special_flags (optional)
Controls how the colors of the source are combined with this Surface. If not provided it defaults to BLENDMODE_NONE (0). See special flags for a list of possible values.

Return
A pygame.Rectpygame object for storing rectangular coordinates object representing the affected area of this Surface that was modified by the blit operation. This area includes only the pixels within this Surface or its clipping area (see set_clip()). Generally you don't need to use this return value, as it was initially designed to pass it to pygame.display.update()Update all, or a portion, of the display. For non-OpenGL displays. to optimize the updating of the display. Since modern computers are fast enough to update the entire display at high speeds, this return value is rarely used nowadays.

Example Use
# create a surface of size 50x50 and fill it with red color
red_surf = pygame.Surface((50, 50))
red_surf.fill("red")

# draw the surface on another surface at position (0, 0)
another_surface.blit(red_surf, (0, 0))
Notes
When self-blitting and there is a colorkey or alpha transparency set, resulting colors may appear slightly different compared to a non-self blit.

The blit is ignored if the source is positioned completely outside this Surface's clipping area. Otherwise only the overlapping area will be drawn.

blits()
draw many images onto another
blits(blit_sequence=((source, dest), ...), doreturn=True) -> [Rect, ...] or None
blits(((source, dest, area), ...)) -> [Rect, ...]
blits(((source, dest, area, special_flags), ...)) -> [Rect, ...]
The blits method efficiently draws a sequence of surfaces onto this Surface.

Parameters

blit_sequence
A sequence that contains each surface to be drawn along with its associated blit arguments. See the Sequence Item Formats section below for the possible formats.

doreturn (optional)
The doreturn parameter controls the return value. When set to True, it returns a list of rectangles representing the changed areas. When set to False, returns None.

Return

A list of rectangles or None.

Sequence Item Formats

(source, dest)
source: Surface object to be drawn.

dest: Position where the source Surface should be blitted.

(source, dest, area)
area: (optional) Specific area of the source Surface to be drawn.

(source, dest, area, special_flags)
special_flags: (optional) Controls the blending mode for drawing colors. See special flags for a list of possible values.

Notes

blits is an advanced method. It is recommended to read the documentation of blit() first.

To draw a Surface with a special flag, you must specify an area as well, e.g., (source, dest, None, special_flags).

Prefer using blits() over blit() when drawing a multiple images for better performance. Use blit() if you need to draw a single image.

For drawing a sequence of (source, dest) pairs with whole source Surface and a singular special_flag, use the fblits() method.

New in pygame 1.9.4.

fblits()
draw many surfaces onto the calling surface at their corresponding location and the same special_flags
fblits(blit_sequence=((source, dest), ...), special_flags=0, /) -> None
This method takes a sequence of tuples (source, dest) as input, where source is a Surface object and dest is its destination position on this Surface. It draws each source Surface fully (meaning that unlike blit() you cannot pass an "area" parameter to represent a smaller portion of the source Surface to draw) on this Surface with the same blending mode specified by special_flags. The sequence must have at least one (source, dest) pair.

Parameters:
blit_sequence -- a sequence of (source, dest)

special_flags -- the flag(s) representing the blend mode used for each surface. See special flags for a list of possible values.

Returns:
None

Note This method only accepts a sequence of (source, dest) pairs and a single special_flags value that's applied to all surfaces drawn. This allows faster iteration over the sequence and better performance over blits(). Further optimizations are applied if blit_sequence is a list or a tuple (using one of them is recommended).
New in pygame-ce 2.1.4.

convert()
change the pixel format of an image
convert(surface, /) -> Surface
convert(depth, flags=0, /) -> Surface
convert(masks, flags=0, /) -> Surface
convert() -> Surface
Creates a new copy of the Surface with the pixel format changed. The new pixel format can be determined from another existing Surface. Otherwise depth, flags, and masks arguments can be used, similar to the pygame.Surface()pygame object for representing images call.

If no arguments are passed the new Surface will have the same pixel format as the display Surface. This is always the fastest format for blitting. It is a good idea to convert all Surfaces before they are blitted many times.

The converted Surface will have no pixel alphas. They will be stripped if the original had them. See convert_alpha() for preserving or creating per-pixel alphas.

The new copy will have the same class as the copied surface. This lets as Surface subclass inherit this method without the need to override, unless subclass specific instance attributes also need copying.

convert_alpha()
change the pixel format of an image including per pixel alphas
convert_alpha() -> Surface
Creates a new copy of the surface with the desired pixel format. The new surface will be in a format suited for quick blitting to the display surface with per pixel alpha.

Unlike the convert() method, the pixel format for the new image will not be exactly the same as the display surface, but it will be optimized for fast alpha blitting to it.

As with convert() the returned surface has the same class as the converted surface.

Changed in pygame-ce 2.4.0: 'Surface' argument deprecated.

copy()
create a new copy of a Surface
copy() -> Surface
Makes a duplicate copy of a Surface. The new surface will have the same pixel formats, color palettes, transparency settings, and class as the original. If a Surface subclass also needs to copy any instance specific attributes then it should override copy(). Shallow copy and deepcopy are supported, Surface implements __copy__ and __deepcopy__ respectively.

New in pygame-ce 2.3.1: Added support for deepcopy by implementing __deepcopy__, calls copy() internally.

fill()
fill Surface with a solid color
fill(color, rect=None, special_flags=0) -> Rect
Fill the Surface with a solid color. If no rect argument is given the entire Surface will be filled. The rect argument will limit the fill to a specific area. The fill will also be contained by the Surface clip area.

The color argument can be an RGB sequence, an RGBA sequence, a string (for Named Colors), or a mapped color index. If using RGBA, the Alpha (A part of RGBA) is ignored unless the surface uses per pixel alpha (Surface has the SRCALPHA flag).

The special_flags argument controls how the colors are combined. See special flags for a list of possible values.

This will return the affected Surface area.

scroll()
Shift the surface image in place
scroll(dx=0, dy=0, /) -> None
Move the image by dx pixels right and dy pixels down. dx and dy may be negative for left and up scrolls respectively. Areas of the surface that are not overwritten retain their original pixel values. Scrolling is contained by the Surface clip area. It is safe to have dx and dy values that exceed the surface size.

New in pygame 1.9.

set_colorkey()
Set the transparent colorkey
set_colorkey(color, flags=0, /) -> None
set_colorkey(None) -> None
Set the current color key for the Surface. When blitting this Surface onto a destination, any pixels that have the same color as the colorkey will be transparent. The color can be an RGB color, a string (for Named Colors), or a mapped color integer. If None is passed, the colorkey will be unset.

The colorkey will be ignored if the Surface is formatted to use per pixel alpha values. The colorkey can be mixed with the full Surface alpha value.

The optional flags argument can be set to pygame.RLEACCEL to provide better performance on non accelerated displays. An RLEACCEL Surface will be slower to modify, but quicker to blit as a source.

get_colorkey()
Get the current transparent colorkey
get_colorkey() -> RGB or None
Return the current colorkey value for the Surface. If the colorkey is not set then None is returned.

set_alpha()
set the alpha value for the full Surface image
set_alpha(value, flags=0, /) -> None
set_alpha(None) -> None
Set the current alpha value for the Surface. When blitting this Surface onto a destination, the pixels will be drawn slightly transparent. The alpha value is an integer from 0 to 255, 0 is fully transparent and 255 is fully opaque. If None is passed for the alpha value, then alpha blending will be disabled, including per-pixel alpha.

This value is different than the per pixel Surface alpha. For a surface with per pixel alpha, blanket alpha is ignored and None is returned.

Changed in pygame 2.0: per-surface alpha can be combined with per-pixel alpha.

The optional flags argument can be set to pygame.RLEACCEL to provide better performance on non accelerated displays. An RLEACCEL Surface will be slower to modify, but quicker to blit as a source.

get_alpha()
get the current Surface transparency value
get_alpha() -> int_value
Return the current alpha value for the Surface.

lock()
lock the Surface memory for pixel access
lock() -> None
Lock the pixel data of a Surface for access. On accelerated Surfaces, the pixel data may be stored in volatile video memory or nonlinear compressed forms. When a Surface is locked the pixel memory becomes available to access by regular software. Code that reads or writes pixel values will need the Surface to be locked.

Surfaces should not remain locked for more than necessary. A locked Surface can often not be displayed or managed by pygame.

Not all Surfaces require locking. The mustlock() method can determine if it is actually required. There is no performance penalty for locking and unlocking a Surface that does not need it.

All pygame functions will automatically lock and unlock the Surface data as needed. If a section of code is going to make calls that will repeatedly lock and unlock the Surface many times, it can be helpful to wrap the block inside a lock and unlock pair.

It is safe to nest locking and unlocking calls. The surface will only be unlocked after the final lock is released.

unlock()
unlock the Surface memory from pixel access
unlock() -> None
Unlock the Surface pixel data after it has been locked. The unlocked Surface can once again be drawn and managed by pygame. See the lock() documentation for more details.

All pygame functions will automatically lock and unlock the Surface data as needed. If a section of code is going to make calls that will repeatedly lock and unlock the Surface many times, it can be helpful to wrap the block inside a lock and unlock pair.

It is safe to nest locking and unlocking calls. The surface will only be unlocked after the final lock is released.

mustlock()
test if the Surface requires locking
mustlock() -> bool
Returns True if the Surface is required to be locked to access pixel data. Usually pure software Surfaces do not require locking. This method is rarely needed, since it is safe and quickest to just lock all Surfaces as needed.

All pygame functions will automatically lock and unlock the Surface data as needed. If a section of code is going to make calls that will repeatedly lock and unlock the Surface many times, it can be helpful to wrap the block inside a lock and unlock pair.

get_locked()
test if the Surface is current locked
get_locked() -> bool
Returns True when the Surface is locked. It doesn't matter how many times the Surface is locked.

get_locks()
Gets the locks for the Surface
get_locks() -> tuple
Returns the currently existing locks for the Surface.

get_at()
get the color value at a single pixel
get_at((x, y), /) -> Color
Return a copy of the RGBA Color value at the given pixel. If the Surface has no per pixel alpha, then the alpha value will always be 255 (opaque). If the pixel position is outside the area of the Surface an IndexError exception will be raised.

Getting and setting pixels one at a time is generally too slow to be used in a game or realtime situation. It is better to use methods which operate on many pixels at a time like with the blit, fill and draw methods - or by using pygame.surfarraypygame module for accessing surface pixel data using array interfaces/pygame.PixelArraypygame object for direct pixel access of surfaces.

This function will temporarily lock and unlock the Surface as needed.

Changed in pygame-ce 2.3.1: can now also accept both float coordinates and Vector2s for pixels.

Returning a Color instead of tuple. Use tuple(surf.get_at((x,y))) if you want a tuple, and not a Color. This should only matter if you want to use the color as a key in a dict.

New in pygame 1.9.

set_at()
set the color value for a single pixel
set_at((x, y), color, /) -> None
Set the color of a single pixel at the specified coordinates to be an RGB, RGBA, string (for Named Colors), or mapped integer color value. If the Surface does not have per pixel alphas, the alpha value is ignored. Setting pixels outside the Surface area or outside the Surface clipping will have no effect.

Getting and setting pixels one at a time is generally too slow to be used in a game or realtime situation.

This function will temporarily lock and unlock the Surface as needed.

Note If the surface is palettized, the pixel color will be set to the most similar color in the palette.
Changed in pygame-ce 2.3.1: can now also accept both float coordinates and Vector2s for pixels.

get_at_mapped()
get the mapped color value at a single pixel
get_at_mapped((x, y), /) -> Color
Return the integer value of the given pixel. If the pixel position is outside the area of the Surface an IndexError exception will be raised.

This method is intended for pygame unit testing. It unlikely has any use in an application.

This function will temporarily lock and unlock the Surface as needed.

New in pygame 1.9.2.

Changed in pygame-ce 2.3.1: can now also accept both float coordinates and Vector2s for pixels.

get_palette()
get the color index palette for an 8-bit Surface
get_palette() -> [RGB, RGB, RGB, ...]
Return a list of up to 256 color elements that represent the indexed colors used in an 8-bit Surface. The returned list is a copy of the palette, and changes will have no effect on the Surface.

Returning a list of Color(with length 3) instances instead of tuples.

New in pygame 1.9.

get_palette_at()
get the color for a single entry in a palette
get_palette_at(index, /) -> RGB
Returns the red, green, and blue color values for a single index in a Surface palette. The index should be a value from 0 to 255.

New in pygame 1.9: Returning Color(with length 3) instance instead of a tuple.

set_palette()
set the color palette for an 8-bit Surface
set_palette([RGB, RGB, RGB, ...], /) -> None
Set the full palette for an 8-bit Surface. This will replace the colors in the existing palette. A partial palette can be passed and only the first colors in the original palette will be changed.

This function has no effect on a Surface with more than 8-bits per pixel.

set_palette_at()
set the color for a single index in an 8-bit Surface palette
set_palette_at(index, RGB, /) -> None
Set the palette value for a single entry in a Surface palette. The index should be a value from 0 to 255.

This function has no effect on a Surface with more than 8-bits per pixel.

map_rgb()
convert a color into a mapped color value
map_rgb(color, /) -> mapped_int
Convert an RGBA color into the mapped integer value for this Surface. The returned integer will contain no more bits than the bit depth of the Surface. Mapped color values are not often used inside pygame, but can be passed to most functions that require a Surface and a color.

See the Surface object documentation for more information about colors and pixel formats.

unmap_rgb()
convert a mapped integer color value into a Color
unmap_rgb(mapped_int, /) -> Color
Convert an mapped integer color into the RGB color components for this Surface. Mapped color values are not often used inside pygame, but can be passed to most functions that require a Surface and a color.

See the Surface object documentation for more information about colors and pixel formats.

set_clip()
set the current clipping area of the Surface
set_clip(rect, /) -> None
set_clip(None) -> None
Each Surface has an active clipping area. This is a rectangle that represents the only pixels on the Surface that can be modified. If None is passed for the rectangle the full Surface will be available for changes.

The clipping area is always restricted to the area of the Surface itself. If the clip rectangle is too large it will be shrunk to fit inside the Surface.

get_clip()
get the current clipping area of the Surface
get_clip() -> Rect
Return a rectangle of the current clipping area. The Surface will always return a valid rectangle that will never be outside the bounds of the image. If the Surface has had None set for the clipping area, the Surface will return a rectangle with the full area of the Surface.

subsurface()
create a new surface that references its parent
subsurface(rect, /) -> Surface
Returns a new Surface that shares its pixels with its new parent. The new Surface is considered a child of the original. Modifications to either Surface pixels will effect each other. Surface information like clipping area and color keys are unique to each Surface.

The new Surface will inherit the palette, color key, and alpha settings from its parent.

It is possible to have any number of subsurfaces and subsubsurfaces on the parent. It is also possible to subsurface the display Surface if the display mode is not hardware accelerated.

See get_offset() and get_parent() to learn more about the state of a subsurface.

A subsurface will have the same class as the parent surface.

get_parent()
find the parent of a subsurface
get_parent() -> Surface
Returns the parent Surface of a subsurface. If this is not a subsurface then None will be returned.

get_abs_parent()
find the top level parent of a subsurface
get_abs_parent() -> Surface
Returns the parent Surface of a subsurface. If this is not a subsurface then this surface will be returned.

get_offset()
find the position of a child subsurface inside a parent
get_offset() -> (x, y)
Get the offset position of a child subsurface inside of a parent. If the Surface is not a subsurface this will return (0, 0).

get_abs_offset()
find the absolute position of a child subsurface inside its top level parent
get_abs_offset() -> (x, y)
Get the offset position of a child subsurface inside of its top level parent Surface. If the Surface is not a subsurface this will return (0, 0).

get_size()
get the dimensions of the Surface
get_size() -> (width, height)
Return the width and height of the Surface in pixels.

get_width()
get the width of the Surface
get_width() -> width
Return the width of the Surface in pixels.

get_height()
get the height of the Surface
get_height() -> height
Return the height of the Surface in pixels.

get_rect()
get the rectangular area of the Surface
get_rect(**kwargs) -> Rect
Returns a new rectangle covering the entire surface. This rectangle will always start at (0, 0) with a width and height the same size as the image.

You can pass keyword argument values to this function. These named values will be applied to the attributes of the Rect before it is returned. An example would be mysurf.get_rect(center=(100, 100)) to create a rectangle for the Surface centered at a given position.

get_frect()
get the rectangular area of the Surface
get_frect(**kwargs) -> FRect
This is the same as Surface.get_rect() but returns an FRect. FRect is similar to Rect, except it stores float values instead.

You can pass keyword argument values to this function. These named values will be applied to the attributes of the FRect before it is returned. An example would be mysurf.get_frect(center=(100.5, 100.5)) to create a rectangle for the Surface centered at a given position.

get_bitsize()
get the bit depth of the Surface pixel format
get_bitsize() -> int
Returns the number of bits used to represent each pixel. This value may not exactly fill the number of bytes used per pixel. For example a 15 bit Surface still requires a full 2 bytes.

get_bytesize()
get the bytes used per Surface pixel
get_bytesize() -> int
Return the number of bytes used per pixel.

get_flags()
get the additional flags used for the Surface
get_flags() -> int
Returns a set of current Surface features. Each feature is a bit in the flags bitmask. Typical flags are RLEACCEL, SRCALPHA, and SRCCOLORKEY.

Here is a more complete list of flags. A full list can be found in SDL_video.h

SWSURFACE      0x00000000    # Surface is in system memory
HWSURFACE      0x00000001    # (obsolete in pygame 2) Surface is in video memory
ASYNCBLIT      0x00000004    # (obsolete in pygame 2) Use asynchronous blits if possible
See pygame.display.set_mode()Initialize a window or screen for display for flags exclusive to the display surface.

Used internally (read-only)

HWACCEL        0x00000100    # Blit uses hardware acceleration
SRCCOLORKEY    0x00001000    # Blit uses a source color key
RLEACCELOK     0x00002000    # Private flag
RLEACCEL       0x00004000    # Surface is RLE encoded
SRCALPHA       0x00010000    # Blit uses source alpha blending
PREALLOC       0x01000000    # Surface uses preallocated memory
get_pitch()
get the number of bytes used per Surface row
get_pitch() -> int
Return the number of bytes separating each row in the Surface. Surfaces in video memory are not always linearly packed. Subsurfaces will also have a larger pitch than their real width.

This value is not needed for normal pygame usage.

get_masks()
the bitmasks needed to convert between a color and a mapped integer
get_masks() -> (R, G, B, A)
Returns the bitmasks used to isolate each color in a mapped integer.

This value is not needed for normal pygame usage.

set_masks()
set the bitmasks needed to convert between a color and a mapped integer
set_masks((r, g, b, a), /) -> None
This is not needed for normal pygame usage.

Note Starting in pygame 2.0, the masks are read-only and accordingly this method will raise a TypeError if called.
Deprecated since pygame 2.0.0.

New in pygame 1.8.1.

get_shifts()
the bit shifts needed to convert between a color and a mapped integer
get_shifts() -> (R, G, B, A)
Returns the pixel shifts need to convert between each color and a mapped integer.

This value is not needed for normal pygame usage.

set_shifts()
sets the bit shifts needed to convert between a color and a mapped integer
set_shifts((r, g, b, a), /) -> None
This is not needed for normal pygame usage.

Note Starting in pygame 2.0, the shifts are read-only and accordingly this method will raise a TypeError if called.
Deprecated since pygame 2.0.0.

New in pygame 1.8.1.

get_losses()
the significant bits used to convert between a color and a mapped integer
get_losses() -> (R, G, B, A)
Return the least significant number of bits stripped from each color in a mapped integer.

This value is not needed for normal pygame usage.

get_bounding_rect()
find the smallest rect containing data
get_bounding_rect(min_alpha = 1) -> Rect
Returns the smallest rectangular region that contains all the pixels in the surface that have an alpha value greater than or equal to the minimum alpha value.

This function will temporarily lock and unlock the Surface as needed.

New in pygame 1.8.

get_view()
return a buffer view of the Surface's pixels.
get_view(kind='2', /) -> BufferProxy
Return an object which exports a surface's internal pixel buffer as a C level array struct, Python level array interface or a C level buffer interface. The new buffer protocol is supported.

The kind argument is the length 1 string '0', '1', '2', '3', 'r', 'g', 'b', or 'a'. The letters are case insensitive; 'A' will work as well. The argument can be either a Unicode or byte (char) string. The default is '2'.

'0' returns a contiguous unstructured bytes view. No surface shape information is given. A ValueError is raised if the surface's pixels are discontinuous.

'1' returns a (surface-width * surface-height) array of continuous pixels. A ValueError is raised if the surface pixels are discontinuous.

'2' returns a (surface-width, surface-height) array of raw pixels. The pixels are surface-bytesize-d unsigned integers. The pixel format is surface specific. The 3 byte unsigned integers of 24 bit surfaces are unlikely accepted by anything other than other pygame functions.

'3' returns a (surface-width, surface-height, 3) array of RGB color components. Each of the red, green, and blue components are unsigned bytes. Only 24-bit and 32-bit surfaces are supported. The color components must be in either RGB or BGR order within the pixel.

'r' for red, 'g' for green, 'b' for blue, and 'a' for alpha return a (surface-width, surface-height) view of a single color component within a surface: a color plane. Color components are unsigned bytes. Both 24-bit and 32-bit surfaces support 'r', 'g', and 'b'. Only 32-bit surfaces with SRCALPHA support 'a'.

The surface is locked only when an exposed interface is accessed. For new buffer interface accesses, the surface is unlocked once the last buffer view is released. For array interface and old buffer interface accesses, the surface remains locked until the BufferProxy object is released.

New in pygame 1.9.2.

get_buffer()
acquires a buffer object for the pixels of the Surface.
get_buffer() -> BufferProxy
Return a buffer object for the pixels of the Surface. The buffer can be used for direct pixel access and manipulation. Surface pixel data is represented as an unstructured block of memory, with a start address and length in bytes. The data need not be contiguous. Any gaps are included in the length, but otherwise ignored.

This method implicitly locks the Surface. The lock will be released when the returned pygame.BufferProxypygame object to export a surface buffer through an array protocol object is garbage collected.

New in pygame 1.8.

_pixels_address
pixel buffer address
_pixels_address -> int
The starting address of the surface's raw pixel bytes.

New in pygame 1.9.2.

premul_alpha()
returns a copy of the surface with the RGB channels pre-multiplied by the alpha channel.
premul_alpha() -> Surface
Returns a copy of the initial surface with the red, green and blue color channels multiplied by the alpha channel. This is intended to make it easier to work with the BLEND_PREMULTIPLED blend mode flag of the blit() method. Surfaces which have called this method will only look correct after blitting if the BLEND_PREMULTIPLED special flag is used.

It is worth noting that after calling this method, methods that return the colour of a pixel such as get_at() will return the alpha multiplied colour values. It is not possible to fully reverse an alpha multiplication of the colours in a surface as integer colour channel data is generally reduced by the operation (e.g. 255 x 0 = 0, from there it is not possible to reconstruct the original 255 from just the two remaining zeros in the colour and alpha channels).

If you call this method, and then call it again, it will multiply the colour channels by the alpha channel twice. There are many possible ways to obtain a surface with the colour channels pre-multiplied by the alpha channel in pygame, and it is not possible to tell the difference just from the information in the pixels. It is completely possible to have two identical surfaces - one intended for pre-multiplied alpha blending and one intended for normal blending. For this reason we do not store state on surfaces intended for pre-multiplied alpha blending.

Surfaces without an alpha channel cannot use this method and will return an error if you use it on them. It is best used on 32 bit surfaces (the default on most platforms) as the blitting on these surfaces can be accelerated by SIMD versions of the pre-multiplied blitter.

In general pre-multiplied alpha blitting is faster then 'straight alpha' blitting and produces superior results when blitting an alpha surface onto another surface with alpha - assuming both surfaces contain pre-multiplied alpha colours.

There is a tutorial on premultiplied alpha blending here. <tutorials/en/premultiplied-alpha>
pygame.sprite
pygame module with basic game object classes
pygame.sprite.Sprite
Simple base class for visible game objects.
pygame.sprite.DirtySprite
A subclass of Sprite with more attributes and features.
pygame.sprite.Group
A container class to hold and manage multiple Sprite objects.
pygame.sprite.RenderUpdates
Group sub-class that tracks dirty updates.
pygame.sprite.LayeredUpdates
LayeredUpdates is a sprite group that handles layers and draws like RenderUpdates.
pygame.sprite.LayeredDirty
LayeredDirty group is for DirtySprite objects. Subclasses LayeredUpdates.
pygame.sprite.GroupSingle
Group container that holds a single sprite.
pygame.sprite.spritecollide
Find sprites in a group that intersect another sprite.
pygame.sprite.collide_rect
Collision detection between two sprites, using rects.
pygame.sprite.collide_rect_ratio
Collision detection between two sprites, using rects scaled to a ratio.
pygame.sprite.collide_circle
Collision detection between two sprites, using circles.
pygame.sprite.collide_circle_ratio
Collision detection between two sprites, using circles scaled to a ratio.
pygame.sprite.collide_mask
Collision detection between two sprites, using masks.
pygame.sprite.groupcollide
Find all sprites that collide between two groups.
pygame.sprite.spritecollideany
Simple test if a sprite intersects anything in a group.
This module contains several simple classes to be used within games. There is the main Sprite class and several Group classes that contain Sprites. The use of these classes is entirely optional when using pygame. The classes are fairly lightweight and only provide a starting place for the code that is common to most games.

The Sprite class is intended to be used as a base class for the different types of objects in the game. There is also a base Group class that simply stores sprites. A game could create new types of Group classes that operate on specially customized Sprite instances they contain.

The basic Group class can draw the Sprites it contains to a Surface. The Group.draw() method requires that each Sprite have a Sprite.image attribute and a Sprite.rect. The Group.clear() method requires these same attributes, and can be used to erase all the Sprites with background. There are also more advanced Groups: pygame.sprite.RenderUpdates().

Lastly, this module contains several collision functions. These help find sprites inside multiple groups that have intersecting bounding rectangles. To find the collisions, the Sprites are required to have a Sprite.rect attribute assigned.

The groups are designed for high efficiency in removing and adding Sprites to them. They also allow cheap testing to see if a Sprite already exists in a Group. A given Sprite can exist in any number of groups. A game could use some groups to control object rendering, and a completely separate set of groups to control interaction or player movement. Instead of adding type attributes or bools to a derived Sprite class, consider keeping the Sprites inside organized Groups. This will allow for easier lookup later in the game.

Sprites and Groups manage their relationships with the add() and remove() methods. These methods can accept a single or multiple targets for membership. The default initializers for these classes also takes a single or list of targets for initial membership. It is safe to repeatedly add and remove the same Sprite from a Group.

While it is possible to design sprite and group classes that don't derive from the Sprite and AbstractGroup classes below, it is strongly recommended that you extend those when you add a Sprite or Group class.

Sprites are not thread safe. So lock them yourself if using threads.

pygame.sprite.Sprite
Simple base class for visible game objects.
Sprite(*groups) -> Sprite
pygame.sprite.Sprite.update
method to control sprite behavior
pygame.sprite.Sprite.add
add the sprite to groups
pygame.sprite.Sprite.remove
remove the sprite from groups
pygame.sprite.Sprite.kill
remove the Sprite from all Groups
pygame.sprite.Sprite.alive
does the sprite belong to any groups
pygame.sprite.Sprite.groups
list of Groups that contain this Sprite
The base class for visible game objects. Derived classes will want to override the Sprite.update() and assign a Sprite.image and Sprite.rect attributes. The initializer can accept any number of Group instances to be added to.

When subclassing the Sprite, be sure to call the base initializer before adding the Sprite to Groups. For example:

class Block(pygame.sprite.Sprite):

    # Constructor. Pass in the color of the block,
    # and its x and y position
    def __init__(self, color, width, height):
       # Call the parent class (Sprite) constructor
       pygame.sprite.Sprite.__init__(self)

       # Create an image of the block, and fill it with a color.
       # This could also be an image loaded from the disk.
       self.image = pygame.Surface([width, height])
       self.image.fill(color)

       # Fetch the rectangle object that has the dimensions of the image
       # Update the position of this object by setting the values of rect.x and rect.y
       self.rect = self.image.get_rect()
update()
method to control sprite behavior
update(*args, **kwargs) -> None
The default implementation of this method does nothing; it's just a convenient "hook" that you can override. This method is called by Group.update() with whatever arguments you give it.

There is no need to use this method if not using the convenience method by the same name in the Group class.

add()
add the sprite to groups
add(*groups) -> None
Any number of Group instances can be passed as arguments. The Sprite will be added to the Groups it is not already a member of.

remove()
remove the sprite from groups
remove(*groups) -> None
Any number of Group instances can be passed as arguments. The Sprite will be removed from the Groups it is currently a member of.

kill()
remove the Sprite from all Groups
kill() -> None
The Sprite is removed from all the Groups that contain it. This won't change anything about the state of the Sprite. It is possible to continue to use the Sprite after this method has been called, including adding it to Groups.

alive()
does the sprite belong to any groups
alive() -> bool
Returns True when the Sprite belongs to one or more Groups.

groups()
list of Groups that contain this Sprite
groups() -> group_list
Return a list of all the Groups that contain this Sprite.

pygame.sprite.DirtySprite
A subclass of Sprite with more attributes and features.
DirtySprite(*groups) -> DirtySprite
Extra DirtySprite attributes with their default values:

dirty = 1

if set to 1, it is repainted and then set to 0 again
if set to 2 then it is always dirty ( repainted each frame,
flag is not reset)
0 means that it is not dirty and therefore not repainted again
blendmode = 0

its the special_flags argument of blit, blendmodes
source_rect = None

source rect to use, remember that it is relative to
topleft (0,0) of self.image
visible = 1

normally 1, if set to 0 it will not be repainted
(you must set it dirty too to be erased from screen)
layer = 0

(READONLY value, it is read when adding it to the
LayeredDirty, for details see doc of LayeredDirty)
pygame.sprite.Group
A container class to hold and manage multiple Sprite objects.
Group(*sprites) -> Group
pygame.sprite.Group.sprites
list of the Sprites this Group contains
pygame.sprite.Group.copy
duplicate the Group
pygame.sprite.Group.add
add Sprites to this Group
pygame.sprite.Group.remove
remove Sprites from the Group
pygame.sprite.Group.has
test if a Group contains Sprites
pygame.sprite.Group.update
call the update method on contained Sprites
pygame.sprite.Group.draw
blit the Sprite images
pygame.sprite.Group.clear
draw a background over the Sprites
pygame.sprite.Group.empty
remove all Sprites
A simple container for Sprite objects. This class can be inherited to create containers with more specific behaviors. The constructor takes any number of Sprite arguments to add to the Group. All sprites in groups are stored in the order they were added to the group. The group supports the following standard Python operations:

in      test if a Sprite is contained
len     the number of Sprites contained
bool    test if any Sprites are contained
iter    iterate through all the Sprites
sprites()
list of the Sprites this Group contains
sprites() -> sprite_list
Return a list of all the Sprites this group contains. You can also get an iterator from the group, but you cannot iterate over a Group while modifying it.

copy()
duplicate the Group
copy() -> Group
Creates a new Group with all the same Sprites as the original. If you have subclassed Group, the new object will have the same (sub-)class as the original. This only works if the derived class's constructor takes the same arguments as the Group class's.

add()
add Sprites to this Group
add(*sprites) -> None
Add any number of Sprites to this Group. This will only add Sprites that are not already members of the Group.

Each sprite argument can also be a iterator containing Sprites.

remove()
remove Sprites from the Group
remove(*sprites) -> None
Remove any number of Sprites from the Group. This will only remove Sprites that are already members of the Group.

Each sprite argument can also be a iterator containing Sprites.

has()
test if a Group contains Sprites
has(*sprites) -> bool
Return True if the Group contains all of the given sprites. This is similar to using the "in" operator on the Group ("if sprite in group: ..."), which tests if a single Sprite belongs to a Group.

Each sprite argument can also be a iterator containing Sprites.

update()
call the update method on contained Sprites
update(*args, **kwargs) -> None
Calls the update() method on all Sprites in the Group. The base Sprite class has an update method that takes any number of arguments and does nothing. The arguments passed to Group.update() will be passed to each Sprite.

There is no way to get the return value from the Sprite.update() methods.

draw()
blit the Sprite images
draw(Surface) -> List[Rect]
Draws the contained Sprites to the Surface argument. This uses the Sprite.image attribute for the source surface, and Sprite.rect for the position.

The Group keeps sprites in the order they were added, they will be drawn in this order.

clear()
draw a background over the Sprites
clear(Surface_dest, background) -> None
Erases the Sprites used in the last Group.draw() call. The destination Surface is cleared by filling the drawn Sprite positions with the background.

The background is usually a Surface image the same dimensions as the destination Surface. However, it can also be a callback function that takes two arguments; the destination Surface and an area to clear. The background callback function will be called several times each clear.

Here is an example callback that will clear the Sprites with solid red:

def clear_callback(surf, rect):
    color = 255, 0, 0
    surf.fill(color, rect)
empty()
remove all Sprites
empty() -> None
Removes all Sprites from this Group.

pygame.sprite.RenderUpdates
Group sub-class that tracks dirty updates.
RenderUpdates(*sprites) -> RenderUpdates
pygame.sprite.RenderUpdates.draw
blit the Sprite images and track changed areas
This class is derived from pygame.sprite.Group(). It has an extended draw() method that tracks the changed areas of the screen.

draw()
blit the Sprite images and track changed areas
draw(surface) -> Rect_list
Draws all the Sprites to the surface, the same as Group.draw(). This method also returns a list of Rectangular areas on the screen that have been changed. The returned changes include areas of the screen that have been affected by previous Group.clear() calls.

The returned Rect list should be passed to pygame.display.update(). This will help performance on software driven display modes. This type of updating is usually only helpful on destinations with non-animating backgrounds.

pygame.sprite.LayeredUpdates
LayeredUpdates is a sprite group that handles layers and draws like RenderUpdates.
LayeredUpdates(*sprites, **kwargs) -> LayeredUpdates
pygame.sprite.LayeredUpdates.add
add a sprite or sequence of sprites to a group
pygame.sprite.LayeredUpdates.sprites
returns a ordered list of sprites (first back, last top).
pygame.sprite.LayeredUpdates.draw
draw all sprites in the right order onto the passed surface.
pygame.sprite.LayeredUpdates.get_sprites_at
returns a list with all sprites at that position.
pygame.sprite.LayeredUpdates.get_sprite
returns the sprite at the index idx from the groups sprites
pygame.sprite.LayeredUpdates.remove_sprites_of_layer
removes all sprites from a layer and returns them as a list.
pygame.sprite.LayeredUpdates.layers
returns a list of layers defined (unique), sorted from bottom up.
pygame.sprite.LayeredUpdates.change_layer
changes the layer of the sprite
pygame.sprite.LayeredUpdates.get_layer_of_sprite
returns the layer that sprite is currently in.
pygame.sprite.LayeredUpdates.get_top_layer
returns the top layer
pygame.sprite.LayeredUpdates.get_bottom_layer
returns the bottom layer
pygame.sprite.LayeredUpdates.move_to_front
brings the sprite to front layer
pygame.sprite.LayeredUpdates.move_to_back
moves the sprite to the bottom layer
pygame.sprite.LayeredUpdates.get_top_sprite
returns the topmost sprite
pygame.sprite.LayeredUpdates.get_sprites_from_layer
returns all sprites from a layer, ordered by how they where added
pygame.sprite.LayeredUpdates.switch_layer
switches the sprites from layer1 to layer2
This group is fully compatible with pygame.sprite.SpriteSimple base class for visible game objects..

You can set the default layer through kwargs using 'default_layer' and an integer for the layer. The default layer is 0.

If the sprite you add has an attribute _layer then that layer will be used. If the **kwarg contains 'layer' then the sprites passed will be added to that layer (overriding the sprite.layer attribute). If neither sprite has attribute layer nor **kwarg then the default layer is used to add the sprites.

New in pygame 1.8.

add()
add a sprite or sequence of sprites to a group
add(*sprites, **kwargs) -> None
If the sprite(s) have an attribute layer then that is used for the layer. If **kwargs contains 'layer' then the sprite(s) will be added to that argument (overriding the sprite layer attribute). If neither is passed then the sprite(s) will be added to the default layer.

sprites()
returns a ordered list of sprites (first back, last top).
sprites() -> sprites
draw()
draw all sprites in the right order onto the passed surface.
draw(surface) -> Rect_list
get_sprites_at()
returns a list with all sprites at that position.
get_sprites_at(pos) -> colliding_sprites
Bottom sprites first, top last.

get_sprite()
returns the sprite at the index idx from the groups sprites
get_sprite(idx) -> sprite
Raises IndexOutOfBounds if the idx is not within range.

remove_sprites_of_layer()
removes all sprites from a layer and returns them as a list.
remove_sprites_of_layer(layer_nr) -> sprites
layers()
returns a list of layers defined (unique), sorted from bottom up.
layers() -> layers
change_layer()
changes the layer of the sprite
change_layer(sprite, new_layer) -> None
sprite must have been added to the renderer. It is not checked.

get_layer_of_sprite()
returns the layer that sprite is currently in.
get_layer_of_sprite(sprite) -> layer
If the sprite is not found then it will return the default layer.

get_top_layer()
returns the top layer
get_top_layer() -> layer
get_bottom_layer()
returns the bottom layer
get_bottom_layer() -> layer
move_to_front()
brings the sprite to front layer
move_to_front(sprite) -> None
Brings the sprite to front, changing sprite layer to topmost layer (added at the end of that layer).

move_to_back()
moves the sprite to the bottom layer
move_to_back(sprite) -> None
Moves the sprite to the bottom layer, moving it behind all other layers and adding one additional layer.

get_top_sprite()
returns the topmost sprite
get_top_sprite() -> Sprite
get_sprites_from_layer()
returns all sprites from a layer, ordered by how they where added
get_sprites_from_layer(layer) -> sprites
Returns all sprites from a layer, ordered by how they where added. It uses linear search and the sprites are not removed from layer.

switch_layer()
switches the sprites from layer1 to layer2
switch_layer(layer1_nr, layer2_nr) -> None
The layers number must exist, it is not checked.

pygame.sprite.LayeredDirty
LayeredDirty group is for DirtySprite objects. Subclasses LayeredUpdates.
LayeredDirty(*sprites, **kwargs) -> LayeredDirty
pygame.sprite.LayeredDirty.draw
draw all sprites in the right order onto the passed surface.
pygame.sprite.LayeredDirty.clear
used to set background
pygame.sprite.LayeredDirty.repaint_rect
repaints the given area
pygame.sprite.LayeredDirty.set_clip
clip the area where to draw. Just pass None (default) to reset the clip
pygame.sprite.LayeredDirty.get_clip
clip the area where to draw. Just pass None (default) to reset the clip
pygame.sprite.LayeredDirty.change_layer
changes the layer of the sprite
pygame.sprite.LayeredDirty.set_timing_treshold
sets the threshold in milliseconds
pygame.sprite.LayeredDirty.set_timing_threshold
sets the threshold in milliseconds
This group requires pygame.sprite.DirtySpriteA subclass of Sprite with more attributes and features. or any sprite that has the following attributes:

image, rect, dirty, visible, blendmode (see doc of DirtySprite).
It uses the dirty flag technique and is therefore faster than the pygame.sprite.RenderUpdatesGroup sub-class that tracks dirty updates. if you have many static sprites. It also switches automatically between dirty rect update and full screen drawing, so you do not have to worry what would be faster.

Same as for the pygame.sprite.GroupA container class to hold and manage multiple Sprite objects.. You can specify some additional attributes through kwargs:

_use_update: True/False   default is False
_default_layer: default layer where sprites without a layer are added.
_time_threshold: threshold time for switching between dirty rect mode
    and fullscreen mode, defaults to 1000./80  == 1000./fps
New in pygame 1.8.

draw()
draw all sprites in the right order onto the passed surface.
draw(surface, bgd=None) -> Rect_list
You can pass the background too. If a background is already set, then the bgd argument has no effect.

clear()
used to set background
clear(surface, bgd) -> None
repaint_rect()
repaints the given area
repaint_rect(screen_rect) -> None
screen_rect is in screen coordinates.

set_clip()
clip the area where to draw. Just pass None (default) to reset the clip
set_clip(screen_rect=None) -> None
get_clip()
clip the area where to draw. Just pass None (default) to reset the clip
get_clip() -> Rect
change_layer()
changes the layer of the sprite
change_layer(sprite, new_layer) -> None
sprite must have been added to the renderer. It is not checked.

set_timing_treshold()
sets the threshold in milliseconds
set_timing_treshold(time_ms) -> None
DEPRECATED: Use set_timing_threshold() instead.

Deprecated since pygame 2.1.1.

set_timing_threshold()
sets the threshold in milliseconds
set_timing_threshold(time_ms) -> None
Defaults to 1000.0 / 80.0. This means that the screen will be painted using the flip method rather than the update method if the update method is taking so long to update the screen that the frame rate falls below 80 frames per second.

New in pygame 2.1.1.

Raises:
TypeError -- if time_ms is not int or float

pygame.sprite.GroupSingle()
Group container that holds a single sprite.
GroupSingle(sprite=None) -> GroupSingle
The GroupSingle container only holds a single Sprite. When a new Sprite is added, the old one is removed.

There is a special property, GroupSingle.sprite, that accesses the Sprite that this Group contains. It can be None when the Group is empty. The property can also be assigned to add a Sprite into the GroupSingle container.

pygame.sprite.spritecollide()
Find sprites in a group that intersect another sprite.
spritecollide(sprite, group, dokill, collided = None) -> Sprite_list
Return a list containing all Sprites in a Group that intersect with another Sprite. Intersection is determined by comparing the Sprite.rect attribute of each Sprite.

The dokill argument is a bool. If set to True, all Sprites that collide will be removed from the Group.

The collided argument is a callback function used to calculate if two sprites are colliding. it should take two sprites as values, and return a bool value indicating if they are colliding. If collided is not passed, all sprites must have a "rect" value, which is a rectangle of the sprite area, which will be used to calculate the collision.

collided callables:

collide_rect, collide_rect_ratio, collide_circle,
collide_circle_ratio, collide_mask
Example:

# See if the Sprite block has collided with anything in the Group block_list
# The True flag will remove the sprite in block_list
blocks_hit_list = pygame.sprite.spritecollide(player, block_list, True)

# Check the list of colliding sprites, and add one to the score for each one
for block in blocks_hit_list:
    score +=1
pygame.sprite.collide_rect()
Collision detection between two sprites, using rects.
collide_rect(left, right) -> bool
Tests for collision between two sprites. Uses the pygame rect colliderect function to calculate the collision. Intended to be passed as a collided callback function to the *collide functions. Sprites must have a "rect" attributes.

New in pygame 1.8.

pygame.sprite.collide_rect_ratio()
Collision detection between two sprites, using rects scaled to a ratio.
collide_rect_ratio(ratio) -> collided_callable
A callable class that checks for collisions between two sprites, using a scaled version of the sprites rects.

Is created with a ratio, the instance is then intended to be passed as a collided callback function to the *collide functions.

A ratio is a floating point number - 1.0 is the same size, 2.0 is twice as big, and 0.5 is half the size.

New in pygame 1.8.1.

pygame.sprite.collide_circle()
Collision detection between two sprites, using circles.
collide_circle(left, right) -> bool
Tests for collision between two sprites, by testing to see if two circles centered on the sprites overlap. If the sprites have a "radius" attribute, that is used to create the circle, otherwise a circle is created that is big enough to completely enclose the sprites rect as given by the "rect" attribute. Intended to be passed as a collided callback function to the *collide functions. Sprites must have a "rect" and an optional "radius" attribute.

New in pygame 1.8.1.

pygame.sprite.collide_circle_ratio()
Collision detection between two sprites, using circles scaled to a ratio.
collide_circle_ratio(ratio) -> collided_callable
A callable class that checks for collisions between two sprites, using a scaled version of the sprites radius.

Is created with a floating point ratio, the instance is then intended to be passed as a collided callback function to the *collide functions.

A ratio is a floating point number - 1.0 is the same size, 2.0 is twice as big, and 0.5 is half the size.

The created callable tests for collision between two sprites, by testing to see if two circles centered on the sprites overlap, after scaling the circles radius by the stored ratio. If the sprites have a "radius" attribute, that is used to create the circle, otherwise a circle is created that is big enough to completely enclose the sprites rect as given by the "rect" attribute. Intended to be passed as a collided callback function to the *collide functions. Sprites must have a "rect" and an optional "radius" attribute.

New in pygame 1.8.1.

pygame.sprite.collide_mask()
Collision detection between two sprites, using masks.
collide_mask(sprite1, sprite2) -> (int, int)
collide_mask(sprite1, sprite2) -> None
Tests for collision between two sprites, by testing if their bitmasks overlap (uses pygame.mask.Mask.overlap()Returns the point of intersection). If the sprites have a mask attribute, it is used as the mask, otherwise a mask is created from the sprite's image (uses pygame.mask.from_surface()Creates a Mask from the given surface). Sprites must have a rect attribute; the mask attribute is optional.

The first point of collision between the masks is returned. The collision point is offset from sprite1's mask's topleft corner (which is always (0, 0)). The collision point is a position within the mask and is not related to the actual screen position of sprite1.

This function is intended to be passed as a collided callback function to the group collide functions (see spritecollide(), groupcollide(), spritecollideany()).

Note To increase performance, create and set a mask attribute for all sprites that will use this function to check for collisions. Otherwise, each time this function is called it will create new masks.
Note A new mask needs to be recreated each time a sprite's image is changed (e.g. if a new image is used or the existing image is rotated).
# Example of mask creation for a sprite.
sprite.mask = pygame.mask.from_surface(sprite.image)
Returns:
first point of collision between the masks or None if no collision

Return type:
tuple(int, int) or NoneType

New in pygame 1.8.0.

pygame.sprite.groupcollide()
Find all sprites that collide between two groups.
groupcollide(group1, group2, dokill1, dokill2, collided = None) -> Sprite_dict
This will find collisions between all the Sprites in two groups. Collision is determined by comparing the Sprite.rect attribute of each Sprite or by using the collided function if it is not None.

Every Sprite inside group1 is added to the return dictionary. The value for each item is the list of Sprites in group2 that intersect.

If either dokill argument is True, the colliding Sprites will be removed from their respective Group.

The collided argument is a callback function used to calculate if two sprites are colliding. It should take two sprites as values and return a bool value indicating if they are colliding. If collided is not passed, then all sprites must have a "rect" value, which is a rectangle of the sprite area, which will be used to calculate the collision.

pygame.sprite.spritecollideany()
Simple test if a sprite intersects anything in a group.
spritecollideany(sprite, group, collided = None) -> Sprite Collision with the returned sprite.
spritecollideany(sprite, group, collided = None) -> None No collision
If the sprite collides with any single sprite in the group, a single sprite from the group is returned. On no collision None is returned.

If you don't need all the features of the pygame.sprite.spritecollide() function, this function will be a bit quicker.

The collided argument is a callback function used to calculate if two sprites are colliding. It should take two sprites as values and return a bool value indicating if they are colliding. If collided is not passed, then all sprites must have a "rect" value, which is a rectangle of the sprite area, which will be used to calculate the collision.