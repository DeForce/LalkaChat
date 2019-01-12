from cefpython3 import cefpython
import platform
import wx

DEFAULT_TIMER_MILLIS = 10


class ChromeWindow(wx.Window):
    """
    Standalone CEF component. The class provides facilites for interacting
    with wx message loop
    """

    def __init__(self, parent, url="", use_timer=True, browser_settings=None,
                 size=(-1, -1), *args, **kwargs):
        wx.Window.__init__(self, parent, id=wx.ID_ANY, size=size,
                           *args, **kwargs)

        # This timer is not used anymore, but creating it for backwards
        # compatibility. In one of external projects ChromeWindow.timer.Stop()
        # is being called during browser destruction.
        self.timer = wx.Timer()

        # On Linux absolute file urls need to start with "file://"
        # otherwise a path of "/home/some" is converted to "http://home/some".
        if platform.system() in ["Linux", "Darwin"]:
            if url.startswith("/"):
                url = "file://" + url
        self.url = url

        window_info = cefpython.WindowInfo()
        window_info.SetAsChild(self.GetHandle())

        if not browser_settings:
            browser_settings = {}

        self.browser = cefpython.CreateBrowserSync(
            window_info,
            browserSettings=browser_settings, navigateUrl=url)

        if platform.system() == "Windows":
            self.Bind(wx.EVT_SET_FOCUS, self.on_set_focus)
            self.Bind(wx.EVT_SIZE, self.on_size)

        self._useTimer = use_timer
        self.Bind(wx.EVT_IDLE, self.on_idle)

        self.Bind(wx.EVT_CLOSE, self.on_close)

    def on_close(self, event):
        if not self._useTimer:
            try:
                self.Unbind(wx.EVT_IDLE)
            except:
                # Calling Unbind() may cause problems on Windows 8:
                # https://groups.google.com/d/topic/cefpython/iXE7e1ekArI/discussion
                # (it was causing problems in __del__, this might not
                #  be true anymore in OnClose, but still let's make sure)
                pass
        self.browser.ParentWindowWillClose()

    def on_idle(self, event):
        """Service CEF message loop when useTimer is False"""
        cefpython.MessageLoopWork()
        event.Skip()

    def on_set_focus(self, event):
        """OS_WIN only."""
        cefpython.WindowUtils.OnSetFocus(self.GetHandle(), 0, 0, 0)
        event.Skip()

    def on_size(self, event):
        """OS_WIN only. Handle the the size event"""
        cefpython.WindowUtils.OnSize(self.GetHandle(), 0, 0, 0)
        event.Skip()

    def get_browser(self):
        """Returns the CEF's browser object"""
        return self.browser

    def load_url(self, url):
        self.get_browser().GetMainFrame().load_url(url)


class ChromeCtrl(wx.Panel):
    def __init__(self, parent, url="", use_timer=True,
                 browser_settings=None, *args, **kwargs):
        # You also have to set the wx.WANTS_CHARS style for
        # all parent panels/controls, if it's deeply embedded.
        wx.Panel.__init__(self, parent, style=wx.WANTS_CHARS, *args, **kwargs)

        self.chromeWindow = ChromeWindow(self, url=str(url), use_timer=use_timer,
                                         browser_settings=browser_settings)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.navigationBar = None

        sizer.Add(self.chromeWindow, 1, wx.EXPAND, 0)

        self.SetSizer(sizer)
        self.Fit()

        ch = DefaultClientHandler(self)
        self.set_client_handler(ch)

    def set_client_handler(self, handler):
        self.chromeWindow.get_browser().SetClientHandler(handler)

    def on_load_start(self, browser, frame):
        pass

    def on_load_end(self, browser, frame, http_code):
        pass


class DefaultClientHandler(object):
    def __init__(self, parent_ctrl):
        self.parentCtrl = parent_ctrl

    def OnLoadStart(self, browser, frame):
        self.parentCtrl.on_load_start(browser, frame)

    def OnLoadEnd(self, browser, frame, http_code=None):
        self.parentCtrl.on_load_end(browser, frame, http_code=http_code)

    def OnLoadError(self, browser, frame, errorCode, errorText, failedUrl):
        pass


class CallbackClientHandler(object):
    def __init__(self, onLoadStart=None, onLoadEnd=None):
        self._onLoadStart = onLoadStart
        self._onLoadEnd = onLoadEnd

    def OnLoadStart(self, browser, frame):
        if self._onLoadStart and frame.GetUrl() != "about:blank":
            self._onLoadStart(browser, frame)

    def OnLoadEnd(self, browser, frame, httpStatusCode):
        if self._onLoadEnd and frame.GetUrl() != "about:blank":
            self._onLoadEnd(browser, frame, httpStatusCode)

    def OnLoadError(self, browser, frame, errorCode, errorText, failedUrl):
        pass


def initialize(settings=None, debug=False):
    """Initializes CEF, We should do it before initializing wx
       If no settings passed a default is used
    """
    switches = {}
    global g_settings
    if not settings:
        settings = {}

    if "log_severity" not in settings:
        settings["log_severity"] = cefpython.LOGSEVERITY_ERROR
    if "log_file" not in settings:
        settings["log_file"] = ""

    if "browser_subprocess_path" not in settings:
        settings["browser_subprocess_path"] = \
            "%s/%s" % (cefpython.GetModuleDirectory(), "subprocess")

    if debug:
        settings["debug"] = True  # cefpython messages in console and log_file
        settings["log_severity"] = cefpython.LOGSEVERITY_VERBOSE
        settings["log_file"] = "debug.log"  # Set to "" to disable.

    g_settings = settings
    cefpython.Initialize(settings, switches)


def shutdown():
    """Shuts down CEF, should be called by app exiting code"""
    cefpython.Shutdown()
